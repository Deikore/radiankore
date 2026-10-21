"""Downloaded bytes and optional EventResponse contracts, without network access."""

from base64 import b64encode
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DianResponseError, DianTransportError, Environment
from radiankore._soap.namespaces import EVENT_RESPONSE, SOAP, WCF, WSA, XSI
from radiankore._soap.xml_document_response import parse_xml_document_response
from radiankore.models.responses import XmlDocumentResult


@pytest.fixture
def soap_response(xml_document_response: bytes) -> bytes:
    return xml_document_response


def result_node(root: etree._Element) -> etree._Element:
    node = root.find(
        f"{{{SOAP}}}Body/{{{WCF}}}GetXmlByDocumentKeyResponse/"
        f"{{{WCF}}}GetXmlByDocumentKeyResult"
    )
    assert node is not None
    return node


def test_full_result_preserves_document_bytes(
    xml_document_response: bytes,
    downloaded_document: bytes,
) -> None:
    result = parse_xml_document_response(xml_document_response)
    assert result == XmlDocumentResult(
        status_code=HTTPStatus.OK,
        message="Synthetic document result",
        validation_date=datetime(
            2026, 10, 20, 15, 30, 45, tzinfo=timezone(timedelta(hours=-5))
        ),
        document_xml=downloaded_document,
    )
    assert result is not None and not hasattr(result, "__dict__")
    assert "<Document" not in repr(result)
    assert "0001" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        field = "document_xml"
        setattr(result, field, b"changed")


@pytest.mark.parametrize("status", list(HTTPStatus))
@pytest.mark.parametrize("padding", ["", " \n\t"])
def test_soap_code_maps_to_http_status(
    xml_document_response: bytes, status: HTTPStatus, padding: str
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}Code")
    assert node is not None
    node.text = f"{padding}{status.value}{padding}"
    result = parse_xml_document_response(etree.tostring(root))
    assert result is not None and result.status_code is status
    assert XmlDocumentResult(status_code=status).status_code is status


@pytest.mark.parametrize(
    "value",
    ["999", "000", "99", "FUTURE-STATUS", "+404", "0404", "4_04", "٤٠٤", "404.0"],
)
def test_invalid_soap_code_keeps_cause(
    xml_document_response: bytes, value: str
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}Code")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError, match="Code") as error:
        parse_xml_document_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("value", [404, "404", True, 404.0])
def test_model_requires_http_status(value: object) -> None:
    with pytest.raises(TypeError, match="HTTPStatus"):
        XmlDocumentResult(status_code=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("http_status", [200, 404])
def test_soap_not_found_is_independent_of_transport_status(
    encrypted_pfx_path: Path,
    xml_document_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}Code")
    assert node is not None
    node.text = "404"
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(http_status, content=etree.tostring(root))
        )
    )
    monkeypatch.setattr(
        "radiankore._soap.transport.create_http_client", lambda timeout: http
    )
    client = DianClient(encrypted_pfx_path, password="test-password")
    if http_status == 200:
        result = client.get_xml_by_document_key("DOCUMENT-KEY")
        assert result is not None and result.status_code is HTTPStatus.NOT_FOUND
    else:
        with pytest.raises(DianTransportError) as error:
            client.get_xml_by_document_key("DOCUMENT-KEY")
        assert error.value.status_code == 404
        assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
    assert http.is_closed


@pytest.mark.parametrize("mode", ["missing", "nil", "empty"])
def test_optional_result(xml_document_response: bytes, mode: str) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root)
    if mode == "missing":
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "true")
    assert parse_xml_document_response(etree.tostring(root)) == (
        XmlDocumentResult() if mode == "empty" else None
    )


@pytest.mark.parametrize(
    "name,field",
    [
        ("Code", "status_code"),
        ("Message", "message"),
        ("ValidationDate", "validation_date"),
        ("XmlBytesBase64", "document_xml"),
    ],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces", "foreign"])
def test_optional_fields(
    xml_document_response: bytes, name: str, field: str, mode: str
) -> None:
    root = etree.fromstring(xml_document_response)
    result = result_node(root)
    node = result.find(f"{{{EVENT_RESPONSE}}}{name}")
    assert node is not None
    if mode == "missing":
        result.remove(node)
    elif mode == "foreign":
        node.tag = f"{{urn:foreign}}{name}"
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "1")
        elif mode == "spaces":
            node.text = " \n\t "
    parsed = parse_xml_document_response(etree.tostring(root))
    assert parsed is not None
    assert getattr(parsed, field) == (
        b"" if name == "XmlBytesBase64" and mode in {"empty", "spaces"} else None
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2024-02-29", date(2024, 2, 29)),
        (" 2026-10-20 ", date(2026, 10, 20)),
        ("2026-10-20T15:30:45", datetime(2026, 10, 20, 15, 30, 45)),
        (
            "2026-10-20T15:30:45.123456Z",
            datetime(2026, 10, 20, 15, 30, 45, 123456, tzinfo=UTC),
        ),
        (
            "2026-10-20T15:30:45+03:00",
            datetime(2026, 10, 20, 15, 30, 45, tzinfo=timezone(timedelta(hours=3))),
        ),
    ],
)
def test_native_dates_preserve_precision_and_offset(
    xml_document_response: bytes,
    value: str,
    expected: date | datetime,
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}ValidationDate")
    assert node is not None
    node.text = value
    result = parse_xml_document_response(etree.tostring(root))
    assert result is not None and result.validation_date == expected
    assert type(result.validation_date) is type(expected)
    assert result.validation_date.isoformat() == expected.isoformat()


