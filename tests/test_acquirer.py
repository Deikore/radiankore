"""GetAcquirer contracts using synthetic SOAP and offline HTTP."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DianResponseError, DianSoapFaultError, Environment
from radiankore._soap.acquirer_response import parse_acquirer_response
from radiankore._soap.namespaces import ACQUIRER, SOAP, WCF, WSA, XSI
from radiankore.catalogs import EventType, IdentificationType
from radiankore.models.responses import AcquirerResult


@pytest.fixture
def soap_response(acquirer_response: bytes) -> bytes:
    """Supply acquirer data to the shared offline HTTP fixture in this module."""
    return acquirer_response


def test_acquirer_result_preserves_unknown_business_status(
    acquirer_response: bytes,
) -> None:
    result = parse_acquirer_response(acquirer_response)
    assert result == AcquirerResult(
        name="Synthetic Buyer",
        email="buyer@example.invalid",
        status_code="TEST-STATUS",
        message="Synthetic result",
    )
    assert result is not None
    attribute_name = "name"
    with pytest.raises(FrozenInstanceError):
        setattr(result, attribute_name, "Changed")
    assert not hasattr(result, "__dict__")


@pytest.mark.parametrize(
    "xml_name,field",
    [
        ("ReceiverName", "name"),
        ("ReceiverEmail", "email"),
        ("StatusCode", "status_code"),
        ("Message", "message"),
    ],
)
@pytest.mark.parametrize(
    "mode", ["missing", "nil_true", "nil_one", "empty", "spaces", "foreign_namespace"]
)
def test_acquirer_fields_are_optional_and_namespace_aware(
    acquirer_response: bytes, xml_name: str, field: str, mode: str
) -> None:
    root = etree.fromstring(acquirer_response)
    result_node = root.find(
        f"{{{SOAP}}}Body/{{{WCF}}}GetAcquirerResponse/{{{WCF}}}GetAcquirerResult"
    )
    assert result_node is not None
    node = result_node.find(f"{{{ACQUIRER}}}{xml_name}")
    assert node is not None
    if mode == "missing":
        result_node.remove(node)
    elif mode.startswith("nil_"):
        node.text = None
        node.set(f"{{{XSI}}}nil", "true" if mode == "nil_true" else "1")
    elif mode == "empty":
        node.text = " \n "
    elif mode == "foreign_namespace":
        node.tag = f"{{{WCF}}}{xml_name}"
    else:
        node.text = "  trimmed value  "
    result = parse_acquirer_response(etree.tostring(root))
    assert result is not None
    assert getattr(result, field) == ("trimmed value" if mode == "spaces" else None)


@pytest.mark.parametrize("mode", ["missing", "nil_true", "nil_one", "empty"])
def test_absent_result_is_distinct_from_present_empty_result(
    acquirer_response: bytes, mode: str
) -> None:
    root = etree.fromstring(acquirer_response)
    response = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetAcquirerResponse")
    assert response is not None
    node = response.find(f"{{{WCF}}}GetAcquirerResult")
    assert node is not None
    if mode == "missing":
        response.remove(node)
    elif mode == "empty":
        node.clear()
    else:
        node.clear()
        node.set(f"{{{XSI}}}nil", "true" if mode == "nil_true" else "1")
    result = parse_acquirer_response(etree.tostring(root))
    assert result == (AcquirerResult() if mode == "empty" else None)


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
def test_malformed_acquirer_structure_is_rejected(
    acquirer_response: bytes, mode: str
) -> None:
    root = etree.fromstring(acquirer_response)
    body = root.find(f"{{{SOAP}}}Body")
    assert body is not None
    response = body.find(f"{{{WCF}}}GetAcquirerResponse")
    assert response is not None
    if mode == "missing_response":
        body.remove(response)
    elif mode == "foreign_response":
        response.tag = f"{{{ACQUIRER}}}GetAcquirerResponse"
    elif mode == "wrong_operation":
        response.tag = f"{{{WCF}}}GetStatusEventResponse"
    elif mode == "duplicate_response":
        body.append(deepcopy(response))
    else:
        node = response.find(f"{{{WCF}}}GetAcquirerResult")
        assert node is not None
        response.append(deepcopy(node))
    with pytest.raises(DianResponseError):
        parse_acquirer_response(etree.tostring(root))


def test_acquirer_fault_uses_shared_soap_error(soap_fault: bytes) -> None:
    with pytest.raises(DianSoapFaultError) as error:
        parse_acquirer_response(soap_fault)
    assert error.value.code == "s:Sender"


@pytest.mark.parametrize("environment", [None, *Environment])
def test_client_queries_acquirer_in_selected_environment(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    environment: Environment | None,
) -> None:
    clients, requests = mock_http
    client = (
        DianClient(
            encrypted_pfx_path,
            password="test-password",
            environment=environment or Environment.PRODUCTION,
        )
        if environment is not None
        else DianClient(encrypted_pfx_path, password="test-password")
    )
    assert not clients
    result = client.get_acquirer(
        identification_type=IdentificationType.PPT,
        identification_number='  00012<&"345  ',
    )
    assert result is not None and result.name == "Synthetic Buyer"
    assert result.status_code == "TEST-STATUS"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (environment or Environment.PRODUCTION).endpoint
    action = "http://wcf.dian.colombia/IWcfDianCustomerServices/GetAcquirer"
    assert f'action="{action}"' in request.headers["Content-Type"]
    root = etree.fromstring(request.content)
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == action
    operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetAcquirer")
    assert operation is not None
    assert [(etree.QName(node).localname, node.text) for node in operation] == [
        ("identificationType", "48"),
        ("identificationNumber", '00012<&"345'),
    ]
    assert len(clients) == 1 and clients[0].is_closed


def test_client_returns_none_for_nil_result(
    encrypted_pfx_path: Path,
    acquirer_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = etree.fromstring(acquirer_response)
    result_node = root.find(
        f"{{{SOAP}}}Body/{{{WCF}}}GetAcquirerResponse/{{{WCF}}}GetAcquirerResult"
    )
    assert result_node is not None
    result_node.clear()
    result_node.set(f"{{{XSI}}}nil", "true")
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=etree.tostring(root))
        )
    )
    monkeypatch.setattr(
        "radiankore._soap.transport.create_http_client", lambda timeout: http
    )
    client = DianClient(encrypted_pfx_path, password="test-password")
    assert (
        client.get_acquirer(
            identification_type=IdentificationType.NIT, identification_number="001"
        )
        is None
    )
    assert http.is_closed


@pytest.mark.parametrize("value", [None, "31", 31, EventType.INVOICE_CLAIM])
def test_acquirer_rejects_invalid_identification_type_before_network(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: object,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(TypeError, match="identification_type"):
        client.get_acquirer(identification_type=value, identification_number="001")  # type: ignore[arg-type]
    assert not mock_http[0] and not mock_http[1]


@pytest.mark.parametrize("value", [None, 31, True])
def test_acquirer_rejects_invalid_number_type_before_network(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: object,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(TypeError, match="identification_number"):
        client.get_acquirer(
            identification_type=IdentificationType.NIT,
            identification_number=value,  # type: ignore[arg-type]
        )
    assert not mock_http[0] and not mock_http[1]


@pytest.mark.parametrize("value", ["", " \n\t "])
def test_acquirer_rejects_empty_number_before_network(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: str,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(ValueError, match="identification_number"):
        client.get_acquirer(
            identification_type=IdentificationType.NIT, identification_number=value
        )
    assert not mock_http[0] and not mock_http[1]
