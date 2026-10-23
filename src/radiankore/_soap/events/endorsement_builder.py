"""RADIAN endorsements, including blank CUDE and multiple ordered participants."""

from decimal import Decimal

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
from radiankore.catalogs import EndorsementForm
from radiankore.environment import Environment
from radiankore.models.events import EndorsementEvent, RadianSoftware

_DESCRIPTIONS = {
    "037": "Endoso en Propiedad",
    "038": "Endoso en Garantía",
    "039": "Endoso en Procuración",
    "047": "Endoso con efectos de cesión ordinaria",
}


def build_endorsement(
    event: EndorsementEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Build a financial event without changing participants, prices or rates."""
    first_sender = event.endorsers[0].party
    first_receiver = event.endorsees[0].party
    assert first_receiver is not None
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=None
        if event.form is EndorsementForm.BLANK
        else (first_sender.tax_number if first_sender is not None else None),
        receiver_nit=first_receiver.tax_number,
        software=software,
        environment=environment,
    )
    terms = event.negotiation
    values: list[tuple[str, Decimal | str]] = [("ValorTotalEndoso", terms.total_value)]
    if terms.price is not None:
        assert terms.discount_rate is not None and terms.payment_means is not None
        values.extend(
            (
                ("PrecioPagarseFEV", terms.price),
                ("TasaDescuento", terms.discount_rate),
                ("MedioPago", terms.payment_means.value),
            )
        )
    custom_extension(root, "InformacionNegociacion", tuple(values))
    financial_party(root, "SenderParty", event.endorsers, terms.currency)
    financial_party(root, "ReceiverParty", event.endorsees, terms.currency)
    block, _ = document_response(
        root,
        event.code,
        _DESCRIPTIONS[event.code.value],
        list_id=event.form.value,
    )
    reference = document_reference(block, event.reference)
    if event.debtors:
        issuer = _sub_element(reference, CAC, "IssuerParty")
        for debtor in event.debtors:
            party_tax(issuer, debtor)
    return root
