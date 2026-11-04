"""Explicit RADIAN preparation/submission, exact bytes and connection ownership."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore.catalogs import EventType, RadianOperationType
from radiankore.exceptions import (
    DianResponseError,
    DianSoapFaultError,
    DianTransportError,
)
from radiankore.models.events import (
    MandateEvent,
    MandateTerminationEvent,
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)
from tests.event_notes import additional_notes
from tests.event_support import assert_submitted_event, install_sync_http, result_xml


@pytest.mark.parametrize(
    "variant",
    [op.value for op in RadianOperationType]
    + ["371-blank", "372-blank", "038-blank", "039-blank"],
)
@pytest.mark.parametrize("environment", list(Environment))
def test_all_event_codes_submit_the_original_archive_once(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    wrap_soap: Callable[[etree._Element], bytes],
    digital_certificate: DigitalCertificate,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
    environment: Environment,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=result_xml(wrap_soap))

    clients = install_sync_http(monkeypatch, handler)

    client = DianClient(
        encrypted_pfx_path, password="test-password", environment=environment
    )
    with monkeypatch.context() as patch:

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("Preparation must not access files.")

        for method in ("read_bytes", "read_text", "write_bytes", "write_text"):
            patch.setattr(Path, method, forbidden)
        prepared = client.prepare_radian_event(
            event=radian_event_factory(variant), software=radian_software
        )
    assert not clients
    assert "xml_bytes=" not in repr(prepared) and "zip_bytes=" not in repr(prepared)
    assert "synthetic-pin" not in repr(radian_software)
    result = client.send_radian_event(prepared)
    assert (
        result is not None and result.is_valid is False and result.status_code == "99"
    )
    assert_submitted_event(prepared, requests, clients, digital_certificate)


def test_artifact_types_environments_and_invalid_inputs_prevent_network(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    mandate_event: MandateEvent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prod = DianClient(encrypted_pfx_path, password="test-password")
    hab = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=Environment.HABILITATION,
    )
    prepared = hab.prepare_radian_event(
        event=radian_event_factory("441"), software=radian_software
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Invalid inputs must not reach the network.")

    monkeypatch.setattr(transport, "create_http_client", forbidden)
    with pytest.raises(ValueError, match="environment"):
        prod.send_radian_event(prepared)
    with pytest.raises(TypeError, match="PreparedRadianEvent"):
        prod.send_radian_event(mandate_event)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="RadianSoftware"):
        prod.prepare_radian_event(event=radian_event_factory("441"), software=None)  # type: ignore[arg-type]
    for invalid in (
        None,
        "044",
        object(),
    ):
        with pytest.raises(TypeError, match="RadianEvent"):
            prod.prepare_radian_event(event=invalid, software=radian_software)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Unsupported"):
        replace(prepared, code=EventType.DIAN_VALIDATED)
    with pytest.raises(TypeError, match="EventType"):
        replace(prepared, code="044")  # type: ignore[arg-type]
    assert isinstance(prepared, PreparedRadianEvent)


@pytest.mark.parametrize(
    "failure", ["network", "connect", "http", "soap", "soap200", "parsing"]
)
def test_failures_are_not_retried_and_connections_close(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    soap_fault: bytes,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if failure == "network":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if failure == "connect":
            raise httpx.ConnectError("synthetic connect failure", request=request)
        if failure in {"soap", "soap200"}:
            return httpx.Response(
                200 if failure == "soap200" else 500, content=soap_fault
            )
        return httpx.Response(200 if failure == "parsing" else 500, content=b"invalid")

    clients = install_sync_http(monkeypatch, handle)

    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = client.prepare_radian_event(
        event=radian_event_factory("371-blank"), software=radian_software
    )
    error = (
        DianSoapFaultError
        if failure in {"soap", "soap200"}
        else (DianResponseError if failure == "parsing" else DianTransportError)
    )
    with pytest.raises(error):
        client.send_radian_event(prepared)
    assert len(clients) == len(requests) == 1 and clients[0].is_closed


@pytest.mark.parametrize("kind", ["nil", "empty"])
def test_optional_result_contract(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    monkeypatch.setattr(
        transport,
        "create_http_client",
        lambda timeout: httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=result_xml(wrap_soap, kind))
            ),
            timeout=timeout,
        ),
    )
    client = DianClient(encrypted_pfx_path, password="test-password")
    result = client.send_radian_event(
        client.prepare_radian_event(
            event=radian_event_factory("441"),
            software=radian_software,
        )
    )
    if kind == "nil":
        assert result is None
    else:
        assert result is not None and result.is_valid is None and result.messages == ()


def test_size_limit_and_no_fe_same_day_restriction(
    radian_event_factory: Callable[[str], RadianEvent],
    encrypted_pfx_path: Path,
    radian_software: RadianSoftware,
) -> None:
    event = radian_event_factory("441")
    assert isinstance(event, MandateTerminationEvent)
    client = DianClient(encrypted_pfx_path, password="test-password")
    # The fixed historical issue date remains valid for this RADIAN profile.
    client.prepare_radian_event(event=event, software=radian_software)
    oversized = replace(
        event,
        header=replace(
            event.header,
            notes=event.header.notes + additional_notes(*("x" * 5000,) * 101),
        ),
    )
    with pytest.raises(ValueError, match="500,000"):
        client.prepare_radian_event(event=oversized, software=radian_software)
