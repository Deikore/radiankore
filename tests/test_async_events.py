"""All async event families preserve serialized signatures and original ZIP bytes."""

import asyncio
from base64 import b64decode
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import httpx
import pytest
from lxml import etree

from radiankore import (
    AsyncDianClient,
    DianTransportError,
    DigitalCertificate,
    Environment,
)
from radiankore._soap.namespaces import WCF
from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events import (
    InvoiceResponseEvent,
    MandateEvent,
    RadianEvent,
    RadianSoftware,
)
from tests.async_support import install_http
from tests.test_send_radian_event import result_xml
from tests.test_signing import _verify


@pytest.mark.parametrize(
    "variant",
    [op.value for op in RadianOperationType]
    + ["371-blank", "372-blank", "038-blank", "039-blank", "mandate"]
    + ["invoice:" + code for code in ("030", "031", "032", "033", "034")],
)
@pytest.mark.parametrize("environment", list(Environment))
def test_async_prepare_and_single_send(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    radian_event_factory: Callable[[str], RadianEvent],
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    wrap_soap: Callable[[etree._Element], bytes],
    variant: str,
    environment: Environment,
) -> None:
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        _verify(request.content, digital_certificate)
        return httpx.Response(200, content=result_xml(wrap_soap))

    clients = install_http(monkeypatch, handle)
    event: RadianEvent
    if variant.startswith("invoice:"):
        event = replace(
            invoice_event_factory(EventType(variant.split(":")[1])),
            issue_date=datetime.now(ZoneInfo("America/Bogota")).date(),
        )
    elif variant == "mandate":
        event = mandate_event
    else:
        event = radian_event_factory(variant)

    async def exercise() -> None:
        async with AsyncDianClient(
            digital_certificate, environment=environment
        ) as client:
            prepared = await client.prepare_radian_event(
                event=event, software=radian_software
            )
            assert not clients
            verify_event_signature(prepared.xml_bytes, digital_certificate)
            with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
                assert archive.namelist() == [f"ar_{prepared.cude}.xml"]
                assert archive.read(archive.namelist()[0]) == prepared.xml_bytes
            result = await client.send_radian_event(prepared)
            assert result is not None and result.is_valid is False
            assert result.status_code == "99"
            assert len(requests) == 1
            root = etree.fromstring(requests[0].content)
            encoded = root.findtext(f".//{{{WCF}}}contentFile")
            assert encoded and b64decode(encoded) == prepared.zip_bytes
            with pytest.raises(ValueError, match="environment"):
                await client.send_radian_event(
                    replace(
                        prepared,
                        environment=(
                            Environment.HABILITATION
                            if environment is Environment.PRODUCTION
                            else Environment.PRODUCTION
                        ),
                    )
                )
            assert len(requests) == 1
        assert all(c.is_closed for c in clients)

    asyncio.run(exercise())


def test_uncertain_send_never_retries(
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("after synthetic send", request=request)

    clients = install_http(monkeypatch, handle)

    async def exercise() -> None:
        async with AsyncDianClient(digital_certificate) as client:
            prepared = await client.prepare_radian_event(
                event=radian_event_factory("441"), software=radian_software
            )
            with pytest.raises(DianTransportError):
                await client.send_radian_event(prepared)
        assert calls == 1 and clients[0].is_closed

    asyncio.run(exercise())
