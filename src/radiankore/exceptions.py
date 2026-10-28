"""Public errors for SOAP signing, transport, and response processing."""


class DianError(Exception):
    """Base error for DIAN operations; certificate loading keeps its own errors."""


class DianSignatureError(DianError):
    """The request cannot be signed with the supplied certificate."""


class DianTransportError(DianError):
    """HTTP communication failed without a usable SOAP Fault."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class DianSoapFaultError(DianError):
    """The service returned a SOAP Fault rather than an operation result."""

    def __init__(self, *, code: str, reason: str) -> None:
        super().__init__("DIAN returned a SOAP Fault.")
        self.code = code
        self.reason = reason


class DianResponseError(DianError):
    """The response contains malformed or unexpected SOAP, Base64, or UBL data."""
