"""Typed UBL notes, cardinalities and safe payload interpretation."""

from base64 import b64encode
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from datetime import date, time, timedelta, timezone

import pytest
from lxml import etree

from radiankore import DianResponseError
from radiankore._soap.namespaces import AR, CAC, CBC, RESPONSE, SOAP, WCF, XSI
from radiankore._soap.reference_notes_response import parse_reference_notes_response
from radiankore.catalogs import DocumentType, IdentificationType
from radiankore.models.responses import (
    NoteDocumentReference,
    NoteLineResponse,
    NoteResponse,
    ReferenceNote,
    ReferenceNotesResult,
)

COLOMBIA = timezone(timedelta(hours=-5))


def read_payload(envelope: bytes, payload: bytes) -> ReferenceNotesResult:
    root = etree.fromstring(envelope)
    node = root.find(
        f"{{{SOAP}}}Body/{{{WCF}}}GetReferenceNotesResponse/"
        f"{{{WCF}}}GetReferenceNotesResult/{{{RESPONSE}}}XmlBase64Bytes"
    )
    assert node is not None
    node.text = b64encode(payload).decode("ascii")
    result = parse_reference_notes_response(etree.tostring(root))
    assert result is not None
    return result


def test_multiple_notes_references_and_line_reasons(
    reference_notes_response: bytes,
) -> None:
    result = parse_reference_notes_response(reference_notes_response)
    assert result is not None and len(result.notes) == 2
    note, second = result.notes
    assert (note.reference_id, second.reference_id) == ("10", "2")
    assert note.code is DocumentType.CREDIT_NOTE
    assert second.code is DocumentType.DEBIT_NOTE
    assert note.description == "Nota de crédito electrónica\nSecond description"
    assert note.date == date(2026, 10, 19)
    assert note.time == time(10, 17, 18, tzinfo=COLOMBIA)
    assert note.references == (
        NoteDocumentReference(id="NC-001", uuid="NOTE-UUID-1"),
        NoteDocumentReference(id="00002"),
    )
    assert note.issuer is not None and note.recipient is not None
    assert note.issuer.tax_number == "000123"
    assert note.issuer.verification_digit == "4"
    assert note.issuer.name == "Synthetic issuer"
    assert note.issuer.identification_type is IdentificationType.NIT
    assert note.recipient.tax_number == "000456"
    assert note.recipient.verification_digit == "7"
    assert note.recipient.identification_type is IdentificationType.CITIZENSHIP_CARD
    assert note.line_responses == (
        NoteLineResponse(
            line_id="001",
            responses=(
                NoteResponse(code="2", description="Anulación de factura electrónica"),
                NoteResponse(
                    reference_id="LINE-REF",
                    code="FUTURE-REASON",
                    description="Other reason",
                    date=date(2026, 10, 19),
                    time=time(21, 30, tzinfo=COLOMBIA),
                ),
            ),
        ),
        NoteLineResponse(line_id="002", responses=(NoteResponse(),)),
    )
    assert second.date is None and second.time is None
    assert (
        second.description == "" and second.issuer is None and second.recipient is None
    )
    assert second.line_responses == ()
    assert second.references == (
        NoteDocumentReference(id="NC-002", uuid="NOTE-UUID-2"),
    )


def test_negative_business_status_does_not_hide_notes(
    reference_notes_response: bytes,
) -> None:
    root = etree.fromstring(reference_notes_response)
    valid = root.find(f".//{{{RESPONSE}}}IsValid")
    code = root.find(f".//{{{RESPONSE}}}StatusCode")
    assert valid is not None and code is not None
    valid.text = "false"
    code.text = "00"
    result = parse_reference_notes_response(etree.tostring(root))
    assert result is not None and result.is_valid is False
    assert result.status_code == "00" and len(result.notes) == 2


