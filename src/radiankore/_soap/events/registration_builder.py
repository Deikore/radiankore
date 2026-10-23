"""RADIAN 036 registration and payment-state extension serialization."""

from lxml import etree

from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    DIAN_PARTY,
    custom_extension,
    document_reference,
    document_response,
    event_root,
    legal_entity,
    named_xml_party,
)
from radiankore._soap.namespaces import CAC
from radiankore.environment import Environment
from radiankore.models.events import RadianRegistrationEvent, RadianSoftware


def build_registration(
    event: RadianRegistrationEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Build all four registration variants without inferring payment history."""
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.sender_party.tax_number,
        receiver_nit=DIAN_PARTY.tax_number,
        software=software,
        environment=environment,
    )
    paid = event.payment_state
    custom_extension(
        root,
        "ConstanciadePagos",
        (
            ("ValorFEV-TV", paid.invoice_value),
            ("ValorPagado", paid.paid_value),
            ("NuevoValorTV", paid.remaining_value),
        ),
    )
    named_xml_party(root, "SenderParty", event.sender_party)
    named_xml_party(root, "ReceiverParty", DIAN_PARTY)
    block, _ = document_response(
        root,
        event.code,
        "Inscripción de la factura electrónica de venta como título valor - RADIAN",
    )
    document_reference(block, event.reference)
    if event.direct_buyer is not None:
        legal_entity(_sub_element(block, CAC, "IssuerParty"), event.direct_buyer)
    return root
