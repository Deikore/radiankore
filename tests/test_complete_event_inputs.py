"""Annex-driven declarations and formerly truncated XML group cardinalities."""

import asyncio
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import date
from io import BytesIO
from zipfile import ZipFile

import pytest
from lxml import etree

from radiankore import AsyncDianClient, DianClient, DigitalCertificate, Environment
from radiankore._soap.events import build_radian_application_response
from radiankore._soap.namespaces import CAC, CBC
from radiankore.catalogs import EventNoteKind as K
from radiankore.catalogs import MandateNature, OrganizationType, PartyTaxScheme
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    EventNote,
    InvoicePaymentEvent,
    InvoiceResponseEvent,
    MandateAttachedDocument,
    MandateEvent,
    MandateNotary,
    MandateRepresentation,
    MandateTerminationEvent,
    ProtestEvent,
    RadianEvent,
    RadianSoftware,
    RadianTaxDetails,
)
from tests.event_notes import additional_notes

NS = {"cac": CAC, "cbc": CBC}


def with_notes(event: RadianEvent, notes: tuple[EventNote, ...]) -> RadianEvent:
    """Apply declarations through public immutable composition boundaries."""
    if isinstance(event, MandateEvent):
        return replace(event, additional_notes=notes)
    if isinstance(event, MandateTerminationEvent):
        return replace(event, additional_notes=notes)
    if isinstance(event, InvoiceResponseEvent):
        return replace(event, notes=notes)
    return replace(event, header=replace(event.header, notes=notes))


@pytest.mark.parametrize(
    "variant",
    [
        "035",
        "372",
        "038",
        "039",
        "402",
        "441",
        "442",
        "443",
        "481",
        "482",
        "491",
        "492",
        "493",
        "494",
    ],
)
def test_additional_note_cannot_replace_a_required_declaration(
    variant: str, radian_event_factory: Callable[[str], RadianEvent]
) -> None:
    event = radian_event_factory(variant)
    if isinstance(event, MandateTerminationEvent):
        with pytest.raises(TypeError, match="declaration"):
            replace(event, declaration=None)  # type: ignore[arg-type]
        return
    for notes in ((), additional_notes("A nonempty unrelated note")):
        with pytest.raises(ValueError, match="declaration"):
            with_notes(event, notes)


@pytest.mark.parametrize("code", ["030", "031", "032", "033", "034"])
def test_invoice_representation_and_tacit_alternatives(
    code: str,
    invoice_event_factory: Callable[[object], InvoiceResponseEvent],
    radian_software: RadianSoftware,
) -> None:
    from radiankore.catalogs import EventType

    event = invoice_event_factory(EventType(code))
    representation = MandateRepresentation(
        mandatee_name="Gestor & Asociados", mandator_name="Comercial <Sintética>"
    ).as_note()
    alternatives = (
        (K.TACIT_ACCEPTANCE_LEGAL_MANDATE, K.TACIT_ACCEPTANCE_NATURAL_MANDATE)
        if code == "034"
        else (None,)
    )
    for kind in alternatives:
        notes: tuple[EventNote, ...] = (representation,)
        if kind is not None:
            notes += (
                EventNote(
                    kind=kind,
                    text="Juramento sintético con los datos del mandante y adquirente.",
                ),
            )
        notes += additional_notes("Igual", "Igual")
        configured = replace(event, notes=notes)
        root = build_radian_application_response(
            configured, software=radian_software, environment=Environment.HABILITATION
        )
        assert [node.text for node in root.findall("cbc:Note", NS)] == [
            n.text for n in notes
        ]
        assert b"&amp;" in etree.tostring(root) and b"&lt;" in etree.tostring(root)
        with pytest.raises(ValueError, match="first"):
            replace(event, notes=(notes[-1], *notes[:-1]))
    if code == "034":
        with pytest.raises(ValueError, match="statement"):
            replace(event, notes=(representation, *event.notes))
        with pytest.raises(ValueError, match="statement"):
            replace(event, notes=additional_notes("Only a nonempty note"))


