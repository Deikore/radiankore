"""Documentation contracts: navigation identity, public API and preserved sources."""

import inspect
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from radiankore import DianClient
from radiankore.catalogs import EventType, OrganizationType, PartyTaxScheme
from radiankore.catalogs.invoice_events import OrganizationType as LegacyOrganization
from radiankore.catalogs.invoice_events import PartyTaxScheme as LegacyTaxScheme
from radiankore.models import events


@pytest.fixture(scope="module")
def documentation_root() -> Path:
    """Documentation is available in checkouts, deliberately absent from sdist."""
    path = Path(__file__).resolve().parents[1] / "docs"
    if not (path / "index.md").is_file():
        pytest.skip("Documentation is excluded from distributions.")
    return path


@pytest.mark.parametrize(
    "name,title,contracts",
    [
        ("api", "API pública", ("prepare_radian_event", "send_radian_event")),
        (
            "models",
            "Modelos públicos",
            ("InvoiceEventsResult", "RadianEvent", "MandateEvent"),
        ),
        (
            "catalogs",
            "Catálogos DIAN",
            ("## Motivos de notas", "AcceptanceFailureType", "IdentificationType"),
        ),
        (
            "errors",
            "Errores y certificado",
            ("DigitalCertificateError", "DianResponseError", "DianTransportError"),
        ),
        (
            "technical-references",
            "Referencias técnicas",
            ("event-reference-map.md", "RADIAN", "FE 1.9"),
        ),
    ],
)
def test_reference_pages_keep_their_own_contract(
    documentation_root: Path, name: str, title: str, contracts: tuple[str, ...]
) -> None:
    content = (documentation_root / f"{name}.md").read_text()
    assert content.splitlines()[0] == f"# {title}"
    assert all(contract in content for contract in contracts)
    if name != "api":
        assert "## Cliente y certificado" not in content


def test_client_methods_are_listed_in_public_api(documentation_root: Path) -> None:
    public = {
        name
        for name, _ in inspect.getmembers(DianClient, inspect.isfunction)
        if not name.startswith("_")
    }
    content = (documentation_root / "api.md").read_text()
    documented = set(re.findall(r"^\| `([a-z_]+)\(", content, re.MULTILINE))
    assert public == documented


def test_event_map_covers_models_guides_and_actual_reference_counts(
    documentation_root: Path,
) -> None:
    content = (documentation_root / "event-reference-map.md").read_text()
    rows = re.findall(r"^\| (\d{3}) \|[^\n]+", content, re.MULTILINE)
    expected = {member.value for member in EventType} - {"02", "04"}
    assert len(rows) == len(set(rows)) and set(rows) == expected
    references = documentation_root / "references/dian"
    if not references.exists():
        pytest.skip("Preserved reference documents are excluded from distributions.")
    radian_count = 0
    for row in content.splitlines():
        if not re.match(r"\| \d{3} \|", row):
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        code, model, guide, generation, _, examples, tests = cells
        assert hasattr(events, model.strip("`"))
        guide_match = re.search(r"\]\((operations/[^)]+)\)", guide)
        assert guide_match is not None
        assert (documentation_root / guide_match[1]).is_file()
        assert ("FE 1.9" in generation) == (int(code) < 35)
        match = re.fullmatch(r"\[(\d+) XML\]\(([^)]+)\)", examples)
        assert match is not None
        source_path = unquote(urlsplit(match[2]).path.split("/blob/HEAD/", 1)[1])
        path = documentation_root.parent / source_path
        assert path.exists()
        actual = (
            sum(1 for p in path.rglob("*") if p.suffix.lower() == ".xml")
            if path.is_dir()
            else 1
        )
        assert actual == int(match[1])
        if int(code) >= 35 and code != "043":
            radian_count += actual
        for url in re.findall(r"\]\(([^)]+)\)", tests):
            local = urlsplit(url).path.split("/blob/HEAD/", 1)[1]
            assert (documentation_root.parent / local).is_file()
    assert radian_count == 36
    assert all(f"`{code}`" in content for code in ("403", "443"))


def test_participant_catalog_imports_preserve_enum_identity() -> None:
    assert LegacyOrganization is OrganizationType
    assert LegacyTaxScheme is PartyTaxScheme


def test_fixture_factory_rejects_unknown_or_inapplicable_variants() -> None:
    from tests.event_factories import radian_event_factory

    factory = radian_event_factory()
    for variant in ("unknown", "035-blank", "511-blank"):
        with pytest.raises(ValueError):
            factory(variant)
