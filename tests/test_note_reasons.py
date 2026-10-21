"""Note reason catalogs, type-dependent SOAP interpretation and model contracts."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from lxml import etree

from radiankore import DianResponseError
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.namespaces import XSI
from radiankore.catalogs import CreditNoteReason, DebitNoteReason, DocumentType
from radiankore.models.responses import DocumentInfo

_DOCUMENT = "http://schemas.datacontract.org/2004/07/Documento"
_RESULT = "http://schemas.datacontract.org/2004/07/DocumentInfoResponse"
_REASONS = [
    *[(DocumentType.CREDIT_NOTE, reason) for reason in CreditNoteReason],
    *[(DocumentType.DEBIT_NOTE, reason) for reason in DebitNoteReason],
]


def document_node(root: etree._Element) -> etree._Element:
    node = root.find(f".//{{{_DOCUMENT}}}Documento")
    assert node is not None
    return node


def set_text(node: etree._Element, name: str, value: str) -> None:
    child = node.find(f"{{{_DOCUMENT}}}{name}")
    assert child is not None
    child.text = value


@pytest.mark.parametrize("kind,reason", _REASONS)
def test_parser_and_model_expose_the_matching_reason_enum(
    document_info_response: bytes,
    kind: DocumentType,
    reason: CreditNoteReason | DebitNoteReason,
) -> None:
    root = etree.fromstring(document_info_response)
    node = document_node(root)
    set_text(node, "DocumentTypeId", kind.value)
    set_text(node, "DocumentCode", f" \n{reason.value}\t ")
    # Names and descriptions deliberately remain unrelated to the type/reason.
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    document = result.documents[0]
    assert document.document_code is reason
    assert document.description == "Synthetic document"
    assert document.document_type_name == "Invoice"
    assert (
        DocumentInfo(document_type_id=kind, document_code=reason).document_code
        is reason
    )
    assert json.loads(json.dumps(asdict(document)["document_code"])) == reason.value
    assert type(reason).from_code(reason.value) is reason
    assert str(reason) == reason.value
    assert reason.label == reason.label.strip() and reason.label
    attribute = "label"
    with pytest.raises(AttributeError):
        setattr(reason, attribute, "Changed")


def test_reason_catalogs_are_distinct_and_have_official_codes() -> None:
    assert {reason.value for reason in CreditNoteReason} == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }
    assert {reason.value for reason in DebitNoteReason} == {"1", "2", "3", "4"}
    assert (
        CreditNoteReason.INVOICE_CANCELLATION.label
        == "Anulación de factura electrónica"
    )
    assert DebitNoteReason.RECEIVABLE_EXPENSES.label == "Gastos por cobrar"


@pytest.mark.parametrize("catalog", [CreditNoteReason, DebitNoteReason])
@pytest.mark.parametrize("value", [None, "", "01", " 1 ", "99", "FUTURE"])
def test_optional_lookup_is_exact(
    catalog: type[CreditNoteReason] | type[DebitNoteReason], value: str | None
) -> None:
    assert catalog.from_code(value) is None
    if value is not None:
        with pytest.raises(ValueError):
            catalog(value)


@pytest.mark.parametrize("kind", [DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE])
@pytest.mark.parametrize("mode", ["missing", "nil", "empty", "spaces"])
def test_optional_document_code_remains_none(
    document_info_response: bytes, kind: DocumentType, mode: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = document_node(root)
    set_text(node, "DocumentTypeId", kind.value)
    code = node.find(f"{{{_DOCUMENT}}}DocumentCode")
    assert code is not None
    if mode == "missing":
        node.remove(code)
    else:
        code.clear()
        if mode == "nil":
            code.set(f"{{{XSI}}}nil", "true")
        elif mode == "spaces":
            code.text = " \t\n "
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    assert result.documents[0].document_code is None
    assert DocumentInfo(document_type_id=kind).document_code is None


@pytest.mark.parametrize(
    "kind,code",
    [
        (kind, code)
        for kind in (DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE)
        for code in ("0", "7", "01", "+1", "1.0", "FUTURE", "\u0661")
    ]
    + [(DocumentType.DEBIT_NOTE, "5"), (DocumentType.DEBIT_NOTE, "6")],
)
def test_unknown_or_noncanonical_note_reasons_keep_cause(
    document_info_response: bytes, kind: DocumentType, code: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = document_node(root)
    set_text(node, "DocumentTypeId", kind.value)
    set_text(node, "DocumentCode", code)
    with pytest.raises(DianResponseError, match="DocumentCode") as error:
        parse_document_info_response(etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("kind", [DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE])
@pytest.mark.parametrize("code", ["1", 1, True, DocumentType.SALES_INVOICE])
def test_note_models_require_enum_members(kind: DocumentType, code: object) -> None:
    with pytest.raises(TypeError, match="document_code"):
        DocumentInfo(document_type_id=kind, document_code=code)  # type: ignore[arg-type]


def test_models_reject_reasons_from_the_wrong_catalog() -> None:
    with pytest.raises(TypeError, match="CreditNoteReason"):
        DocumentInfo(
            document_type_id=DocumentType.CREDIT_NOTE,
            document_code=DebitNoteReason.RECEIVABLE_EXPENSES,
        )
    with pytest.raises(TypeError, match="DebitNoteReason"):
        DocumentInfo(
            document_type_id=DocumentType.DEBIT_NOTE,
            document_code=CreditNoteReason.INVOICE_CANCELLATION,
        )


@pytest.mark.parametrize(
    "kind", [None, DocumentType.SALES_INVOICE, DocumentType.APPLICATION_RESPONSE]
)
@pytest.mark.parametrize("code", ["2", "FUTURE", "01"])
def test_non_note_codes_stay_text_without_inferring_type(
    document_info_response: bytes, kind: DocumentType | None, code: str
) -> None:
    root = etree.fromstring(document_info_response)
    node = document_node(root)
    set_text(node, "DocumentCode", code)
    if kind is None:
        type_node = node.find(f"{{{_DOCUMENT}}}DocumentTypeId")
        assert type_node is not None
        node.remove(type_node)
    else:
        set_text(node, "DocumentTypeId", kind.value)
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and result.documents[0] is not None
    assert type(result.documents[0].document_code) is str
    assert result.documents[0].document_code == code
    assert DocumentInfo(document_type_id=kind, document_code=code).document_code == code


@pytest.mark.parametrize("kind", [None, DocumentType.SALES_INVOICE])
@pytest.mark.parametrize(
    "code", [1, True, CreditNoteReason.INVOICE_CANCELLATION, DebitNoteReason.OTHER]
)
def test_non_note_models_reject_reason_enums_and_non_text(
    kind: DocumentType | None, code: object
) -> None:
    with pytest.raises(TypeError, match="document_code"):
        DocumentInfo(document_type_id=kind, document_code=code)  # type: ignore[arg-type]


def test_mixed_documents_select_reason_per_entry_and_preserve_metadata(
    document_info_response: bytes,
) -> None:
    root = etree.fromstring(document_info_response)
    container = root.find(f".//{{{_RESULT}}}DocumentInfo")
    assert container is not None
    template = deepcopy(document_node(root))
    container.clear()
    for kind in (
        DocumentType.SALES_INVOICE,
        DocumentType.CREDIT_NOTE,
        DocumentType.DEBIT_NOTE,
    ):
        node = deepcopy(template)
        set_text(node, "DocumentCode", "2")
        set_text(node, "DocumentTypeId", kind.value)
        container.append(node)
    nil = etree.SubElement(container, f"{{{_DOCUMENT}}}Documento")
    nil.set(f"{{{XSI}}}nil", "true")
    result = parse_document_info_response(etree.tostring(root))
    assert result is not None and len(result.documents) == 4
    invoice, credit, debit, missing = result.documents
    assert invoice is not None and credit is not None and debit is not None
    assert type(invoice.document_code) is str and invoice.document_code == "2"
    assert credit.document_code is CreditNoteReason.INVOICE_CANCELLATION
    assert debit.document_code is DebitNoteReason.RECEIVABLE_EXPENSES
    assert missing is None
    assert credit.description == debit.description == "Synthetic document"
    note = credit.notes[0]
    assert note is not None and note.correction is not None
    assert note.correction.code == "UNKNOWN-CORRECTION"
