"""Read GetStatus independently of RADIAN event and note payload interpretation."""

from radiankore._soap.dian_response import read_binary, read_is_valid, read_messages
from radiankore._soap.namespaces import RESPONSE
from radiankore._soap.parsing import element_text, soap_result
from radiankore.models.responses import DocumentStatusResult


def parse_document_status_response(data: bytes) -> DocumentStatusResult | None:
    """Return all DianResponse fields without interpreting statuses or payloads."""
    result = soap_result(data, "GetStatus")
    if result is None:
        return None
    return DocumentStatusResult(
        is_valid=read_is_valid(result, operation="GetStatus"),
        status_code=element_text(result, f"{{{RESPONSE}}}StatusCode"),
        status_description=element_text(result, f"{{{RESPONSE}}}StatusDescription"),
        status_message=element_text(result, f"{{{RESPONSE}}}StatusMessage"),
        messages=read_messages(result),
        document_key=element_text(result, f"{{{RESPONSE}}}XmlDocumentKey"),
        file_name=element_text(result, f"{{{RESPONSE}}}XmlFileName"),
        xml_base64_bytes=read_binary(result, "XmlBase64Bytes"),
        xml_bytes=read_binary(result, "XmlBytes"),
    )
