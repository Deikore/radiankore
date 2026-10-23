"""Shared RADIAN serialization primitives; no public models perform XML work."""

from decimal import Decimal
from hashlib import sha384

from lxml import etree

from radiankore._datetime import colombian_issue_datetime
from radiankore._soap.events.common import (
    _NSMAP,
    _build_dian_extensions,
    _identified,
    _party_tax_scheme,
    _sub_element,
)
from radiankore._soap.events.cude import (
    compute_application_response_cude,
    compute_blank_endorsement_cude,
)
from radiankore._soap.namespaces import AR, CAC, CBC, EXT
from radiankore.catalogs import (
    CurrencyCode,
    EventType,
    IdentificationType,
    OrganizationType,
)
from radiankore.environment import Environment
from radiankore.models.events import (
    RadianEventHeader,
    RadianEventReference,
    RadianInvoiceReference,
    RadianParticipation,
    RadianParty,
    RadianSoftware,
)

DIAN_PARTY = RadianParty(
    name="Dirección de Impuestos y Aduanas Nacionales",
    tax_number="800197268",
    identification_type=IdentificationType.NIT,
    verification_digit="4",
    organization_type=OrganizationType.LEGAL_PERSON,
)


def decimal_text(value: Decimal) -> str:
    """Preserve validated Decimal precision without exponent notation or rounding."""
    return format(value, "f")


