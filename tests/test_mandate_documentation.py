"""Execute each published mandate example independently, including XML fragments."""

import re
from base64 import b64decode
from collections import Counter
from collections.abc import Callable
from datetime import date
from itertools import product
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore._soap.namespaces import CAC, CBC, WCF, XSI
from radiankore.catalogs import EventNoteKind as K
from radiankore.models.events import (
    MandateEvent,
    MandateTerminationEvent,
    RadianSoftware,
)
from tests.documentation_support import python_blocks

DOCS = Path(__file__).resolve().parents[1] / "docs/operations"
NS = {"cac": CAC, "cbc": CBC}
# Independent inventory: no expected combination is inferred from a published case.
MANDATES = tuple(
    product(("431", "432", "433", "434"), "SG", ("ONE", "MULTIPLE", "ALL"), "NJ")
)
TERMINATIONS = {
    "T441-SIN-SIN": ("441", False, False, (K.MANDATE_TERMINATION,)),
    "T441-SIN-CON": (
        "441",
        False,
        True,
        (K.MANDATE_TERMINATION, K.MANDATE_RATIFICATION),
    ),
    "T441-CON-SIN": (
        "441",
        True,
        False,
        (K.MANDATE_REPRESENTATION, K.MANDATE_TERMINATION),
    ),
    "T441-CON-CON": (
        "441",
        True,
        True,
        (K.MANDATE_REPRESENTATION, K.MANDATE_RATIFICATION, K.MANDATE_TERMINATION),
    ),
    "T442-SIN": (
        "442",
        False,
        False,
        (K.MANDATE_TERMINATION, K.MANDATE_NO_PENDING_ACTS),
    ),
    "T442-CON": (
        "442",
        True,
        False,
        (K.MANDATE_REPRESENTATION, K.MANDATE_NO_PENDING_ACTS, K.MANDATE_TERMINATION),
    ),
    "T443-SIN": ("443", False, False, (K.MANDATE_TERMINATION,)),
    "T443-CON": ("443", True, False, (K.MANDATE_REPRESENTATION, K.MANDATE_TERMINATION)),
}
RECIPES = (
    "VERBAL",
    "ROLES",
    "CHANNELS",
    "POWERS",
    "INVOICE-SCOPES",
    "REPRESENTATIVES",
    "NOTARIES",
    "REPEATED-REFERENCES",
    "TWENTY",
    "NOTES",
)
ERRORS = {
    "DECLARANT": ("invalid_declarant", "declarant"),
    "CITY-LEGAL": ("invalid_legal_city", "chamber city"),
    "CITY-NATURAL": ("invalid_natural_city", "chamber city"),
    "SUPPORT": ("invalid_support", "validity note"),
    "DV": ("invalid_digit", "verification_digit"),
    "PT": ("invalid_channel", "PT channel"),
    "COUNT": ("invalid_count", "Reference count"),
    "TERMINATION": ("invalid_termination", "Ratification"),
}


def read_page(relative: str) -> str:
    path = DOCS / relative
    if not path.is_file():
        pytest.skip("Documentation is excluded from distributions.")
    return path.read_text()


def section(relative: str, identifier: str) -> str:
    matches = list(
        re.finditer(
            rf"^## {re.escape(identifier)}(?: — [^\n]*)?\n(.*?)(?=^## |\Z)",
            read_page(relative),
            re.MULTILINE | re.DOTALL,
        )
    )
    assert len(matches) == 1, identifier
    return matches[0].group(1)


def execute(content: str, namespace: dict[str, Any]) -> None:
    for block in re.findall(r"```python\n(.*?)```", content, re.DOTALL):
        exec(compile(block, "published-mandate-example", "exec"), namespace)


