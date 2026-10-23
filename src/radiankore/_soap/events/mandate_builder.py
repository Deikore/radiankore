"""Serialize validated mandate inputs as UBL ApplicationResponse 2.1."""

from base64 import b64encode
from hashlib import sha384

from lxml import etree

from radiankore._soap.events.common import (
    _NSMAP,
    _build_dian_extensions,
    _identified,
    _party_tax_scheme,
    _sub_element,
)
from radiankore._soap.events.common import (
    _person as _build_person,
)
from radiankore._soap.events.cude import colombian_issue_datetime, compute_mandate_cude
from radiankore._soap.namespaces import AR, CAC, CBC
from radiankore.catalogs import IdentificationType, MandateeType
from radiankore.environment import Environment
from radiankore.models.events import (
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateParty,
    MandatePerson,
    MandateScope,
    RadianSoftware,
)


def _person(parent: etree._Element, person: MandatePerson) -> None:
    _build_person(
        parent,
        identification_number=person.identification_number,
        identification_type=person.identification_type,
        verification_digit=person.verification_digit,
        first_name=person.first_name,
        family_name=person.family_name,
        job_title=person.job_title,
        nationality_id=person.nationality_id,
        organization_department=person.organization_department,
    )


def _party(parent: etree._Element, tag: str, party: MandateParty) -> None:
    node = _sub_element(parent, CAC, tag)
    mandatee = isinstance(party.role, MandateeType)
    if not mandatee:
        _party_tax_scheme(
            node,
            name=party.name,
            number=party.tax_number,
            kind=party.identification_type,
            digit=party.verification_digit,
        )
        _person(node, party.representative)
    poa = _sub_element(node, CAC, "PowerOfAttorney")
    _identified(
        poa, "ID", party.tax_number, party.identification_type, party.verification_digit
    )
    _sub_element(poa, CBC, "Description", party.role.label)
    agent = _sub_element(poa, CAC, "AgentParty")
    identification = _sub_element(agent, CAC, "PartyIdentification")
    role = _sub_element(identification, CBC, "ID", party.role.value)
    role.set(
        "schemeDataURI",
        "mandatarioTipo_radian.gc" if mandatee else "mandanteTipo_radian.gc",
    )
    if mandatee:
        _person(agent, party.representative)


def _attachment(
    parent: etree._Element, attachment: MandateAttachedDocument, *, validity_note: bool
) -> None:
    line = _sub_element(parent, CAC, "LineResponse")
    ref = _sub_element(line, CAC, "LineReference")
    _sub_element(ref, CBC, "LineID", "2" if validity_note else "1")
    doc = _sub_element(ref, CAC, "DocumentReference")
    _sub_element(doc, CBC, "ID", attachment.document_id)
    _sub_element(
        doc,
        CBC,
        "DocumentDescription",
        "Evidencia de la nota de Vigencia"
        if validity_note
        else "Evidencia del Contrato de Mandato",
    )
    binary = _sub_element(
        _sub_element(doc, CAC, "Attachment"),
        CBC,
        "EmbeddedDocumentBinaryObject",
        b64encode(attachment.embedded_bytes).decode("ascii"),
    )
    for key, value in (
        ("format", "PDF"),
        ("mimeCode", "PDF"),
        ("encodingCode", "base64, PDF"),
        ("characterSetCode", "base64, PDF"),
        (
            "filename",
            "Nota de Vigencia, PDF" if validity_note else "Contrato de Mandato, PDF",
        ),
    ):
        binary.set(key, value)
    if attachment.issuer is not None:
        _person(_sub_element(doc, CAC, "IssuerParty"), attachment.issuer)
    response = _sub_element(line, CAC, "Response")
    _sub_element(
        response,
        CBC,
        "Description",
        "Este documento corresponde a la nota de vigencia del contrato de mandato"
        if validity_note
        else "Este documento corresponde al contrato de mandato firmado por las partes",
    )
    if not validity_note and attachment.effective_date is not None:
        _sub_element(
            response, CBC, "EffectiveDate", attachment.effective_date.isoformat()
        )