def event_root(
    header: RadianEventHeader,
    *,
    code: EventType,
    operation_type: str,
    reference: RadianInvoiceReference | RadianEventReference,
    sender_nit: str | None,
    receiver_nit: str,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Construct the unsigned header and common extensions with real hash inputs."""
    if sender_nit is None:
        cude = compute_blank_endorsement_cude(
            header.event_number,
            header.issue_date,
            header.issue_time,
            receiver_nit,
            code.value,
            reference.document_number,
            software.pin,
        )
    else:
        cude = compute_application_response_cude(
            header.event_number,
            header.issue_date,
            header.issue_time,
            sender_nit,
            software.pin,
            receiver_nit=receiver_nit,
            response_code=code.value,
            document_number=reference.document_number,
            document_type_code=reference.document_type.value,
        )
    root = etree.Element(f"{{{AR}}}ApplicationResponse", nsmap=_NSMAP)  # type: ignore[arg-type]
    host = (
        "catalogo-vpfe.dian.gov.co"
        if environment is Environment.PRODUCTION
        else ("catalogo-vpfe-hab.dian.gov.co")
    )
    _build_dian_extensions(
        root,
        provider_nit=software.provider_tax_number,
        provider_verification_digit=software.provider_verification_digit,
        software_id=software.software_id,
        software_security_code=sha384(
            (software.software_id + software.pin + header.event_number).encode("utf-8")
        ).hexdigest(),
        authorization_provider_nit="800197268",
        authorization_provider_dv="4",
        qr_code=f"https://{host}/document/searchqr?documentkey={reference.uuid}",
    )
    stamp = colombian_issue_datetime(header.issue_date, header.issue_time)
    for tag, value in (
        ("UBLVersionID", "UBL 2.1"),
        ("CustomizationID", operation_type),
        (
            "ProfileID",
            "DIAN 2.1: ApplicationResponse de la Factura Electrónica de Venta",
        ),
        ("ProfileExecutionID", environment.profile_execution_id),
        ("ID", header.event_number),
    ):
        _sub_element(root, CBC, tag, value)
    uuid = _sub_element(root, CBC, "UUID", cude)
    uuid.set("schemeID", environment.profile_execution_id)
    uuid.set("schemeName", "CUDE-SHA384")
    _sub_element(root, CBC, "IssueDate", stamp.date().isoformat())
    _sub_element(root, CBC, "IssueTime", stamp.timetz().isoformat(timespec="seconds"))
    for note in header.notes:
        _sub_element(root, CBC, "Note", note)
    return root


def party_tax(parent: etree._Element, party: RadianParty) -> None:
    """Serialize a party's explicit tax identity and organization."""
    _party_tax_scheme(
        parent,
        name=party.name,
        number=party.tax_number,
        kind=party.identification_type,
        digit=party.verification_digit,
        organization_type=party.organization_type,
        tax_scheme=party.tax_scheme,
    )


def named_xml_party(
    root: etree._Element, tag: str, party: RadianParty
) -> etree._Element:
    """Add a named participant without inventing legal-entity participation."""
    node = _sub_element(root, CAC, tag)
    party_tax(node, party)
    return node


def legal_entity(
    parent: etree._Element,
    party: RadianParty | None,
    *,
    participation: RadianParticipation | None = None,
    currency: CurrencyCode = CurrencyCode.COP,
) -> None:
    """Keep identity/amount pairing and UBL PartyLegalEntity child order."""
    node = _sub_element(parent, CAC, "PartyLegalEntity")
    if party is not None:
        if party.name is not None:
            _sub_element(node, CBC, "RegistrationName", party.name)
        company = _identified(
            node,
            "CompanyID",
            party.tax_number,
            party.identification_type,
            party.verification_digit,
        )
        company.set("schemeAgencyID", "195")
        company.set(
            "schemeAgencyName", "CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
        )
        company.set("schemeVersionID", party.organization_type.value)
    if participation is not None:
        if participation.factor_type is not None:
            _sub_element(
                node, CBC, "CompanyLegalFormCode", participation.factor_type.value
            )
        _sub_element(
            node, CBC, "CorporateStockAmount", decimal_text(participation.amount)
        ).set("currencyID", currency.value)


def financial_party(
    root: etree._Element,
    tag: str,
    participants: tuple[RadianParticipation, ...],
    currency: CurrencyCode,
) -> None:
    """Emit tax identities before legal entities, preserving each tuple's order."""
    node = _sub_element(root, CAC, tag)
    for participant in participants:
        if participant.party is not None:
            party_tax(node, participant.party)
    for participant in participants:
        legal_entity(
            node, participant.party, participation=participant, currency=currency
        )


def document_response(
    root: etree._Element,
    code: EventType,
    description: str,
    *,
    list_id: str | None = None,
) -> tuple[etree._Element, etree._Element]:
    """Return DocumentResponse and its Response in UBL sequence."""
    block = _sub_element(root, CAC, "DocumentResponse")
    response = _sub_element(block, CAC, "Response")
    code_node = _sub_element(response, CBC, "ResponseCode", code.value)
    if list_id is not None:
        code_node.set("listID", list_id)
    _sub_element(response, CBC, "Description", description)
    return block, response


def document_reference(
    block: etree._Element,
    reference: RadianInvoiceReference | RadianEventReference,
    *,
    include_due: bool = True,
) -> etree._Element:
    """Serialize invoice and event references without confusing CUFE and CUDE."""
    node = _sub_element(block, CAC, "DocumentReference")
    _sub_element(node, CBC, "ID", reference.document_number)
    _sub_element(node, CBC, "UUID", reference.uuid).set(
        "schemeName",
        "CUFE-SHA384"
        if isinstance(reference, RadianInvoiceReference)
        else "CUDE-SHA384",
    )
    _sub_element(node, CBC, "DocumentTypeCode", reference.document_type.value)
    if (
        include_due
        and isinstance(reference, RadianInvoiceReference)
        and reference.due_date is not None
    ):
        _sub_element(
            _sub_element(node, CAC, "ValidityPeriod"),
            CBC,
            "EndDate",
            reference.due_date.isoformat(),
        )
    return node


def custom_extension(
    root: etree._Element, name: str, values: tuple[tuple[str, Decimal | str], ...]
) -> None:
    """Add Name/Value pairs in the sample's ApplicationResponse namespace."""
    extensions = root.find(f"{{{EXT}}}UBLExtensions")
    assert extensions is not None
    content = _sub_element(
        _sub_element(extensions, EXT, "UBLExtension"), EXT, "ExtensionContent"
    )
    custom = _sub_element(content, AR, "CustomTagGeneral")
    node = _sub_element(custom, AR, name)
    for key, value in values:
        _sub_element(node, AR, "Name", key)
        _sub_element(
            node,
            AR,
            "Value",
            decimal_text(value) if isinstance(value, Decimal) else value,
        )
