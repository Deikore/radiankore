"""GetStatus contracts using synthetic SOAP and offline HTTP."""

from base64 import b64encode
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DianResponseError, Environment
from radiankore._soap import transport
from radiankore._soap.document_status_response import parse_document_status_response
from radiankore._soap.namespaces import ARRAY, RESPONSE, SOAP, WCF, WSA, XSI
from radiankore.models.responses import DocumentStatusResult


@pytest.fixture
def soap_response(document_status_response: bytes) -> bytes:
    return document_status_response


def result_node(root: etree._Element) -> etree._Element:
    node = root.find(
        f"{{{SOAP}}}Body/{{{WCF}}}GetStatusResponse/{{{WCF}}}GetStatusResult"
    )
    assert node is not None
    return node


def change_field(data: bytes, name: str, mode: str) -> bytes:
    root = etree.fromstring(data)
    result = result_node(root)
    node = result.find(f"{{{RESPONSE}}}{name}")
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
    return etree.tostring(root)


def test_complete_result_preserves_independent_payloads(
    document_status_response: bytes,
) -> None:
    result = parse_document_status_response(document_status_response)
    assert result is not None
    assert result == DocumentStatusResult(
        is_valid=True,
        status_code="FUTURE-STATUS",
        status_description="Synthetic status",
        status_message="Synthetic message",
        messages=("Synthetic notification", None, "", "Synthetic notification"),
        document_key="000-DOCUMENT-KEY",
        file_name="synthetic-status.xml",
        xml_base64_bytes=b"<validation/>",
        xml_bytes=b"\x00\xffSTATUS",
    )
    assert result is not None and not hasattr(result, "__dict__")
    assert "xml_bytes=" not in repr(result) and "<validation" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        attribute = "status_code"
        setattr(result, attribute, "changed")


@pytest.mark.parametrize("mode", ["missing", "nil", "empty"])
def test_optional_result(document_status_response: bytes, mode: str) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root)
    parent = node.getparent()
    assert parent is not None
    if mode == "missing":
        parent.remove(node)
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "true")
    assert parse_document_status_response(etree.tostring(root)) == (
        DocumentStatusResult() if mode == "empty" else None
    )


@pytest.mark.parametrize(
    "name,field",
    [
        ("StatusCode", "status_code"),
        ("StatusDescription", "status_description"),
        ("StatusMessage", "status_message"),
        ("XmlDocumentKey", "document_key"),
        ("XmlFileName", "file_name"),
    ],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces", "foreign"])
def test_optional_text_fields(
    document_status_response: bytes,
    name: str,
    field: str,
    mode: str,
) -> None:
    result = parse_document_status_response(
        change_field(document_status_response, name, mode)
    )
    assert result is not None and getattr(result, field) is None
    assert result.xml_base64_bytes == b"<validation/>"


@pytest.mark.parametrize(
    "name,field,other",
    [
        ("XmlBase64Bytes", "xml_base64_bytes", "xml_bytes"),
        ("XmlBytes", "xml_bytes", "xml_base64_bytes"),
    ],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces", "foreign"])
def test_optional_binary_fields_never_fall_back(
    document_status_response: bytes,
    name: str,
    field: str,
    other: str,
    mode: str,
) -> None:
    original = parse_document_status_response(document_status_response)
    result = parse_document_status_response(
        change_field(document_status_response, name, mode)
    )
    assert result is not None and original is not None
    assert getattr(result, field) == (b"" if mode in {"empty", "spaces"} else None)
    assert getattr(result, other) == getattr(original, other)


@pytest.mark.parametrize("name", ["XmlBase64Bytes", "XmlBytes"])
@pytest.mark.parametrize("payload", [b"not xml", b"\x00\x80\xff", b"<!DOCTYPE x><x/>"])
def test_binary_content_is_not_interpreted(
    document_status_response: bytes,
    name: str,
    payload: bytes,
) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root).find(f"{{{RESPONSE}}}{name}")
    assert node is not None
    encoded = b64encode(payload).decode("ascii")
    node.text = " \n\t" + " \r\n".join(
        encoded[i : i + 4] for i in range(0, len(encoded), 4)
    )
    result = parse_document_status_response(etree.tostring(root))
    assert result is not None
    field = "xml_base64_bytes" if name == "XmlBase64Bytes" else "xml_bytes"
    assert getattr(result, field) == payload


@pytest.mark.parametrize("name", ["XmlBase64Bytes", "XmlBytes"])
@pytest.mark.parametrize("value", ["%%%", "abc", "é", "YQ==\u00a0"])
def test_invalid_base64_raises_with_cause(
    document_status_response: bytes,
    name: str,
    value: str,
) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root).find(f"{{{RESPONSE}}}{name}")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError) as error:
        parse_document_status_response(etree.tostring(root))
    assert error.value.__cause__ is not None
    assert name in str(error.value)


