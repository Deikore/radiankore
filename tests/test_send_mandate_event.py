"""Explicit preparation and submission, independent of any live DIAN service."""

from base64 import b64decode, b64encode
from collections.abc import Callable
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore._soap.events import parse_send_event_response
from radiankore._soap.namespaces import ARRAY, CBC, DS, RESPONSE, WCF, XSI
from radiankore.catalogs import MandateChannel, MandateOperationType, MandatePower
from radiankore.exceptions import (
    DianResponseError,
    DianSoapFaultError,
    DianTransportError,
)
from radiankore.models.events import (
    MandateEvent,
    MandateScope,
    MandateValidityPeriod,
    RadianSoftware,
)
from radiankore.models.responses import SendEventResult


def result_xml(
    fields: dict[str, str | None],
    wrap: Callable[[etree._Element], bytes],
    *,
    messages: bool = False,
) -> bytes:
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    result = etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult")
    for name, value in fields.items():
        node = etree.SubElement(result, f"{{{RESPONSE}}}{name}")
        if value is None:
            node.set(f"{{{XSI}}}nil", "true")
        else:
            node.text = value
    if messages:
        errors = etree.SubElement(result, f"{{{RESPONSE}}}ErrorMessage")
        for value in ("Rejected", "Rejected", ""):
            etree.SubElement(errors, f"{{{ARRAY}}}string").text = value
    return wrap(response)