@pytest.mark.parametrize(
    "variant,kind,text",
    [
        (
            "361",
            K.SPECIAL_PAYMENT_TERMS,
            "Condiciones especiales pactadas por las partes.",
        ),
        ("372", K.WITHOUT_RECOURSE, "sin mi responsabilidad"),
        ("038", K.GUARANTEE_ENDORSEMENT, "en prenda"),
        ("039", K.COLLECTION_ENDORSEMENT, "al cobro"),
        (
            "402",
            K.COLLECTION_REVOCATION,
            "Revoco la procuración del endoso identificado.",
        ),
        ("481", K.PROTEST, "Con protesto"),
        (
            "491",
            K.ECONOMIC_RIGHTS_TRANSFER,
            "Juramento sintético de cesión de derechos económicos.",
        ),
        ("047", K.WITHOUT_RECOURSE, "sin mi responsabilidad"),
    ],
)
def test_specific_note_is_serialized_after_representation(
    variant: str,
    kind: K,
    text: str,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    event = radian_event_factory(variant)
    representation = MandateRepresentation(
        mandatee_name="Gestor Sintético", mandator_name="Comercial Sintética"
    ).as_note()
    clause = EventNote(kind=kind, text=text)
    notes = (representation, clause, *additional_notes("Otro", "Otro"))
    configured = with_notes(event, notes)
    root = build_radian_application_response(
        configured, software=radian_software, environment=Environment.PRODUCTION
    )
    assert [node.text for node in root.findall("cbc:Note", NS)] == [
        n.text for n in notes
    ]
    # Notes do not change CUDE inputs or select a different environment.
    baseline = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    assert root.findtext("cbc:UUID", namespaces=NS) == baseline.findtext(
        "cbc:UUID", namespaces=NS
    )


@pytest.mark.parametrize(
    "variant",
    ["401", "403", "361", "451", "046", "050", "511", "371", "411", "421", "047"],
)
def test_profiles_without_a_specific_required_note_allow_empty_notes(
    variant: str, radian_event_factory: Callable[[str], RadianEvent]
) -> None:
    assert with_notes(radian_event_factory(variant), ())


def test_optional_ratification_and_mandate_statement_variants(
    radian_event_factory: Callable[[str], RadianEvent], mandate_event: MandateEvent
) -> None:
    event = radian_event_factory("441")
    assert isinstance(event, MandateTerminationEvent)
    assert replace(event, declaration=replace(event.declaration, ratify_acts=True))
    resignation = radian_event_factory("442")
    assert isinstance(resignation, MandateTerminationEvent)
    with pytest.raises(ValueError, match="revocation"):
        replace(
            resignation, declaration=replace(resignation.declaration, ratify_acts=True)
        )
    with pytest.raises(ValueError, match="no_pending_acts"):
        replace(
            resignation,
            declaration=replace(resignation.declaration, no_pending_acts=None),
        )
    natural = replace(
        mandate_event.mandatee_party, organization_type=OrganizationType.NATURAL_PERSON
    )
    assert replace(
        mandate_event,
        mandatee_party=natural,
        declaration=replace(mandate_event.declaration, chamber_of_commerce_city=None),
    )
    with pytest.raises(ValueError, match="chamber"):
        replace(mandate_event, mandatee_party=natural)


@pytest.mark.parametrize("environment", list(Environment))
@pytest.mark.parametrize(
    "organization,kind",
    [
        (OrganizationType.LEGAL_PERSON, K.MANDATE_LEGAL_PERSON),
        (OrganizationType.NATURAL_PERSON, K.MANDATE_NATURAL_PERSON),
    ],
)
def test_mandate_representation_precedes_required_declaration_in_signed_xml(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
    environment: Environment,
    organization: OrganizationType,
    kind: K,
) -> None:
    event = replace(
        mandate_event,
        mandatee_party=replace(
            mandate_event.mandatee_party, organization_type=organization
        ),
        declaration=replace(
            mandate_event.declaration,
            chamber_of_commerce_city="Bogotá"
            if organization is OrganizationType.LEGAL_PERSON
            else None,
        ),
        additional_notes=(),
    )
    with DianClient.from_certificate(
        digital_certificate, environment=environment
    ) as client:
        prepared = client.prepare_radian_event(event=event, software=radian_software)
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    root = etree.fromstring(prepared.xml_bytes)
    if radian_schema is not None:
        radian_schema.assertValid(root)
    assert [node.text for node in root.findall("cbc:Note", NS)] == [
        note.text for note in event.notes
    ]
    assert event.notes[1].kind is kind
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.read(f"ar_{prepared.cude}.xml") == prepared.xml_bytes
    with pytest.raises(ValueError, match="ADDITIONAL"):
        replace(event, additional_notes=(event.notes[0],))


@pytest.mark.parametrize("variant", ["411", "421", "481"])
def test_repeated_document_groups_preserve_per_reference_evidence(
    variant: str,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
) -> None:
    event = radian_event_factory(variant)
    assert isinstance(
        event,
        (
            CirculationRestrictionEvent,
            CirculationRestrictionTerminationEvent,
            ProtestEvent,
        ),
    )
    if isinstance(event, CirculationRestrictionEvent):
        reference = event.responses[0].references[0]
        extra = replace(
            reference,
            reference=replace(event.reference, document_number="SECOND", uuid="b" * 96),
            attachment=replace(
                reference.attachment, content_bytes=b"%PDF-1.7\nSecond PDF\n%%EOF"
            ),
        )
        configured: RadianEvent = replace(
            event,
            responses=(
                replace(event.responses[0], references=(reference, extra)),
                event.responses[0],
            ),
        )
        expected_refs = [2, 1]
    elif isinstance(event, ProtestEvent):
        configured = replace(
            event,
            responses=(
                replace(
                    event.responses[0],
                    references=(
                        event.reference,
                        replace(
                            event.reference, document_number="SECOND", uuid="b" * 96
                        ),
                    ),
                ),
                replace(
                    event.responses[0],
                    act=replace(event.responses[0].act, notary_number="99"),
                ),
            ),
        )
        expected_refs = [2, 1]
    else:
        configured = replace(
            event,
            responses=(
                event.responses[0],
                replace(
                    event.responses[0],
                    reference=replace(
                        event.responses[0].reference,
                        reference=replace(
                            event.reference, document_number="SECOND", uuid="b" * 96
                        ),
                    ),
                ),
            ),
        )
        expected_refs = [1, 1]
    with DianClient.from_certificate(digital_certificate) as client:
        prepared = client.prepare_radian_event(
            event=configured, software=radian_software
        )
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    root = etree.fromstring(prepared.xml_bytes)
    if radian_schema is not None:
        radian_schema.assertValid(root)
    blocks = root.findall("cac:DocumentResponse", NS)
    assert len(blocks) == 2
    assert [
        len(block.findall("cac:DocumentReference", NS)) for block in blocks
    ] == expected_refs
    if isinstance(event, ProtestEvent):
        assert (
            blocks[1].findtext(
                "cac:LineResponse/cac:LineReference/cac:DocumentReference/cbc:ID",
                namespaces=NS,
            )
            == "99"
        )
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.read(archive.namelist()[0]) == prepared.xml_bytes

    async def prepare() -> bytes:
        async with AsyncDianClient.from_certificate(digital_certificate) as client:
            result = await client.prepare_radian_event(
                event=configured, software=radian_software
            )
            verify_event_signature(result.xml_bytes, digital_certificate)
            return result.xml_bytes

    async_root = etree.fromstring(asyncio.run(prepare()))
    assert len(async_root.findall("cac:DocumentResponse", NS)) == 2


def test_multiple_mandate_people_and_notaries(
    mandate_event: MandateEvent,
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
) -> None:
    person = mandate_event.sender_party.representatives[0]
    second = replace(
        person,
        identification_number="100000099",
        job_title="Suplente",
        nationality_id="AR",
        organization_department="Comercial",
    )
    notary = MandateNotary(
        identification_number="900000001",
        verification_digit="2",
        first_name="Synthetic",
        family_name="Notary",
        job_title="Notario",
        office_number="5",
    )
    issuers = (
        notary,
        replace(notary, identification_number="100000088", verification_digit="0"),
    )
    contract = replace(
        mandate_event.attached_contract,
        issuers=issuers,
        effective_date=date(2026, 10, 21),
    )
    validity = MandateAttachedDocument(
        document_id="VALIDITY",
        embedded_bytes=b"%PDF-1.7\nValidity\n%%EOF",
        issuers=issuers,
    )
    event = replace(
        mandate_event,
        nature=MandateNature.GENERAL,
        sender_party=replace(
            mandate_event.sender_party, representatives=(person, second)
        ),
        mandatee_party=replace(
            mandate_event.mandatee_party, representatives=(second, person)
        ),
        attached_contract=contract,
        attached_validity_note=validity,
    )
    root = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    if radian_schema is not None:
        radian_schema.assertValid(root)
    assert [n.text for n in root.findall("cac:SenderParty/cac:Person/cbc:ID", NS)] == [
        "100000001",
        "100000099",
    ]
    assert [
        n.text
        for n in root.findall(
            "cac:DocumentResponse/cac:IssuerParty/cac:PowerOfAttorney/cac:AgentParty/cac:Person/cbc:ID",
            NS,
        )
    ] == ["100000099", "100000001"]
    for path, nationalities, departments in (
        ("cac:SenderParty/cac:Person", ["CO", "AR"], ["Legal", "Comercial"]),
        (
            "cac:DocumentResponse/cac:IssuerParty/cac:PowerOfAttorney/"
            "cac:AgentParty/cac:Person",
            ["AR", "CO"],
            ["Comercial", "Legal"],
        ),
    ):
        assert [
            node.findtext("cbc:NationalityID", namespaces=NS)
            for node in root.findall(path, NS)
        ] == nationalities
        assert [
            node.findtext("cbc:OrganizationDepartment", namespaces=NS)
            for node in root.findall(path, NS)
        ] == departments
    assert (
        len(
            root.findall(
                "cac:DocumentResponse/cac:LineResponse/cac:LineReference/cac:DocumentReference/cac:IssuerParty/cac:Person",
                NS,
            )
        )
        == 4
    )


@pytest.mark.parametrize(
    "code,name",
    [
        (None, None),
        (PartyTaxScheme.VAT, None),
        (None, "IVA"),
        (PartyTaxScheme.VAT, "IVA"),
    ],
)
def test_tax_scheme_optional_children_are_independent(
    code: PartyTaxScheme | None,
    name: str | None,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
) -> None:
    event = radian_event_factory("451")
    assert isinstance(event, InvoicePaymentEvent) and event.payer.party is not None
    party = replace(
        event.payer.party, tax_scheme=RadianTaxDetails(code=code, name=name)
    )
    configured = replace(
        event,
        payer=replace(event.payer, party=party),
        additional_sender_parties=(party, party),
    )
    root = build_radian_application_response(
        configured, software=radian_software, environment=Environment.PRODUCTION
    )
    if radian_schema is not None:
        radian_schema.assertValid(root)
    assert len(root.findall("cac:SenderParty/cac:PartyTaxScheme", NS)) == 3
    assert len(root.findall("cac:SenderParty/cac:PartyLegalEntity", NS)) == 1
    tax = root.find("cac:SenderParty/cac:PartyTaxScheme/cac:TaxScheme", NS)
    assert tax is not None
    assert [n.tag for n in tax] == ([f"{{{CBC}}}ID"] if code is not None else []) + (
        [f"{{{CBC}}}Name"] if name is not None else []
    )


@pytest.mark.parametrize("kind", list(K))
def test_note_objects_are_immutable_and_reject_untyped_kinds(kind: K) -> None:
    value = (
        "Con protesto"
        if kind is K.PROTEST
        else "Gestor OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante"
        if kind is K.MANDATE_REPRESENTATION
        else "Texto sintético"
    )
    note = EventNote(kind=kind, text=value)
    with pytest.raises(FrozenInstanceError):
        note.text = "Changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        EventNote(kind=kind.value, text=value)  # type: ignore[arg-type]
    for invalid in ("", " ", "X" * 10001):
        with pytest.raises(ValueError):
            EventNote(kind=kind, text=invalid)


def test_all_public_input_fields_have_documented_xml_correspondences() -> None:
    """Keep the published API inventory complete as constructor contracts evolve."""
    import json
    from dataclasses import fields, is_dataclass
    from pathlib import Path

    from radiankore.models import events

    base = Path(__file__).parent
    manifest = json.loads((base / "fixtures/event_input_fields.json").read_text())
    inventory = {item["model"]: item for item in manifest}
    public = {
        name: getattr(events, name)
        for name in events.__all__
        if isinstance(getattr(events, name), type)
        and is_dataclass(getattr(events, name))
        and name != "PreparedRadianEvent"
    }
    assert inventory.keys() == public.keys()
    for name, model in public.items():
        assert {field.name for field in fields(model)} == {
            item["field"] for item in inventory[name]["fields"]
        }
        assert all(item["xml"] for item in inventory[name]["fields"])
    document = base.parent / "docs/technical/event-input-matrix.md"
    if document.is_file():
        contents = document.read_text()
        for name in public:
            assert f"### {name}\n" in contents


def test_published_note_example_executes_with_only_public_imports() -> None:
    import re
    from pathlib import Path

    path = Path(__file__).parents[1] / "docs/operations/event-notes.md"
    if not path.is_file():
        pytest.skip("Documentation is excluded from distributions.")
    blocks = re.findall(r"```python\n(.*?)```", path.read_text(), re.DOTALL)
    namespace: dict[str, object] = {}
    for number, block in enumerate(blocks):
        exec(compile(block, f"event-notes.md:{number}", "exec"), namespace)
    notes = namespace["guarantee_endorsement_notes"]
    assert isinstance(notes, tuple)
    assert [note.kind for note in notes] == [
        K.MANDATE_REPRESENTATION,
        K.GUARANTEE_ENDORSEMENT,
        K.ADDITIONAL,
        K.ADDITIONAL,
    ]


@pytest.mark.parametrize("variant", ["401", "451", "046", "481", "050", "511"])
def test_additional_generator_identities_are_not_legal_participations(
    variant: str,
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    from radiankore.models.events import (
        EconomicRightsNotificationEvent,
        EconomicRightsPaymentEvent,
        EndorsementCancellationEvent,
        PaymentReportEvent,
    )

    event = radian_event_factory(variant)
    assert isinstance(
        event,
        (
            EndorsementCancellationEvent,
            InvoicePaymentEvent,
            EconomicRightsPaymentEvent,
            EconomicRightsNotificationEvent,
            PaymentReportEvent,
            ProtestEvent,
        ),
    )
    if isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent)):
        party = event.payer.party
        assert party is not None
    else:
        party = event.sender_party
    extra = replace(party, tax_number="900000099", verification_digit="9")
    configured = replace(event, additional_sender_parties=(extra, extra))
    root = build_radian_application_response(
        configured, software=radian_software, environment=Environment.PRODUCTION
    )
    assert [
        n.text
        for n in root.findall("cac:SenderParty/cac:PartyTaxScheme/cbc:CompanyID", NS)
    ] == [party.tax_number, "900000099", "900000099"]
    expected_legal = (
        1 if isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent)) else 0
    )
    assert (
        len(root.findall("cac:SenderParty/cac:PartyLegalEntity", NS)) == expected_legal
    )
    with pytest.raises(TypeError):
        replace(event, additional_sender_parties=[])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(event, additional_sender_parties=(None,))  # type: ignore[arg-type]