@pytest.mark.parametrize(
    "value", ["2026-02-29", "20/10/2026", "2026-10-20T25:00:00", "invalid"]
)
def test_invalid_validation_date_keeps_cause(
    xml_document_response: bytes, value: str
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}ValidationDate")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError) as error:
        parse_xml_document_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x00\xffopaque",
        b'<ApplicationResponse xmlns="urn:synthetic"/>',
        b'<?xml version="1.0" encoding="ISO-8859-1"?><Invoice>\xe1</Invoice>',
        b"<!DOCTYPE x><x/>",
    ],
)
def test_no_document_interpretation_or_reformatting(
    xml_document_response: bytes, payload: bytes
) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}XmlBytesBase64")
    assert node is not None
    encoded = b64encode(payload).decode("ascii")
    node.text = " \t\r\n" + " \n".join(
        encoded[i : i + 4] for i in range(0, len(encoded), 4)
    )
    result = parse_xml_document_response(etree.tostring(root))
    assert result is not None and result.document_xml == payload


@pytest.mark.parametrize("value", ["%%%", "abc", "é", "YQ==\u00a0"])
def test_invalid_base64_keeps_cause(xml_document_response: bytes, value: str) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root).find(f"{{{EVENT_RESPONSE}}}XmlBytesBase64")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError) as error:
        parse_xml_document_response(etree.tostring(root))
    assert error.value.__cause__ is not None
    assert "XmlBytesBase64" in str(error.value)


@pytest.mark.parametrize(
    "mode",
    [
        "missing_response",
        "foreign_response",
        "wrong_operation",
        "duplicate_response",
        "duplicate_result",
    ],
)
def test_invalid_soap_wrapper(xml_document_response: bytes, mode: str) -> None:
    root = etree.fromstring(xml_document_response)
    node = result_node(root)
    response = node.getparent()
    assert response is not None
    body = response.getparent()
    assert body is not None
    if mode == "missing_response":
        body.remove(response)
    elif mode == "foreign_response":
        response.tag = "{urn:foreign}GetXmlByDocumentKeyResponse"
    elif mode == "wrong_operation":
        response.tag = f"{{{WCF}}}GetStatusEventResponse"
    elif mode == "duplicate_response":
        body.append(deepcopy(response))
    else:
        response.append(deepcopy(node))
    with pytest.raises(DianResponseError):
        parse_xml_document_response(etree.tostring(root))


@pytest.mark.parametrize("environment", [None, *Environment])
def test_client_query_and_automatic_connection_closure(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    downloaded_document: bytes,
    environment: Environment | None,
) -> None:
    clients, requests = mock_http
    client = (
        DianClient(encrypted_pfx_path, password="test-password")
        if environment is None
        else DianClient(
            encrypted_pfx_path, password="test-password", environment=environment
        )
    )
    assert not clients
    result = client.get_xml_by_document_key('  000arbitrary<&"key  ')
    assert result is not None and result.document_xml == downloaded_document
    request = requests[0]
    assert str(request.url) == (environment or Environment.PRODUCTION).endpoint
    action = f"{WCF}/IWcfDianCustomerServices/GetXmlByDocumentKey"
    assert f'action="{action}"' in request.headers["Content-Type"]
    root = etree.fromstring(request.content)
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == action
    operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetXmlByDocumentKey")
    assert operation is not None
    assert [(etree.QName(n).localname, n.text) for n in operation] == [
        ("trackId", '000arbitrary<&"key')
    ]
    assert len(clients) == 1 and clients[0].is_closed


@pytest.mark.parametrize("value", [None, 123, b"key", "", " \t\n"])
def test_invalid_key_does_not_send(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: Any,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(ValueError if isinstance(value, str) else TypeError):
        client.get_xml_by_document_key(value)
    assert mock_http == ([], [])
