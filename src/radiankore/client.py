"""Synchronous DIAN client for invoice events, documents and acquirer information."""

from base64 import b64encode
from dataclasses import replace
from datetime import UTC, datetime
from math import isfinite
from os import PathLike

from lxml import etree

from radiankore._soap import transport
from radiankore._soap.acquirer_response import parse_acquirer_response
from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.document_status_response import parse_document_status_response
from radiankore._soap.envelope import build_signed_request
from radiankore._soap.events import (
    build_radian_application_response,
    pack_event,
    parse_send_event_response,
    sign_application_response,
)
from radiankore._soap.events.cude import colombian_issue_datetime
from radiankore._soap.exchange_emails_response import (
    parse_exchange_emails_csv,
    parse_exchange_emails_response,
)
from radiankore._soap.namespaces import ACTION_PREFIX, CBC
from radiankore._soap.numbering_range_response import parse_numbering_range_response
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore._soap.response import parse_invoice_events_response
from radiankore._soap.xml_document_response import parse_xml_document_response
from radiankore.catalogs import EventType, IdentificationType
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment
from radiankore.exceptions import DianTransportError
from radiankore.models.events import (
    InvoiceResponseEvent,
    MandateEvent,
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
        parameters: list[tuple[str, str]] = []
        for name, wire_name, value in (
            ("account_code", "accountCode", account_code),
            ("account_code_t", "accountCodeT", account_code_t),
            ("software_code", "softwareCode", software_code),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            value = value.strip()
            if not value:
                raise ValueError(f"{name} must not be empty.")
            if name != "software_code" and not (value.isascii() and value.isdecimal()):
                raise ValueError(f"{name} must contain only ASCII digits.")
            parameters.append((wire_name, value))
        return parse_numbering_range_response(
            self._request("GetNumberingRange", tuple(parameters))
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
        return None. SOAP StatusCode maps to HTTPStatus; unknown or invalid codes
        raise DianResponseError independently of HTTP transport failures.
        All Documento entries are preserved in XML order, including nil entries.
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

    def prepare_radian_event(
        self,
        *,
        event: RadianEvent,
        software: RadianSoftware,
    ) -> PreparedRadianEvent:
        """Validate, sign and ZIP any supported event locally, without I/O.

        Invoice events 030-034 must be issued on the signing date in Colombia.
        Other families retain their own profile-specific rules. Inspect or persist
        the immutable artifact before explicitly calling send_radian_event.
        """
        if not isinstance(software, RadianSoftware):
            raise TypeError("software must be a RadianSoftware.")
        signing_time = None
        if isinstance(event, InvoiceResponseEvent):
            signing_time = datetime.now(UTC)
            stamp = colombian_issue_datetime(event.issue_date, event.issue_time)
            signing_stamp = colombian_issue_datetime(
                signing_time.date(), signing_time.timetz()
            )
            if stamp.date() != signing_stamp.date():
                raise ValueError(
                    "Invoice event issue_date must match the signing date in Colombia."
                )
        root = build_radian_application_response(
            event,
            software=software,
            environment=self._environment,
        )
        sign_application_response(
            root,
            certificate=self._certificate,
            signer_role=software.signer_role,
            signing_time=signing_time,
        )
        if isinstance(event, MandateEvent):
            code = EventType.MANDATE
            event_number = event.event_number
        else:
            code = event.code
            event_number = (
                event.event_number
                if isinstance(event, InvoiceResponseEvent)
                else event.header.event_number
            )
        cude, xml_bytes, zip_bytes = self._serialize_event(root)
        return PreparedRadianEvent(
            code=code,
            event_number=event_number,
            cude=cude,
            environment=self._environment,
            xml_bytes=xml_bytes,
            zip_bytes=zip_bytes,
        )

    def send_radian_event(
        self,
        prepared: PreparedRadianEvent,
    ) -> SendEventResult | None:
        """Submit the exact prepared ZIP once, without retries or rebuilding.

        The artifact must belong to this client's environment. Business rejection
        remains response data; technical failures raise the existing exceptions.
        """
        if not isinstance(prepared, PreparedRadianEvent):
            raise TypeError("prepared must be a PreparedRadianEvent.")
        if prepared.environment is not self._environment:
            raise ValueError("Prepared event environment does not match the client.")
        return parse_send_event_response(
            self._request(
                "SendEventUpdateStatus",
                (("contentFile", b64encode(prepared.zip_bytes).decode("ascii")),),
            )
        )

    def _serialize_event(self, root: etree._Element) -> tuple[str, bytes, bytes]:
        """Serialize the signed tree once, enforce ZA01 and package its exact bytes."""
        xml_bytes = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        if len(xml_bytes) > 500_000:
            raise ValueError("Signed event XML exceeds DIAN's 500,000-byte limit.")
        cude = root.findtext(f"{{{CBC}}}UUID")
        assert cude is not None
        return cude, xml_bytes, pack_event(xml_bytes, xml_name=f"ar_{cude}.xml")

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
