"""Read GetDocumentInfo with ISO dates and uninterpreted compressed text."""

import re
from collections.abc import Callable
from datetime import date
from decimal import MAX_EMAX, MIN_ETINY, Decimal, InvalidOperation
from enum import StrEnum

from lxml import etree

from radiankore._soap.namespaces import ARRAY
from radiankore._soap.parsing import (
    element_text,
    is_nil,
    read_date,
    read_http_status,
    soap_result,
)
from radiankore.catalogs import (
    CreditNoteReason,
    DebitNoteReason,
    DocumentType,
    EventType,
    IdentificationType,
)
from radiankore.exceptions import DianResponseError
from radiankore.models.responses.document_info import (
    DocumentCorrection,
    DocumentEvent,
    DocumentHolder,
    DocumentInfo,
    DocumentInfoResult,
    DocumentNote,
    DocumentNumber,
    DocumentParty,
    DocumentReference,
    DocumentState,
    DocumentTotals,
    DocumentValidation,
)

_CONTRACT = "http://schemas.datacontract.org/2004/07"
_RESULT = f"{_CONTRACT}/DocumentInfoResponse"
_DOCUMENT = f"{_CONTRACT}/Documento"
_PARTY = f"{_CONTRACT}/Entidad"
_NUMBER = f"{_CONTRACT}/NumeroDocumento"
_HOLDER = f"{_CONTRACT}/LegitimoTenedor"
_TOTALS = f"{_CONTRACT}/TotalEImpuestos"
_VALIDATION = f"{_CONTRACT}/ValidacionDoc"
_CORRECTION = f"{_CONTRACT}/ConceptoCorreccion"
_REFERENCE = f"{_CONTRACT}/ReferenciaDocumento"
_EVENT = f"{_CONTRACT}/Evento"
_NOTE = f"{_CONTRACT}/Nota"
_DOUBLE = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|INF|-INF|NaN"
)
_INTEGER = re.compile(r"[+-]?[0-9]+")


def _text(node: etree._Element, namespace: str, name: str) -> str | None:
    return element_text(node, f"{{{namespace}}}{name}")


def _child(node: etree._Element, namespace: str, name: str) -> etree._Element | None:
    child = node.find(f"{{{namespace}}}{name}")
    return None if child is None or is_nil(child) else child


def _object[T](
    node: etree._Element, namespace: str, name: str, read: Callable[[etree._Element], T]
) -> T | None:
    child = _child(node, namespace, name)
    return read(child) if child is not None else None


def _items[T](
    node: etree._Element,
    namespace: str,
    name: str,
    item_namespace: str,
    item_name: str,
    read: Callable[[etree._Element], T],
) -> tuple[T | None, ...]:
    container = _child(node, namespace, name)
    if container is None:
        return ()
    return tuple(
        None if is_nil(item) else read(item)
        for item in container.findall(f"{{{item_namespace}}}{item_name}")
    )


def _scalar(
    node: etree._Element, namespace: str, name: str, *, required: bool = False
) -> str | None:
    child = node.find(f"{{{namespace}}}{name}")
    if child is None:
        if required:
            raise DianResponseError(f"Missing required {name} in document information.")
        return None
    if is_nil(child):
        raise DianResponseError(f"{name} must not be nil in document information.")
    return (child.text or "").strip()


def _decimal(node: etree._Element, name: str) -> Decimal | None:
    value = _scalar(node, _TOTALS, name)
    if value is None:
        return None
    try:
        if _DOUBLE.fullmatch(value) is None:
            raise ValueError("Invalid xs:double lexical value.")
        _, _, exponent = value.lower().partition("e")
        if exponent and not MIN_ETINY <= int(exponent) <= MAX_EMAX:
            raise ValueError("Decimal exponent is outside the supported range.")
        return Decimal(value)
    except (ValueError, InvalidOperation) as exc:
        raise DianResponseError(f"Invalid {name} in document totals.") from exc


def _boolean(node: etree._Element, name: str) -> bool | None:
    value = _scalar(node, _VALIDATION, name)
    if value is None:
        return None
    if value not in {"true", "false", "1", "0"}:
        cause = ValueError("Invalid xs:boolean lexical value.")
        raise DianResponseError(f"Invalid {name} in document validation.") from cause
    return value in {"true", "1"}