def test_repeated_notes_are_not_deduplicated(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
) -> None:
    root = etree.fromstring(reference_notes_application)
    first = root.find(f"{{{CAC}}}DocumentResponse")
    assert first is not None
    root.append(deepcopy(first))
    result = read_payload(reference_notes_response, etree.tostring(root))
    assert len(result.notes) == 3 and result.notes[0] == result.notes[2]


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        f'<ApplicationResponse xmlns="{AR}"/>'.encode(),
        (
            f'<ApplicationResponse xmlns="{AR}">'
            '<DocumentResponse xmlns="urn:foreign"/></ApplicationResponse>'
        ).encode(),
    ],
)
def test_empty_payloads_and_no_direct_notes(
    reference_notes_response: bytes,
    payload: bytes,
) -> None:
    result = read_payload(reference_notes_response, payload)
    assert result.notes == () and result.xml_base64_bytes == payload
    assert result.xml_bytes == b"\x00\xffNOTES"


@pytest.mark.parametrize(
    "payload",
    [
        b"not xml",
        b"\x00\x80\xff",
        b"<broken",
        b"<notes/>",
        b'<ApplicationResponse xmlns="urn:foreign"/>',
        (
            '<!DOCTYPE ApplicationResponse [<!ENTITY test "x">]>'
            f'<ApplicationResponse xmlns="{AR}"/>'
        ).encode(),
    ],
)
def test_nonempty_invalid_payload_fails(
    reference_notes_response: bytes, payload: bytes
) -> None:
    with pytest.raises(DianResponseError):
        read_payload(reference_notes_response, payload)


@pytest.mark.parametrize(
    "path",
    [
        f"{{{CAC}}}Response",
        f"{{{CAC}}}DocumentReference",
        f"{{{CAC}}}DocumentReference/{{{CBC}}}ID",
        f"{{{CAC}}}LineResponse/{{{CAC}}}LineReference",
        f"{{{CAC}}}LineResponse/{{{CAC}}}LineReference/{{{CBC}}}LineID",
        f"{{{CAC}}}LineResponse/{{{CAC}}}Response",
    ],
)
@pytest.mark.parametrize("mode", ["missing", "foreign", "empty"])
def test_required_note_structure(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    path: str,
    mode: str,
) -> None:
    root = etree.fromstring(reference_notes_application)
    note = root.find(f"{{{CAC}}}DocumentResponse")
    assert note is not None
    nodes = note.findall(path)
    assert nodes
    for node in nodes:
        parent = node.getparent()
        assert parent is not None
        if mode == "missing":
            parent.remove(node)
        elif mode == "foreign":
            node.tag = f"{{urn:foreign}}{etree.QName(node).localname}"
        else:
            node.clear()
    # Empty Response is legal: its scalar children are optional.
    if mode == "empty" and path.endswith(f"{{{CAC}}}Response"):
        assert read_payload(reference_notes_response, etree.tostring(root)).notes
    else:
        with pytest.raises(DianResponseError):
            read_payload(reference_notes_response, etree.tostring(root))


@pytest.mark.parametrize(
    "path",
    [
        f"{{{CAC}}}Response",
        f"{{{CAC}}}LineResponse/{{{CAC}}}LineReference",
    ],
)
def test_duplicate_singletons_rejected(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    path: str,
) -> None:
    root = etree.fromstring(reference_notes_application)
    note = root.find(f"{{{CAC}}}DocumentResponse")
    assert note is not None
    node = note.find(path)
    assert node is not None
    parent = node.getparent()
    assert parent is not None
    parent.append(deepcopy(node))
    with pytest.raises(DianResponseError):
        read_payload(reference_notes_response, etree.tostring(root))


@pytest.mark.parametrize(
    "field",
    ["ReferenceID", "ResponseCode", "Description", "EffectiveDate", "EffectiveTime"],
)
@pytest.mark.parametrize("mode", ["missing", "nil", "empty"])
def test_optional_response_fields(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    field: str,
    mode: str,
) -> None:
    root = etree.fromstring(reference_notes_application)
    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    for node in response.findall(f"{{{CBC}}}{field}"):
        if mode == "missing":
            response.remove(node)
        elif mode == "nil":
            node.text = None
            node.set(f"{{{XSI}}}nil", "true")
        else:
            node.text = " \n "
    result = read_payload(reference_notes_response, etree.tostring(root))
    note = result.notes[0]
    attribute = {
        "ReferenceID": "reference_id",
        "ResponseCode": "code",
        "Description": "description",
        "EffectiveDate": "date",
        "EffectiveTime": "time",
    }[field]
    assert getattr(note, attribute) == ("" if field == "Description" else None)


