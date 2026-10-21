"""Synthetic contracts and offline integration for authorized numbering ranges."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree

from radiankore import (
    DianClient,
    DianResponseError,
    DianSoapFaultError,
    DianTransportError,
    Environment,
)
from radiankore._soap import transport
from radiankore._soap.namespaces import (
    NUMBER_RANGE,
    NUMBER_RANGE_LIST,
    SOAP,
    WCF,
    WSA,
    XSI,
)
from radiankore._soap.numbering_range_response import parse_numbering_range_response
from radiankore.models.responses import NumberingRange, NumberingRangeResult


@pytest.fixture
def range_response(
    wrap_soap: Callable[[etree._Element], bytes],
) -> Callable[[list[dict[str, str | None] | None]], bytes]:
    def build(items: list[dict[str, str | None] | None]) -> bytes:
        response = etree.Element(f"{{{WCF}}}GetNumberingRangeResponse")
        result = etree.SubElement(response, f"{{{WCF}}}GetNumberingRangeResult")
        etree.SubElement(result, f"{{{NUMBER_RANGE_LIST}}}OperationCode").text = "100"
        etree.SubElement(
            result, f"{{{NUMBER_RANGE_LIST}}}OperationDescription"
        ).text = "Synthetic status"
        container = etree.SubElement(result, f"{{{NUMBER_RANGE_LIST}}}ResponseList")
        for fields in items:
            node = etree.SubElement(container, f"{{{NUMBER_RANGE}}}NumberRangeResponse")
            if fields is None:
                node.set(f"{{{XSI}}}nil", "1")
                continue
            for name, value in fields.items():
                child = etree.SubElement(node, f"{{{NUMBER_RANGE}}}{name}")
                if value is None:
                    child.set(f"{{{XSI}}}nil", "true")
                else:
                    child.text = value
        return wrap_soap(response)

    return build


def test_all_range_fields_and_order(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
) -> None:
    fields: dict[str, str | None] = {
        "ResolutionNumber": " 000123 ",
        "ResolutionDate": "2026-01-01",
        "Prefix": "Z",
        "FromNumber": " +00010 ",
        "ToNumber": "20",
        "ValidDateFrom": "2026-01-02",
        "ValidDateTo": "2026-12-31",
        "TechnicalKey": "SYNTHETIC-SECRET-KEY",
    }
    result = parse_numbering_range_response(
        range_response([fields, None, {"Prefix": "A"}, fields, {}])
    )
    assert result is not None
    expected = NumberingRange(
        resolution_number="000123",
        resolution_date=date(2026, 1, 1),
        prefix="Z",
        from_number=10,
        to_number=20,
        valid_date_from=date(2026, 1, 2),
        valid_date_to=date(2026, 12, 31),
        technical_key="SYNTHETIC-SECRET-KEY",
    )
    assert result == NumberingRangeResult(
        operation_code="100",
        operation_description="Synthetic status",
        ranges=(expected, None, NumberingRange(prefix="A"), expected, NumberingRange()),
    )
    assert "SYNTHETIC-SECRET-KEY" not in repr(result)
    assert not hasattr(expected, "__dict__")
    with pytest.raises(FrozenInstanceError):
        expected.prefix = "B"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.operation_code = "500"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["FromNumber", "ToNumber"])
@pytest.mark.parametrize(
    "value", ["-9223372036854775808", "9223372036854775807", "0", "+0001", "-01"]
)
def test_long_values(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
    name: str,
    value: str,
) -> None:
    result = parse_numbering_range_response(range_response([{name: value}]))
    assert result is not None and result.ranges[0] is not None
    assert getattr(
        result.ranges[0], "from_number" if name == "FromNumber" else "to_number"
    ) == int(value)


@pytest.mark.parametrize("name", ["FromNumber", "ToNumber"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "1.5",
        "1e2",
        "\u0661",
        "1_000",
        "--1",
        "9223372036854775808",
        "-9223372036854775809",
    ],
)
def test_invalid_long(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
    name: str,
    value: str | None,
) -> None:
    with pytest.raises(DianResponseError) as error:
        parse_numbering_range_response(range_response([{name: value}]))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("name", ["ResolutionDate", "ValidDateFrom", "ValidDateTo"])
@pytest.mark.parametrize(
    "value", ["2026-02-30", "20260101", "2026-01-01T00:00:00Z", "2026-W01-1", "invalid"]
)
def test_invalid_dates(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
    name: str,
    value: str,
) -> None:
    with pytest.raises(DianResponseError) as error:
        parse_numbering_range_response(range_response([{name: value}]))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("value", [None, "", " \n "])
def test_nullable_text_and_dates(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
    value: str | None,
) -> None:
    fields = {
        name: value
        for name in [
            "ResolutionNumber",
            "ResolutionDate",
            "Prefix",
            "ValidDateFrom",
            "ValidDateTo",
            "TechnicalKey",
        ]
    }
    result = parse_numbering_range_response(range_response([fields]))
    assert result is not None and result.ranges == (NumberingRange(),)


@pytest.mark.parametrize(
    "kind",
    [
        "missing-result",
        "nil-result",
        "empty-result",
        "missing-list",
        "nil-list",
        "empty-list",
        "duplicate-result",
        "wrong-operation",
        "wrong-namespace",
    ],
)
def test_result_shapes(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes], kind: str
) -> None:
    root = etree.fromstring(range_response([]))
    response = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetNumberingRangeResponse")
    assert response is not None
    result = response.find(f"{{{WCF}}}GetNumberingRangeResult")
    assert result is not None
    container = result.find(f"{{{NUMBER_RANGE_LIST}}}ResponseList")
    assert container is not None
    if kind == "missing-result":
        response.remove(result)
    elif kind == "nil-result":
        result.set(f"{{{XSI}}}nil", "true")
    elif kind == "empty-result":
        result.clear()
    elif kind == "missing-list":
        result.remove(container)
    elif kind == "nil-list":
        container.set(f"{{{XSI}}}nil", "true")
    elif kind == "duplicate-result":
        etree.SubElement(response, f"{{{WCF}}}GetNumberingRangeResult")
    elif kind == "wrong-operation":
        response.tag = f"{{{WCF}}}OtherResponse"
    elif kind == "wrong-namespace":
        response.tag = "GetNumberingRangeResponse"
    if kind in {"duplicate-result", "wrong-operation", "wrong-namespace"}:
        with pytest.raises(DianResponseError):
            parse_numbering_range_response(etree.tostring(root))
    else:
        parsed = parse_numbering_range_response(etree.tostring(root))
        if kind in {"missing-result", "nil-result"}:
            assert parsed is None
        elif kind == "empty-result":
            assert parsed == NumberingRangeResult()
        else:
            assert parsed is not None and parsed.ranges == ()


@pytest.mark.parametrize("code", ["100", "301", "302", "303", "401", "500", "FUTURE"])
def test_business_codes_preserved(
    range_response: Callable[[list[dict[str, str | None] | None]], bytes], code: str
) -> None:
    root = etree.fromstring(range_response([{}]))
    node = root.find(f".//{{{NUMBER_RANGE_LIST}}}OperationCode")
    assert node is not None
    node.text = f" {code} "
    parsed = parse_numbering_range_response(etree.tostring(root))
    assert (
        parsed is not None
        and parsed.operation_code == code
        and parsed.ranges == (NumberingRange(),)
    )


@pytest.mark.parametrize(
    "environment", [None, Environment.PRODUCTION, Environment.HABILITATION]
)
def test_request_environment_and_resource_lifecycle(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    range_response: Callable[[list[dict[str, str | None] | None]], bytes],
    environment: Environment | None,
) -> None:
    clients: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=range_response([{"Prefix": "PRE1"}]))

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=environment or Environment.PRODUCTION,
        timeout=7.5,
    )
    encrypted_pfx_path.unlink()
    for _ in range(2):
        result = client.get_numbering_range(
            account_code=" 000123 ",
            account_code_t=" 000456 ",
            software_code=' SYNTHETIC<&"SOFTWARE ',
        )
        assert result is not None and result.ranges == (NumberingRange(prefix="PRE1"),)
    assert len(clients) == len(requests) == 2 and all(
        http.is_closed for http in clients
    )
    selected = environment or Environment.PRODUCTION
    for request in requests:
        assert str(request.url) == selected.endpoint
        assert "GetNumberingRange" in request.headers["Content-Type"]
        assert request.extensions["timeout"]["read"] == 7.5
        root = etree.fromstring(request.content)
        assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}To") == selected.addressing_to
        operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetNumberingRange")
        assert operation is not None
        assert [(etree.QName(n).localname, n.text) for n in operation] == [
            ("accountCode", "000123"),
            ("accountCodeT", "000456"),
            ("softwareCode", 'SYNTHETIC<&"SOFTWARE'),
        ]


@pytest.mark.parametrize("name", ["account_code", "account_code_t", "software_code"])
@pytest.mark.parametrize("value", [None, 123, True, b"123", "", " \n "])
def test_invalid_arguments_do_not_connect(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    name: str,
    value: Any,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    arguments = {
        "account_code": "000123",
        "account_code_t": "000456",
        "software_code": "synthetic",
    }
    arguments[name] = value
    with pytest.raises(ValueError if isinstance(value, str) else TypeError):
        client.get_numbering_range(**arguments)
    assert mock_http == ([], [])


@pytest.mark.parametrize("name", ["account_code", "account_code_t"])
@pytest.mark.parametrize(
    "value", ["١٢٣", "123.456", "123-4", "+123", "12 34", "software"]
)
def test_nit_requires_ascii_digits(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    name: str,
    value: str,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    arguments = {
        "account_code": "000123",
        "account_code_t": "000456",
        "software_code": "synthetic",
    }
    arguments[name] = value
    with pytest.raises(ValueError):
        client.get_numbering_range(**arguments)
    assert mock_http == ([], [])


@pytest.mark.parametrize("failure", ["fault", "404", "timeout", "invalid-response"])
def test_errors_close_connections(
    encrypted_pfx_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    soap_fault: bytes,
    failure: str,
) -> None:
    clients: list[httpx.Client] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("Synthetic timeout", request=request)
        return httpx.Response(
            500 if failure == "fault" else 404 if failure == "404" else 200,
            content=soap_fault if failure == "fault" else b"invalid",
        )

    def create(timeout: float) -> httpx.Client:
        http = httpx.Client(transport=httpx.MockTransport(handle), timeout=timeout)
        clients.append(http)
        return http

    monkeypatch.setattr(transport, "create_http_client", create)
    client = DianClient(encrypted_pfx_path, password="test-password")
    expected = (
        DianSoapFaultError
        if failure == "fault"
        else DianResponseError
        if failure == "invalid-response"
        else DianTransportError
    )
    with pytest.raises(expected):
        client.get_numbering_range(
            account_code="000123", account_code_t="000456", software_code="synthetic"
        )
    assert len(clients) == 1 and clients[0].is_closed