def _enum[T: StrEnum](
    node: etree._Element, namespace: str, name: str, enum_type: type[T]
) -> T | None:
    value = _text(node, namespace, name)
    try:
        return enum_type(value) if value is not None else None
    except ValueError as exc:
        raise DianResponseError(
            f"Unknown {name} code in document information."
        ) from exc


def _document_type(node: etree._Element, namespace: str) -> DocumentType | None:
    """Resolve canonical document types and the unpadded aliases 1 through 4."""
    value = _text(node, namespace, "DocumentTypeId")
    if value is None:
        return None
    if value in {"1", "2", "3", "4"}:
        value = f"0{value}"
    try:
        return DocumentType(value)
    except ValueError as exc:
        raise DianResponseError(
            "Unknown DocumentTypeId in document information."
        ) from exc


def _identification_type(node: etree._Element) -> IdentificationType | None:
    """Resolve numeric codes and the Nit spelling observed in GetDocumentInfo."""
    value = _text(node, _PARTY, "TipoDoc")
    if value is not None and value.casefold() == "nit":
        return IdentificationType.NIT
    try:
        return IdentificationType(value) if value is not None else None
    except ValueError as exc:
        raise DianResponseError(
            "Unknown TipoDoc code in document information."
        ) from exc


def _date(node: etree._Element, namespace: str, name: str) -> date | None:
    """Read YYYY-MM-DD calendar dates, preserving missing values as None."""
    return read_date(node, namespace, name, context="document information")


def _party(node: etree._Element) -> DocumentParty:
    return DocumentParty(
        name=_text(node, _PARTY, "Nombre"),
        tax_number=_text(node, _PARTY, "NumeroDoc"),
        identification_type=_identification_type(node),
        origin=_text(node, _PARTY, "Procedencia"),
    )


def _number(node: etree._Element) -> DocumentNumber:
    return DocumentNumber(
        issue_date=_date(node, _NUMBER, "FechaEmision"),
        signature_date=_date(node, _NUMBER, "FechaFirma"),
        folio=_text(node, _NUMBER, "Folio"),
        series=_text(node, _NUMBER, "Serie"),
    )


def _holder(node: etree._Element) -> DocumentHolder:
    return DocumentHolder(
        name=_text(node, _HOLDER, "Nombre"),
        title_registration_date=_date(node, _HOLDER, "FechaInscripcionComoTituloValor"),
    )


def _totals(node: etree._Element) -> DocumentTotals:
    return DocumentTotals(vat=_decimal(node, "Iva"), total=_decimal(node, "Total"))


def _state(node: etree._Element) -> DocumentState:
    if is_nil(node):
        raise DianResponseError("A document state must not be nil.")
    value = _scalar(node, ARRAY, "Key", required=True) or ""
    try:
        if _INTEGER.fullmatch(value) is None:
            raise ValueError("Invalid xs:int lexical value.")
        key = int(value)
        if not -(2**31) <= key < 2**31:
            raise ValueError("Document state key is outside the xs:int range.")
    except ValueError as exc:
        raise DianResponseError("Invalid document state key.") from exc
    if node.find(f"{{{ARRAY}}}Value") is None:
        raise DianResponseError("Missing required Value in document state.")
    return DocumentState(key=key, value=_text(node, ARRAY, "Value"))


def _states(node: etree._Element) -> tuple[DocumentState, ...]:
    container = _child(node, _DOCUMENT, "Estado")
    if container is None:
        return ()
    return tuple(
        _state(item) for item in container.findall(f"{{{ARRAY}}}KeyValueOfintstring")
    )


def _validation(node: etree._Element) -> DocumentValidation:
    return DocumentValidation(
        is_notification=_boolean(node, "IsNotification"),
        is_valid=_boolean(node, "IsValida"),
        error_message=_text(node, _VALIDATION, "MensajeError"),
        name=_text(node, _VALIDATION, "Nombre"),
        status=_text(node, _VALIDATION, "Status"),
    )


def _validations(
    node: etree._Element, namespace: str
) -> tuple[DocumentValidation | None, ...]:
    return _items(
        node, namespace, "ValidacionesDoc", _VALIDATION, "ValidacionDoc", _validation
    )


def _correction(node: etree._Element) -> DocumentCorrection:
    return DocumentCorrection(
        code=_text(node, _CORRECTION, "Codigo"),
        description=_text(node, _CORRECTION, "Descripcion"),
        name=_text(node, _CORRECTION, "Nombre"),
    )


