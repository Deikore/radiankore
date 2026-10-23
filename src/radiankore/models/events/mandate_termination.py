"""RADIAN 044: revocation, resignation and rejection of a mandate."""

from dataclasses import dataclass

from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianEventReference,
    RadianParty,
    RadianPerson,
    event_inputs,
    named_party,
    operation,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MandateTerminationEvent:
    """Terminate a prior mandate; declarations and represented acts are explicit."""

    header: RadianEventHeader
    operation_type: RadianOperationType
    sender_party: RadianParty
    representatives: tuple[RadianPerson, ...]
    reference: RadianEventReference

    def __post_init__(self) -> None:
        operation(self.operation_type, ("441", "442", "443"))
        event_inputs(self.header, self.reference, RadianEventReference)
        named_party(self.sender_party, sender=True)
        if not isinstance(self.representatives, tuple) or not self.representatives:
            raise ValueError("representatives must be a nonempty tuple.")
        if not all(isinstance(p, RadianPerson) for p in self.representatives):
            raise TypeError("representatives must contain RadianPerson instances.")
        if not self.header.notes:
            raise ValueError("Mandate termination requires an explicit declaration.")

    @property
    def code(self) -> EventType:
        """Return the fixed event code independently of the operation variant."""
        return EventType.MANDATE_TERMINATION
