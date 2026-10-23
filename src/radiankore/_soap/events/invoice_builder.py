"""FE 1.9 ApplicationResponse serialization for events 030-034.

See sections 6.5.4-6.5.5, rejection rules 8.5-8.6 and CUDE section 11.5.
Shared UBL primitives do not imply a shared mandate/invoice document profile.
"""

from hashlib import sha384

from lxml import etree

from radiankore._soap.events.common import (
    _NSMAP,
    _build_dian_extensions,
    _party_tax_scheme,
    _person,
    _sub_element,
)
from radiankore._soap.events.cude import (
    colombian_issue_datetime,
    compute_application_response_cude,
)
from radiankore._soap.namespaces import AR, CAC, CBC
from radiankore.catalogs import EventType, IdentificationType, OrganizationType
from radiankore.environment import Environment
from radiankore.models.events import (
    InvoiceEventParty,
    InvoiceResponseEvent,
    RadianSoftware,
)

_DIAN_PARTY = InvoiceEventParty(
    name="Unidad Administrativa Especial Dirección de Impuestos y Aduanas Nacionales",
    tax_number="800197268",
    identification_type=IdentificationType.NIT,
    verification_digit="4",
    organization_type=OrganizationType.LEGAL_PERSON,
)
# EventType.label is a display catalog, not the wire literal required by AAH04.
_DESCRIPTIONS = {
    EventType.INVOICE_ACKNOWLEDGEMENT: (
        "Acuse de recibo de Factura Electrónica de Venta"
    ),
    EventType.INVOICE_CLAIM: "Reclamo de la Factura Electrónica de Venta",
    EventType.GOODS_OR_SERVICES_RECEIPT: "Recibo del bien y/o prestación del servicio",
    EventType.EXPRESS_ACCEPTANCE: "Aceptación expresa",
    EventType.TACIT_ACCEPTANCE: "Aceptación Tácita",
}


def _party(parent: etree._Element, tag: str, party: InvoiceEventParty) -> None:
    _party_tax_scheme(
        _sub_element(parent, CAC, tag),
        name=party.name,
        number=party.tax_number,
        kind=party.identification_type,
        digit=party.verification_digit,
        organization_type=party.organization_type,
        tax_scheme=party.tax_scheme,
    )


def build_invoice_application_response(
    event: InvoiceResponseEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Build an unsigned invoice event; every hash uses the serialized values."""
    receiver = (
        _DIAN_PARTY
        if event.code is EventType.TACIT_ACCEPTANCE
        else (event.receiver_party)
    )
    assert receiver is not None  # Validated by the public immutable model.
    ref = event.document_reference
    stamp = colombian_issue_datetime(event.issue_date, event.issue_time)
    cude = compute_application_response_cude(
        event_number=event.event_number,
        issue_date=event.issue_date,
        issue_time=event.issue_time,
        issuer_nit=event.sender_party.tax_number,
        receiver_nit=receiver.tax_number,
        response_code=event.code.value,
        document_number=ref.document_number,
        document_type_code=ref.document_type.value,
        software_pin=software.pin,
    )
    root = etree.Element(f"{{{AR}}}ApplicationResponse", nsmap=_NSMAP)  # type: ignore[arg-type]
    host = (
        "catalogo-vpfe.dian.gov.co"
        if environment is Environment.PRODUCTION
        else "catalogo-vpfe-hab.dian.gov.co"
    )
    _build_dian_extensions(
        root,
        provider_nit=software.provider_tax_number,
        provider_verification_digit=software.provider_verification_digit,
        software_id=software.software_id,
        software_security_code=sha384(
            (software.software_id + software.pin + event.event_number).encode("utf-8")
        ).hexdigest(),
        authorization_provider_nit="800197268",
        authorization_provider_dv="4",
        qr_code=f"https://{host}/document/searchqr?documentkey={ref.uuid}",
    )
    _sub_element(root, CBC, "UBLVersionID", "UBL 2.1")
    _sub_element(root, CBC, "CustomizationID", "1")
    _sub_element(
        root,
        CBC,
        "ProfileID",
        "DIAN 2.1: ApplicationResponse de Factura Electrónica de Venta",
    )
    code = environment.profile_execution_id
    _sub_element(root, CBC, "ProfileExecutionID", code)
    _sub_element(root, CBC, "ID", event.event_number)
    uuid = _sub_element(root, CBC, "UUID", cude)
    uuid.set("schemeID", code)
    uuid.set("schemeName", "CUDE-SHA384")
    _sub_element(root, CBC, "IssueDate", stamp.date().isoformat())
    _sub_element(root, CBC, "IssueTime", stamp.timetz().isoformat(timespec="seconds"))
    for note in event.notes:
        _sub_element(root, CBC, "Note", note)
    _party(root, "SenderParty", event.sender_party)
    _party(root, "ReceiverParty", receiver)
    response = _sub_element(root, CAC, "DocumentResponse")
    detail = _sub_element(response, CAC, "Response")
    response_code = _sub_element(detail, CBC, "ResponseCode", event.code.value)
    if event.claim_reason is not None:
        response_code.set("listID", event.claim_reason.value)
        response_code.set("name", event.claim_reason.label)
    _sub_element(detail, CBC, "Description", _DESCRIPTIONS[event.code])
    reference = _sub_element(response, CAC, "DocumentReference")
    _sub_element(reference, CBC, "ID", ref.document_number)
    _sub_element(reference, CBC, "UUID", ref.uuid).set("schemeName", "CUFE-SHA384")
    _sub_element(reference, CBC, "DocumentTypeCode", ref.document_type.value)
    if event.issuer_person is not None:
        person = event.issuer_person
        _person(
            _sub_element(response, CAC, "IssuerParty"),
            identification_number=person.identification_number,
            identification_type=person.identification_type,
            verification_digit=person.verification_digit,
            first_name=person.first_name,
            family_name=person.family_name,
            job_title=person.job_title,
            organization_department=person.organization_department,
        )
    return root