def _reference(node: etree._Element) -> DocumentReference:
    return DocumentReference(
        description=_text(node, _REFERENCE, "Descripcion"),
        document_type_id=_document_type(node, _REFERENCE),
        document_type_name=_text(node, _REFERENCE, "DocumentTypeName"),
        issuer=_object(node, _REFERENCE, "Emisor", _party),
        recipient=_object(node, _REFERENCE, "Receptor", _party),
        date=_date(node, _REFERENCE, "Fecha"),
        uuid=_text(node, _REFERENCE, "UUID"),
    )


def _event(node: etree._Element) -> DocumentEvent:
    return DocumentEvent(
        code=_enum(node, _EVENT, "Codigo", EventType),
        description=_text(node, _EVENT, "Descripcion"),
        issuer=_object(node, _EVENT, "Emisor", _party),
        recipient=_object(node, _EVENT, "Receptor", _party),
        number=_object(node, _EVENT, "NumeroDocumento", _number),
        references=_items(
            node,
            _EVENT,
            "ReferenciasDocumento",
            _REFERENCE,
            "ReferenciaDocumento",
            _reference,
        ),
        uuid=_text(node, _EVENT, "UUID"),
        validations=_validations(node, _EVENT),
    )


def _note(node: etree._Element) -> DocumentNote:
    return DocumentNote(
        correction=_object(node, _NOTE, "ConceptoCorreccion", _correction),
        document_type_name=_text(node, _NOTE, "NombreTipoDocumento"),
        issuer=_object(node, _NOTE, "Emisor", _party),
        recipient=_object(node, _NOTE, "Receptor", _party),
        number=_object(node, _NOTE, "NumeroDocumento", _number),
        holder=_object(node, _NOTE, "LegitimoTenedor", _holder),
        totals=_object(node, _NOTE, "TotalEImpuestos", _totals),
        uuid=_text(node, _NOTE, "UUID"),
        validations=_validations(node, _NOTE),
    )


def _document_code(
    node: etree._Element, document_type: DocumentType | None
) -> CreditNoteReason | DebitNoteReason | str | None:
    """Resolve note reasons by type while preserving other document codes as text."""
    value = _text(node, _DOCUMENT, "DocumentCode")
    if value is None:
        return None
    try:
        if document_type is DocumentType.CREDIT_NOTE:
            return CreditNoteReason(value)
        if document_type is DocumentType.DEBIT_NOTE:
            return DebitNoteReason(value)
        return value
    except ValueError as exc:
        raise DianResponseError("Unknown DocumentCode reason for note type.") from exc


def _document(node: etree._Element) -> DocumentInfo:
    document_type = _document_type(node, _DOCUMENT)
    return DocumentInfo(
        document_code=_document_code(node, document_type),
        description=_text(node, _DOCUMENT, "DocumentDescription"),
        document_type_id=document_type,
        document_type_name=_text(node, _DOCUMENT, "DocumentTypeName"),
        uuid=_text(node, _DOCUMENT, "UUID"),
        issuer=_object(node, _DOCUMENT, "Emisor", _party),
        recipient=_object(node, _DOCUMENT, "Receptor", _party),
        number=_object(node, _DOCUMENT, "NumeroDocumento", _number),
        holder=_object(node, _DOCUMENT, "LegitimoTenedor", _holder),
        totals=_object(node, _DOCUMENT, "TotalEImpuestos", _totals),
        states=_states(node),
        events=_items(node, _DOCUMENT, "Eventos", _EVENT, "Evento", _event),
        references=_items(
            node,
            _DOCUMENT,
            "Referencias",
            _REFERENCE,
            "ReferenciaDocumento",
            _reference,
        ),
        notes=_items(node, _DOCUMENT, "DocumentTags", _NOTE, "Nota", _note),
        validations=_validations(node, _DOCUMENT),
    )


def parse_document_info_response(data: bytes) -> DocumentInfoResult | None:
    """Return typed documents in XML order, leaving compressed text uninterpreted."""
    result = soap_result(data, "GetDocumentInfo")
    if result is None:
        return None
    compressed = _child(result, _RESULT, "CompressedDocumentInfo")
    return DocumentInfoResult(
        status_code=read_http_status(result, _RESULT, "StatusCode"),
        status_description=_text(result, _RESULT, "StatusDescription"),
        documents=_items(
            result, _RESULT, "DocumentInfo", _DOCUMENT, "Documento", _document
        ),
        compressed_document_info=(compressed.text or "")
        if compressed is not None
        else None,
    )
