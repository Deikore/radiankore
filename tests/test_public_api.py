"""Public imports and examples, shared by checkout and installed-wheel checks."""

import inspect
from datetime import date
from decimal import Decimal
from importlib.resources import files
from types import ModuleType
from typing import get_args

import pytest

import radiankore
from radiankore import (
    DianClient,
    DigitalCertificate,
    DigitalCertificateError,
    Environment,
    catalogs,
)
from radiankore.catalogs import (
    AcceptanceFailureType,
    CreditNoteReason,
    CurrencyCode,
    DebitNoteReason,
    DocumentType,
    EndorsementForm,
    EventType,
    IdentificationType,
    InvoiceClaimReason,
    MandateeType,
    MandateReferenceType,
    OrganizationType,
    PartyTaxScheme,
    PaymentRestriction,
    RadianOperationType,
)
from radiankore.models import events, responses
from radiankore.models.events import (
    RadianPdfAttachment,
    RadianSoftware,
)
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfo,
    DocumentInfoResult,
    DocumentReference,
    DocumentStatusResult,
    DocumentTotals,
    EventParty,
    ExchangeEmailsResult,
    InvoiceEvent,
    InvoiceEventsResult,
    NoteDocumentReference,
    NoteLineResponse,
    NoteResponse,
    NumberingRange,
    NumberingRangeResult,
    ReferenceNote,
    ReferenceNotesResult,
    SendEventResult,
    XmlDocumentResult,
)


def test_public_event_catalog_examples() -> None:
    assert (
        RadianOperationType.MANDATE_REJECTION.event_type
        is EventType.MANDATE_TERMINATION
    )
    assert PaymentRestriction.RESTRICTED.value == "2"
    assert EndorsementForm.BLANK.value == "2"
    assert CurrencyCode.VES.value == "VES"
    assert len(RadianOperationType) == 32
    assert (
        RadianOperationType.ECONOMIC_RIGHTS_FULL_PAYMENT.event_type
        is EventType.ECONOMIC_RIGHTS_TRANSFER_PAYMENT
    )
    assert AcceptanceFailureType.TOTAL.label == "Falta de aceptación total"
    evidence = RadianPdfAttachment(
        filename="example.pdf", content_bytes=b"%PDF-1.7\nSynthetic PDF.\n%%EOF"
    )
    assert "content_bytes=" not in repr(evidence)
    assert InvoiceClaimReason.GOODS_PARTIALLY_DELIVERED.value == "03"
    assert OrganizationType.NATURAL_PERSON.value == "2"
    assert PartyTaxScheme.NOT_APPLICABLE.label == "No aplica"
    assert MandateReferenceType.MULTIPLE.value == "2"
    assert MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM.value == "M-SN-e"
    software = RadianSoftware(
        software_id="test",
        pin="secret-pin",
        provider_tax_number="900000001",
        provider_verification_digit="1",
        signer_role="supplier",
    )
    assert "secret-pin" not in repr(software)
    assert SendEventResult().is_valid is None


def test_public_numbering_range_examples() -> None:
    numbering = NumberingRange(
        resolution_number="0001",
        resolution_date=date(2026, 1, 1),
        from_number=1,
        to_number=99,
        technical_key="synthetic-secret",
    )
    assert NumberingRangeResult(ranges=(numbering, None)).ranges == (numbering, None)
    assert NumberingRangeResult(operation_code="301").operation_code == "301"
    assert "synthetic-secret" not in repr(numbering)


def test_public_exchange_email_examples() -> None:
    emails = ExchangeEmailsResult(
        success=False,
        status_code="00",
        download_url="https://example.invalid/directory.zip",
        csv=({"email": "synthetic@example.invalid"},),
    )
    assert emails.success is False and emails.csv == (
        {"email": "synthetic@example.invalid"},
    )
    assert "download_url=" not in repr(emails) and "csv=" not in repr(emails)


