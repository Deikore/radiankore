"""Synthetic submission responses shared by event families."""

from base64 import b64decode
from collections.abc import Callable
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
from lxml import etree

from radiankore import DigitalCertificate
from radiankore._soap import transport
from radiankore._soap.namespaces import RESPONSE, WCF, XSI
from radiankore.models.events import PreparedRadianEvent
from tests.signature_support import verify_signature


def result_xml(
    wrap: Callable[[etree._Element], bytes], kind: str = "rejection"
) -> bytes:
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    result = etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult")
    if kind == "nil":
        result.set(f"{{{XSI}}}nil", "true")
    elif kind == "rejection":
        for name, value in (("IsValid", "false"), ("StatusCode", "99")):
            etree.SubElement(result, f"{{{RESPONSE}}}{name}").text = value
    return wrap(response)


def install_sync_http(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Client]:
    """Capture ownership while replacing only the HTTP transport boundary."""
    clients: list[httpx.Client] = []

    def factory(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", factory)
    return clients


def assert_submitted_event(
    prepared: PreparedRadianEvent,
    requests: list[httpx.Request],
    clients: list[httpx.Client],
    certificate: DigitalCertificate,
) -> None:
    """Verify one signed submission of the original archive and resource closure."""
    assert len(clients) == len(requests) == 1 and clients[0].is_closed
    request = requests[0]
    assert request.url == prepared.environment.endpoint
    assert "SendEventUpdateStatus" in request.headers["Content-Type"]
    encoded = etree.fromstring(request.content).findtext(f".//{{{WCF}}}contentFile")
    assert encoded is not None and b64decode(encoded) == prepared.zip_bytes
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.namelist() == [f"ar_{prepared.cude}.xml"]
        assert archive.read(archive.namelist()[0]) == prepared.xml_bytes
    verify_signature(prepared.xml_bytes, certificate)
    verify_signature(request.content, certificate)
