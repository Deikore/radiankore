"""Local preparation, exact-byte submission and failures without any live service."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, time
from pathlib import Path

import httpx
import pytest
from lxml import etree

import radiankore._soap.operations as operations_module
from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore._soap.namespaces import CBC, RESPONSE, WCF, XADES
from radiankore.catalogs import EventType
from radiankore.models.events import (
    InvoiceResponseEvent,
    RadianSoftware,
)
from tests.event_notes import additional_notes
from tests.event_support import assert_submitted_event, install_sync_http


@pytest.fixture
def invoice_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Freeze the real signing clock, not the event's supplied issue date."""

    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            assert tz is UTC
            return datetime(2026, 10, 22, 18, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(operations_module, "datetime", Clock)


def send_result(wrap: Callable[[etree._Element], bytes]) -> bytes:
    """Return a synthetic business rejection, which must remain response data."""
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    result = etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult")
    for name, value in (("IsValid", "false"), ("StatusCode", "99")):
        etree.SubElement(result, f"{{{RESPONSE}}}{name}").text = value
    return wrap(response)


@pytest.mark.parametrize("code", ["030", "031", "032", "033", "034"])
@pytest.mark.parametrize("environment", list(Environment))
def test_prepare_and_send_original_bytes(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    invoice_clock: None,
    monkeypatch: pytest.MonkeyPatch,
    wrap_soap: Callable[[etree._Element], bytes],
    code: str,
    environment: Environment,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=send_result(wrap_soap))

    clients = install_sync_http(monkeypatch, handler)

    client = DianClient(
        encrypted_pfx_path, password="test-password", environment=environment
    )
    event = invoice_event_factory(EventType(code))
    with monkeypatch.context() as patch:

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError(
                "Preparation must neither reload files nor write them."
            )

        for method in ("read_bytes", "read_text", "write_bytes", "write_text"):
            patch.setattr(Path, method, forbidden)
        prepared = client.prepare_radian_event(event=event, software=radian_software)
    assert not clients
    assert prepared.code is event.code and prepared.environment is environment
    assert "xml_bytes=" not in repr(prepared) and "zip_bytes=" not in repr(prepared)
    assert "synthetic-pin" not in repr(radian_software)
    parsed = etree.fromstring(prepared.xml_bytes)
    assert parsed.findtext(f".//{{{XADES}}}SigningTime") == "2026-10-22T18:00:00Z"
    assert parsed.findtext(f"{{{CBC}}}IssueDate") == "2026-10-22"
    result = client.send_radian_event(prepared)
    assert (
        result is not None and result.is_valid is False and result.status_code == "99"
    )
    assert_submitted_event(prepared, requests, clients, digital_certificate)


def test_mismatched_environment_and_event_types_prevent_network(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    invoice_clock: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prod = DianClient(encrypted_pfx_path, password="test-password")
    hab = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=Environment.HABILITATION,
    )
    event = invoice_event_factory(EventType.EXPRESS_ACCEPTANCE)
    prepared = hab.prepare_radian_event(event=event, software=radian_software)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Invalid artifacts must not access the network.")

    monkeypatch.setattr(transport, "create_http_client", forbidden)
    with pytest.raises(ValueError, match="environment"):
        prod.send_radian_event(prepared)
    with pytest.raises(TypeError, match="PreparedRadianEvent"):
        prod.send_radian_event(event)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RadianEvent"):
        prod.prepare_radian_event(event=None, software=radian_software)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RadianSoftware"):
        prod.prepare_radian_event(event=event, software=None)  # type: ignore[arg-type]


def test_signing_date_and_size_limits(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    invoice_clock: None,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    event = invoice_event_factory(EventType.EXPRESS_ACCEPTANCE)
    with pytest.raises(ValueError, match="signing date"):
        client.prepare_radian_event(
            event=replace(event, issue_date=date(2026, 10, 21)),
            software=radian_software,
        )
    # Same Colombian date despite a different date supplied in UTC.
    prepared = client.prepare_radian_event(
        event=replace(
            event, issue_date=date(2026, 10, 23), issue_time=time(2, 30, tzinfo=UTC)
        ),
        software=radian_software,
    )
    assert (
        b"2026-10-22" in prepared.xml_bytes and b"21:30:00-05:00" in prepared.xml_bytes
    )
    with pytest.raises(ValueError, match="500,000"):
        client.prepare_radian_event(
            event=replace(
                event, notes=event.notes + additional_notes(*("x" * 10_000,) * 51)
            ),
            software=radian_software,
        )


def test_colombian_signing_date_at_utc_midnight(
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            return datetime(2026, 10, 23, 2, 0, tzinfo=UTC)

    monkeypatch.setattr(operations_module, "datetime", Clock)
    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = client.prepare_radian_event(
        event=invoice_event_factory(EventType.EXPRESS_ACCEPTANCE),
        software=radian_software,
    )
    root = etree.fromstring(prepared.xml_bytes)
    assert root.findtext(f"{{{CBC}}}IssueDate") == "2026-10-22"
    assert root.findtext(f".//{{{XADES}}}SigningTime") == "2026-10-23T02:00:00Z"
