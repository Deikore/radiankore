"""Namespace-aware SOAP and UBL parsing, separate from public data models."""

from lxml import etree

from radiankore._soap.namespaces import AR, ARRAY, CAC, CBC, RESPONSE
from radiankore._soap.parsing import (
    decode_base64_text,
    element_text,
    parse_xml,
    soap_result,
)
from radiankore._soap.ubl import effective_datetime, party, texts
from radiankore.catalogs import EventType
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import InvoiceEvent, InvoiceEventsResult


def _event(node: etree._Element) -> InvoiceEvent:
    response = node.find(f"{{{CAC}}}Response")
    if response is None:
        raise DianResponseError("An invoice event is missing its Response element.")
    reference = node.find(f"{{{CAC}}}DocumentReference")
    if reference is None:
        raise DianResponseError("An invoice event is missing its DocumentReference.")
    event_id = element_text(reference, f"{{{CBC}}}ID")
    if event_id is None:
        raise DianResponseError(
            "An invoice event is missing its document reference ID."
        )
    code_text = element_text(response, f"{{{CBC}}}ResponseCode")
    try:
        code = EventType(code_text) if code_text is not None else None
    except ValueError as exc:
        raise DianResponseError("Unknown invoice event code.") from exc
    event_date, event_time = effective_datetime(
        element_text(response, f"{{{CBC}}}EffectiveDate"),
        element_text(response, f"{{{CBC}}}EffectiveTime"),
    )
    return InvoiceEvent(
        id=event_id,
        code=code,
        description="\n".join(texts(response, f"{{{CBC}}}Description")),
        reference_id=element_text(response, f"{{{CBC}}}ReferenceID"),
        date=event_date,
        time=event_time,
        uuid=element_text(reference, f"{{{CBC}}}UUID"),
        issuer=party(node, "IssuerParty"),
        recipient=party(node, "RecipientParty"),
    )


def _event_order(event: InvoiceEvent) -> tuple[int, int, str]:
    reference = event.reference_id
    if reference is None or not reference.isascii() or not reference.isdecimal():
        return (1, 0, "")
    digits = reference.lstrip("0") or "0"
    return (0, len(digits), digits)


def parse_invoice_events_response(data: bytes) -> InvoiceEventsResult:
    """Decode GetStatusEvent metadata and events sorted by numeric ReferenceID."""
    result = soap_result(data, "GetStatusEvent")
    if result is None:
        raise DianResponseError("Expected a non-null GetStatusEventResult.")
    valid = element_text(result, f"{{{RESPONSE}}}IsValid")
    status_code = element_text(result, f"{{{RESPONSE}}}StatusCode")
    if valid not in {"true", "false", "1", "0"} or status_code is None:
        raise DianResponseError("Missing or invalid DIAN status metadata.")
    encoded = element_text(result, f"{{{RESPONSE}}}XmlBase64Bytes")
    application_xml = None
    events: tuple[InvoiceEvent, ...] = ()
    if encoded:
        application_xml = decode_base64_text(
            "".join(encoded.split()), field_name="XmlBase64Bytes"
        )
        application = parse_xml(application_xml)
        if application.tag != f"{{{AR}}}ApplicationResponse":
            raise DianResponseError("Expected a UBL ApplicationResponse payload.")
        events = tuple(
            sorted(
                (
                    _event(node)
                    for node in application.findall(f"{{{CAC}}}DocumentResponse")
                ),
                key=_event_order,
            )
        )
    return InvoiceEventsResult(
        is_valid=valid in {"true", "1"},
        status_code=status_code,
        status_description=element_text(result, f"{{{RESPONSE}}}StatusDescription"),
        status_message=element_text(result, f"{{{RESPONSE}}}StatusMessage"),
        messages=texts(result, f"{{{RESPONSE}}}ErrorMessage/{{{ARRAY}}}string"),
        document_key=element_text(result, f"{{{RESPONSE}}}XmlDocumentKey"),
        file_name=element_text(result, f"{{{RESPONSE}}}XmlFileName"),
        events=events,
        application_response_xml=application_xml,
    )
