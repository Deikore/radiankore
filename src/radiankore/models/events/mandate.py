"""Immutable, validated inputs for RADIAN mandate event 043."""

import datetime as dt
from dataclasses import dataclass, field

from radiankore.catalogs import (
    DocumentType,
    IdentificationType,
    MandateChannel,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandateTime,
    MandatorType,
)
from radiankore.models.events._validation import identity as _identity
from radiankore.models.events._validation import text as _text


@dataclass(frozen=True, slots=True, kw_only=True)
class MandatePerson:
    """A representative or notary; department identifies the notary office."""

    identification_number: str
    identification_type: IdentificationType
    first_name: str
    family_name: str
    verification_digit: str | None = None
    job_title: str | None = None
    nationality_id: str | None = None
    organization_department: str | None = None

    def __post_init__(self) -> None:
        _identity(
            self.identification_number,
            self.identification_type,
            self.verification_digit,
        )
        _text(self.first_name, "first_name")
        _text(self.family_name, "family_name")
        for name, value in (
            ("job_title", self.job_title),
            ("nationality_id", self.nationality_id),
            ("organization_department", self.organization_department),
        ):
            if value is not None:
                _text(value, name)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateParty:
    """Mandator or mandatee with an explicit role and representative."""

    name: str
    tax_number: str
    identification_type: IdentificationType
    role: MandatorType | MandateeType
    representative: MandatePerson
    verification_digit: str | None = None

    def __post_init__(self) -> None:
        _text(self.name, "name")
        _identity(self.tax_number, self.identification_type, self.verification_digit)
        if not isinstance(self.role, (MandatorType, MandateeType)):
            raise TypeError("role must be a MandatorType or MandateeType.")
        if not isinstance(self.representative, MandatePerson):
            raise TypeError("representative must be a MandatePerson.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateScope:
    """Ordered powers and channels; descriptions are derived from the catalog."""

    powers: tuple[tuple[MandatePower, MandateChannel], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.powers, tuple):
            raise TypeError("powers must be a tuple.")
        if not self.powers:
            raise ValueError("powers must not be empty.")
        for pair in self.powers:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError(
                    "Each power must be a (MandatePower, MandateChannel) pair."
                )
            power, channel = pair
            if not isinstance(power, MandatePower) or not isinstance(
                channel, MandateChannel
            ):
                raise TypeError("Use MandatePower and MandateChannel members.")
            if power.value in {"R01", "R02", "R03", "R04", "R05"} and (
                channel is MandateChannel.TECHNOLOGY_PROVIDER
            ):
                raise ValueError("R01-R05 do not permit the PT channel.")

    @property
    def description(self) -> str:
        """Return the descriptions in the same order as the powers."""
        return ";".join(power.label for power, _ in self.powers)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateDocumentReference:
    """Invoice number and CUFE, optionally overriding the common scope."""

    document_number: str
    uuid: str
    document_type: DocumentType = DocumentType.SALES_INVOICE
    scope: MandateScope | None = None

    def __post_init__(self) -> None:
        _text(self.document_number, "document_number")
        if not isinstance(self.document_type, DocumentType):
            raise TypeError("document_type must be a DocumentType.")
        if self.document_type is not DocumentType.SALES_INVOICE:
            raise ValueError("Mandates must reference sales invoices (01).")
        if (
            not isinstance(self.uuid, str)
            or len(self.uuid) != 96
            or any(c not in "0123456789abcdefABCDEF" for c in self.uuid)
        ):
            raise ValueError("uuid must be a 96-character hexadecimal CUFE.")
        if self.scope is not None and not isinstance(self.scope, MandateScope):
            raise TypeError("scope must be a MandateScope.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateValidityPeriod:
    """Inclusive validity dates; time type is derived from the operation."""

    start_date: dt.date | None = None
    end_date: dt.date | None = None

    def __post_init__(self) -> None:
        for value in (self.start_date, self.end_date):
            if value is not None and type(value) is not dt.date:
                raise TypeError("Validity dates must be native date objects.")
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Supply both start_date and end_date.")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not precede start_date.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateAttachedDocument:
    """PDF evidence in memory; fixed XML metadata is supplied by the builder."""

    document_id: str
    embedded_bytes: bytes = field(repr=False)
    issuer: MandatePerson | None = None
    effective_date: dt.date | None = None

    def __post_init__(self) -> None:
        _text(self.document_id, "document_id")
        if not isinstance(self.embedded_bytes, bytes):
            raise TypeError("embedded_bytes must be bytes.")
        if not self.embedded_bytes.startswith(b"%PDF-"):
            raise ValueError("Attachment must contain PDF bytes.")
        if self.issuer is not None and not isinstance(self.issuer, MandatePerson):
            raise TypeError("issuer must be a MandatePerson.")
        if self.effective_date is not None and type(self.effective_date) is not dt.date:
            raise TypeError("effective_date must be a native date.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateEvent:
    """Explicit mandate inputs. Declarations and acceptance are caller supplied."""

    operation_type: MandateOperationType
    nature: MandateNature
    reference_type: MandateReferenceType
    event_number: str
    issue_date: dt.date
    issue_time: dt.time
    notes: tuple[str, ...]
    sender_party: MandateParty
    mandatee_party: MandateParty
    effective_date: dt.date
    document_references: tuple[MandateDocumentReference, ...]
    validity_period: MandateValidityPeriod
    scope: MandateScope
    attached_contract: MandateAttachedDocument
    acceptance: bool
    attached_validity_note: MandateAttachedDocument | None = None

    def __post_init__(self) -> None:
        for value, kind in (
            (self.operation_type, MandateOperationType),
            (self.nature, MandateNature),
            (self.reference_type, MandateReferenceType),
            (self.validity_period, MandateValidityPeriod),
            (self.scope, MandateScope),
            (self.attached_contract, MandateAttachedDocument),
        ):
            if not isinstance(value, kind):
                raise TypeError(f"Expected {kind.__name__}.")
        _text(self.event_number, "event_number")
        if (
            type(self.issue_date) is not dt.date
            or type(self.effective_date) is not dt.date
        ):
            raise TypeError("issue_date and effective_date must be native dates.")
        if not isinstance(self.issue_time, dt.time):
            raise TypeError("issue_time must be a native time.")
        if not isinstance(self.notes, tuple) or not self.notes:
            raise ValueError("notes must be a nonempty tuple of declarations.")
        for note in self.notes:
            _text(note, "declaration")
        if not isinstance(self.sender_party, MandateParty) or not isinstance(
            self.mandatee_party, MandateParty
        ):
            raise TypeError("Parties must be MandateParty instances.")
        if not isinstance(self.sender_party.role, MandatorType):
            raise ValueError("sender_party must have a MandatorType role.")
        if not isinstance(self.mandatee_party.role, MandateeType):
            raise ValueError("mandatee_party must have a MandateeType role.")
        if self.acceptance is not True:
            raise ValueError("Mandatee acceptance must be explicitly True.")
        if not isinstance(self.document_references, tuple) or not all(
            isinstance(ref, MandateDocumentReference)
            for ref in self.document_references
        ):
            raise TypeError("document_references must be a tuple of references.")
        count = len(self.document_references)
        valid_count = {
            MandateReferenceType.ONE: count == 1,
            MandateReferenceType.MULTIPLE: 2 <= count <= 20,
            MandateReferenceType.ALL: count == 0,
        }[self.reference_type]
        if not valid_count:
            raise ValueError(
                "Reference count does not match reference_type (1, 2-20, 0)."
            )
        limited_time = self.operation_type in (
            MandateOperationType.GENERAL_LIMITED_TIME,
            MandateOperationType.LIMITED_LIMITED_TIME,
        )
        if limited_time != (self.validity_period.start_date is not None):
            raise ValueError("Limited time requires dates; unlimited time omits dates.")
        general_documents = self.operation_type in (
            MandateOperationType.GENERAL_LIMITED_TIME,
            MandateOperationType.GENERAL_UNLIMITED_TIME,
        )
        for scope in (self.scope, *(ref.scope for ref in self.document_references)):
            if scope is None:
                continue
            powers = tuple(power for power, _ in scope.powers)
            if general_documents:
                if powers != (MandatePower.GENERAL_DOCUMENT,):
                    raise ValueError(
                        "General document mandates require one ALL17 power."
                    )
            elif (
                len(powers) < 2
                or powers[0] is not MandatePower.WITH_REPRESENTATION
                or any(not power.value.startswith("R") for power in powers[1:])
            ):
                raise ValueError("Limited documents require MR91 followed by R01-R22.")
        if general_documents and any(
            ref.scope is not None for ref in self.document_references
        ):
            raise ValueError("Per-invoice scopes require operation 433 or 434.")
        if self.attached_validity_note is not None and not isinstance(
            self.attached_validity_note, MandateAttachedDocument
        ):
            raise TypeError("attached_validity_note must be a MandateAttachedDocument.")
        if self.nature is MandateNature.GENERAL:
            if self.attached_validity_note is None:
                raise ValueError("General powers require a validity note.")
            if self.attached_contract.effective_date is None:
                raise ValueError("General powers require the public deed date.")
            for attachment in (self.attached_contract, self.attached_validity_note):
                if (
                    attachment.issuer is None
                    or not attachment.issuer.organization_department
                ):
                    raise ValueError(
                        "General powers require notary identity and office number."
                    )
        elif self.attached_validity_note is not None:
            raise ValueError("Special powers do not include a notarial validity note.")

    @property
    def time_type(self) -> MandateTime:
        """Derive the validity code without accepting a conflicting input."""
        return (
            MandateTime.LIMITED
            if self.validity_period.start_date is not None
            else MandateTime.UNLIMITED
        )