def test_declaration_duplicates_and_optional_singletons(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    clause = EventNote(kind=K.GUARANTEE_ENDORSEMENT, text="en garantía")
    event = with_notes(radian_event_factory("038"), (clause, clause))
    root = build_radian_application_response(
        event, software=radian_software, environment=Environment.PRODUCTION
    )
    assert [n.text for n in root.findall("cbc:Note", NS)] == [
        "en garantía",
        "en garantía",
    ]
    terms = EventNote(kind=K.SPECIAL_PAYMENT_TERMS, text="Condiciones pactadas.")
    with pytest.raises(ValueError, match="at most once"):
        with_notes(radian_event_factory("361"), (terms, terms))
    with pytest.raises(ValueError, match="not applicable"):
        with_notes(radian_event_factory("451"), (terms,))
    with pytest.raises(ValueError, match="position"):
        with_notes(
            radian_event_factory("035"),
            (
                *additional_notes("Extra"),
                EventNote(kind=K.GUARANTEE_LEGAL_PERSON, text="Declaración de aval."),
            ),
        )
    with pytest.raises(ValueError, match="position"):
        with_notes(radian_event_factory("038"), (*additional_notes("Extra"), clause))


def test_nested_collection_errors_are_detected_before_xml(
    radian_event_factory: Callable[[str], RadianEvent],
    mandate_event: MandateEvent,
) -> None:
    restriction = radian_event_factory("411")
    termination = radian_event_factory("421")
    protest = radian_event_factory("481")
    assert isinstance(restriction, CirculationRestrictionEvent)
    assert isinstance(termination, CirculationRestrictionTerminationEvent)
    assert isinstance(protest, ProtestEvent)
    for event in (restriction, termination, protest):
        with pytest.raises(ValueError, match="nonempty"):
            replace(event, responses=())  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="responses"):
            replace(event, responses=(None,))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonempty"):
        replace(restriction.responses[0], references=())
    with pytest.raises(TypeError):
        replace(restriction.responses[0], references=(None,))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(termination.responses[0], reference=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(protest.responses[0], references=())
    with pytest.raises(TypeError):
        replace(protest.responses[0], references=(None,))  # type: ignore[arg-type]
    for party in (mandate_event.sender_party, mandate_event.mandatee_party):
        with pytest.raises(ValueError):
            replace(party, representatives=())
        with pytest.raises(TypeError):
            replace(party, representatives=(None,))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(mandate_event.attached_contract, issuers=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "code,name,error",
    [
        ("01", None, TypeError),
        (None, 1, TypeError),
        (None, "Unknown", ValueError),
        (PartyTaxScheme.VAT, "INC", ValueError),
    ],
)
def test_tax_detail_invalid_values(
    code: object, name: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        RadianTaxDetails(code=code, name=name)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kind,text,message",
    [
        (K.MANDATE_REPRESENTATION, "Missing official declaration", "official"),
        (K.PROTEST, "con protesto", "literal"),
    ],
)
def test_note_literals_are_exact(kind: K, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        EventNote(kind=kind, text=text)


@pytest.mark.parametrize(
    "code,operation,kinds,message",
    [
        ("034", "034", (K.TACIT_ACCEPTANCE_LEGAL_MANDATE,), "sworn statement"),
        ("044", "442", (K.MANDATE_RATIFICATION,), "Ratification"),
        ("044", "441", (K.MANDATE_NO_PENDING_ACTS,), "No-pending-acts"),
        ("040", "401", (K.COLLECTION_REVOCATION,), "Collection revocation"),
        ("037", "371", (K.WITHOUT_RECOURSE,), "Without-recourse"),
        ("035", "035", (K.ADDITIONAL, K.GUARANTEE_LEGAL_PERSON), "position"),
    ],
)
def test_note_purposes_match_operation_and_position(
    code: str, operation: str, kinds: tuple[K, ...], message: str
) -> None:
    from radiankore.models.events.notes import validate_event_notes

    notes = tuple(EventNote(kind=kind, text="Synthetic declaration") for kind in kinds)
    with pytest.raises(ValueError, match=message):
        validate_event_notes(notes, code=code, operation=operation)


def test_common_components_reject_invalid_reference_and_accept_person_details(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    from radiankore.models.events import (
        CirculationRestrictionEvent,
        MandateTerminationEvent,
    )

    event = radian_event_factory("411")
    assert isinstance(event, CirculationRestrictionEvent)
    with pytest.raises(TypeError, match="invoice or prior event"):
        replace(event.responses[0].references[0], reference=None)  # type: ignore[arg-type]
    mandate = radian_event_factory("441")
    assert isinstance(mandate, MandateTerminationEvent)
    person = replace(
        mandate.representatives[0],
        job_title="Agent",
        nationality_id="CO",
        organization_department="Legal",
    )
    assert person.job_title == "Agent"
    with pytest.raises(ValueError, match="job_title"):
        replace(person, job_title="")


def test_mandate_ratification_requires_its_paired_position() -> None:
    from radiankore.models.events.notes import validate_event_notes

    notes = tuple(
        EventNote(kind=kind, text="Synthetic declaration")
        for kind in (K.MANDATE_RATIFICATION, K.MANDATE_TERMINATION)
    )
    with pytest.raises(ValueError, match="invalid note position"):
        validate_event_notes(notes, code="044", operation="441")


def test_multiple_guarantee_declarations_preserve_each_guarantors_statement(
    radian_event_factory: Callable[[str], RadianEvent],
) -> None:
    from radiankore.models.events import GuaranteeEvent

    event = radian_event_factory("035")
    assert isinstance(event, GuaranteeEvent)
    notes = (
        EventNote(kind=K.GUARANTEE_LEGAL_PERSON, text="Synthetic legal guarantor"),
        EventNote(kind=K.GUARANTEE_NATURAL_PERSON, text="Synthetic natural guarantor"),
    )
    updated = replace(event, header=replace(event.header, notes=notes))
    assert updated.header.notes == notes
