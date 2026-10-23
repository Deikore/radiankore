"""RADIAN economic-rights transfer, notification and payment serialization."""

from lxml import etree

from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    custom_extension,
    document_reference,
    document_response,
    event_root,
    financial_party,
    party_tax,
)
from radiankore._soap.namespaces import CAC
from radiankore.environment import Environment
from radiankore.models.events import EconomicRightsTransferEvent, RadianSoftware


def build_economic_rights_transfer(
    event: EconomicRightsTransferEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Serialize the explicit assignment without applying endorsement-only rules."""
    first_sender, first_receiver = (
        event.transferors[0].party,
        event.transferees[0].party,
    )
    assert first_sender is not None and first_receiver is not None
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=first_sender.tax_number,
        receiver_nit=first_receiver.tax_number,
        software=software,
        environment=environment,
    )
    terms = event.terms
    custom_extension(
        root,
        "InformacionTransferenciaDerechos",
        (
            ("ValorTransferenciaDerechos", terms.transferred_value),
            ("PrecioPagarseFEV", terms.price),
            ("FactordeDescuento", terms.discount_factor),
            ("MedioPago", terms.payment_means.value),
        ),
    )
    financial_party(root, "SenderParty", event.transferors, terms.currency)
    financial_party(root, "ReceiverParty", event.transferees, terms.currency)
    block, _ = document_response(
        root, event.code, "Transferencia de los derechos económicos"
    )
    reference = document_reference(block, event.reference)
    issuer = _sub_element(reference, CAC, "IssuerParty")
    for party in event.debtors:
        party_tax(issuer, party)
    return root
