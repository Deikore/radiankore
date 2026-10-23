"""Reference-backed catalog and sample comparisons; originals remain read-only."""

from collections.abc import Callable
from pathlib import Path

import pytest
from lxml import etree

from radiankore._soap.events.radian_builder import build_radian_application_response
from radiankore._soap.namespaces import CBC
from radiankore.catalogs import CurrencyCode, PaymentMeans, RadianOperationType
from radiankore.environment import Environment
from radiankore.models.events import RadianEvent, RadianSoftware

REFERENCES = Path(__file__).resolve().parents[1] / "docs/references/dian/radian/toolbox"


def test_currency_catalog_against_preserved_genericode() -> None:
    path = REFERENCES / "Listas de valores/TipoMoneda-2.1.gc"
    if not path.exists():
        pytest.skip("Reference documents are excluded from distributions.")
    expected = {}
    for row in etree.parse(str(path)).findall(".//Row"):
        values = {
            v.get("ColumnRef"): v.findtext("SimpleValue") for v in row.findall("Value")
        }
        code, label = values["code"], values["name"]
        assert code is not None and label is not None
        expected["VES" if code == "VES7" else code] = label.strip()
    assert {member.value: member.label for member in CurrencyCode} == expected
    assert CurrencyCode.from_code("VES7") is None
    assert CurrencyCode.VES.label == "Bolívar soberano"
    assert {m.value for m in PaymentMeans} == {
        "10",
        "48",
        "49",
        "47",
        "42",
        "44",
        "3",
        "20",
        "25",
        "23",
        "26",
        "71",
        "24",
        "72",
    }


def test_operations_against_preserved_genericode() -> None:
    folder = REFERENCES / "Listas de valores"
    paths = list(folder.glob("TiposOperacio*"))
    if not paths:
        pytest.skip("Reference documents are excluded from distributions.")
    expected = {}
    known = {m.value for m in RadianOperationType}
    for row in etree.parse(str(paths[0])).findall(".//Row"):
        values = {
            v.get("ColumnRef"): v.findtext("SimpleValue") for v in row.findall("Value")
        }
        if values["code"] in known:
            expected[values["code"]] = (values["name"], values["Description"])
    assert len(expected) == 32
    for member in RadianOperationType:
        label, event = expected[member.value]
        assert label is not None
        assert (member.label, member.event_type.value) == (label.strip(), event)


def test_all_available_examples_match_supported_operation_shapes(
    radian_event_factory: Callable[[str], RadianEvent],
    radian_software: RadianSoftware,
) -> None:
    folder = REFERENCES / "Ejemplificaciones/XMLs de ejemplo"
    if not folder.exists():
        pytest.skip("Reference documents are excluded from distributions.")
    seen = set()
    for path in folder.rglob("*"):
        if path.suffix.lower() != ".xml":
            continue
        if path.parent.name[:3] not in {
            "035",
            "041",
            "042",
            "048",
            "049",
            "050",
            "051",
            "036",
            "037",
            "038",
            "039",
            "040",
            "044",
            "045",
            "046",
            "047",
        }:
            continue
        original = etree.parse(str(path))
        op = original.findtext(f"{{{CBC}}}CustomizationID")
        assert op is not None
        codes = original.xpath('//*[local-name()="ResponseCode"]')
        assert isinstance(codes, list) and codes
        first = codes[0]
        assert isinstance(first, etree._Element)
        variant = op + (
            "-blank"
            if first.get("listID") == "2" and op in {"371", "372", "038", "039"}
            else ""
        )
        event = radian_event_factory(variant)
        root = build_radian_application_response(
            event, software=radian_software, environment=Environment.HABILITATION
        )
        assert root.findtext(f"{{{CBC}}}CustomizationID") == op
        built_codes = root.xpath('//*[local-name()="ResponseCode"]')
        assert isinstance(built_codes, list) and built_codes
        built = built_codes[0]
        assert isinstance(built, etree._Element) and built.text == first.text
        # The payment and 047 listID discrepancies are documented separately.
        if op not in {"451", "452", "047", "511", "512"}:
            assert built.get("listID") == first.get("listID")
        seen.add(op)
    assert seen == {m.value for m in RadianOperationType} - {"403", "443"}
