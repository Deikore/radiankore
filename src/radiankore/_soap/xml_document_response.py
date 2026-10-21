"""Read GetXmlByDocumentKey without interpreting the downloaded document."""

from datetime import date, datetime
from http import HTTPStatus

from lxml import etree

from radiankore._soap.namespaces import EVENT_RESPONSE
from radiankore._soap.parsing import (
    decode_base64_text,
    element_text,
    is_nil,
    soap_result,
)
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import XmlDocumentResult


def _status_code(result: etree._Element) -> HTTPStatus | None:
    value = element_text(result, f"{{{EVENT_RESPONSE}}}Code")
    if value is None:
        return None
    try:
        if len(value) != 3 or not value.isascii() or not value.isdecimal():
            raise ValueError("Code must contain three ASCII digits.")
        return HTTPStatus(int(value))
    except ValueError as exc:
        raise DianResponseError(
            "Invalid HTTP status Code in document response."
        ) from exc


def _validation_date(result: etree._Element) -> date | datetime | None:
    value = element_text(result, f"{{{EVENT_RESPONSE}}}ValidationDate")
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise DianResponseError(
                "Invalid ValidationDate in document response."
            ) from exc


def parse_xml_document_response(data: bytes) -> XmlDocumentResult | None:
    """Decode document bytes and map the optional SOAP Code to HTTPStatus."""
    result = soap_result(data, "GetXmlByDocumentKey")
    if result is None:
        return None
    node = result.find(f"{{{EVENT_RESPONSE}}}XmlBytesBase64")
    document = (
        decode_base64_text(node.text or "", field_name="XmlBytesBase64")
        if node is not None and not is_nil(node)
        else None
    )
    return XmlDocumentResult(
        status_code=_status_code(result),
        message=element_text(result, f"{{{EVENT_RESPONSE}}}Message"),
        validation_date=_validation_date(result),
        document_xml=document,
    )
