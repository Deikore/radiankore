"""Public catalog contracts and lossless code resolution."""

import json
from dataclasses import asdict

import pytest

from radiankore.catalogs import EventType, IdentificationType
from radiankore.models.responses import EventParty, InvoiceEvent


def test_identification_catalog_contains_documented_codes() -> None:
    assert {member.value for member in IdentificationType} == {
        "11",
        "12",
        "13",
        "21",
        "22",
        "31",
        "41",
        "42",
        "47",
        "48",
        "50",
        "91",
    }
    assert all(member.label.strip() for member in IdentificationType)
    assert IdentificationType.CITIZENSHIP_CARD.label == "Cédula de ciudadanía"
    assert IdentificationType.NUIP.label == "NUIP"


def test_event_catalog_combines_documented_sources() -> None:
    assert {member.value for member in EventType} == {
        "02",
        "04",
        "030",
        "031",
        "032",
        "033",
        "034",
        "035",
        "036",
        "037",
        "038",
        "039",
        "040",
        "041",
        "042",
        "043",
        "044",
        "045",
        "046",
        "047",
        "048",
        "049",
        "050",
        "051",
    }
    assert all(member.label.strip() for member in EventType)
    assert EventType.DIAN_VALIDATED.label == "Documento validado por la DIAN"
    assert EventType.EXPRESS_ACCEPTANCE.label == "Aceptación expresa"
    assert EventType.OWNERSHIP_ENDORSEMENT.label == "Endoso en propiedad"


def test_catalog_members_are_string_codes_with_read_only_labels() -> None:
    assert str(IdentificationType.NIT) == "31"
    assert IdentificationType("31") is IdentificationType.NIT
    assert isinstance(IdentificationType.NIT, str)
    assert EventType("030") is EventType.INVOICE_ACKNOWLEDGEMENT
    assert json.loads(
        json.dumps([IdentificationType.NIT, EventType.DIAN_VALIDATED])
    ) == ["31", "02"]
    attribute_name = "label"
    for member in (IdentificationType.NIT, EventType.EXPRESS_ACCEPTANCE):
        with pytest.raises(AttributeError):
            setattr(member, attribute_name, "Changed")


@pytest.mark.parametrize("code", list(IdentificationType))
def test_identification_catalog_resolves_model_code(code: IdentificationType) -> None:
    party = EventParty(identification_type=code)
    assert party.identification_type is code
    assert IdentificationType.from_code(code.value) is code
    assert party.identification_type == code
    assert asdict(party)["identification_type"] is code
    assert json.loads(json.dumps(asdict(party)))["identification_type"] == code.value


@pytest.mark.parametrize("code", list(EventType))
def test_event_catalog_resolves_model_code(code: EventType) -> None:
    event = InvoiceEvent(id="EVENT-1", code=code, description="XML description")
    assert event.code is code
    assert EventType.from_code(code.value) is code
    assert event.code == code
    assert asdict(event)["code"] is code
    assert json.loads(json.dumps(asdict(event)))["code"] == code.value
    assert event.description == "XML description"


def test_models_accept_absent_enum_fields() -> None:
    assert EventParty().identification_type is None
    assert EventParty(identification_type=None).identification_type is None
    assert InvoiceEvent(id="EVENT-1").code is None
    assert InvoiceEvent(id="EVENT-1", code=None).code is None


@pytest.mark.parametrize(
    "value", ["31", "FUTURE", "", 31, True, EventType.INVOICE_CLAIM]
)
def test_party_requires_identification_enum(value: object) -> None:
    with pytest.raises(TypeError, match="identification_type"):
        EventParty(identification_type=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value", ["033", "FUTURE", "", 33, True, IdentificationType.NIT]
)
def test_event_requires_event_enum(value: object) -> None:
    with pytest.raises(TypeError, match="code"):
        InvoiceEvent(id="EVENT-1", code=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "code", [None, "", "099", "1", "0310", " 31 ", "031", "FUTURE"]
)
def test_identification_lookup_handles_unknown_codes(code: str | None) -> None:
    assert IdentificationType.from_code(code) is None
    if code is not None:
        with pytest.raises(ValueError):
            IdentificationType(code)


@pytest.mark.parametrize("code", [None, "", "999", "30", "002", " 030 ", "FUTURE"])
def test_event_lookup_handles_unknown_codes(code: str | None) -> None:
    assert EventType.from_code(code) is None
    if code is not None:
        with pytest.raises(ValueError):
            EventType(code)