@pytest.fixture
def common(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Load the complete public base in a new namespace and forbid real HTTP."""
    monkeypatch.chdir(tmp_path)
    for filename in ("contrato.pdf", "vigencia.pdf"):
        (tmp_path / filename).write_bytes(b"%PDF-1.7\nSynthetic evidence.\n%%EOF")

    def forbid_network(timeout: float) -> httpx.Client:
        pytest.fail("Preparation must not open an HTTP client.")

    monkeypatch.setattr(transport, "create_http_client", forbid_network)
    namespace: dict[str, Any] = {}
    execute(read_page("mandate/participants.md"), namespace)
    return namespace


def case(namespace: dict[str, Any], identifier: str) -> str:
    relative = (
        f"mandate/{identifier[1:4]}.md"
        if identifier.startswith("M")
        else "radian-termination.md"
    )
    content = section(relative, identifier)
    execute(content, namespace)
    return content


def shape(node: etree._Element) -> object:
    """Compare expanded names, attributes and text, ignoring display indentation."""
    return (
        node.tag,
        dict(node.items()),
        (node.text or "").strip(),
        tuple(shape(child) for child in node),
    )


def assert_fragments(root: etree._Element, content: str) -> None:
    fragments = re.findall(
        r"<!-- xml-path: (.*?) -->\s*```xml\n(.*?)```", content, re.DOTALL
    )
    assert fragments
    for path, fragment in fragments:
        wrapper = etree.fromstring(
            (
                f'<fragments xmlns:cac="{CAC}" xmlns:cbc="{CBC}">{fragment}</fragments>'
            ).encode()
        )
        actual = root.findall(path, namespaces=NS)
        assert len(actual) == 1, path
        assert shape(actual[0]) == shape(wrapper[0]), path


@pytest.fixture
def prepare(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
) -> Callable[[MandateEvent | MandateTerminationEvent, RadianSoftware], etree._Element]:
    """Verify the bytes produced by the real public API, not a documentation builder."""

    def checked(
        event: MandateEvent | MandateTerminationEvent, software: RadianSoftware
    ) -> etree._Element:
        with DianClient(
            encrypted_pfx_path,
            password="test-password",
            environment=Environment.HABILITATION,
        ) as client:
            prepared = client.prepare_radian_event(event=event, software=software)
        verify_event_signature(prepared.xml_bytes, digital_certificate)
        root = etree.fromstring(prepared.xml_bytes)
        if radian_schema is not None:
            radian_schema.assertValid(root)
        assert root.xpath("cbc:Note/text()", namespaces=NS) == [
            n.text for n in event.notes
        ]
        if isinstance(event, MandateEvent):
            attachments = root.findall(
                "cac:DocumentResponse[1]/cac:LineResponse/cac:LineReference/cac:DocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject",
                namespaces=NS,
            )
            expected = [event.attached_contract]
            if event.attached_validity_note is not None:
                expected.append(event.attached_validity_note)
            assert len(attachments) == len(expected)
            for binary, attachment in zip(attachments, expected, strict=True):
                assert binary.text is not None
                assert b64decode(binary.text) == attachment.embedded_bytes
                assert binary.get("format") == binary.get("mimeCode") == "PDF"
                assert (
                    binary.get("encodingCode")
                    == binary.get("characterSetCode")
                    == "base64, PDF"
                )
        return root

    return checked


def test_inventory_has_exactly_48_and_eight_independent_cases() -> None:
    identifiers = []
    for operation in ("431", "432", "433", "434"):
        identifiers.extend(
            re.findall(
                r"^## (M\S+)\s*$", read_page(f"mandate/{operation}.md"), re.MULTILINE
            )
        )
    expected = {
        f"M{op}-{nature}-{refs}-{person}" for op, nature, refs, person in MANDATES
    }
    assert Counter(identifiers) == Counter(expected)
    termination_ids = re.findall(
        r"^## (T\S+)\s*$", read_page("radian-termination.md"), re.MULTILINE
    )
    assert Counter(termination_ids) == Counter(TERMINATIONS.keys())
    assert len(expected) == 48 and len(TERMINATIONS) == 8
    assert set(
        re.findall(r"^## REC-([\w-]+) —", read_page("mandate/recipes.md"), re.MULTILINE)
    ) == set(RECIPES)
    assert set(
        re.findall(r"^### ERR-([\w-]+) —", read_page("mandate/notes.md"), re.MULTILINE)
    ) == set(ERRORS)


@pytest.mark.parametrize("operation,nature,refs,person", MANDATES)
def test_each_constitution_is_copyable_and_matches_published_xml(
    common: dict[str, Any],
    prepare: Callable[
        [MandateEvent | MandateTerminationEvent, RadianSoftware], etree._Element
    ],
    operation: str,
    nature: str,
    refs: str,
    person: str,
) -> None:
    identifier = f"M{operation}-{nature}-{refs}-{person}"
    content = case(common, identifier)
    event = common["event"]
    assert isinstance(event, MandateEvent)
    assert event.event_number == identifier
    assert event.operation_type.value == operation
    assert event.nature.value == ("1" if nature == "S" else "2")
    assert event.reference_type.name == refs
    assert event.mandatee_party.organization_type.value == (
        "2" if person == "N" else "1"
    )
    assert event.declaration.chamber_of_commerce_city == (
        None if person == "N" else "Bogotá"
    )
    assert len(event.document_references) == {"ONE": 1, "MULTIPLE": 2, "ALL": 0}[refs]
    assert (event.validity_period.start_date is not None) == (
        operation in {"431", "433"}
    )
    assert [p.value for p, _ in event.scope.powers] == (
        ["ALL17"] if operation in {"431", "432"} else ["MR91", "R14"]
    )
    assert event.declaration.contract_form.value == "escrito"
    assert {channel.value for _, channel in event.scope.powers} == {"SNE"}
    expected_ending = (
        "por el tiempo consignado en este documento."
        if operation in {"431", "433"}
        else "sin limitaciones de tiempo."
    )
    assert event.notes[1].text.endswith(expected_ending)
    assert ("Cámara de Comercio de Bogotá" in event.notes[1].text) == (person == "J")
    root = prepare(event, common["software"])
    assert root.xpath(
        "cac:DocumentResponse[2]/cac:LineResponse/cac:Response/cbc:ResponseCode/text()",
        namespaces=NS,
    ) == ["ACEPTA"]
    assert_fragments(root, content)
    assert [n.kind for n in event.notes] == [
        K.MANDATE_REPRESENTATION,
        K.MANDATE_NATURAL_PERSON if person == "N" else K.MANDATE_LEGAL_PERSON,
    ]
    if identifier in {"M433-S-ONE-N", "M433-S-ONE-J", "M433-G-ONE-J"}:
        notes = read_page("mandate/notes.md")
        if nature == "G":
            excerpt = notes.split("## XML de soportes\n")[1].split("\n## ")[0]
        else:
            excerpt = (
                notes.split(f"### {identifier}\n")[1]
                .split("\n### ")[0]
                .split("\n## ")[0]
            )
        assert_fragments(root, excerpt)


@pytest.mark.parametrize("identifier", TERMINATIONS)
def test_each_termination_matches_notes_actor_reference_and_xml(
    common: dict[str, Any],
    prepare: Callable[
        [MandateEvent | MandateTerminationEvent, RadianSoftware], etree._Element
    ],
    identifier: str,
) -> None:
    content = case(common, identifier)
    event = common["event"]
    assert isinstance(event, MandateTerminationEvent)
    operation, representation, ratification, kinds = TERMINATIONS[identifier]
    assert event.operation_type.value == operation
    assert (event.declaration.representation is not None) == representation
    assert event.declaration.ratify_acts is ratification
    assert event.declaration.no_pending_acts is (True if operation == "442" else None)
    assert (
        event.sender_party
        is common["mandatee_legal" if operation == "442" else "mandator"]
    )
    assert event.representatives == event.sender_party.representatives
    assert event.reference == common["original_mandate"]
    assert event.declaration.effective_date == date(2026, 10, 24)
    assert tuple(n.kind for n in event.notes) == kinds
    root = prepare(event, common["software"])
    assert not root.xpath(
        "cac:DocumentResponse/cac:Response/cbc:EffectiveDate", namespaces=NS
    )
    assert_fragments(root, content)


@pytest.mark.parametrize(
    "recipe,seed",
    [(recipe, "M433-S-MULTIPLE-J") for recipe in RECIPES]
    + [("INVOICE-SCOPES", "M434-S-MULTIPLE-J")],
)
def test_complementary_recipes_execute_independently(
    common: dict[str, Any],
    prepare: Callable[
        [MandateEvent | MandateTerminationEvent, RadianSoftware], etree._Element
    ],
    recipe: str,
    seed: str,
) -> None:
    case(common, seed)
    execute(section("mandate/recipes.md", f"REC-{recipe}"), common)
    event = common["event"]
    root = prepare(event, common["software"])
    if recipe == "VERBAL":
        assert "contrato de mandato verbal" in event.notes[1].text
    elif recipe in {"ROLES", "CHANNELS"}:
        alternatives = common[
            "role_examples" if recipe == "ROLES" else "channel_examples"
        ]
        assert len(alternatives) == (16 if recipe == "ROLES" else 3)
        for alternative in alternatives.values():
            prepare(alternative, common["software"])
    elif recipe == "POWERS":
        assert [p.value for p, _ in event.scope.powers] == [
            "MR91",
            *[f"R{i:02}" for i in range(1, 23)],
        ]
    elif recipe == "INVOICE-SCOPES":
        assert root.xpath(
            "cac:DocumentResponse/cac:Response/cbc:ResponseCode/text()", namespaces=NS
        ) == ["043", "MR91-SNE;R14-SNE", "MR91-F;R06-F"]
        for block, invoice in ((2, "FE1"), (3, "FE2")):
            assert root.xpath(
                f"cac:DocumentResponse[{block}]/cac:DocumentReference/cbc:ID/text()",
                namespaces=NS,
            ) == [invoice]
    elif recipe == "REPRESENTATIVES":
        assert root.xpath(
            "cac:SenderParty/cac:Person/cbc:FirstName/text()", namespaces=NS
        ) == ["Ana", "Marta"]
        assert root.xpath(
            "cac:DocumentResponse[1]/cac:IssuerParty/cac:PowerOfAttorney/cac:AgentParty/cac:Person/cbc:FirstName/text()",
            namespaces=NS,
        ) == ["Luis", "Marta"]
        assert event.notes[1].text.startswith("Marta Sintético")
    elif recipe == "NOTARIES":
        for attachment in (1, 2):
            assert root.xpath(
                f"cac:DocumentResponse[1]/cac:LineResponse[{attachment}]/cac:LineReference/cac:DocumentReference/cac:IssuerParty/cac:Person/cbc:FirstName/text()",
                namespaces=NS,
            ) == ["Clara", "Pedro"]
    elif recipe in {"REPEATED-REFERENCES", "TWENTY"}:
        for block in (1, 2):
            ids = root.xpath(
                f"cac:DocumentResponse[{block}]/cac:DocumentReference/cbc:ID/text()",
                namespaces=NS,
            )
            assert ids == (
                ["FE1", "FE1"]
                if recipe == "REPEATED-REFERENCES"
                else [f"FE{i}" for i in range(1, 21)]
            )
    elif recipe == "NOTES":
        assert [note.text for note in root.findall("cbc:Note", namespaces=NS)][-2:] == [
            "Observación ficticia."
        ] * 2


@pytest.mark.parametrize("error", ERRORS)
def test_documented_errors_raise_for_the_documented_reason(
    common: dict[str, Any], error: str
) -> None:
    case(common, "M433-S-MULTIPLE-J")
    content = re.search(
        rf"^### ERR-{error} — [^\n]*\n(.*?)(?=^### |\Z)",
        read_page("mandate/notes.md"),
        re.MULTILINE | re.DOTALL,
    )
    assert content is not None
    execute(content[1], common)
    function, message = ERRORS[error]
    with pytest.raises(ValueError, match=message):
        common[function]()


def test_published_preparation_and_send_preserve_zip_and_close_connections(
    common: dict[str, Any],
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    wrap_soap: Callable[[etree._Element], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Execute both real published blocks, intercepting only transport creation."""
    from io import BytesIO
    from zipfile import ZipFile

    case(common, "M433-S-MULTIPLE-J")
    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption,
        pkcs12,
    )

    Path("certificado.pfx").write_bytes(
        pkcs12.serialize_key_and_certificates(
            name=b"synthetic-documentation",
            key=digital_certificate.private_key,
            cert=digital_certificate.certificate,
            cas=None,
            encryption_algorithm=BestAvailableEncryption(b"password-ficticio"),
        )
    )
    blocks = python_blocks(DOCS / "mandate.md")
    assert len(blocks) == 2
    exec(compile(blocks[0], "mandate-preparation", "exec"), common)
    prepared = common["prepared"]
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult").set(
        f"{{{XSI}}}nil", "true"
    )
    payload = wrap_soap(response)
    requests: list[httpx.Request] = []
    connections: list[httpx.Client] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        verify_event_signature(request.content, digital_certificate)
        soap = etree.fromstring(request.content)
        content = soap.find(f".//{{{WCF}}}contentFile")
        assert content is not None and content.text is not None
        assert b64decode(content.text) == prepared.zip_bytes
        return httpx.Response(200, content=payload)

    def factory(timeout: float) -> httpx.Client:
        connection = httpx.Client(
            transport=httpx.MockTransport(handler), timeout=timeout
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(transport, "create_http_client", factory)
    exec(compile(blocks[1], "mandate-send", "exec"), common)
    assert common["result"] is None
    assert len(requests) == 1 and all(c.is_closed for c in connections)
    with ZipFile(BytesIO(prepared.zip_bytes)) as archive:
        assert archive.read(f"ar_{prepared.cude}.xml") == prepared.xml_bytes
