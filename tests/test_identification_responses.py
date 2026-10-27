"""Identification evidence is tolerant on input and strict for outbound models."""

import unicodedata
from base64 import b64encode
from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import Any

import pytest
from lxml import etree

from radiankore._soap.document_info_response import parse_document_info_response
from radiankore._soap.namespaces import CBC, RESPONSE, SOAP, WCF, XSI
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore._soap.response import parse_invoice_events_response
from radiankore.catalogs import IdentificationType, OrganizationType
from radiankore.models.events import InvoiceEventParty, RadianParty
from radiankore.models.responses import DocumentParty, EventParty

_OPERATIONS = ("document_info", "invoice_events", "reference_notes")
_ENTITY = "http://schemas.datacontract.org/2004/07/Entidad"


def _parties(value: Any) -> list[DocumentParty | EventParty]:
    if isinstance(value, DocumentParty | EventParty):
        return [value]
    if is_dataclass(value) and not isinstance(value, type):
        return [
            party
            for field in fields(value)
            for party in _parties(getattr(value, field.name))
        ]
    if isinstance(value, tuple):
        return [party for item in value for party in _parties(item)]
    return []


def _read(
    request: pytest.FixtureRequest,
    operation: str,
    raw: str | None,
    *,
    nil: bool = False,
) -> list[DocumentParty | EventParty]:
    fixture = {
        "document_info": "document_info_response",
        "invoice_events": "application_response",
        "reference_notes": "reference_notes_application",
    }[operation]
    root = etree.fromstring(request.getfixturevalue(fixture))
    tag = (
        f"{{{_ENTITY}}}TipoDoc"
        if operation == "document_info"
        else f"{{{CBC}}}CompanyID"
    )
    for node in list(root.iter(tag)):
        if nil:
            node.set(f"{{{XSI}}}nil", "true")
        elif operation == "document_info":
            if raw is None:
                parent = node.getparent()
                assert parent is not None
                parent.remove(node)
            else:
                node.text = raw
        elif raw is None:
            node.attrib.pop("schemeName", "")
        else:
            node.set("schemeName", raw)
    result: Any
    if operation == "document_info":
        result = parse_document_info_response(etree.tostring(root))
    else:
        event_query = operation == "invoice_events"
        envelope = etree.fromstring(
            request.getfixturevalue(
                "soap_response" if event_query else "reference_notes_response"
            )
        )
        name = "GetStatusEvent" if event_query else "GetReferenceNotes"
        payload = envelope.find(
            f"{{{SOAP}}}Body/{{{WCF}}}{name}Response/{{{WCF}}}{name}Result/{{{RESPONSE}}}XmlBase64Bytes"
        )
        assert payload is not None
        payload.text = b64encode(etree.tostring(root)).decode("ascii")
        result = (
            parse_invoice_events_response
            if event_query
            else parse_reference_notes_response
        )(etree.tostring(envelope))
    parties = _parties(result)
    assert len(parties) >= 2
    return parties


@pytest.mark.parametrize("operation", _OPERATIONS)
@pytest.mark.parametrize("kind", list(IdentificationType))
@pytest.mark.parametrize(
    "variant",
    ["code", "label", "uppercase", "unaccented", "decomposed", "unicode_spaces"],
)
def test_known_identification_codes_and_labels(
    request: pytest.FixtureRequest,
    operation: str,
    kind: IdentificationType,
    variant: str,
) -> None:
    raw = {
        "code": kind.value,
        "label": kind.label,
        "uppercase": f"  {'  '.join(kind.label.upper().split())}  ",
        "unaccented": "".join(
            c
            for c in unicodedata.normalize("NFD", kind.label)
            if not unicodedata.combining(c)
        ),
        "decomposed": unicodedata.normalize("NFD", kind.label),
        "unicode_spaces": "\t" + "\u00a0".join(kind.label.split()) + "\n",
    }[variant]
    for party in _read(request, operation, raw):
        assert party.identification_type is kind
        assert party.identification_type_raw == raw


@pytest.mark.parametrize("operation", _OPERATIONS)
@pytest.mark.parametrize(
    "raw", ["999", "031", "  FUTURE-ID  ", "N.I.T.", "Cedula ciudadania"]
)
def test_unknown_identification_keeps_original_evidence(
    request: pytest.FixtureRequest, operation: str, raw: str
) -> None:
    for party in _read(request, operation, raw):
        assert party.identification_type is None
        assert party.identification_type_raw == raw


@pytest.mark.parametrize("operation", _OPERATIONS)
@pytest.mark.parametrize(
    "raw,nil", [(None, False), ("", False), ("   ", False), ("13", True)]
)
def test_absent_empty_and_nil_identification(
    request: pytest.FixtureRequest, operation: str, raw: str | None, nil: bool
) -> None:
    for party in _read(request, operation, raw, nil=nil):
        assert party.identification_type is None
        assert party.identification_type_raw is None


@pytest.mark.parametrize("model", [DocumentParty, EventParty])
def test_raw_identification_is_optional_typed_and_immutable(
    model: type[DocumentParty] | type[EventParty],
) -> None:
    assert model().identification_type_raw is None
    party = model(identification_type_raw="FUTURE")
    with pytest.raises(FrozenInstanceError):
        party.identification_type_raw = "13"  # type: ignore[misc]
    invalid_values: tuple[object, ...] = (13, [], {})
    for invalid in invalid_values:
        with pytest.raises(TypeError, match="identification_type_raw"):
            model(identification_type_raw=invalid)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="identification_type"):
        model(identification_type="13")  # type: ignore[arg-type]


@pytest.mark.parametrize("party_type", [InvoiceEventParty, RadianParty])
@pytest.mark.parametrize("raw", ["Cédula de ciudadanía", "FUTURE-ID", "31", None])
def test_emission_still_requires_identification_enum(
    party_type: type[InvoiceEventParty] | type[RadianParty], raw: str | None
) -> None:
    with pytest.raises(TypeError, match="IdentificationType"):
        party_type(
            name="Synthetic participant",
            tax_number="900123456",
            identification_type=raw,  # type: ignore[arg-type]
            organization_type=OrganizationType("1"),
        )
