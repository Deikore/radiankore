"""Immutable, validated inputs for RADIAN mandate event 043."""

import datetime as dt
from dataclasses import dataclass, field

from radiankore.catalogs import (
    DocumentType,
    EventNoteKind,
    IdentificationType,
    MandateChannel,
    MandateContractForm,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandateTime,
    MandatorType,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events._validation import identity as _identity
from radiankore.models.events._validation import text as _text
from radiankore.models.events.notes import (
    EventNote,
    MandateRepresentation,
    note_inputs,
    validate_event_notes,
)
from radiankore.models.events.tax_details import RadianTaxDetails


def _validate_mandate_dv(number: str, digit: str) -> None:
    """Validate the caller's NIT check digit without rewriting the identity."""
    weights = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
    remainder = (
        sum(
            int(n) * weight
            for n, weight in zip(reversed(number), weights, strict=False)
        )
        % 11
    )
    expected = remainder if remainder < 2 else 11 - remainder
    if digit != str(expected):
        raise ValueError("verification_digit does not match the NIT.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandatePerson:
    """A mandate representative with explicit nationality, department and title."""

    identification_number: str
    identification_type: IdentificationType
    first_name: str
    family_name: str
    nationality_id: str
    organization_department: str
    job_title: str
    verification_digit: str | None = None

    def __post_init__(self) -> None:
        _identity(
            self.identification_number,
            self.identification_type,
            self.verification_digit,
            minimum=3,
            maximum=15,
        )
        if self.identification_type is IdentificationType.NIT:
            assert self.verification_digit is not None
            _validate_mandate_dv(self.identification_number, self.verification_digit)
        _text(self.first_name, "first_name", maximum=100)
        _text(self.family_name, "family_name", maximum=100)
        _text(self.nationality_id, "nationality_id", maximum=100)
        _text(self.organization_department, "organization_department", maximum=200)
        _text(self.job_title, "job_title", maximum=100)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateDeclaration:
    """Facts explicitly attested by the declarant, never inferred from a certificate."""

    declarant: MandatePerson
    contract_form: MandateContractForm
    chamber_of_commerce_city: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.declarant, MandatePerson):
            raise TypeError("declarant must be a MandatePerson.")
        if not isinstance(self.contract_form, MandateContractForm):
            raise TypeError("contract_form must be a MandateContractForm.")
        if self.chamber_of_commerce_city is not None:
            _text(
                self.chamber_of_commerce_city, "chamber_of_commerce_city", maximum=100
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateNotary:
    """Notary issuing evidence of a general power; office is not a company area."""

    identification_number: str
    verification_digit: str
    first_name: str
    family_name: str
    job_title: str
    office_number: str

    def __post_init__(self) -> None:
        _identity(
            self.identification_number,
            IdentificationType.NIT,
            self.verification_digit,
            minimum=3,
            maximum=15,
        )
        _validate_mandate_dv(self.identification_number, self.verification_digit)
        for name, value in (
            ("first_name", self.first_name),
            ("family_name", self.family_name),
            ("job_title", self.job_title),
            ("office_number", self.office_number),
        ):
            _text(value, name, maximum=200 if name == "office_number" else 100)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateParty:
    """Mandator or mandatee with an explicit role and representative."""

    name: str
    tax_number: str
    identification_type: IdentificationType
    role: MandatorType | MandateeType
    representatives: tuple[MandatePerson, ...]
    verification_digit: str | None = None
    organization_type: OrganizationType = OrganizationType.LEGAL_PERSON
    tax_scheme: PartyTaxScheme | RadianTaxDetails = PartyTaxScheme.VAT

    def __post_init__(self) -> None:
        _text(self.name, "name", minimum=5, maximum=450)
        _identity(
            self.tax_number,
            self.identification_type,
            self.verification_digit,
            minimum=3,
            maximum=13,
        )
        if self.identification_type is IdentificationType.NIT:
            assert self.verification_digit is not None
            _validate_mandate_dv(self.tax_number, self.verification_digit)
        if not isinstance(self.organization_type, OrganizationType):
            raise TypeError("organization_type must be an OrganizationType.")
        if not isinstance(self.tax_scheme, (PartyTaxScheme, RadianTaxDetails)):
            raise TypeError("tax_scheme must be a PartyTaxScheme or RadianTaxDetails.")
        if not isinstance(self.role, (MandatorType, MandateeType)):
            raise TypeError("role must be a MandatorType or MandateeType.")
        if not isinstance(self.representatives, tuple) or not self.representatives:
            raise ValueError("representatives must be a nonempty tuple.")
        if not all(
            isinstance(person, MandatePerson) for person in self.representatives
        ):
            raise TypeError("representatives must contain MandatePerson instances.")


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
        _text(self.document_number, "document_number", maximum=50)
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
    issuers: tuple[MandateNotary, ...] = ()
    effective_date: dt.date | None = None

    def __post_init__(self) -> None:
        _text(self.document_id, "document_id")
        if not isinstance(self.embedded_bytes, bytes):
            raise TypeError("embedded_bytes must be bytes.")
        if not self.embedded_bytes.startswith(b"%PDF-"):
            raise ValueError("Attachment must contain PDF bytes.")
        if not isinstance(self.issuers, tuple):
            raise TypeError("issuers must be a tuple.")
        if not all(isinstance(person, MandateNotary) for person in self.issuers):
            raise TypeError("issuers must contain MandateNotary instances.")
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
    declaration: MandateDeclaration
    sender_party: MandateParty
    mandatee_party: MandateParty
    effective_date: dt.date
    document_references: tuple[MandateDocumentReference, ...]
    validity_period: MandateValidityPeriod
    scope: MandateScope
    attached_contract: MandateAttachedDocument
    acceptance: bool
    attached_validity_note: MandateAttachedDocument | None = None
    additional_notes: tuple[EventNote, ...] = ()

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
        _text(self.event_number, "event_number", maximum=50)
        if (
            type(self.issue_date) is not dt.date
            or type(self.effective_date) is not dt.date
        ):
            raise TypeError("issue_date and effective_date must be native dates.")
        if not isinstance(self.issue_time, dt.time):
            raise TypeError("issue_time must be a native time.")
        if not isinstance(self.declaration, MandateDeclaration):
            raise TypeError("declaration must be a MandateDeclaration.")
        note_inputs(self.additional_notes)
        if any(
            note.kind is not EventNoteKind.ADDITIONAL for note in self.additional_notes
        ):
            raise ValueError("additional_notes only accepts ADDITIONAL notes.")
        if not isinstance(self.sender_party, MandateParty) or not isinstance(
            self.mandatee_party, MandateParty
        ):
            raise TypeError("Parties must be MandateParty instances.")
        if not isinstance(self.sender_party.role, MandatorType):
            raise ValueError("sender_party must have a MandatorType role.")
        if not isinstance(self.mandatee_party.role, MandateeType):
            raise ValueError("mandatee_party must have a MandateeType role.")
        for representative in self.sender_party.representatives:
            _text(
                representative.identification_number,
                "sender representative identification number",
                maximum=14,
            )
        if self.declaration.declarant not in self.mandatee_party.representatives:
            raise ValueError("declarant must belong to mandatee representatives.")
        legal = self.mandatee_party.organization_type is OrganizationType.LEGAL_PERSON
        if legal != (self.declaration.chamber_of_commerce_city is not None):
            raise ValueError(
                "Legal mandatees require a chamber city; natural mandatees omit it."
            )
        validate_event_notes(
            self.notes,
            code="043",
            operation=self.operation_type.value,
            mandatee_organization=self.mandatee_party.organization_type,
        )
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
            _text(
                ";".join(
                    f"{power.value}-{channel.value}" for power, channel in scope.powers
                ),
                "power codes",
                maximum=600,
            )
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
                if not attachment.issuers:
                    raise ValueError(
                        "General powers require notary identity and office number."
                    )
        elif self.attached_validity_note is not None:
            raise ValueError("Special powers do not include a notarial validity note.")
        elif (
            self.attached_contract.issuers
            or self.attached_contract.effective_date is not None
        ):
            raise ValueError(
                "Special powers omit notarial issuers and public deed date."
            )

    @property
    def notes(self) -> tuple[EventNote, ...]:
        """Compose the two ordered declarations from validated facts."""
        person = self.declaration.declarant
        text = (
            f"{person.first_name} {person.family_name}, identificado con "
            f"el documento {person.identification_type.label} No. "
            f"{person.identification_number}, "
        )
        legal = self.mandatee_party.organization_type is OrganizationType.LEGAL_PERSON
        if legal:
            text += (
                f"en mi calidad de representante legal de la sociedad "
                f"{self.mandatee_party.name}, según consta en el certificado de "
                "existencia y representación legal expedido por la Cámara de "
                f"Comercio de {self.declaration.chamber_of_commerce_city}, "
            )
        text += (
            "expresamente manifiesto que obro en nombre y representación de "
            f"{self.sender_party.name}, de conformidad con el contrato de mandato "
            f"{self.declaration.contract_form.value} existente entre las partes y "
            "con las facultades señaladas en el presente documento y "
        )
        text += (
            "por el tiempo consignado en este documento."
            if self.time_type is MandateTime.LIMITED
            else "sin limitaciones de tiempo."
        )
        return (
            MandateRepresentation(
                mandatee_name=self.mandatee_party.name,
                mandator_name=self.sender_party.name,
            ).as_note(),
            EventNote(
                kind=EventNoteKind.MANDATE_LEGAL_PERSON
                if legal
                else EventNoteKind.MANDATE_NATURAL_PERSON,
                text=text,
            ),
            *self.additional_notes,
        )

    @property
    def time_type(self) -> MandateTime:
        """Derive the validity code without accepting a conflicting input."""
        return (
            MandateTime.LIMITED
            if self.validity_period.start_date is not None
            else MandateTime.UNLIMITED
        )