def _reference(
    parent: etree._Element,
    reference: MandateDocumentReference | None,
    *,
    event: MandateEvent,
    environment_code: str,
    primary: bool,
) -> None:
    node = _sub_element(parent, CAC, "DocumentReference")
    _sub_element(
        node, CBC, "ID", "1" if reference is None else reference.document_number
    )
    if reference is not None:
        uuid = _sub_element(node, CBC, "UUID", reference.uuid)
        uuid.set("schemeName", "CUFE-SHA384")
        uuid.set("schemeID", environment_code)
        if primary:
            _sub_element(node, CBC, "DocumentTypeCode", reference.document_type.value)
    if primary:
        period = _sub_element(node, CAC, "ValidityPeriod")
        if event.validity_period.start_date is not None:
            _sub_element(
                period, CBC, "StartDate", event.validity_period.start_date.isoformat()
            )
        if event.validity_period.end_date is not None:
            _sub_element(
                period, CBC, "EndDate", event.validity_period.end_date.isoformat()
            )
        _sub_element(period, CBC, "DescriptionCode", event.time_type.value)
        _sub_element(period, CBC, "Description", event.time_type.label)


def build_mandate_application_response(
    event: MandateEvent, *, software: RadianSoftware, environment: Environment
) -> etree._Element:
    """Return the complete unsigned tree; all hashes use the serialized timestamp."""
    root = etree.Element(f"{{{AR}}}ApplicationResponse", nsmap=_NSMAP)  # type: ignore[arg-type]
    code = environment.profile_execution_id
    stamp = colombian_issue_datetime(event.issue_date, event.issue_time)
    first = event.document_references[0] if event.document_references else None
    cude = compute_mandate_cude(
        event_number=event.event_number,
        issue_date=event.issue_date,
        issue_time=event.issue_time,
        issuer_nit=event.sender_party.tax_number,
        software_pin=software.pin,
        document_number=first.document_number if first else "1",
    )
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
            (software.software_id + software.pin + event.event_number).encode()
        ).hexdigest(),
        authorization_provider_nit="800197268",
        authorization_provider_dv="4",
        qr_code=f"https://{host}/document/searchqr?documentkey={cude}",
    )
    _sub_element(root, CBC, "UBLVersionID", "UBL 2.1")
    customization = _sub_element(
        root, CBC, "CustomizationID", event.operation_type.value
    )
    customization.set("schemeID", event.nature.value)
    _sub_element(
        root,
        CBC,
        "ProfileID",
        "DIAN 2.1: ApplicationResponse de la Factura Electrónica de Venta",
    )
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
    receiver = _sub_element(root, CAC, "ReceiverParty")
    _party_tax_scheme(
        receiver,
        name="Dirección de Impuestos y Aduanas Nacionales",
        number="800197268",
        kind=IdentificationType.NIT,
        digit="4",
    )
    primary = _sub_element(root, CAC, "DocumentResponse")
    response = _sub_element(primary, CAC, "Response")
    response_code = _sub_element(response, CBC, "ResponseCode", "043")
    response_code.set("listID", event.reference_type.value)
    _sub_element(response, CBC, "Description", "Mandato")
    _sub_element(response, CBC, "EffectiveDate", event.effective_date.isoformat())
    refs: tuple[MandateDocumentReference | None, ...] = event.document_references or (
        None,
    )
    for ref in refs:
        _reference(primary, ref, event=event, environment_code=code, primary=True)
    _party(primary, "IssuerParty", event.mandatee_party)
    _attachment(primary, event.attached_contract, validity_note=False)
    if event.attached_validity_note is not None:
        _attachment(primary, event.attached_validity_note, validity_note=True)
    groups: list[tuple[MandateScope, list[MandateDocumentReference | None]]] = []
    for ref in refs:
        scope = ref.scope if ref is not None and ref.scope is not None else event.scope
        for existing, members in groups:
            if existing == scope:
                members.append(ref)
                break
        else:
            groups.append((scope, [ref]))
    for scope, members in groups:
        block = _sub_element(root, CAC, "DocumentResponse")
        response = _sub_element(block, CAC, "Response")
        _sub_element(
            response,
            CBC,
            "ResponseCode",
            ";".join(
                f"{power.value}-{channel.value}" for power, channel in scope.powers
            ),
        )
        _sub_element(response, CBC, "Description", scope.description)
        for ref in members:
            _reference(block, ref, event=event, environment_code=code, primary=False)
        line = _sub_element(block, CAC, "LineResponse")
        _sub_element(_sub_element(line, CAC, "LineReference"), CBC, "LineID", "1")
        acceptance = _sub_element(line, CAC, "Response")
        _sub_element(acceptance, CBC, "ResponseCode", "ACEPTA")
        _sub_element(
            acceptance,
            CBC,
            "Description",
            "Aceptación del Mandato por parte del Mandatario",
        )
    return root
