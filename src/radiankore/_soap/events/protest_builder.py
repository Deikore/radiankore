"""RADIAN protest with a signed notarial act nested in LineResponse."""

from lxml import etree

from radiankore._soap.events.attachments import attach_pdf
from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    custom_extension,
    document_reference,
    document_response,
    event_root,
    named_xml_party,
)
from radiankore._soap.namespaces import CAC, CBC
from radiankore.environment import Environment
from radiankore.models.events import ProtestEvent, RadianSoftware


def build_protest(
    event: ProtestEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Keep the act date and notary separate from the invoice reference."""
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.sender_party.tax_number,
        receiver_nit=event.receiver_party.tax_number,
        software=software,
        environment=environment,
    )
    values = [("ValorFEV-TV", event.title_value)]
    if event.acceptance_failure is not None:
        customization = root.find(f"{{{CBC}}}CustomizationID")
        assert customization is not None
        customization.set("schemeID", event.acceptance_failure.value)
        assert event.accepted_value is not None and event.pending_value is not None
        values.extend(
            (
                ("ValorAceptado", event.accepted_value),
                ("ValorPendiente", event.pending_value),
            )
        )
    custom_extension(root, "InformacionProtesto", tuple(values))
    named_xml_party(root, "SenderParty", event.sender_party)
    named_xml_party(root, "ReceiverParty", event.receiver_party)
    block, _ = document_response(root, event.code, "Protesto")
    document_reference(block, event.reference)
    line = _sub_element(block, CAC, "LineResponse")
    line_reference = _sub_element(line, CAC, "LineReference")
    _sub_element(line_reference, CBC, "LineID", "1")
    act_reference = _sub_element(line_reference, CAC, "DocumentReference")
    _sub_element(act_reference, CBC, "ID", event.act.notary_number)
    _sub_element(act_reference, CBC, "DocumentDescription", "Acta de Protesto")
    attach_pdf(act_reference, event.act.attachment, protest=True)
    issuer = _sub_element(act_reference, CAC, "IssuerParty")
    for notary in event.act.notaries:
        person = _sub_element(issuer, CAC, "Person")
        for tag, value in (
            ("FirstName", notary.first_name),
            ("FamilyName", notary.family_name),
            ("JobTitle", notary.job_title),
        ):
            _sub_element(person, CBC, tag, value)
    response = _sub_element(line, CAC, "Response")
    _sub_element(
        response, CBC, "Description", "Este documento corresponde al Acta de Protesto"
    )
    _sub_element(response, CBC, "EffectiveDate", event.act.effective_date.isoformat())
    return root