@pytest.mark.parametrize(
    "value,expected", [("true", True), ("1", True), ("false", False), ("0", False)]
)
def test_boolean_values(
    document_status_response: bytes, value: str, expected: bool
) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root).find(f"{{{RESPONSE}}}IsValid")
    assert node is not None
    node.text = f" {value} "
    result = parse_document_status_response(etree.tostring(root))
    assert result is not None and result.is_valid is expected
    assert result.messages
    assert result.xml_base64_bytes == b"<validation/>"
    assert result.xml_bytes == b"\x00\xffSTATUS"


@pytest.mark.parametrize("mode", ["nil", "empty", "spaces"])
def test_invalid_boolean_modes(document_status_response: bytes, mode: str) -> None:
    with pytest.raises(DianResponseError):
        parse_document_status_response(
            change_field(document_status_response, "IsValid", mode)
        )


def test_unknown_boolean_raises(document_status_response: bytes) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root).find(f"{{{RESPONSE}}}IsValid")
    assert node is not None
    node.text = "True"
    with pytest.raises(DianResponseError) as error:
        parse_document_status_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("mode", ["missing", "foreign"])
def test_absent_boolean_remains_none(
    document_status_response: bytes, mode: str
) -> None:
    result = parse_document_status_response(
        change_field(document_status_response, "IsValid", mode)
    )
    assert result is not None and result.is_valid is None


@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "foreign"])
def test_optional_message_container(document_status_response: bytes, mode: str) -> None:
    result = parse_document_status_response(
        change_field(document_status_response, "ErrorMessage", mode)
    )
    assert result is not None and result.messages == ()


def test_foreign_message_items_ignored(document_status_response: bytes) -> None:
    root = etree.fromstring(document_status_response)
    container = result_node(root).find(f"{{{RESPONSE}}}ErrorMessage")
    assert container is not None
    etree.SubElement(container, "{urn:foreign}string").text = "foreign"
    result = parse_document_status_response(etree.tostring(root))
    assert result is not None and len(result.messages) == 4
    assert container.find(f"{{{ARRAY}}}string") is not None


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
def test_invalid_wrapper(document_status_response: bytes, mode: str) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root)
    response = node.getparent()
    assert response is not None
    body = response.getparent()
    assert body is not None
    if mode == "missing_response":
        body.remove(response)
    elif mode == "foreign_response":
        response.tag = "{urn:foreign}GetStatusResponse"
    elif mode == "wrong_operation":
        response.tag = f"{{{WCF}}}GetStatusEventResponse"
    elif mode == "duplicate_response":
        body.append(deepcopy(response))
    else:
        response.append(deepcopy(node))
    with pytest.raises(DianResponseError):
        parse_document_status_response(etree.tostring(root))


@pytest.mark.parametrize("environment", [None, *Environment])
def test_client_queries_selected_environment(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
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
    result = client.get_status('  arbitrary<&"identifier  ')
    assert result is not None and result.xml_bytes == b"\x00\xffSTATUS"
    request = requests[0]
    assert str(request.url) == (environment or Environment.PRODUCTION).endpoint
    root = etree.fromstring(request.content)
    action = f"{WCF}/IWcfDianCustomerServices/GetStatus"
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == action
    assert f'action="{action}"' in request.headers["Content-Type"]
    operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetStatus")
    assert operation is not None
    assert [(etree.QName(n).localname, n.text) for n in operation] == [
        ("trackId", 'arbitrary<&"identifier'),
    ]
    assert len(clients) == 1 and clients[0].is_closed


@pytest.mark.parametrize("value", [None, 123, b"id", "", " \t\n"])
def test_invalid_identifier_does_not_send(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: Any,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(ValueError if isinstance(value, str) else TypeError):
        client.get_status(value)
    assert mock_http == ([], [])


def test_client_returns_none_for_nil_result(
    encrypted_pfx_path: Path,
    document_status_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = etree.fromstring(document_status_response)
    node = result_node(root)
    node.clear()
    node.set(f"{{{XSI}}}nil", "true")
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=etree.tostring(root))
        )
    )
    monkeypatch.setattr(transport, "create_http_client", lambda timeout: http)
    client = DianClient(encrypted_pfx_path, password="test-password")
    assert client.get_status("identifier") is None
    assert http.is_closed
