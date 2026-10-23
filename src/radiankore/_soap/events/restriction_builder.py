"""Authority restrictions and termination with distinct invoice/event references."""

from decimal import Decimal

from lxml import etree

from radiankore._soap.events.attachments import attach_pdf
from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    DIAN_PARTY,
    custom_extension,
    document_reference,
    document_response,
    event_root,
    named_xml_party,
    party_tax,
)
from radiankore._soap.namespaces import CAC
from radiankore.environment import Environment
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    RadianSoftware,
)


def build_restriction(
    event: CirculationRestrictionEvent | CirculationRestrictionTerminationEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Attach exact PDF evidence and preserve authorities and officials in order."""
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.authorities[0].tax_number,
        receiver_nit=DIAN_PARTY.tax_number,
        software=software,
        environment=environment,
    )
    if isinstance(event, CirculationRestrictionEvent):
        values: tuple[tuple[str, Decimal], ...] = (
            ("MontoMedidaCautelar", event.measure_value),
        )
        description = (
            "Limitaciones a la circulación de la "
            "factura electrónica de venta como título"
        )
    else:
        values = (
            ("ValorDeuda", event.debt_value),
            ("ValorLimitación", event.restriction_value),
        )
        description = (
            "Terminación de las limitaciones a la circulación "
            "de la factura electrónica de venta como título"
        )
    custom_extension(root, "InformacionMedidaCautelar", values)
    sender = _sub_element(root, CAC, "SenderParty")
    for authority in event.authorities:
        party_tax(sender, authority)
    named_xml_party(root, "ReceiverParty", DIAN_PARTY)
    block, _ = document_response(root, event.code, description)
    reference = document_reference(block, event.reference, include_due=False)
    attach_pdf(reference, event.attachment)
    issuer = _sub_element(reference, CAC, "IssuerParty")
    for official in event.officials:
        party_tax(issuer, official)
    return root
