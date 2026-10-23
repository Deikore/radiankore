"""Immutable emission payloads for RADIAN events."""

from radiankore.models.events.attachments import (
    RadianPdfAttachment,
)
from radiankore.models.events.economic_rights import (
    EconomicRightsNotificationEvent,
    EconomicRightsPaymentEvent,
    EconomicRightsTransferEvent,
    EconomicRightsTransferTerms,
)
from radiankore.models.events.endorsements import (
    EndorsementCancellationEvent,
    EndorsementEvent,
    NegotiationTerms,
)
from radiankore.models.events.guarantees import (
    GuaranteeBeneficiary,
    GuaranteeCommitment,
    GuaranteeEvent,
)
from radiankore.models.events.invoice import (
    InvoiceEventDocumentReference,
    InvoiceEventParty,
    InvoiceEventPerson,
    InvoiceResponseEvent,
)
from radiankore.models.events.mandate import (
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateParty,
    MandatePerson,
    MandateScope,
    MandateValidityPeriod,
)
from radiankore.models.events.mandate_termination import MandateTerminationEvent
from radiankore.models.events.payments import InvoicePaymentEvent, PaymentReportEvent
from radiankore.models.events.prepared import (
    PreparedRadianEvent,
    RadianSoftware,
)
from radiankore.models.events.protests import (
    ProtestAct,
    ProtestEvent,
    ProtestNotary,
)
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    RadianEventReference,
    RadianInvoiceReference,
    RadianParticipation,
    RadianParty,
    RadianPerson,
)
from radiankore.models.events.registration import (
    RadianRegistrationEvent,
    RegistrationPaymentState,
)
from radiankore.models.events.restrictions import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
)

type RadianEvent = (
    InvoiceResponseEvent
    | MandateEvent
    | MandateTerminationEvent
    | GuaranteeEvent
    | EconomicRightsTransferEvent
    | EconomicRightsNotificationEvent
    | EconomicRightsPaymentEvent
    | CirculationRestrictionEvent
    | CirculationRestrictionTerminationEvent
    | ProtestEvent
    | RadianRegistrationEvent
    | InvoicePaymentEvent
    | PaymentReportEvent
    | EndorsementEvent
    | EndorsementCancellationEvent
)

__all__ = [
    "CirculationRestrictionEvent",
    "CirculationRestrictionTerminationEvent",
    "EconomicRightsNotificationEvent",
    "EconomicRightsPaymentEvent",
    "EconomicRightsTransferEvent",
    "EconomicRightsTransferTerms",
    "EndorsementCancellationEvent",
    "EndorsementEvent",
    "GuaranteeBeneficiary",
    "GuaranteeCommitment",
    "GuaranteeEvent",
    "InvoiceEventDocumentReference",
    "InvoiceEventParty",
    "InvoiceEventPerson",
    "InvoicePaymentEvent",
    "InvoiceResponseEvent",
    "MandateAttachedDocument",
    "MandateDocumentReference",
    "MandateEvent",
    "MandateParty",
    "MandatePerson",
    "MandateScope",
    "MandateTerminationEvent",
    "MandateValidityPeriod",
    "NegotiationTerms",
    "PaymentReportEvent",
    "PreparedRadianEvent",
    "ProtestAct",
    "ProtestEvent",
    "ProtestNotary",
    "RadianEvent",
    "RadianEventHeader",
    "RadianEventReference",
    "RadianInvoiceReference",
    "RadianParticipation",
    "RadianParty",
    "RadianPdfAttachment",
    "RadianPerson",
    "RadianRegistrationEvent",
    "RadianSoftware",
    "RegistrationPaymentState",
]
