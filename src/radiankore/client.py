"""Synchronous DIAN client for invoice events, documents and acquirer information."""

from dataclasses import replace
from datetime import UTC, datetime
from math import isfinite
from os import PathLike
from typing import Self

from lxml import etree

from radiankore._soap import transport
from radiankore._soap.acquirer_response import parse_acquirer_response
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.document_status_response import parse_document_status_response
from radiankore._soap.envelope import build_signed_request
from radiankore._soap.events import parse_send_event_response
from radiankore._soap.exchange_emails_response import (
    parse_exchange_emails_csv,
    parse_exchange_emails_response,
)
from radiankore._soap.namespaces import ACTION_PREFIX
from radiankore._soap.numbering_range_response import parse_numbering_range_response
from radiankore._soap.operations import (
    acquirer_parameters,
    event_parameters,
    numbering_parameters,
    prepare_event,
    serialize_event,
    text,
)
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore._soap.response import parse_invoice_events_response
from radiankore._soap.xml_document_response import parse_xml_document_response
from radiankore.catalogs import IdentificationType
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment
from radiankore.exceptions import DianTransportError
from radiankore.models.events import (
    InvoiceResponseEvent,
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfoResult,
    DocumentStatusResult,
    ExchangeEmailsResult,
    InvoiceEventsResult,
    NumberingRangeResult,
    ReferenceNotesResult,
    SendEventResult,
    XmlDocumentResult,
)