@pytest.mark.parametrize(
    "day,clock,expected_day,expected_time",
    [
        ("2026-10-20", "02:30:00Z", date(2026, 10, 19), time(21, 30, tzinfo=COLOMBIA)),
        (
            "2026-10-19",
            "10:17:18",
            date(2026, 10, 19),
            time(10, 17, 18, tzinfo=COLOMBIA),
        ),
        (None, "02:30:00Z", None, time(21, 30, tzinfo=COLOMBIA)),
        ("2024-02-29", None, date(2024, 2, 29), None),
    ],
)
def test_native_effective_dates_and_colombian_times(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    day: str | None,
    clock: str | None,
    expected_day: date | None,
    expected_time: time | None,
) -> None:
    root = etree.fromstring(reference_notes_application)
    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    for name, value in [("EffectiveDate", day), ("EffectiveTime", clock)]:
        node = response.find(f"{{{CBC}}}{name}")
        assert node is not None
        node.text = value
    note = read_payload(reference_notes_response, etree.tostring(root)).notes[0]
    assert note.date == expected_day and note.time == expected_time
    if note.date is not None:
        assert type(note.date) is date


@pytest.mark.parametrize(
    "field,value",
    [
        ("EffectiveDate", "2026-02-29"),
        ("EffectiveDate", "20261020"),
        ("EffectiveDate", "2026-10-20T10:00:00"),
        ("EffectiveTime", "bad-time"),
    ],
)
@pytest.mark.parametrize("line", [False, True])
def test_invalid_dates_and_times_retain_cause(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    field: str,
    value: str,
    line: bool,
) -> None:
    root = etree.fromstring(reference_notes_application)
    path = (
        f"{{{CAC}}}DocumentResponse/"
        + (f"{{{CAC}}}LineResponse/" if line else "")
        + f"{{{CAC}}}Response"
    )
    response = root.find(path)
    assert response is not None
    node = response.find(f"{{{CBC}}}{field}")
    if node is None:
        node = etree.SubElement(response, f"{{{CBC}}}{field}")
    node.text = value
    with pytest.raises(DianResponseError) as error:
        read_payload(reference_notes_response, etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "model",
    [
        NoteDocumentReference(id="001"),
        NoteLineResponse(line_id="001"),
        NoteResponse(),
        ReferenceNote(),
    ],
)
def test_note_models_are_immutable(
    model: NoteDocumentReference | NoteLineResponse | NoteResponse | ReferenceNote,
) -> None:
    assert not hasattr(model, "__dict__")
    attribute = fields(model)[0].name
    with pytest.raises(FrozenInstanceError):
        setattr(model, attribute, "changed")


@pytest.mark.parametrize("code", [DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE])
def test_note_document_type_identity(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    code: DocumentType,
) -> None:
    root = etree.fromstring(reference_notes_application)
    node = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert node is not None
    node.text = f" {code.value} "
    result = read_payload(reference_notes_response, etree.tostring(root))
    assert result.notes[0].code is code
    assert ReferenceNote(code=code).code is code
    assert (
        result.notes[0].description == "Nota de crédito electrónica\nSecond description"
    )
    assert result.notes[0].line_responses[0].responses[0].code == "2"
    assert result.notes[0].line_responses[0].responses[1].code == "FUTURE-REASON"
    assert result.xml_base64_bytes == etree.tostring(root)


@pytest.mark.parametrize(
    "value",
    ["FUTURE-NOTE", "091", "092", "1", "01", "02", "03", "04", "96", "2", "030"],
)
def test_unknown_or_non_note_document_type(
    reference_notes_response: bytes,
    reference_notes_application: bytes,
    value: str,
) -> None:
    root = etree.fromstring(reference_notes_application)
    node = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError) as error:
        read_payload(reference_notes_response, etree.tostring(root))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("value", ["91", "92", "", 91, True, IdentificationType.NIT])
def test_reference_note_requires_document_enum(value: object) -> None:
    with pytest.raises(TypeError):
        ReferenceNote(code=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        item
        for item in DocumentType
        if item not in {DocumentType.CREDIT_NOTE, DocumentType.DEBIT_NOTE}
    ],
)
def test_reference_note_rejects_other_document_types(value: DocumentType) -> None:
    with pytest.raises(ValueError):
        ReferenceNote(code=value)