@pytest.mark.parametrize("environment", list(Environment))
@pytest.mark.parametrize("operation", list(MandateOperationType))
def test_prepare_and_send_exact_bytes(
    encrypted_pfx_path: Path,
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
    wrap_soap: Callable[[etree._Element], bytes],
    digital_certificate: DigitalCertificate,
    environment: Environment,
    operation: MandateOperationType,
) -> None:
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            content=result_xml(
                {
                    "IsValid": "false",
                    "StatusCode": "99",
                    "StatusDescription": "Rejected",
                    "StatusMessage": "Synthetic rejection",
                    "XmlDocumentKey": "key",
                    "XmlFileName": "result.xml",
                    "XmlBase64Bytes": b64encode(b"first").decode(),
                    "XmlBytes": b64encode(b"second").decode(),
                },
                wrap_soap,
                messages=True,
            ),
        )

    def factory(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", factory)
    client = DianClient(
        encrypted_pfx_path, password="test-password", environment=environment
    )
    mandate_event = replace(
        mandate_event,
        operation_type=operation,
        validity_period=(
            mandate_event.validity_period
            if operation
            in (
                MandateOperationType.GENERAL_LIMITED_TIME,
                MandateOperationType.LIMITED_LIMITED_TIME,
            )
            else MandateValidityPeriod()
        ),
        scope=(
            mandate_event.scope
            if operation
            in (
                MandateOperationType.GENERAL_LIMITED_TIME,
                MandateOperationType.GENERAL_UNLIMITED_TIME,
            )
            else MandateScope(
                powers=(
                    (
                        MandatePower.WITH_REPRESENTATION,
                        MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
                    ),
                    (
                        MandatePower.ACKNOWLEDGEMENT,
                        MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
                    ),
                )
            )
        ),
    )
    # All PFX loading has already happened. Preparation must neither connect nor write.
    with monkeypatch.context() as patch:

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("Preparation must not access files.")

        for method in ("read_bytes", "read_text", "write_bytes", "write_text"):
            patch.setattr(Path, method, forbidden)
        prepared = client.prepare_radian_event(
            event=mandate_event, software=radian_software
        )
    assert not clients
    assert "xml_bytes=" not in repr(prepared) and "zip_bytes=" not in repr(prepared)
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.namelist() == [f"ar_{prepared.cude}.xml"]
        assert archive.read(archive.namelist()[0]) == prepared.xml_bytes
    assert (
        etree.fromstring(prepared.xml_bytes).findtext(f"{{{CBC}}}UUID") == prepared.cude
    )
    result = client.send_radian_event(prepared)
    assert result == SendEventResult(
        is_valid=False,
        status_code="99",
        status_description="Rejected",
        status_message="Synthetic rejection",
        messages=("Rejected", "Rejected", ""),
        document_key="key",
        file_name="result.xml",
        xml_base64_bytes=b"first",
        xml_bytes=b"second",
    )
    assert len(clients) == len(requests) == 1 and clients[0].is_closed
    envelope = etree.fromstring(requests[0].content)
    assert requests[0].url == environment.endpoint
    assert "SendEventUpdateStatus" in requests[0].headers["Content-Type"]
    content = envelope.findtext(f".//{{{WCF}}}contentFile")
    assert content is not None and b64decode(content) == prepared.zip_bytes
    signature = envelope.find(f".//{{{DS}}}Signature")
    assert signature is not None
    xmlsec.tree.add_ids(envelope, ["Id"])
    context = xmlsec.SignatureContext()
    context.key = xmlsec.Key.from_memory(
        digital_certificate.certificate.public_bytes(Encoding.PEM),
        xmlsec.constants.KeyDataFormatCertPem,
        None,
    )
    context.verify(signature)


def test_environment_mismatch_prevents_network(
    encrypted_pfx_path: Path,
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prod = DianClient(encrypted_pfx_path, password="test-password")
    hab = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=Environment.HABILITATION,
    )
    prepared = hab.prepare_radian_event(event=mandate_event, software=radian_software)
    assert b">2<" in prepared.xml_bytes

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network must not be used.")

    monkeypatch.setattr(transport, "create_http_client", forbidden)
    with pytest.raises(ValueError, match="environment"):
        prod.send_radian_event(prepared)
    with pytest.raises(TypeError):
        prod.send_radian_event(mandate_event)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        prod.prepare_radian_event(event=None, software=radian_software)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        prod.prepare_radian_event(event=mandate_event, software=None)  # type: ignore[arg-type]


def test_size_limit(
    encrypted_pfx_path: Path,
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    oversized = replace(
        mandate_event,
        attached_contract=replace(
            mandate_event.attached_contract, embedded_bytes=b"%PDF-" + b"x" * 400_000
        ),
    )
    with pytest.raises(ValueError, match="500,000"):
        client.prepare_radian_event(event=oversized, software=radian_software)


@pytest.mark.parametrize("kind", ["missing", "nil", "empty"])
def test_missing_nil_and_empty_result(
    wrap_soap: Callable[[etree._Element], bytes], kind: str
) -> None:
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    if kind != "missing":
        result = etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult")
        if kind == "nil":
            result.set(f"{{{XSI}}}nil", "true")
    assert parse_send_event_response(wrap_soap(response)) == (
        SendEventResult() if kind == "empty" else None
    )


@pytest.mark.parametrize(
    "value,expected",
    [("true", True), ("1", True), ("false", False), ("0", False), (None, None)],
)
def test_boolean_and_binary_optional_fields(
    wrap_soap: Callable[[etree._Element], bytes],
    value: str | None,
    expected: bool | None,
) -> None:
    parsed = parse_send_event_response(
        result_xml(
            {
                **({"IsValid": value} if value is not None else {}),
                "StatusCode": None,
                "XmlBytes": "",
                "XmlBase64Bytes": None,
            },
            wrap_soap,
        )
    )
    assert parsed is not None
    assert parsed.is_valid is expected and parsed.status_code is None
    assert parsed.xml_bytes == b"" and parsed.xml_base64_bytes is None


@pytest.mark.parametrize(
    "fields",
    [
        {"IsValid": "yes"},
        {"IsValid": None},
        {"XmlBytes": "*invalid*"},
        {"XmlBase64Bytes": "*invalid*"},
    ],
)
def test_invalid_response_fields(
    wrap_soap: Callable[[etree._Element], bytes], fields: dict[str, str | None]
) -> None:
    with pytest.raises(DianResponseError):
        parse_send_event_response(result_xml(fields, wrap_soap))


@pytest.mark.parametrize(
    "raw", [b"<bad", b"<!DOCTYPE x [<!ENTITY x 'bad'>]><x/>", b"<not-soap/>"]
)
def test_safe_parser(raw: bytes) -> None:
    with pytest.raises(DianResponseError):
        parse_send_event_response(raw)


@pytest.mark.parametrize("failure", ["http", "timeout", "fault"])
def test_failures_close_connections_without_retry(
    encrypted_pfx_path: Path,
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    monkeypatch: pytest.MonkeyPatch,
    soap_fault: bytes,
    failure: str,
) -> None:
    clients: list[httpx.Client] = []
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        return httpx.Response(
            500 if failure == "http" else 200,
            content=b"unavailable" if failure == "http" else soap_fault,
        )

    def factory(timeout: float) -> httpx.Client:
        client = httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(transport, "create_http_client", factory)
    client = DianClient(encrypted_pfx_path, password="test-password")
    prepared = client.prepare_radian_event(
        event=mandate_event, software=radian_software
    )
    error = DianSoapFaultError if failure == "fault" else DianTransportError
    with pytest.raises(error):
        client.send_radian_event(prepared)
    assert len(calls) == 1 and clients[0].is_closed