class DianClient:
    """Entry point for RADIAN events and invoice information queries.

    The certificate is loaded once during construction by DigitalCertificate.
    Only the decoded material is retained; the path and password are not stored.
    By default each operation closes its HTTP connections. Opt in to connection
    reuse and close the client explicitly or use a context manager. This is a
    synchronous API; the timeout applies per HTTP phase, not as a total deadline.
    Loading a certificate does not check trust, revocation or DIAN authorization.
    See docs/guides/communication-and-signatures.md for both signature profiles.
    """

    def __init__(
        self,
        certificate_path: str | PathLike[str],
        *,
        password: str | bytes | None = None,
        environment: Environment | str = Environment.PRODUCTION,
        timeout: float = 30.0,
        reuse_connections: bool = False,
    ) -> None:
        """Load a PFX/P12 file, raising immediately if reading or decoding fails.

        Filesystem errors propagate as OSError subclasses. Invalid certificate
        data or passwords raise DigitalCertificateError. String passwords use
        UTF-8; None supports unencrypted containers. No network access occurs.
        """
        self._validate_options(environment, timeout, reuse_connections)
        self._initialize(
            DigitalCertificate.from_file(certificate_path, password=password),
            environment=environment,
            timeout=timeout,
            reuse_connections=reuse_connections,
        )

    def _initialize(
        self,
        certificate: DigitalCertificate,
        *,
        environment: Environment | str,
        timeout: float,
        reuse_connections: bool,
    ) -> None:
        self._validate_options(environment, timeout, reuse_connections)
        self._environment = Environment(environment)
        if not isinstance(certificate, DigitalCertificate):
            raise TypeError("certificate must be a DigitalCertificate.")
        self._certificate = certificate
        self._transport = transport.SoapTransport(
            timeout=timeout, reuse_connections=reuse_connections
        )

    @staticmethod
    def _validate_options(
        environment: Environment | str, timeout: float, reuse_connections: bool
    ) -> None:
        Environment(environment)
        if isinstance(timeout, bool) or not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite.")
        if not isinstance(reuse_connections, bool):
            raise TypeError("reuse_connections must be a bool.")

    @classmethod
    def from_pfx(
        cls,
        data: bytes,
        *,
        password: str | bytes | None = None,
        environment: Environment | str = Environment.PRODUCTION,
        timeout: float = 30.0,
        reuse_connections: bool = False,
    ) -> Self:
        """Decode PKCS#12 bytes once without retaining the container or password."""
        cls._validate_options(environment, timeout, reuse_connections)
        return cls.from_certificate(
            DigitalCertificate.from_pfx(data, password=password),
            environment=environment,
            timeout=timeout,
            reuse_connections=reuse_connections,
        )

    @classmethod
    def from_certificate(
        cls,
        certificate: DigitalCertificate,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        timeout: float = 30.0,
        reuse_connections: bool = False,
    ) -> Self:
        """Use decoded material without I/O; trust and validity remain caller policy.

        The caller must not mutate the native key. Do not share clients across
        processes or use the same client concurrently. No HTTP connection opens
        until the first request, even when connection reuse is enabled.
        """
        client = cls.__new__(cls)
        client._initialize(
            certificate,
            environment=environment,
            timeout=timeout,
            reuse_connections=reuse_connections,
        )
        return client

    def close(self) -> None:
        """Release owned HTTP resources. Repeated closes have no effect."""
        self._transport.close()

    def __enter__(self) -> Self:
        self._transport.ensure_open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def certificate(self) -> DigitalCertificate:
        """Return the certificate loaded at construction without reloading it."""
        return self._certificate

    @property
    def environment(self) -> Environment:
        """Return the selected deployment environment."""
        return self._environment

    def get_numbering_range(
        self, *, account_code: str, account_code_t: str, software_code: str
    ) -> NumberingRangeResult | None:
        """Query ranges using taxpayer NIT, software-owner NIT and software ID.

        NITs require ASCII digits without separators or a check digit; no digit
        is calculated or removed. All arguments require nonempty strings. Outer
        whitespace is stripped; leading zeros and software ID format are retained.
        The selected environment is always used, although DIAN documents service
        availability only in production. Business statuses remain uninterpreted.
        """
        return parse_numbering_range_response(
            self._request(
                "GetNumberingRange",
                numbering_parameters(account_code, account_code_t, software_code),
            )
        )

    def get_exchange_emails(self) -> ExchangeEmailsResult | None:
        """Query exchange-email metadata and return CSV records parsed in memory.

        No parameters are required. Missing or nil results return None. A missing
        URL leaves csv as None. A valid URL is downloaded regardless of
        Success, before it expires, using the configured timeout. Download errors
        propagate without a partial result, automatic retry or redirect.
        The ZIP must contain exactly one UTF-8 CSV. Native csv.DictReader uses
        its header as dictionary keys and preserves values as strings. No files
        are written; malformed CSV raises DianResponseError.
        """
        result = parse_exchange_emails_response(self._request("GetExchangeEmails", ()))
        if result is None or result.download_url is None:
            return result
        archive = self._transport.get(result.download_url)
        return replace(result, csv=parse_exchange_emails_csv(archive))

    def get_status(self, track_id: str) -> DocumentStatusResult | None:
        """Query document validation status and independently decoded payloads.

        The identifier must be a nonempty string after stripping outer whitespace.
        Missing or nil results return None. Business codes are not interpreted;
        payloads are decoded without XML parsing, decompression or fallback.
        """
        track_id = text(track_id, "track_id")
        return parse_document_status_response(
            self._request("GetStatus", (("trackId", track_id),))
        )

    def get_invoice_events(self, cufe: str) -> InvoiceEventsResult:
        """Query GetStatusEvent by invoice CUFE, preserving DIAN business statuses."""
        cufe = text(cufe, "cufe")
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
        parameters = acquirer_parameters(identification_type, identification_number)
        try:
            response = self._request("GetAcquirer", parameters)
        except DianTransportError as exc:
            if exc.status_code == 404:
                return None
            raise
        return parse_acquirer_response(response)

    def get_document_info(self, uuid: str) -> DocumentInfoResult | None:
        """Query structured documents by identifier without interpreting compression.

        The identifier must be a nonempty string after stripping outer whitespace.
        No UUID or hexadecimal format is imposed. Missing or nil operation results
        return None. SOAP StatusCode maps to HTTPStatus; unknown or invalid codes
        raise DianResponseError independently of HTTP transport failures.
        All Documento entries are preserved in XML order, including nil entries.
        """
        uuid = text(uuid, "uuid")
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
        track_id = text(track_id, "track_id")
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
        document_key = text(document_key, "document_key")
        return parse_xml_document_response(
            self._request("GetXmlByDocumentKey", (("trackId", document_key),))
        )

    def prepare_radian_event(
        self,
        *,
        event: RadianEvent,
        software: RadianSoftware,
    ) -> PreparedRadianEvent:
        """Validate, sign and ZIP any supported event locally, without I/O.

        Invoice events 030-034 must be issued on the signing date in Colombia.
        Other families retain their own profile-specific rules. Inspect or persist
        the immutable artifact before explicitly calling send_radian_event. The signed
        XML limit is 500,000 bytes, including embedded attachments. Do not reformat
        its bytes: the ZIP contains exactly that serialized, signed XML.
        """
        self._transport.ensure_open()
        return prepare_event(
            event,
            software,
            self._certificate,
            self._environment,
            datetime.now(UTC) if isinstance(event, InvoiceResponseEvent) else None,
        )

    def send_radian_event(
        self,
        prepared: PreparedRadianEvent,
    ) -> SendEventResult | None:
        """Submit the exact prepared ZIP once, without retries or rebuilding.

        The artifact must belong to this client's environment. Business rejection
        remains response data; technical failures raise the existing exceptions.
        None means an absent/nil result, not confirmed business acceptance.
        Calling this method twice can transmit twice. After an uncertain network
        failure, reconcile the result before deciding whether to send again.
        """
        return parse_send_event_response(
            self._request(
                "SendEventUpdateStatus", event_parameters(prepared, self._environment)
            )
        )

    def _serialize_event(self, root: etree._Element) -> tuple[str, bytes, bytes]:
        """Serialize the signed tree once, enforce ZA01 and package its exact bytes."""
        return serialize_event(root)

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
