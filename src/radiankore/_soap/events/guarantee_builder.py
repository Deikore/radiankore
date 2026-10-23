"""RADIAN guarantee serialization preserving zero-as-full-coverage commitments."""

from lxml import etree

from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    DIAN_PARTY,
    custom_extension,
    decimal_text,
    document_reference,
    document_response,
    event_root,
    legal_entity,
    named_xml_party,
    party_tax,
)
from radiankore._soap.namespaces import CAC, CBC
from radiankore.environment import Environment
from radiankore.models.events import GuaranteeEvent, RadianSoftware


def build_guarantee(
    event: GuaranteeEvent, *, software: RadianSoftware, environment: Environment
) -> etree._Element:
    """Emit guarantors and optional beneficiaries without inventing identities."""
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.guarantors[0].party.tax_number,
        receiver_nit=DIAN_PARTY.tax_number,
        software=software,
        environment=environment,
    )
    custom_extension(root, "InformacionAvalar", (("ValorFEVavala", event.title_value),))
    sender = _sub_element(root, CAC, "SenderParty")
    for commitment in event.guarantors:
        party_tax(sender, commitment.party)
    for commitment in event.guarantors:
        legal_entity(sender, commitment.party)
        _sub_element(
            sender[-1], CBC, "CorporateStockAmount", decimal_text(commitment.amount)
        ).set("currencyID", event.currency.value)
    named_xml_party(root, "ReceiverParty", DIAN_PARTY)
    block, _ = document_response(root, event.code, "Aval")
    document_reference(block, event.reference, include_due=False)
    if event.beneficiaries:
        issuer = _sub_element(block, CAC, "IssuerParty")
        for beneficiary in event.beneficiaries:
            legal_entity(issuer, beneficiary.party)
            if beneficiary.amount is not None:
                _sub_element(
                    issuer[-1],
                    CBC,
                    "CorporateStockAmount",
                    decimal_text(beneficiary.amount),
                ).set("currencyID", event.currency.value)
    return root
