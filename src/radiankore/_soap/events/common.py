"""Shared UBL primitives; builders retain their event-specific document profiles."""

from lxml import etree

from radiankore._soap.namespaces import AR, CAC, CBC, DS, EXT, STS, XADES, XADES141, XSI
from radiankore.catalogs import IdentificationType, OrganizationType, PartyTaxScheme

_DIAN_AGENCY_ID = "195"
_DIAN_AGENCY_NAME = "CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
_NSMAP = {
    None: AR,
    "cac": CAC,
    "cbc": CBC,
    "ds": DS,
    "ext": EXT,
    "sts": STS,
    "xades": XADES,
    "xades141": XADES141,
    "xsi": XSI,
}


def _sub_element(
    parent: etree._Element, ns: str, tag: str, text: str | None = None
) -> etree._Element:
    node = etree.SubElement(parent, f"{{{ns}}}{tag}")
    node.text = text
    return node


def _identified(
    parent: etree._Element,
    tag: str,
    number: str,
    kind: IdentificationType,
    digit: str | None,
) -> etree._Element:
    node = _sub_element(parent, CBC, tag, number)
    node.set("schemeName", kind.value)
    if digit is not None:
        node.set("schemeID", digit)
    return node


def _person(
    parent: etree._Element,
    *,
    identification_number: str,
    identification_type: IdentificationType,
    verification_digit: str | None,
    first_name: str,
    family_name: str,
    job_title: str | None,
    organization_department: str | None,
    nationality_id: str | None = None,
) -> None:
    """Serialize shared person fields without depending on event-specific models."""
    node = _sub_element(parent, CAC, "Person")
    _identified(
        node, "ID", identification_number, identification_type, verification_digit
    )
    for tag, value in (
        ("FirstName", first_name),
        ("FamilyName", family_name),
        ("JobTitle", job_title),
        ("NationalityID", nationality_id),
        ("OrganizationDepartment", organization_department),
    ):
        if value is not None:
            _sub_element(node, CBC, tag, value)


def _party_tax_scheme(
    parent: etree._Element,
    *,
    name: str | None,
    number: str,
    kind: IdentificationType,
    digit: str | None,
    organization_type: OrganizationType = OrganizationType.LEGAL_PERSON,
    tax_scheme: PartyTaxScheme = PartyTaxScheme.VAT,
) -> None:
    node = _sub_element(parent, CAC, "PartyTaxScheme")
    if name is not None:
        _sub_element(node, CBC, "RegistrationName", name)
    company = _identified(node, "CompanyID", number, kind, digit)
    company.set("schemeAgencyID", _DIAN_AGENCY_ID)
    company.set("schemeAgencyName", _DIAN_AGENCY_NAME)
    company.set("schemeVersionID", organization_type.value)
    tax = _sub_element(node, CAC, "TaxScheme")
    _sub_element(tax, CBC, "ID", tax_scheme.value)
    _sub_element(tax, CBC, "Name", tax_scheme.label)


def _build_dian_extensions(
    root: etree._Element,
    *,
    provider_nit: str,
    provider_verification_digit: str,
    software_id: str,
    software_security_code: str,
    authorization_provider_nit: str,
    authorization_provider_dv: str,
    qr_code: str,
) -> None:
    extensions = _sub_element(root, EXT, "UBLExtensions")
    extension = _sub_element(extensions, EXT, "UBLExtension")
    content = _sub_element(extension, EXT, "ExtensionContent")
    dian = _sub_element(content, STS, "DianExtensions")

    source = _sub_element(dian, STS, "InvoiceSource")
    id_code = _sub_element(source, CBC, "IdentificationCode", "CO")
    id_code.set("listAgencyID", "6")
    id_code.set("listAgencyName", "United Nations Economic Commission for Europe")
    id_code.set(
        "listSchemeURI",
        "urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1",
    )

    provider = _sub_element(dian, STS, "SoftwareProvider")
    provider_id = _sub_element(provider, STS, "ProviderID", provider_nit)
    provider_id.set("schemeID", provider_verification_digit)
    provider_id.set("schemeName", IdentificationType.NIT.value)
    provider_id.set("schemeAgencyID", _DIAN_AGENCY_ID)
    provider_id.set("schemeAgencyName", _DIAN_AGENCY_NAME)
    software = _sub_element(provider, STS, "SoftwareID", software_id)
    software.set("schemeAgencyID", _DIAN_AGENCY_ID)
    software.set("schemeAgencyName", _DIAN_AGENCY_NAME)

    security = _sub_element(dian, STS, "SoftwareSecurityCode", software_security_code)
    security.set("schemeAgencyID", _DIAN_AGENCY_ID)
    security.set("schemeAgencyName", _DIAN_AGENCY_NAME)

    auth = _sub_element(dian, STS, "AuthorizationProvider")
    auth_id = _sub_element(
        auth, STS, "AuthorizationProviderID", authorization_provider_nit
    )
    auth_id.set("schemeID", authorization_provider_dv)
    auth_id.set("schemeName", IdentificationType.NIT.value)
    auth_id.set("schemeAgencyID", _DIAN_AGENCY_ID)
    auth_id.set("schemeAgencyName", _DIAN_AGENCY_NAME)

    _sub_element(dian, STS, "QRCode", qr_code)
