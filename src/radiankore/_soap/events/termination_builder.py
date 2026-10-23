"""RADIAN 044 and 040 serializers for references to existing events."""

from lxml import etree

from radiankore._soap.events.common import _person
from radiankore._soap.events.radian_common import (
    DIAN_PARTY,
    document_reference,
    document_response,
    event_root,
    named_xml_party,
)
from radiankore.environment import Environment
from radiankore.models.events import (
    EndorsementCancellationEvent,
    MandateTerminationEvent,
    RadianSoftware,
)


def build_termination(
    event: MandateTerminationEvent | EndorsementCancellationEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Build the event with its original target CUDE and caller declarations."""
    receiver = (
        DIAN_PARTY
        if isinstance(event, MandateTerminationEvent)
        else event.receiver_party
    )
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.sender_party.tax_number,
        receiver_nit=receiver.tax_number,
        software=software,
        environment=environment,
    )
    sender = named_xml_party(root, "SenderParty", event.sender_party)
    if isinstance(event, MandateTerminationEvent):
        for person in event.representatives:
            _person(
                sender,
                identification_number=person.identification_number,
                identification_type=person.identification_type,
                verification_digit=person.verification_digit,
                first_name=person.first_name,
                family_name=person.family_name,
                job_title=person.job_title,
                nationality_id=person.nationality_id,
                organization_department=person.organization_department,
            )
    named_xml_party(root, "ReceiverParty", receiver)
    block, _ = document_response(
        root,
        event.code,
        "Terminacion del Mandato"
        if isinstance(event, MandateTerminationEvent)
        else "Cancelación de endoso",
    )
    document_reference(block, event.reference)
    return root
