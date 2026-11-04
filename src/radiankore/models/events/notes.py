"""Pure typed declarations and conditional note rules for DIAN event profiles."""

from dataclasses import dataclass

from radiankore.catalogs import EventNoteKind, OrganizationType
from radiankore.models.events._validation import text as validate_text

__all__ = ["EventNote", "MandateRepresentation"]

_REPRESENTATION = " OBRANDO EN NOMBRE Y REPRESENTACION DE "
_K = EventNoteKind


@dataclass(frozen=True, slots=True, kw_only=True)
class EventNote:
    """A declared purpose and original text; no legal facts are inferred."""

    kind: EventNoteKind
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EventNoteKind):
            raise TypeError("kind must be an EventNoteKind.")
        validate_text(self.text, "note text", maximum=10_000)
        if self.kind is _K.MANDATE_REPRESENTATION:
            if self.text.count(_REPRESENTATION) != 1:
                raise ValueError("Representation requires the official declaration.")
            for name in self.text.split(_REPRESENTATION):
                validate_text(name, "represented party name", maximum=450)
        if self.kind is _K.PROTEST and self.text != "Con protesto":
            raise ValueError(
                "The protest note must contain the literal 'Con protesto'."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateRepresentation:
    """One mandatee and mandator; this does not attest authorization or validity."""

    mandatee_name: str
    mandator_name: str

    def __post_init__(self) -> None:
        validate_text(self.mandatee_name, "mandatee_name", maximum=450)
        validate_text(self.mandator_name, "mandator_name", maximum=450)

    def as_note(self) -> EventNote:
        """Compose the annex's declaration without XML or I/O."""
        return EventNote(
            kind=_K.MANDATE_REPRESENTATION,
            text=self.mandatee_name + _REPRESENTATION + self.mandator_name,
        )


def note_inputs(notes: tuple[EventNote, ...], *, maximum: int = 5000) -> None:
    """Require typed ordered notes; never reinterpret a legacy string."""
    if not isinstance(notes, tuple):
        raise TypeError("notes must be a tuple of EventNote instances.")
    for note in notes:
        if not isinstance(note, EventNote):
            raise TypeError("notes must contain EventNote instances, not strings.")
        validate_text(note.text, "note text", maximum=maximum)


_TACIT = frozenset(
    (
        _K.TACIT_ACCEPTANCE_DIRECT,
        _K.TACIT_ACCEPTANCE_LEGAL_MANDATE,
        _K.TACIT_ACCEPTANCE_NATURAL_MANDATE,
    )
)
_GUARANTEE = frozenset((_K.GUARANTEE_NATURAL_PERSON, _K.GUARANTEE_LEGAL_PERSON))
_MANDATE = frozenset((_K.MANDATE_NATURAL_PERSON, _K.MANDATE_LEGAL_PERSON))
_SPECIFIC: dict[str, frozenset[EventNoteKind]] = {
    "034": _TACIT,
    "035": _GUARANTEE,
    "036": frozenset((_K.SPECIAL_PAYMENT_TERMS,)),
    "037": frozenset((_K.WITHOUT_RECOURSE,)),
    "038": frozenset((_K.GUARANTEE_ENDORSEMENT,)),
    "039": frozenset((_K.COLLECTION_ENDORSEMENT,)),
    "040": frozenset((_K.COLLECTION_REVOCATION,)),
    "043": _MANDATE,
    "044": frozenset(
        (_K.MANDATE_TERMINATION, _K.MANDATE_RATIFICATION, _K.MANDATE_NO_PENDING_ACTS)
    ),
    "047": frozenset((_K.WITHOUT_RECOURSE,)),
    "048": frozenset((_K.PROTEST,)),
    "049": frozenset((_K.ECONOMIC_RIGHTS_TRANSFER,)),
}


def validate_event_notes(
    notes: tuple[EventNote, ...],
    *,
    code: str,
    operation: str,
    mandatee_organization: OrganizationType | None = None,
) -> None:
    """Validate purposes, alternatives and conditional positions before signing.

    Representation is conditional and cannot be inferred from the certificate.
    Additional notes never substitute for a required declaration. Text equivalence
    and business facts remain the caller's responsibility.
    """
    note_inputs(
        notes, maximum=10_000 if code in {"030", "031", "032", "033", "034"} else 5000
    )
    allowed = {_K.ADDITIONAL, _K.MANDATE_REPRESENTATION, *_SPECIFIC.get(code, ())}
    if code in {"037", "038", "039", "040", "047"}:
        allowed.add(_K.ACTING_CAPACITY)
    kinds = [note.kind for note in notes]
    for kind in kinds:
        if kind not in allowed:
            raise ValueError(
                f"Note purpose {kind.value} is not applicable to event {code}."
            )
        if (
            kind
            in {_K.MANDATE_REPRESENTATION, _K.SPECIAL_PAYMENT_TERMS, *_TACIT, *_MANDATE}
            and kinds.count(kind) > 1
        ):
            raise ValueError(f"Note purpose {kind.value} must occur at most once.")
    represented = _K.MANDATE_REPRESENTATION in kinds
    if represented and kinds[0] is not _K.MANDATE_REPRESENTATION:
        raise ValueError("The mandate representation must be the first note.")
    required: set[EventNoteKind] = set()
    alternatives: frozenset[EventNoteKind] = frozenset()
    if code == "034":
        alternatives = _TACIT
        if represented == (_K.TACIT_ACCEPTANCE_DIRECT in kinds):
            raise ValueError(
                "The sworn statement must match direct or mandated emission."
            )
    elif code == "035":
        alternatives = _GUARANTEE
    elif code == "043":
        alternatives = _MANDATE
        expected = (
            _K.MANDATE_NATURAL_PERSON
            if mandatee_organization is OrganizationType.NATURAL_PERSON
            else _K.MANDATE_LEGAL_PERSON
        )
        required.add(expected)
    elif code == "044":
        required.add(_K.MANDATE_TERMINATION)
        if operation == "442":
            required.add(_K.MANDATE_NO_PENDING_ACTS)
        if _K.MANDATE_RATIFICATION in kinds and operation != "441":
            raise ValueError("Ratification is only applicable to revocation 441.")
        if _K.MANDATE_NO_PENDING_ACTS in kinds and operation != "442":
            raise ValueError("No-pending-acts declaration is only applicable to 442.")
    for op, kind in (
        ("372", _K.WITHOUT_RECOURSE),
        ("038", _K.GUARANTEE_ENDORSEMENT),
        ("039", _K.COLLECTION_ENDORSEMENT),
        ("402", _K.COLLECTION_REVOCATION),
    ):
        if operation == op:
            required.add(kind)
    if code == "048":
        required.add(_K.PROTEST)
    if code == "049":
        required.add(_K.ECONOMIC_RIGHTS_TRANSFER)
    if _K.WITHOUT_RECOURSE in kinds and operation not in {"372", "047"}:
        raise ValueError("Without-recourse notes require operation 372 or 047.")
    if _K.COLLECTION_REVOCATION in kinds and operation != "402":
        raise ValueError("Collection revocation requires operation 402.")
    if code == "035":
        positions = [i for i, kind in enumerate(kinds) if kind in _GUARANTEE]
        if positions and positions[0] != (1 if represented else 0):
            raise ValueError(
                "The first guarantee declaration is in an invalid note position."
            )
    if alternatives:
        selected = set(kinds) & alternatives
        if not selected or (code != "035" and len(selected) != 1):
            raise ValueError(
                f"Event {code} requires its applicable explicit declaration."
            )
    missing = required - set(kinds)
    if missing:
        names = ", ".join(sorted(kind.value for kind in missing))
        raise ValueError(
            f"Event {code}/{operation} requires explicit declarations: {names}."
        )
    # Annex Note[2] follows representation, without inserting a blank Note[1]
    # when representation is not applicable. 044 has its own paired statements.
    positioned = (required | (set(kinds) & alternatives)) - {_K.MANDATE_TERMINATION}
    if code == "044":
        positioned |= set(kinds) & {_K.MANDATE_RATIFICATION}
    for kind in positioned:
        if code == "035" and kinds.index(kind) > (1 if represented else 0):
            continue  # Several guarantors may supply several applicable statements.
        expected_index = 1 if represented else 0
        if code == "044" and not represented:
            expected_index = 1
        if kinds.index(kind) != expected_index:
            raise ValueError(
                f"Declaration {kind.value} is in an invalid note position."
            )
