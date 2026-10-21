"""Synchronous DIAN client for invoice events, documents and acquirer information."""

from math import isfinite
from os import PathLike

from radiankore._soap import transport
from radiankore._soap.acquirer_response import parse_acquirer_response
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.document_status_response import parse_document_status_response
from radiankore._soap.envelope import build_signed_request
from radiankore._soap.namespaces import ACTION_PREFIX
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore._soap.response import parse_invoice_events_response
from radiankore._soap.xml_document_response import parse_xml_document_response
from radiankore.catalogs import IdentificationType
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment
from radiankore.exceptions import DianTransportError
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfoResult,
    DocumentStatusResult,
    InvoiceEventsResult,
    ReferenceNotesResult,
    XmlDocumentResult,
)


class DianClient:
    """Entry point for RADIAN events and invoice information queries.

    The certificate is loaded once during construction by DigitalCertificate.
    Only the decoded material is retained; the path and password are not stored.
    Each operation owns and automatically closes its HTTP connections.
    """

    def __init__(
        self,
        certificate_path: str | PathLike[str],
        *,
        password: str | bytes | None = None,
        environment: Environment | str = Environment.PRODUCTION,
        timeout: float = 30.0,
    ) -> None:
        """Load a PFX/P12 file, raising immediately if reading or decoding fails.

        Filesystem errors propagate as OSError subclasses. Invalid certificate
        data or passwords raise DigitalCertificateError. String passwords use
        UTF-8; None supports unencrypted containers. No network access occurs.
        """
        self._environment = Environment(environment)
        if isinstance(timeout, bool) or not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite.")
        self._certificate = DigitalCertificate.from_file(
            certificate_path, password=password
        )
        self._transport = transport.SoapTransport(timeout=timeout)

    @property
    def certificate(self) -> DigitalCertificate:
        """Return the certificate loaded at construction without reloading it."""
        return self._certificate

    @property
    def environment(self) -> Environment:
        """Return the selected deployment environment."""
        return self._environment

    def get_status(self, track_id: str) -> DocumentStatusResult | None:
        """Query document validation status and independently decoded payloads.

        The identifier must be a nonempty string after stripping outer whitespace.
        Missing or nil results return None. Business codes are not interpreted;
        payloads are decoded without XML parsing, decompression or fallback.
        """
        if not isinstance(track_id, str):
            raise TypeError("track_id must be a string.")
        track_id = track_id.strip()
        if not track_id:
            raise ValueError("track_id must not be empty.")
        return parse_document_status_response(
            self._request("GetStatus", (("trackId", track_id),))
        )

    def get_invoice_events(self, cufe: str) -> InvoiceEventsResult:
        """Query GetStatusEvent by invoice CUFE, preserving DIAN business statuses."""
        if not isinstance(cufe, str):
            raise TypeError("cufe must be a string.")
        cufe = cufe.strip()
        if not cufe:
            raise ValueError("cufe must not be empty.")
        return parse_invoice_events_response(
            self._request("GetStatusEvent", (("trackId", cufe),))
        )

    def get_acquirer(
        self,
        *,
        identification_type: IdentificationType,
        identification_number: str,
    ) -> AcquirerResult | None:
        """Query name, email and status; missing, nil or HTTP 404 returns None.

        Both arguments are required. The number is stripped but otherwise
        preserved without changing leading zeros or adding a check digit.
        Incorrect argument types raise TypeError; an empty number raises
        ValueError. Business statuses are returned without interpretation.
        """
        if not isinstance(identification_type, IdentificationType):
            raise TypeError("identification_type must be an IdentificationType.")
        if not isinstance(identification_number, str):
            raise TypeError("identification_number must be a string.")
        identification_number = identification_number.strip()
        if not identification_number:
            raise ValueError("identification_number must not be empty.")
        try:
            response = self._request(
                "GetAcquirer",
                (
                    ("identificationType", identification_type.value),
                    ("identificationNumber", identification_number),
                ),
            )
        except DianTransportError as exc:
            if exc.status_code == 404:
                return None
            raise
        return parse_acquirer_response(response)

    def get_document_info(self, uuid: str) -> DocumentInfoResult | None:
        """Query structured documents by identifier without interpreting compression.

        The identifier must be a nonempty string after stripping outer whitespace.
        No UUID or hexadecimal format is imposed. Missing or nil operation results
        return None; business statuses are returned without interpretation.
        """
        if not isinstance(uuid, str):
            raise TypeError("uuid must be a string.")
        uuid = uuid.strip()
        if not uuid:
            raise ValueError("uuid must not be empty.")
        return parse_document_info_response(
            self._request("GetDocumentInfo", (("uuid", uuid),))
        )

    def get_reference_notes(self, track_id: str) -> ReferenceNotesResult | None:
        """Query typed reference notes, metadata and independent binary payloads.

        The identifier must be a nonempty string after stripping outer whitespace.
        Missing or nil results return None. XmlBase64Bytes is parsed as UBL
        ApplicationResponse; XmlBytes is independent and never used as a fallback.
        Business statuses are returned unchanged, including when notes are present.
        """
        if not isinstance(track_id, str):
            raise TypeError("track_id must be a string.")
        track_id = track_id.strip()
        if not track_id:
            raise ValueError("track_id must not be empty.")
        return parse_reference_notes_response(
            self._request("GetReferenceNotes", (("trackId", track_id),))
        )

    def get_xml_by_document_key(self, document_key: str) -> XmlDocumentResult | None:
        """Download original document bytes without interpreting their XML root.

        A nonempty string is required and sent as trackId after stripping outer
        whitespace. Missing or nil results return None. Base64 is decoded without
        reformatting the document. SOAP Code maps to HTTPStatus; unknown or invalid
        codes raise DianResponseError independently of HTTP transport failures.
        """
        if not isinstance(document_key, str):
            raise TypeError("document_key must be a string.")
        document_key = document_key.strip()
        if not document_key:
            raise ValueError("document_key must not be empty.")
        return parse_xml_document_response(
            self._request("GetXmlByDocumentKey", (("trackId", document_key),))
        )

    def _request(
        self, operation: str, parameters: tuple[tuple[str, str], ...]
    ) -> bytes:
        action = f"{ACTION_PREFIX}/{operation}"
        payload = build_signed_request(
            operation,
            parameters,
            action=action,
            certificate=self._certificate,
            environment=self._environment,
        )
        return self._transport.post(self._environment.endpoint, payload, action=action)
