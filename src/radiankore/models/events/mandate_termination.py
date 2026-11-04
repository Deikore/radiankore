"""Structured declarations for RADIAN mandate termination (044)."""

from dataclasses import dataclass
from datetime import date

from radiankore.catalogs import EventNoteKind as K
from radiankore.catalogs import (
    EventType,
    IdentificationType,
    MandateeType,
    MandatorType,
    RadianOperationType,
)
from radiankore.models.events.mandate import MandateParty, MandatePerson
from radiankore.models.events.notes import EventNote, MandateRepresentation, note_inputs
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianEventReference,
    event_inputs,
    operation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateTerminationDeclaration:
    """Caller-attested facts; None does not assert absence of pending acts."""

    effective_date: date
    ratify_acts: bool = False
    no_pending_acts: bool | None = None
    representation: MandateRepresentation | None = None

    def __post_init__(self) -> None:
        if type(self.effective_date) is not date:
            raise TypeError("effective_date must be a native date.")
        if type(self.ratify_acts) is not bool:
            raise TypeError("ratify_acts must be bool.")
        if self.no_pending_acts is not None and type(self.no_pending_acts) is not bool:
            raise TypeError("no_pending_acts must be bool or None.")
        if self.representation is not None and not isinstance(
            self.representation, MandateRepresentation
        ):
            raise TypeError("representation must be a MandateRepresentation.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateTerminationEvent:
    """Terminate the identified mandate with an operation-derived sender."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    mandator_party: MandateParty
    mandatee_party: MandateParty
    reference: RadianEventReference
    declaration: MandateTerminationDeclaration
    additional_notes: tuple[EventNote, ...] = ()

    def __post_init__(self) -> None:
        operation(self.operation_type, ("441", "442", "443"))
        event_inputs(self.header, self.reference, RadianEventReference)
        if self.header.notes:
            raise ValueError(
                "044 header.notes must be empty; use declaration and additional_notes."
            )
        if not isinstance(self.declaration, MandateTerminationDeclaration):
            raise TypeError("declaration must be a MandateTerminationDeclaration.")
        for party, role in (
            (self.mandator_party, MandatorType),
            (self.mandatee_party, MandateeType),
        ):
            if not isinstance(party, MandateParty) or not isinstance(party.role, role):
                raise TypeError("Mandate parties must have their corresponding roles.")
        if self.sender_party.identification_type is not IdentificationType.NIT:
            raise ValueError("The event generator must be identified by NIT.")
        representation = self.declaration.representation
        if representation is not None and (
            representation.mandator_name != self.mandator_party.name
            or representation.mandatee_name != self.mandatee_party.name
        ):
            raise ValueError(
                "representation must identify the original mandate parties."
            )
        if self.declaration.ratify_acts and self.operation_type.value != "441":
            raise ValueError("Ratification is only applicable to revocation 441.")
        if self.operation_type.value == "442":
            if self.declaration.no_pending_acts is not True:
                raise ValueError(
                    "Resignation requires an explicit no_pending_acts=True."
                )
        elif self.declaration.no_pending_acts is not None:
            raise ValueError("No-pending-acts declaration is only applicable to 442.")
        note_inputs(self.additional_notes)
        if any(note.kind is not K.ADDITIONAL for note in self.additional_notes):
            raise ValueError("additional_notes only accepts ADDITIONAL notes.")
        note_inputs(self.notes)

    @property
    def sender_party(self) -> MandateParty:
        """Return the party authorized to generate this operation."""
        return (
            self.mandatee_party
            if self.operation_type.value == "442"
            else self.mandator_party
        )

    @property
    def representatives(self) -> tuple[MandatePerson, ...]:
        """Preserve all representatives of the selected sender in order."""
        return self.sender_party.representatives

    @property
    def notes(self) -> tuple[EventNote, ...]:
        """Keep the conditional statement in Note[2], with no blank placeholders."""
        action = {"441": "la revocación", "442": "la renuncia", "443": "rechazo"}[
            self.operation_type.value
        ]
        statement = EventNote(
            kind=K.MANDATE_TERMINATION,
            text=(
                f"Manifiesto {action} del mandato {self.reference.document_number}, "
                f"CUDE {self.reference.uuid}, conferido por {self.mandator_party.name} "
                f"a {self.mandatee_party.name}, con efectos a partir de "
                f"{self.declaration.effective_date.isoformat()}."
            ),
        )
        conditional: tuple[EventNote, ...] = ()
        if self.declaration.ratify_acts:
            conditional = (
                EventNote(
                    kind=K.MANDATE_RATIFICATION,
                    text=(
                        "Ratifico los actos realizados por el mandatario "
                        "en virtud del mandato identificado."
                    ),
                ),
            )
        if self.declaration.no_pending_acts is True:
            conditional = (
                EventNote(
                    kind=K.MANDATE_NO_PENDING_ACTS,
                    text=(
                        "Dejo constancia de que no se encuentra pendiente de ejecución "
                        "ningún acto en virtud del mandato que se termina."
                    ),
                ),
            )
        if self.declaration.representation is not None:
            return (
                self.declaration.representation.as_note(),
                *conditional,
                statement,
                *self.additional_notes,
            )
        return (statement, *conditional, *self.additional_notes)

    @property
    def code(self) -> EventType:
        """Return the fixed event code."""
        return EventType.MANDATE_TERMINATION