def test_public_document_response_examples() -> None:
    xml_result = XmlDocumentResult(
        document_xml=b"<document/>", validation_date=date(2026, 10, 20)
    )
    assert xml_result.document_xml == b"<document/>"
    assert "<document" not in repr(xml_result)
    status = DocumentStatusResult(
        is_valid=False, xml_base64_bytes=b"validation", xml_bytes=b"other"
    )
    assert status.is_valid is False and status.xml_base64_bytes == b"validation"
    assert "xml_base64_bytes=" not in repr(status)
    assert DocumentStatusResult().messages == ()
    assert ReferenceNotesResult().is_valid is None
    note = ReferenceNote(
        code=DocumentType.CREDIT_NOTE,
        references=(NoteDocumentReference(id="001"),),
        line_responses=(
            NoteLineResponse(line_id="1", responses=(NoteResponse(code="2"),)),
        ),
    )
    assert ReferenceNotesResult(notes=(note,)).notes[0].references[0].id == "001"
    assert note.code is DocumentType.CREDIT_NOTE
    assert ReferenceNote(code=DocumentType.DEBIT_NOTE).code is DocumentType.DEBIT_NOTE
    assert note.line_responses[0].responses[0].code == "2"
    notes = ReferenceNotesResult(xml_base64_bytes=b"first", xml_bytes=b"second")
    assert notes.xml_base64_bytes != notes.xml_bytes
    assert "first" not in repr(notes)
    assert DocumentInfoResult().documents == ()
    doc = DocumentInfo(document_type_id=DocumentType.SALES_INVOICE)
    assert DocumentInfoResult(documents=(doc,)).documents == (doc,)
    assert (
        DocumentReference(document_type_id=DocumentType.CREDIT_NOTE).document_type_id
        is DocumentType.CREDIT_NOTE
    )
    assert DocumentType.SALES_INVOICE.label == "Factura electrónica de Venta"
    credit = DocumentInfo(
        document_type_id=DocumentType.CREDIT_NOTE,
        document_code=CreditNoteReason.INVOICE_CANCELLATION,
    )
    debit = DocumentInfo(
        document_type_id=DocumentType.DEBIT_NOTE,
        document_code=DebitNoteReason.RECEIVABLE_EXPENSES,
    )
    assert credit.document_code is CreditNoteReason.INVOICE_CANCELLATION
    assert debit.document_code is DebitNoteReason.RECEIVABLE_EXPENSES
    assert DocumentTotals(total=Decimal("1.01")).total == Decimal("1.01")
    assert AcquirerResult().name is None
    assert IdentificationType("48") is IdentificationType.PPT
    assert callable(DigitalCertificate.from_pfx)
    assert issubclass(DigitalCertificateError, ValueError)
    assert Environment.PRODUCTION.value == "production"
    assert InvoiceEventsResult(is_valid=False, status_code="90").events == ()
    assert IdentificationType("31") is IdentificationType.NIT
    party = EventParty(identification_type=IdentificationType.NIT)
    assert party.identification_type is IdentificationType.NIT
    event = InvoiceEvent(id="EVENT-1", code=EventType.EXPRESS_ACCEPTANCE)
    event_type = event.code
    assert event_type is EventType.EXPRESS_ACCEPTANCE
    assert event_type.label == "Aceptación expresa"
    assert EventType.from_code("FUTURE") is None


@pytest.mark.parametrize("module", [radiankore, catalogs, events, responses])
def test_public_exports_resolve(module: ModuleType) -> None:
    names = module.__all__
    assert names and len(names) == len(set(names))
    assert all(not name.startswith("_") for name in names)
    for name in names:
        assert getattr(module, name) is not None


def test_client_public_operations() -> None:
    public = {
        name
        for name, _ in inspect.getmembers(DianClient, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public == {
        "close",
        "get_numbering_range",
        "get_exchange_emails",
        "get_status",
        "get_invoice_events",
        "get_acquirer",
        "get_document_info",
        "get_reference_notes",
        "get_xml_by_document_key",
        "prepare_radian_event",
        "send_radian_event",
    }
    assert {name for name in events.__all__ if name.startswith("Prepared")} == {
        "PreparedRadianEvent"
    }


def test_radian_input_union_covers_every_family() -> None:
    assert set(get_args(events.RadianEvent.__value__)) == {
        events.InvoiceResponseEvent,
        events.MandateEvent,
        events.MandateTerminationEvent,
        events.GuaranteeEvent,
        events.EconomicRightsTransferEvent,
        events.EconomicRightsNotificationEvent,
        events.EconomicRightsPaymentEvent,
        events.CirculationRestrictionEvent,
        events.CirculationRestrictionTerminationEvent,
        events.ProtestEvent,
        events.RadianRegistrationEvent,
        events.InvoicePaymentEvent,
        events.PaymentReportEvent,
        events.EndorsementEvent,
        events.EndorsementCancellationEvent,
    }


def test_typing_marker_is_distributed() -> None:
    assert files("radiankore").joinpath("py.typed").is_file()
