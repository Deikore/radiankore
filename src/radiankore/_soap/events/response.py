"""Read SendEventUpdateStatus without interpreting business statuses or XML."""

from radiankore._soap.dian_response import read_binary, read_is_valid, read_messages
from radiankore._soap.namespaces import RESPONSE
from radiankore._soap.parsing import element_text, soap_result
from radiankore.models.responses import SendEventResult


def parse_send_event_response(data: bytes) -> SendEventResult | None:
    """Return all DianResponse fields without interpreting statuses or payloads."""
    result = soap_result(data, "SendEventUpdateStatus")
    if result is None:
        return None
    return SendEventResult(
        is_valid=read_is_valid(result, operation="SendEventUpdateStatus"),
        status_code=element_text(result, f"{{{RESPONSE}}}StatusCode"),
        status_description=element_text(result, f"{{{RESPONSE}}}StatusDescription"),
        status_message=element_text(result, f"{{{RESPONSE}}}StatusMessage"),
        messages=read_messages(result),
        document_key=element_text(result, f"{{{RESPONSE}}}XmlDocumentKey"),
        file_name=element_text(result, f"{{{RESPONSE}}}XmlFileName"),
        xml_base64_bytes=read_binary(result, "XmlBase64Bytes"),
        xml_bytes=read_binary(result, "XmlBytes"),
    )
