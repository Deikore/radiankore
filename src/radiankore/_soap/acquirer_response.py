"""Map GetAcquirer results independently of invoice event response processing."""

from radiankore._soap.namespaces import ACQUIRER
from radiankore._soap.parsing import element_text, soap_result
from radiankore.models.responses import AcquirerResult


def parse_acquirer_response(data: bytes) -> AcquirerResult | None:
    """Return optional acquirer data, preserving any returned business status."""
    result = soap_result(data, "GetAcquirer")
    if result is None:
        return None
    return AcquirerResult(
        name=element_text(result, f"{{{ACQUIRER}}}ReceiverName"),
        email=element_text(result, f"{{{ACQUIRER}}}ReceiverEmail"),
        status_code=element_text(result, f"{{{ACQUIRER}}}StatusCode"),
        message=element_text(result, f"{{{ACQUIRER}}}Message"),
    )
