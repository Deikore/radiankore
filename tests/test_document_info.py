"""Document contracts exercised through synthetic SOAP and offline HTTP."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DianResponseError, DianTransportError, Environment
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.namespaces import SOAP, WCF, WSA, XSI
from radiankore.catalogs import DocumentType, EventType, IdentificationType
from radiankore.models.responses import (
    DocumentEvent,
    DocumentInfo,
    DocumentInfoResult,
    DocumentParty,
    DocumentReference,
    DocumentState,
    DocumentTotals,
)


@pytest.fixture
def soap_response(document_info_response: bytes) -> bytes:
    return document_info_response


def find(root: etree._Element, name: str) -> etree._Element:
    """Locate a fixture element independently of parser namespace constants."""
    document_fields = {
        "Emisor",
        "Receptor",
        "NumeroDocumento",
        "LegitimoTenedor",
        "TotalEImpuestos",
        "ValidacionesDoc",
    }
    if name in document_fields:
        path = f"//*[local-name()='Documento'][1]/*[local-name()='{name}']"
    elif name in {"Total", "Iva"}:
        path = (
            "//*[local-name()='Documento'][1]/*[local-name()='TotalEImpuestos']"
            f"/*[local-name()='{name}']"
        )
    elif name == "Codigo":
        path = "//*[local-name()='Evento'][1]/*[local-name()='Codigo']"
    else:
        path = f"//*[local-name()='{name}']"
    nodes = root.xpath(path)
    assert isinstance(nodes, list) and nodes
    node = nodes[0]
    assert isinstance(node, etree._Element)
    return node


def test_complete_document_graph(document_info_response: bytes) -> None:
    result = parse_document_info_response(document_info_response)
    assert result is not None
    assert result.status_code is HTTPStatus.OK
    assert result.status_description == "Synthetic status"
    assert result.compressed_document_info == (
        "\n OPAQUE-PAYLOAD <not-xml> & not-assumed-base64 \n"
    )
    assert "OPAQUE" not in repr(result)
    assert not hasattr(result, "document_info")
    document = result.documents[0]
    assert document is not None
    assert document.document_code == "FUTURE-DOC-CODE"
    assert document.description == "Synthetic document"
    assert document.document_type_id is DocumentType.SALES_INVOICE
    assert document.document_type_name == "Invoice"
    assert document.uuid == "DOCUMENT-UUID"
    assert document.issuer == DocumentParty(
        name="Document issuer",
        tax_number="000123",
        origin="Document origin",
        identification_type=IdentificationType("31"),
    )
    assert document.recipient is not None
    assert document.recipient.identification_type is IdentificationType("13")
    assert document.number is not None
    assert document.number.issue_date == date(2026, 1, 15)
    assert document.number.signature_date == date(2026, 1, 16)
    assert (document.number.folio, document.number.series) == ("0001", "FV")
    assert document.holder is not None
    assert document.holder.title_registration_date == date(2026, 1, 15)
    assert document.totals == DocumentTotals(
        vat=Decimal("19.000000000000000001"),
        total=Decimal("100.000000000000000001"),
    )
    assert document.states == (
        DocumentState(key=2, value="First state"),
        DocumentState(key=2),
        DocumentState(key=-1, value="Other state"),
    )
    event, nil_event, later = document.events
    assert event is not None and nil_event is None and later is not None
    assert event.code is EventType("033") and later.code is EventType("030")
    assert event.description == "Event XML description"
    assert event.uuid == "EVENT-UUID"
    assert event.issuer is not None and event.issuer.origin == "Event origin"
    assert event.recipient is not None
    assert event.recipient.identification_type is IdentificationType("48")
    assert event.number is not None and event.number.folio == "0003"
    assert event.number.issue_date == date(2026, 1, 20)
    assert event.number.signature_date == date(2026, 1, 21)
    assert event.references[0] is not None
    assert event.references[0].uuid == "EVENT-REF"
    assert event.references[0].date == date(2026, 1, 19)
    assert event.references[1] is None
    validation = event.validations[0]
    assert validation is not None and validation.is_notification is False
    assert validation.is_valid is True and validation.error_message is None
    assert validation.name == "Event rule" and validation.status == "EVENT-STATUS"
    reference = document.references[0]
    assert reference is not None and document.references[1] is None
    assert reference.description == "Document reference"
    assert reference.document_type_id is DocumentType.CREDIT_NOTE
    assert reference.document_type_name == "Reference type"
    assert reference.date == date(2026, 1, 10) and reference.uuid == "REFERENCE-UUID"
    assert reference.issuer is not None and reference.issuer.tax_number == "000REF"
    assert reference.recipient is not None
    assert reference.recipient.tax_number == "000REF-R"
    note = document.notes[0]
    assert note is not None and document.notes[1] is None
    assert note.correction is not None
    assert note.correction.code == "UNKNOWN-CORRECTION"
    assert note.correction.description == "Correction description"
    assert note.correction.name == "Correction name"
    assert note.document_type_name == "Credit note"
    assert note.uuid == "NOTE-UUID"
    assert note.issuer is not None and note.issuer.tax_number == "000NOTE"
    assert note.recipient is not None and note.recipient.tax_number == "000NOTE-R"
    assert note.number is not None and note.number.series == "NC"
    assert note.number.issue_date == date(2026, 2, 4)
    assert note.number.signature_date == date(2026, 2, 5)
    assert note.holder is not None and note.holder.title_registration_date == date(
        2026, 2, 6
    )
    assert note.totals == DocumentTotals(vat=Decimal("19"), total=Decimal("1000"))
    note_validation = note.validations[0]
    assert note_validation is not None and note_validation.is_valid is False
    assert note_validation.is_notification is True
    assert note_validation.error_message == "Note message"
    assert note_validation.status == "FUTURE-NOTE-STATUS"
    document_validation = document.validations[0]
    assert document_validation is not None
    assert document_validation.is_valid is True
    assert document_validation.is_notification is False
    assert document_validation.error_message == "Document message"
    assert document_validation.name == "Document rule"
    assert document_validation.status == "FUTURE-VALIDATION-STATUS"
    assert document.validations[1] is None
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        attribute = "status_code"
        setattr(result, attribute, "changed")


@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "foreign"])
def test_single_document_optional_values(
    document_info_response: bytes, mode: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, "Documento")
    parent = node.getparent()
    assert parent is not None
    if mode == "missing":
        parent.remove(node)
    elif mode == "foreign":
        node.tag = "{urn:foreign}Documento"
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "true")
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None
    expected = (
        (DocumentInfo(),) if mode == "empty" else (None,) if mode == "nil" else ()
    )
    assert result.documents == expected
    assert result.status_code is HTTPStatus.OK
    assert result.compressed_document_info is not None


@pytest.mark.parametrize(
    "uuids", [("Z", "A", "A"), ("Z", None, "A"), (None, None), (None,), ()]
)
def test_multiple_documents_preserve_order_duplicates_and_nil_entries(
    document_info_response: bytes, uuids: tuple[str | None, ...]
) -> None:
    root = etree.fromstring(document_info_response)
    container = find(root, "DocumentInfo")
    template = deepcopy(find(root, "Documento"))
    container.clear()
    for uuid in uuids:
        node = deepcopy(template)
        if uuid is None:
            node.clear()
            node.set(f"{{{XSI}}}nil", "true")
        else:
            identifier = node.find(
                "{http://schemas.datacontract.org/2004/07/Documento}UUID"
            )
            assert identifier is not None
            identifier.text = uuid
        container.append(node)
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None
    assert (
        tuple(doc.uuid if doc is not None else None for doc in result.documents)
        == uuids
    )
    assert result.status_code is HTTPStatus.OK
    assert result.compressed_document_info is not None
    assert all(
        doc is None or doc.document_type_id is DocumentType.SALES_INVOICE
        for doc in result.documents
    )


@pytest.mark.parametrize("namespace", ["Documento", "ReferenciaDocumento"])
@pytest.mark.parametrize("kind", list(DocumentType))
def test_document_types_in_documents_and_references(
    document_info_response: bytes, namespace: str, kind: DocumentType
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, namespace)
    tag = f"{{http://schemas.datacontract.org/2004/07/{namespace}}}DocumentTypeId"
    child = node.find(tag)
    if child is None:
        child = etree.SubElement(node, tag)
    child.text = f"  {kind.value} \n"
    if namespace == "Documento" and kind in {
        DocumentType.CREDIT_NOTE,
        DocumentType.DEBIT_NOTE,
    }:
        find(root, "DocumentCode").text = "1"
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    parsed = result.documents[0]
    if namespace == "ReferenciaDocumento":
        event = parsed.events[0]
        assert event is not None and event.references[0] is not None
        assert event.references[0].document_type_id is kind
    else:
        assert parsed.document_type_id is kind


@pytest.mark.parametrize("namespace", ["Documento", "ReferenciaDocumento"])
@pytest.mark.parametrize("value", ["1", "2", "3", "4"])
def test_unpadded_document_types_are_normalized_only_in_parser(
    document_info_response: bytes, namespace: str, value: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, namespace)
    tag = f"{{http://schemas.datacontract.org/2004/07/{namespace}}}DocumentTypeId"
    child = node.find(tag)
    if child is None:
        child = etree.SubElement(node, tag)
    child.text = value
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    parsed: DocumentInfo | DocumentReference = result.documents[0]
    if namespace == "ReferenciaDocumento":
        event = result.documents[0].events[0]
        assert event is not None and event.references[0] is not None
        parsed = event.references[0]
    assert parsed.document_type_id is DocumentType(f"0{value}")
    assert parsed.document_type_id.value == f"0{value}"
    assert DocumentType.from_code(value) is None


@pytest.mark.parametrize("namespace", ["Documento", "ReferenciaDocumento"])
@pytest.mark.parametrize("value", ["99", "001", "+1", "1.0", "\u0661", "FUTURE"])
def test_unknown_document_types_preserve_error_cause(
    document_info_response: bytes, namespace: str, value: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, namespace)
    tag = f"{{http://schemas.datacontract.org/2004/07/{namespace}}}DocumentTypeId"
    child = node.find(tag)
    if child is None:
        child = etree.SubElement(node, tag)
    child.text = value
    with pytest.raises(DianResponseError, match="DocumentTypeId") as error:
        parse_document_info_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("model", [DocumentInfo, DocumentReference])
@pytest.mark.parametrize("value", ["01", "1", 1, True, EventType.DIAN_VALIDATED])
def test_document_models_require_document_type(
    model: type[DocumentInfo] | type[DocumentReference], value: object
) -> None:
    with pytest.raises(TypeError, match="document_type_id"):
        model(document_type_id=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("namespace", ["Documento", "ReferenciaDocumento"])
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "foreign"])
def test_document_types_are_optional(
    document_info_response: bytes, namespace: str, mode: str
) -> None:
    root = etree.fromstring(document_info_response)
    parent = find(root, namespace)
    tag = f"{{http://schemas.datacontract.org/2004/07/{namespace}}}DocumentTypeId"
    node = (
        etree.SubElement(parent, tag)
        if namespace == "ReferenciaDocumento"
        else find(root, "DocumentTypeId")
    )
    if mode == "missing":
        parent.remove(node)
    elif mode == "foreign":
        node.tag = "{urn:foreign}DocumentTypeId"
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "true")
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    if namespace == "Documento":
        assert result.documents[0].document_type_id is None
    else:
        event = result.documents[0].events[0]
        assert event is not None and event.references[0] is not None
        assert event.references[0].document_type_id is None


@pytest.mark.parametrize("status", list(HTTPStatus))
def test_document_status_maps_to_http_status(
    document_info_response: bytes, status: HTTPStatus
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "StatusCode").text = f" \n{status.value}\t "
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.status_code is status
    assert DocumentInfoResult(status_code=status).status_code is status


@pytest.mark.parametrize(
    "value",
    ["999", "000", "99", "FUTURE-STATUS", "+404", "0404", "4_04", "٤٠٤", "404.0"],
)
def test_invalid_document_status_keeps_cause(
    document_info_response: bytes, value: str
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "StatusCode").text = value
    with pytest.raises(DianResponseError, match="StatusCode") as error:
        parse_document_info_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("value", [200, "200", True, 200.0])
def test_document_result_requires_http_status(value: object) -> None:
    with pytest.raises(TypeError, match="HTTPStatus"):
        DocumentInfoResult(status_code=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("http_status", [200, 404])
def test_document_not_found_is_independent_of_transport_status(
    encrypted_pfx_path: Path,
    document_info_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
    http_status: int,
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "StatusCode").text = "404"
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
        result = client.get_document_info("DOCUMENT-UUID")
        assert result is not None and result.status_code is HTTPStatus.NOT_FOUND
    else:
        with pytest.raises(DianTransportError) as error:
            client.get_document_info("DOCUMENT-UUID")
        assert error.value.status_code == 404
        assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
    assert http.is_closed


@pytest.mark.parametrize("mode", ["missing", "nil", "empty"])
def test_optional_result(document_info_response: bytes, mode: str) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, "GetDocumentInfoResult")
    if mode == "missing":
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "1")
    assert parse_document_info_response(etree.tostring(root)) == (
        DocumentInfoResult() if mode == "empty" else None
    )


@pytest.mark.parametrize(
    "name",
    [
        "Emisor",
        "Receptor",
        "NumeroDocumento",
        "LegitimoTenedor",
        "TotalEImpuestos",
        "Estado",
        "Eventos",
        "Referencias",
        "DocumentTags",
        "ValidacionesDoc",
        "DocumentInfo",
        "CompressedDocumentInfo",
        "StatusCode",
    ],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "foreign"])
def test_optional_records_and_collections(
    document_info_response: bytes,
    name: str,
    mode: str,
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, name)
    if mode == "missing":
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    elif mode == "foreign":
        node.tag = f"{{urn:foreign}}{name}"
    else:
        node.clear()
        if mode == "nil":
            node.set(f"{{{XSI}}}nil", "true")
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None
    if name == "DocumentInfo":
        assert result.documents == ()
    elif name == "CompressedDocumentInfo":
        assert result.compressed_document_info == ("" if mode == "empty" else None)
    elif name == "StatusCode":
        assert result.status_code is None
    else:
        document = result.documents[0]
        assert document is not None
        fields = {
            "Emisor": "issuer",
            "Receptor": "recipient",
            "NumeroDocumento": "number",
            "LegitimoTenedor": "holder",
            "TotalEImpuestos": "totals",
            "Estado": "states",
            "Eventos": "events",
            "Referencias": "references",
            "DocumentTags": "notes",
            "ValidacionesDoc": "validations",
        }
        value = getattr(document, fields[name])
        if name in {
            "Estado",
            "Eventos",
            "Referencias",
            "DocumentTags",
            "ValidacionesDoc",
        }:
            assert value == ()
        elif mode == "empty":
            assert value is not None
            assert all(getattr(value, field) is None for field in value.__slots__)
        else:
            assert value is None


@pytest.mark.parametrize("value", ["1E3", "-0", ".5", "+12.3e-2", "INF", "-INF", "NaN"])
def test_decimal_lexical_forms(document_info_response: bytes, value: str) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "Total").text = value
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    totals = result.documents[0].totals
    assert totals is not None and totals.total is not None
    assert totals.total.as_tuple() == Decimal(value).as_tuple()


@pytest.mark.parametrize(
    "name,value",
    [
        ("Total", ""),
        ("Total", "Infinity"),
        ("Total", "1_000"),
        ("Total", "1E9999999999999999999999999"),
        ("Total", "1E-9999999999999999999999999"),
        ("IsValida", "True"),
        ("IsNotification", "yes"),
        ("Key", "2147483648"),
        ("Key", "-2147483649"),
        ("Key", ""),
        ("Key", "1_0"),
        ("Key", "\u0661"),
        ("Codigo", "999"),
        ("TipoDoc", "999"),
    ],
)
def test_invalid_typed_values_keep_cause(
    document_info_response: bytes,
    name: str,
    value: str,
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, name).text = value
    with pytest.raises(DianResponseError) as error:
        parse_document_info_response(etree.tostring(root))
    assert error.value.__cause__ is not None


@pytest.mark.parametrize("name", ["Key", "Value", "KeyValueOfintstring"])
@pytest.mark.parametrize("mode", ["missing", "nil"])
def test_state_requirements(
    document_info_response: bytes, name: str, mode: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, name)
    if mode == "missing":
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    else:
        node.set(f"{{{XSI}}}nil", "true")
    if (name == "Value" and mode == "nil") or (
        name == "KeyValueOfintstring" and mode == "missing"
    ):
        assert parse_document_info_response(etree.tostring(root)) is not None
    else:
        with pytest.raises(DianResponseError):
            parse_document_info_response(etree.tostring(root))


@pytest.mark.parametrize("name", ["Iva", "Total", "IsNotification", "IsValida"])
def test_numeric_and_boolean_nil_rejected(
    document_info_response: bytes, name: str
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, name).set(f"{{{XSI}}}nil", "true")
    with pytest.raises(DianResponseError):
        parse_document_info_response(etree.tostring(root))


@pytest.mark.parametrize("value", ["-2147483648", "2147483647", "+0002"])
def test_state_integer_boundaries(document_info_response: bytes, value: str) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "Key").text = value
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    assert result.documents[0].states[0].key == int(value)


@pytest.mark.parametrize("value", ["31", EventType("030"), 31])
def test_party_rejects_non_identification_enum(value: Any) -> None:
    with pytest.raises(TypeError):
        DocumentParty(identification_type=value)


@pytest.mark.parametrize("value", ["030", IdentificationType("31"), 30])
def test_event_rejects_non_event_enum(value: Any) -> None:
    with pytest.raises(TypeError):
        DocumentEvent(code=value)


@pytest.mark.parametrize("environment", [None, *Environment])
def test_client_document_query(
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
    result = client.get_document_info('  arbitrary<&"uuid  ')
    assert result is not None and result.documents[0] is not None
    request = requests[0]
    assert str(request.url) == (environment or Environment.PRODUCTION).endpoint
    root = etree.fromstring(request.content)
    action = "http://wcf.dian.colombia/IWcfDianCustomerServices/GetDocumentInfo"
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == action
    assert f'action="{action}"' in request.headers["Content-Type"]
    operation = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetDocumentInfo")
    assert operation is not None
    assert [(etree.QName(n).localname, n.text) for n in operation] == [
        ("uuid", 'arbitrary<&"uuid'),
    ]
    assert len(clients) == 1 and clients[0].is_closed


@pytest.mark.parametrize("value", [None, 123, b"uuid", "", " \n\t"])
def test_invalid_uuid_does_not_open_connection(
    encrypted_pfx_path: Path,
    mock_http: tuple[list[httpx.Client], list[httpx.Request]],
    value: Any,
) -> None:
    client = DianClient(encrypted_pfx_path, password="test-password")
    with pytest.raises(ValueError if isinstance(value, str) else TypeError):
        client.get_document_info(value)
    assert mock_http == ([], [])


@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces"])
@pytest.mark.parametrize("name", ["TipoDoc", "Codigo"])
def test_optional_catalog_codes(
    document_info_response: bytes,
    mode: str,
    name: str,
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, name)
    parent = node.getparent()
    assert parent is not None
    if mode == "missing":
        parent.remove(node)
    elif mode == "nil":
        node.set(f"{{{XSI}}}nil", "true")
    else:
        node.text = "" if mode == "empty" else f"  {node.text}  "
    assert parse_document_info_response(etree.tostring(root)) is not None


@pytest.mark.parametrize("name", ["IsNotification", "IsValida"])
@pytest.mark.parametrize(
    "value,expected",
    [("true", True), ("1", True), ("false", False), ("0", False), (None, None)],
)
def test_validation_boolean_values(
    document_info_response: bytes,
    name: str,
    value: str | None,
    expected: bool | None,
) -> None:
    root = etree.fromstring(document_info_response)
    # DocumentTags precedes Eventos in the WSDL sequence.
    node = find(root, name)
    if value is None:
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    else:
        node.text = value
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    note = result.documents[0].notes[0]
    assert note is not None and note.validations[0] is not None
    field = "is_notification" if name == "IsNotification" else "is_valid"
    assert getattr(note.validations[0], field) is expected


@pytest.mark.parametrize(
    "mode",
    ["wrong_operation", "foreign_response", "duplicate_response", "duplicate_result"],
)
def test_malformed_document_wrapper(document_info_response: bytes, mode: str) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, "GetDocumentInfoResponse")
    parent = node.getparent()
    assert parent is not None
    if mode == "wrong_operation":
        node.tag = f"{{{WCF}}}GetAcquirerResponse"
    elif mode == "foreign_response":
        node.tag = "{urn:foreign}GetDocumentInfoResponse"
    elif mode == "duplicate_response":
        parent.append(deepcopy(node))
    else:
        node.append(deepcopy(find(root, "GetDocumentInfoResult")))
    with pytest.raises(DianResponseError):
        parse_document_info_response(etree.tostring(root))


def test_compressed_only_result_is_not_decoded(document_info_response: bytes) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, "DocumentInfo")
    parent = node.getparent()
    assert parent is not None
    parent.remove(node)
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents == ()
    assert result.compressed_document_info is not None
    assert "not-assumed-base64" in result.compressed_document_info


def test_client_returns_none_for_nil_document_result(
    encrypted_pfx_path: Path,
    document_info_response: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from radiankore._soap import transport

    root = etree.fromstring(document_info_response)
    node = find(root, "GetDocumentInfoResult")
    node.clear()
    node.set(f"{{{XSI}}}nil", "true")
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=etree.tostring(root))
        )
    )
    monkeypatch.setattr(transport, "create_http_client", lambda timeout: http)
    client = DianClient(encrypted_pfx_path, password="test-password")
    assert client.get_document_info("UUID") is None
    assert http.is_closed


@pytest.mark.parametrize("value", ["Nit", "NIT", "nit", "  Nit  ", "31"])
def test_document_party_nit_spelling_in_all_nested_records(
    document_info_response: bytes,
    value: str,
) -> None:
    """Use synthetic parties to reproduce the spelling returned by DIAN."""
    root = etree.fromstring(document_info_response)
    namespace = "http://schemas.datacontract.org/2004/07/Entidad"
    for node in root.iter(f"{{{namespace}}}TipoDoc"):
        node.text = value
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    document = result.documents[0]
    event = document.events[0]
    note = document.notes[0]
    reference = document.references[0]
    assert event is not None and note is not None and reference is not None
    parties = (
        document.issuer,
        document.recipient,
        event.issuer,
        event.recipient,
        note.issuer,
        note.recipient,
        reference.issuer,
        reference.recipient,
    )
    for party in parties:
        assert party is not None
        assert party.identification_type is IdentificationType.NIT
        assert party.identification_type.value == "31"
    assert document.totals is not None
    assert document.totals.total == Decimal("100.000000000000000001")
    assert document.states[0].key == 2
    assert event.description == "Event XML description"


@pytest.mark.parametrize("value", ["Unknown document", "Nitt", "N.I.T.", "Nit31"])
def test_unrecognized_document_identification_names_still_raise(
    document_info_response: bytes,
    value: str,
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, "TipoDoc").text = value
    with pytest.raises(DianResponseError) as error:
        parse_document_info_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


def test_nit_text_alias_is_local_to_document_info_parser() -> None:
    with pytest.raises(ValueError):
        IdentificationType("Nit")
    with pytest.raises(TypeError):
        DocumentParty(identification_type="Nit")  # type: ignore[arg-type]


def first_date(result: DocumentInfoResult, xml_name: str) -> date | None:
    """Read the model field corresponding to the first fixture date element."""
    document = result.documents[0]
    assert document is not None
    if xml_name == "Fecha":
        event = document.events[0]
        assert event is not None and event.references[0] is not None
        return event.references[0].date
    note = document.notes[0]
    assert note is not None
    if xml_name == "FechaInscripcionComoTituloValor":
        assert note.holder is not None
        return note.holder.title_registration_date
    assert note.number is not None
    return (
        note.number.issue_date
        if xml_name == "FechaEmision"
        else note.number.signature_date
    )


@pytest.mark.parametrize(
    "name",
    [
        "FechaEmision",
        "FechaFirma",
        "FechaInscripcionComoTituloValor",
        "Fecha",
    ],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces", "leap_day"])
def test_optional_dates_and_valid_calendar_values(
    document_info_response: bytes,
    name: str,
    mode: str,
) -> None:
    root = etree.fromstring(document_info_response)
    node = find(root, name)
    if mode == "missing":
        parent = node.getparent()
        assert parent is not None
        parent.remove(node)
    elif mode == "nil":
        node.set(f"{{{XSI}}}nil", "true")
    else:
        node.text = {
            "empty": " \n ",
            "spaces": " 2026-09-21 ",
            "leap_day": "2024-02-29",
        }[mode]
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None
    actual = first_date(result, name)
    expected = {
        "spaces": date(2026, 9, 21),
        "leap_day": date(2024, 2, 29),
    }.get(mode)
    assert actual == expected
    if actual is not None:
        assert expected is not None
        assert type(actual) is date
        assert actual.isoformat() == expected.isoformat()


@pytest.mark.parametrize(
    "name",
    [
        "FechaEmision",
        "FechaFirma",
        "FechaInscripcionComoTituloValor",
        "Fecha",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        "2026-02-29",
        "2026-04-31",
        "0000-01-01",
        "2026-13-01",
        "21/09/2026",
        "20260921",
        "2026-W39-1",
        "2026-9-21",
        "2026-09-21T00:00:00-05:00",
        "2026-09-21Z",
        "not-a-date",
    ],
)
def test_invalid_document_dates_raise_with_cause(
    document_info_response: bytes,
    name: str,
    value: str,
) -> None:
    root = etree.fromstring(document_info_response)
    find(root, name).text = value
    with pytest.raises(DianResponseError) as error:
        parse_document_info_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)
    assert name in str(error.value)
