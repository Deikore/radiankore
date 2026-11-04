"""Independent declaration contracts, including facts that must not be inferred."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime

import pytest
from lxml import etree

from radiankore.catalogs import EventNoteKind, OrganizationType
from radiankore.models.events import (
    EventNote,
    MandateContractForm,
    MandateEvent,
    MandateNotary,
    MandateRepresentation,
    MandateTerminationDeclaration,
    MandateTerminationEvent,
    RadianEvent,
    RadianSoftware,
)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("declarant", None, TypeError),
        ("contract_form", "escrito", TypeError),
        ("chamber_of_commerce_city", "", ValueError),
    ],
)
def test_declaration_invalid_facts(
    mandate_event: MandateEvent, field: str, value: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        replace(mandate_event.declaration, **{field: value})  # type: ignore[arg-type]


def test_no_guessed_representative_or_city(mandate_event: MandateEvent) -> None:
    with pytest.raises(ValueError, match="declarant"):
        replace(
            mandate_event,
            declaration=replace(
                mandate_event.declaration,
                declarant=replace(
                    mandate_event.declaration.declarant, first_name="Another"
                ),
            ),
        )
    with pytest.raises(ValueError, match="chamber"):
        replace(
            mandate_event,
            declaration=replace(
                mandate_event.declaration, chamber_of_commerce_city=None
            ),
        )
    with pytest.raises(TypeError, match="declaration"):
        replace(mandate_event, declaration=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="ADDITIONAL"):
        replace(mandate_event, additional_notes=(mandate_event.notes[1],))


@pytest.mark.parametrize("form", list(MandateContractForm))
def test_literal_legal_declaration(
    mandate_event: MandateEvent, form: MandateContractForm
) -> None:
    event = replace(
        mandate_event,
        declaration=replace(mandate_event.declaration, contract_form=form),
        additional_notes=(),
    )
    assert (
        event.notes[0].text
        == "Synthetic Mandatee OBRANDO EN NOMBRE Y REPRESENTACION DE Synthetic Mandator"
    )
    assert event.notes[1].text == (
        "Synthetic Representative, identificado con el documento "
        "Cédula de ciudadanía No. 100000001, "
        "en mi calidad de representante legal de la sociedad Synthetic Mandatee, "
        "según consta en el certificado de existencia y representación legal expedido "
        "por la Cámara de Comercio de Bogotá, expresamente manifiesto que obro en "
        "nombre y representación de Synthetic Mandator, de conformidad con el contrato "
        f"de mandato {form.value} existente entre las partes y con las facultades "
        "señaladas en el presente documento y "
        "por el tiempo consignado en este documento."
    )
    natural = replace(
        event,
        mandatee_party=replace(
            event.mandatee_party, organization_type=OrganizationType.NATURAL_PERSON
        ),
        declaration=replace(event.declaration, chamber_of_commerce_city=None),
    )
    assert natural.notes[1].kind is EventNoteKind.MANDATE_NATURAL_PERSON
    assert "Cámara" not in natural.notes[1].text


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("effective_date", datetime(2026, 1, 1), TypeError),
        ("ratify_acts", 1, TypeError),
        ("no_pending_acts", 1, TypeError),
        ("representation", "manual", TypeError),
    ],
)
def test_termination_declaration_invalid_types(
    field: str, value: object, error: type[Exception]
) -> None:
    declaration = MandateTerminationDeclaration(effective_date=date(2026, 1, 1))
    with pytest.raises(error):
        replace(declaration, **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("variant", ["441", "442", "443"])
@pytest.mark.parametrize("represented", [False, True])
def test_termination_order_and_actor(
    radian_event_factory: Callable[[str], RadianEvent], variant: str, represented: bool
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(event, MandateTerminationEvent)
    representation = (
        MandateRepresentation(
            mandatee_name="Synthetic Mandatee", mandator_name="Synthetic Mandator"
        )
        if represented
        else None
    )
    event = replace(
        event,
        declaration=replace(
            event.declaration,
            representation=representation,
            ratify_acts=variant == "441",
        ),
    )
    assert event.sender_party == (
        event.mandatee_party if variant == "442" else event.mandator_party
    )
    assert event.representatives == event.sender_party.representatives
    kinds = [n.kind for n in event.notes]
    assert "2026-10-22" in event.notes[-1 if represented else 0].text
    if variant in ("441", "442"):
        assert kinds[1] is (
            EventNoteKind.MANDATE_RATIFICATION
            if variant == "441"
            else EventNoteKind.MANDATE_NO_PENDING_ACTS
        )
    if represented:
        assert kinds[0] is EventNoteKind.MANDATE_REPRESENTATION
    extra = EventNote(kind=EventNoteKind.ADDITIONAL, text="Repeated")
    assert replace(event, additional_notes=(extra, extra)).notes[-2:] == (extra, extra)
    for changes in (
        {"header": replace(event.header, notes=(extra,))},
        {"declaration": None},
        {"mandator_party": None},
        {"mandatee_party": event.mandator_party},
        {"additional_notes": (event.notes[0],)},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(event, **changes)
    if variant != "442":
        with pytest.raises(ValueError, match="442"):
            replace(event, declaration=replace(event.declaration, no_pending_acts=True))
    else:
        with pytest.raises(ValueError, match="no_pending_acts"):
            replace(
                event, declaration=replace(event.declaration, no_pending_acts=False)
            )
        with pytest.raises(ValueError, match="revocation"):
            replace(event, declaration=replace(event.declaration, ratify_acts=True))


def test_notary_is_a_separate_identity() -> None:
    notary = MandateNotary(
        identification_number="900000001",
        verification_digit="2",
        first_name="Synthetic",
        family_name="Notary",
        job_title="Notario",
        office_number="5",
    )
    for field, maximum in [
        ("first_name", 100),
        ("family_name", 100),
        ("job_title", 100),
        ("office_number", 200),
    ]:
        assert (
            getattr(replace(notary, **{field: "X" * maximum}), field) == "X" * maximum
        )
        for invalid in ("", " ", "X" * (maximum + 1)):
            with pytest.raises(ValueError):
                replace(notary, **{field: invalid})


def test_mandate_nit_integrity_and_natural_identity(
    mandate_event: MandateEvent,
) -> None:
    from radiankore.catalogs import IdentificationType

    person = mandate_event.declaration.declarant
    valid = replace(
        person,
        identification_type=IdentificationType.NIT,
        identification_number="900000001",
        verification_digit="2",
    )
    assert valid.verification_digit == "2"
    with pytest.raises(ValueError, match="verification_digit"):
        replace(valid, verification_digit="1")
    party = replace(
        mandate_event.sender_party,
        identification_type=IdentificationType.CITIZENSHIP_CARD,
        tax_number="100000001",
        verification_digit=None,
    )
    assert party.tax_number == "100000001"
    with pytest.raises(ValueError, match="verification_digit"):
        replace(mandate_event.sender_party, verification_digit="9")


@pytest.mark.parametrize(
    "field", ["job_title", "nationality_id", "organization_department"]
)
def test_other_families_keep_optional_person_fields(field: str) -> None:
    from radiankore.catalogs import IdentificationType
    from radiankore.models.events import RadianPerson

    person = RadianPerson(
        identification_number="100000099",
        identification_type=IdentificationType.CITIZENSHIP_CARD,
        first_name="Synthetic",
        family_name="Representative",
    )
    assert getattr(person, field) is None
    changed = replace(person, **{field: "Explicit value"})  # type: ignore[arg-type]
    assert getattr(changed, field) == "Explicit value"
    with pytest.raises(ValueError, match=field):
        replace(person, **{field: ""})  # type: ignore[arg-type]


def test_special_power_omits_notarial_metadata(mandate_event: MandateEvent) -> None:
    from radiankore.models.events import MandateNotary

    notary = MandateNotary(
        identification_number="900000001",
        verification_digit="2",
        first_name="Test",
        family_name="Notary",
        job_title="Notario",
        office_number="1",
    )
    for contract in (
        replace(mandate_event.attached_contract, issuers=(notary,)),
        replace(mandate_event.attached_contract, effective_date=date(2026, 1, 1)),
    ):
        with pytest.raises(ValueError, match="Special powers"):
            replace(mandate_event, attached_contract=contract)


def test_termination_rejects_wrong_identity_context(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    from radiankore.catalogs import IdentificationType

    event = radian_event_factory("441")
    assert isinstance(event, MandateTerminationEvent)
    with pytest.raises(ValueError, match="generator"):
        replace(
            event,
            mandator_party=replace(
                event.mandator_party,
                identification_type=IdentificationType.CITIZENSHIP_CARD,
                verification_digit=None,
            ),
        )
    for representation in (
        MandateRepresentation(
            mandator_name="Other Mandator", mandatee_name=event.mandatee_party.name
        ),
        MandateRepresentation(
            mandator_name=event.mandator_party.name, mandatee_name="Other Mandatee"
        ),
    ):
        with pytest.raises(ValueError, match="original mandate"):
            replace(
                event,
                declaration=replace(event.declaration, representation=representation),
            )


@pytest.mark.parametrize("mutation", ["scope", "all_type", "note_order", "vigency"])
def test_mandate_oracle_rejects_xsd_valid_mutations(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
    mutation: str,
) -> None:

    from radiankore import Environment
    from radiankore._soap.events import build_mandate_application_response
    from radiankore._soap.namespaces import CAC, CBC
    from radiankore.catalogs import MandateReferenceType
    from tests.profile_support import assert_profile

    event = replace(
        mandate_event, reference_type=MandateReferenceType.ALL, document_references=()
    )
    root = build_mandate_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    if mutation == "scope":
        node = root.findall(f"{{{CAC}}}DocumentResponse")[1].find(
            f"{{{CAC}}}Response/{{{CBC}}}Description"
        )
        assert node is not None
        node.text = "Mandato con Representación"
    elif mutation == "all_type":
        ref = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}DocumentReference")
        assert ref is not None
        etree.SubElement(ref, f"{{{CBC}}}DocumentTypeCode").text = "01"
        ref.insert(1, ref[-1])
    elif mutation == "note_order":
        notes = root.findall(f"{{{CBC}}}Note")
        notes[0].text, notes[1].text = notes[1].text, notes[0].text
    else:
        node = root.find(
            f"{{{CAC}}}DocumentResponse/{{{CAC}}}DocumentReference/"
            f"{{{CAC}}}ValidityPeriod/{{{CBC}}}Description"
        )
        assert node is not None
        node.text = "Tiempo limitado"
    if radian_schema is not None:
        radian_schema.assertValid(root)
    with pytest.raises(AssertionError):
        assert_profile(root, "043", Environment.PRODUCTION)
