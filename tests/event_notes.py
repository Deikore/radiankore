"""Synthetic declarations by purpose; these do not assert real business facts."""

from radiankore.catalogs import EventNoteKind
from radiankore.models.events import EventNote


def synthetic_notes(code: str, operation: str | None = None) -> tuple[EventNote, ...]:
    """Build the independently selected minimum declarations plus repeated notes."""
    kinds: list[EventNoteKind] = []
    kind = EventNoteKind
    if code == "034":
        kinds = [kind.TACIT_ACCEPTANCE_DIRECT]
    elif code == "035":
        kinds = [kind.GUARANTEE_LEGAL_PERSON]
    elif code == "043":
        kinds = [kind.MANDATE_LEGAL_PERSON]
    elif code == "044":
        kinds = [kind.MANDATE_TERMINATION]
        if operation == "442":
            kinds.append(kind.MANDATE_NO_PENDING_ACTS)
    elif code == "038":
        kinds = [kind.GUARANTEE_ENDORSEMENT]
    elif code == "039":
        kinds = [kind.COLLECTION_ENDORSEMENT]
    elif code == "048":
        kinds = [kind.PROTEST]
    elif code == "049":
        kinds = [kind.ECONOMIC_RIGHTS_TRANSFER]
    elif operation == "372":
        kinds = [kind.WITHOUT_RECOURSE]
    elif operation == "402":
        kinds = [kind.COLLECTION_REVOCATION]
    declarations = tuple(
        EventNote(
            kind=value,
            text="Con protesto"
            if value is kind.PROTEST
            else ("Declaración sintética; no constituye un acto mercantil real."),
        )
        for value in kinds
    )
    return declarations + additional_notes("Nota repetida", "Nota repetida")


def additional_notes(*texts: str) -> tuple[EventNote, ...]:
    """Keep original free text, order and intentional duplicates."""
    return tuple(EventNote(kind=EventNoteKind.ADDITIONAL, text=text) for text in texts)
