"""Small private dispatcher for supported RADIAN model families."""

from lxml import etree

from radiankore._soap.events.economic_rights_builder import (
    build_economic_rights_transfer,
)
from radiankore._soap.events.endorsement_builder import build_endorsement
from radiankore._soap.events.guarantee_builder import build_guarantee
from radiankore._soap.events.invoice_builder import build_invoice_application_response
from radiankore._soap.events.mandate_builder import build_mandate_application_response
from radiankore._soap.events.payment_builder import build_payment
from radiankore._soap.events.protest_builder import build_protest
from radiankore._soap.events.registration_builder import build_registration
from radiankore._soap.events.restriction_builder import build_restriction
from radiankore._soap.events.termination_builder import build_termination
from radiankore.environment import Environment
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    EconomicRightsNotificationEvent,
    EconomicRightsPaymentEvent,
    EconomicRightsTransferEvent,
    EndorsementCancellationEvent,
    EndorsementEvent,
    GuaranteeEvent,
    InvoicePaymentEvent,
    InvoiceResponseEvent,
    MandateEvent,
    MandateTerminationEvent,
    PaymentReportEvent,
    ProtestEvent,
    RadianEvent,
    RadianRegistrationEvent,
    RadianSoftware,
)


def build_radian_application_response(
    event: RadianEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Dispatch only supported immutable inputs; never guess a profile from XML."""
    if isinstance(event, InvoiceResponseEvent):
        return build_invoice_application_response(
            event, software=software, environment=environment
        )
    if isinstance(event, MandateEvent):
        return build_mandate_application_response(
            event, software=software, environment=environment
        )
    if isinstance(event, (MandateTerminationEvent, EndorsementCancellationEvent)):
        return build_termination(event, software=software, environment=environment)
    if isinstance(event, RadianRegistrationEvent):
        return build_registration(event, software=software, environment=environment)
    if isinstance(
        event,
        (
            InvoicePaymentEvent,
            InvoiceResponseEvent,
            MandateEvent,
            PaymentReportEvent,
            EconomicRightsNotificationEvent,
            EconomicRightsPaymentEvent,
        ),
    ):
        return build_payment(event, software=software, environment=environment)
    if isinstance(event, EndorsementEvent):
        return build_endorsement(event, software=software, environment=environment)
    if isinstance(event, GuaranteeEvent):
        return build_guarantee(event, software=software, environment=environment)
    if isinstance(event, EconomicRightsTransferEvent):
        return build_economic_rights_transfer(
            event, software=software, environment=environment
        )
    if isinstance(
        event, (CirculationRestrictionEvent, CirculationRestrictionTerminationEvent)
    ):
        return build_restriction(event, software=software, environment=environment)
    if isinstance(event, ProtestEvent):
        return build_protest(event, software=software, environment=environment)
    raise TypeError("event must be a supported RadianEvent model.")
