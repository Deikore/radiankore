"""Read GetReferenceNotes metadata and UBL note records from DianResponse."""

import re

from lxml import etree

from radiankore._soap.dian_response import read_binary, read_is_valid, read_messages
from radiankore._soap.namespaces import AR, CAC, CBC, RESPONSE
from radiankore._soap.parsing import (
    element_text,
    parse_xml,
    soap_result,
)
from radiankore._soap.ubl import effective_datetime, party, texts
from radiankore.catalogs import DocumentType
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import (
    NoteDocumentReference,
    NoteLineResponse,
    NoteResponse,
    ReferenceNote,
    ReferenceNotesResult,
)


def _required_one(parent: etree._Element, name: str) -> etree._Element:
    nodes = parent.findall(f"{{{CAC}}}{name}")
    if len(nodes) != 1:
        raise DianResponseError(f"Expected one {name} in a reference note.")
    return nodes[0]


def _response(node: etree._Element) -> NoteResponse:
    date_text = element_text(node, f"{{{CBC}}}EffectiveDate")
    if (
        date_text is not None
        and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date_text) is None
    ):
        cause = ValueError("Expected a YYYY-MM-DD calendar date.")
        raise DianResponseError("Invalid date in a reference note.") from cause
    note_date, note_time = effective_datetime(
        date_text, element_text(node, f"{{{CBC}}}EffectiveTime")
    )
    return NoteResponse(
        reference_id=element_text(node, f"{{{CBC}}}ReferenceID"),
        code=element_text(node, f"{{{CBC}}}ResponseCode"),
        description="\n".join(texts(node, f"{{{CBC}}}Description")),
        date=note_date,
        time=note_time,
    )


def _reference(node: etree._Element) -> NoteDocumentReference:
    identifier = element_text(node, f"{{{CBC}}}ID")
    if identifier is None:
        raise DianResponseError("Missing document reference ID in a reference note.")
    return NoteDocumentReference(
        id=identifier, uuid=element_text(node, f"{{{CBC}}}UUID")
    )


def _line(node: etree._Element) -> NoteLineResponse:
    reference = _required_one(node, "LineReference")
    line_id = element_text(reference, f"{{{CBC}}}LineID")
    if line_id is None:
        raise DianResponseError("Missing LineID in a reference note.")
    responses = node.findall(f"{{{CAC}}}Response")
    if not responses:
        raise DianResponseError("Missing line Response in a reference note.")
    return NoteLineResponse(
        line_id=line_id, responses=tuple(_response(item) for item in responses)
    )


def _note_code(value: str | None) -> DocumentType | None:
    if value is None:
        return None
    try:
        code = DocumentType(value)
        if code not in {DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE}:
            raise ValueError("Expected a credit or debit note document type.")
        return code
    except ValueError as exc:
        raise DianResponseError("Invalid document type in a reference note.") from exc


def _note(node: etree._Element) -> ReferenceNote:
    response = _response(_required_one(node, "Response"))
    references = node.findall(f"{{{CAC}}}DocumentReference")
    if not references:
        raise DianResponseError("Missing DocumentReference in a reference note.")
    return ReferenceNote(
        reference_id=response.reference_id,
        code=_note_code(response.code),
        description=response.description,
        date=response.date,
        time=response.time,
        references=tuple(_reference(item) for item in references),
        issuer=party(node, "IssuerParty"),
        recipient=party(node, "RecipientParty"),
        line_responses=tuple(
            _line(item) for item in node.findall(f"{{{CAC}}}LineResponse")
        ),
    )


def _notes(payload: bytes | None) -> tuple[ReferenceNote, ...]:
    if not payload:
        return ()
    application = parse_xml(payload)
    if application.tag != f"{{{AR}}}ApplicationResponse":
        raise DianResponseError("Expected a UBL ApplicationResponse payload.")
    return tuple(
        _note(node) for node in application.findall(f"{{{CAC}}}DocumentResponse")
    )


def parse_reference_notes_response(data: bytes) -> ReferenceNotesResult | None:
    """Return notes and original bytes, even for negative business statuses."""
    result = soap_result(data, "GetReferenceNotes")
    if result is None:
        return None
    application_xml = read_binary(result, "XmlBase64Bytes")
    return ReferenceNotesResult(
        is_valid=read_is_valid(result, operation="GetReferenceNotes"),
        status_code=element_text(result, f"{{{RESPONSE}}}StatusCode"),
        status_description=element_text(result, f"{{{RESPONSE}}}StatusDescription"),
        status_message=element_text(result, f"{{{RESPONSE}}}StatusMessage"),
        messages=read_messages(result),
        document_key=element_text(result, f"{{{RESPONSE}}}XmlDocumentKey"),
        file_name=element_text(result, f"{{{RESPONSE}}}XmlFileName"),
        xml_base64_bytes=application_xml,
        xml_bytes=read_binary(result, "XmlBytes"),
        notes=_notes(application_xml),
    )
