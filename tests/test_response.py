"""Parser contracts, including malformed and potentially unsafe XML inputs."""

from base64 import b64encode
from dataclasses import FrozenInstanceError
from datetime import date, time, timedelta

import pytest
from lxml import etree

from radiankore import DianResponseError, DianSoapFaultError
from radiankore._soap.namespaces import AR, CAC, CBC, RESPONSE, SOAP, WCF, XSI
from radiankore._soap.parsing import parse_xml
from radiankore._soap.response import parse_invoice_events_response
from radiankore.catalogs import EventType, IdentificationType
from radiankore.models.responses import EventParty, InvoiceEvent, InvoiceEventsResult


def test_parse_nine_events_without_deduplication(soap_response: bytes) -> None:
    result = parse_invoice_events_response(soap_response)
    assert isinstance(result, InvoiceEventsResult)
    assert result.is_valid
    assert result.status_code == "00"
    assert result.messages == ("Synthetic notification",)
    assert result.document_key == "SYNTHETIC-CUFE"
    assert result.file_name == "synthetic.xml"
    assert [e.code for e in result.events] == [
        "030",
        "032",
        "033",
        "036",
        "037",
        "036",
        "037",
        "036",
        "037",
    ]
    event = result.events[0]
    assert event.reference_id == "1"
    assert event.description == "Synthetic event\nAdditional description"
    assert event.date == date(2026, 1, 15)
    assert event.time is not None
    assert event.time.hour == 10 and event.time.minute == 30
    assert event.time.utcoffset() == timedelta(hours=-5)
    assert event.issuer is not None and event.issuer.tax_number == "000123456"
    assert event.recipient is not None
    assert event.issuer.verification_digit == "0"
    assert event.issuer.identification_type is IdentificationType.NIT
    assert event.recipient.identification_type is IdentificationType.CITIZENSHIP_CARD
    assert event.code is EventType.INVOICE_ACKNOWLEDGEMENT
    event_type = event.code
    assert event_type is not None
    assert event.description != event_type.label
    assert event.recipient == EventParty(
        tax_number="000987654",
        name="Synthetic RecipientParty",
        verification_digit="7",
        identification_type=IdentificationType.CITIZENSHIP_CARD,
        identification_type_raw="13",
    )
    assert event.id == "EVENT-0001"
    assert event.uuid == "SYNTHETIC-EVENT-UUID-1"
    assert "ApplicationResponse" not in repr(result)
    assert result.application_response_xml is not None
    field_name = "code"
    with pytest.raises(FrozenInstanceError):
        setattr(event, field_name, "changed")
    assert not hasattr(event, "__dict__")


def _replace_payload(soap: bytes, payload: bytes) -> bytes:
    root = etree.fromstring(soap)
    node = root.find(f".//{{{RESPONSE}}}XmlBase64Bytes")
    assert node is not None
    node.text = b64encode(payload).decode("ascii")
    return etree.tostring(root)


def test_events_are_sorted_by_numeric_reference_without_deduplication(
    soap_response: bytes,
) -> None:
    root = etree.Element(f"{{{AR}}}ApplicationResponse")
    references = ["10", "2", None, "001", "2", "unknown", "0", "0002", ""]
    for index, value in enumerate(references):
        event = etree.SubElement(root, f"{{{CAC}}}DocumentResponse")
        response = etree.SubElement(event, f"{{{CAC}}}Response")
        if value is not None:
            etree.SubElement(response, f"{{{CBC}}}ReferenceID").text = value
        reference = etree.SubElement(event, f"{{{CAC}}}DocumentReference")
        etree.SubElement(reference, f"{{{CBC}}}ID").text = f"EVENT-{index}"
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert [event.id for event in result.events] == [
        "EVENT-6",
        "EVENT-3",
        "EVENT-1",
        "EVENT-4",
        "EVENT-7",
        "EVENT-0",
        "EVENT-2",
        "EVENT-5",
        "EVENT-8",
    ]
    assert [event.reference_id for event in result.events] == [
        "0",
        "001",
        "2",
        "2",
        "0002",
        "10",
        None,
        "unknown",
        None,
    ]
    assert result.application_response_xml == etree.tostring(root)


@pytest.mark.parametrize("code", ["FUTURE-CODE", "30", "002", "999"])
def test_unknown_event_code_is_rejected(soap_response: bytes, code: str) -> None:
    payload = f'''<ApplicationResponse xmlns="{AR}" xmlns:cac="{CAC}" xmlns:cbc="{CBC}">
      <cac:DocumentResponse><cac:Response><cbc:ResponseCode>{code}</cbc:ResponseCode>
      </cac:Response><cac:DocumentReference><cbc:ID>EVENT-0001</cbc:ID>
      </cac:DocumentReference></cac:DocumentResponse></ApplicationResponse>'''.encode()
    with pytest.raises(DianResponseError, match="Unknown invoice event code") as error:
        parse_invoice_events_response(_replace_payload(soap_response, payload))
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize("value", [None, "", " \t "])
def test_event_code_is_optional(soap_response: bytes, value: str | None) -> None:
    root = etree.Element(f"{{{AR}}}ApplicationResponse")
    event = etree.SubElement(root, f"{{{CAC}}}DocumentResponse")
    response = etree.SubElement(event, f"{{{CAC}}}Response")
    if value is not None:
        etree.SubElement(response, f"{{{CBC}}}ResponseCode").text = value
    reference = etree.SubElement(event, f"{{{CAC}}}DocumentReference")
    etree.SubElement(reference, f"{{{CBC}}}ID").text = "  0001  "
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events == (InvoiceEvent(id="0001"),)
    assert result.events[0].code is None


def test_nil_event_code_is_absent(
    soap_response: bytes, application_response: bytes
) -> None:
    root = etree.fromstring(application_response)
    code = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert code is not None
    code.set(f"{{{XSI}}}nil", "true")
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events[0].code is None


@pytest.mark.parametrize("party_name", ["IssuerParty", "RecipientParty"])
@pytest.mark.parametrize("value", ["099", "1", "031", "FUTURE"])
def test_unknown_identification_is_preserved(
    soap_response: bytes, application_response: bytes, party_name: str, value: str
) -> None:
    root = etree.fromstring(application_response)
    company = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}{party_name}/"
        f"{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID"
    )
    assert company is not None
    company.set("schemeName", value)
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    parsed = (
        result.events[0].issuer
        if party_name == "IssuerParty"
        else result.events[0].recipient
    )
    assert parsed is not None
    assert parsed.identification_type is None
    assert parsed.identification_type_raw == value


def test_spaced_event_code_resolves_to_enum(
    soap_response: bytes, application_response: bytes
) -> None:
    root = etree.fromstring(application_response)
    code = root.find(
        f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}ResponseCode"
    )
    assert code is not None
    code.text = " 033 "
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events[0].code is EventType.EXPRESS_ACCEPTANCE
    assert result.events[0].code.value == "033"


@pytest.mark.parametrize(
    "missing", ["Response", "DocumentReference", "ID", "empty_id", "nil_id"]
)
def test_event_requires_response_and_reference_id(
    soap_response: bytes, application_response: bytes, missing: str
) -> None:
    root = etree.fromstring(application_response)
    event = root.find(f"{{{CAC}}}DocumentResponse")
    assert event is not None
    if missing in {"Response", "DocumentReference"}:
        node = event.find(f"{{{CAC}}}{missing}")
        assert node is not None
        event.remove(node)
    else:
        reference = event.find(f"{{{CAC}}}DocumentReference")
        assert reference is not None
        node = reference.find(f"{{{CBC}}}ID")
        assert node is not None
        if missing == "ID":
            reference.remove(node)
        elif missing == "empty_id":
            node.text = " \t "
        else:
            node.set(f"{{{XSI}}}nil", "true")
    with pytest.raises(DianResponseError):
        parse_invoice_events_response(
            _replace_payload(soap_response, etree.tostring(root))
        )


@pytest.mark.parametrize("party_name", ["IssuerParty", "RecipientParty"])
@pytest.mark.parametrize(
    "mode",
    [
        "attributes_missing",
        "attributes_empty",
        "text_values",
        "company_missing",
        "scheme_missing",
        "party_missing",
        "company_nil",
    ],
)
def test_optional_party_identification(
    soap_response: bytes, application_response: bytes, party_name: str, mode: str
) -> None:
    root = etree.fromstring(application_response)
    event = root.find(f"{{{CAC}}}DocumentResponse")
    assert event is not None
    party = event.find(f"{{{CAC}}}{party_name}")
    assert party is not None
    scheme = party.find(f"{{{CAC}}}PartyTaxScheme")
    assert scheme is not None
    company = scheme.find(f"{{{CBC}}}CompanyID")
    assert company is not None
    if mode == "attributes_missing":
        company.attrib.clear()
    elif mode == "attributes_empty":
        company.set("schemeID", " \t ")
        company.set("schemeName", "")
    elif mode == "text_values":
        company.text = " 00001234 "
        company.set("schemeID", " 0 ")
        company.set("schemeName", " 31 ")
    elif mode == "company_missing":
        scheme.remove(company)
    elif mode == "scheme_missing":
        party.remove(scheme)
    elif mode == "party_missing":
        event.remove(party)
    else:
        company.set(f"{{{XSI}}}nil", "true")
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    parsed = (
        result.events[0].issuer
        if party_name == "IssuerParty"
        else result.events[0].recipient
    )
    if mode == "party_missing":
        assert parsed is None
        return
    assert parsed is not None
    assert parsed.name == (
        None if mode == "scheme_missing" else f"Synthetic {party_name}"
    )
    if mode == "text_values":
        assert parsed.tax_number == "00001234"
        assert parsed.verification_digit == "0"
        assert parsed.identification_type is IdentificationType.NIT
    else:
        assert parsed.verification_digit is None
        assert parsed.identification_type is None
        expected = "000123456" if party_name == "IssuerParty" else "000987654"
        assert parsed.tax_number == (
            expected if mode.startswith("attributes_") else None
        )


def test_event_uses_first_document_reference(
    soap_response: bytes, application_response: bytes
) -> None:
    root = etree.fromstring(application_response)
    event = root.find(f"{{{CAC}}}DocumentResponse")
    assert event is not None
    reference = etree.SubElement(event, f"{{{CAC}}}DocumentReference")
    etree.SubElement(reference, f"{{{CBC}}}ID").text = "SECOND-ID"
    etree.SubElement(reference, f"{{{CBC}}}UUID").text = "SECOND-UUID"
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events[0].id == "EVENT-0001"
    assert result.events[0].uuid == "SYNTHETIC-EVENT-UUID-1"


@pytest.mark.parametrize(
    "values,expected",
    [
        ([], ""),
        ([None, "", " \t "], ""),
        ([" Single description "], "Single description"),
        ([" First ", None, "  ", "Second", " Third "], "First\nSecond\nThird"),
    ],
)
def test_description_is_one_text_without_losing_nonempty_values(
    soap_response: bytes, values: list[str | None], expected: str
) -> None:
    root = etree.Element(f"{{{AR}}}ApplicationResponse")
    event = etree.SubElement(root, f"{{{CAC}}}DocumentResponse")
    response = etree.SubElement(event, f"{{{CAC}}}Response")
    etree.SubElement(response, f"{{{CBC}}}ResponseCode").text = "030"
    for value in values:
        etree.SubElement(response, f"{{{CBC}}}Description").text = value
    reference = etree.SubElement(event, f"{{{CAC}}}DocumentReference")
    etree.SubElement(reference, f"{{{CBC}}}ID").text = "EVENT-0001"
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events[0].description == expected


@pytest.mark.parametrize("missing", ["date", "time", "both"])
def test_event_dates_do_not_fall_back_to_container_issue_dates(
    soap_response: bytes, application_response: bytes, missing: str
) -> None:
    root = etree.fromstring(application_response)
    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    for field in ["EffectiveDate", "EffectiveTime"]:
        if (
            missing == "both"
            or (missing == "date" and field == "EffectiveDate")
            or (missing == "time" and field == "EffectiveTime")
        ):
            node = response.find(f"{{{CBC}}}{field}")
            assert node is not None
            response.remove(node)
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    event = result.events[0]
    assert (event.date is None) == (missing in {"date", "both"})
    assert (event.time is None) == (missing in {"time", "both"})


@pytest.mark.parametrize(
    "date_text,time_text,expected_date,expected_time",
    [
        ("2026-01-15", "10:30:00-05:00", "2026-01-15", "10:30:00-05:00"),
        ("2026-01-15", "10:30:00", "2026-01-15", "10:30:00-05:00"),
        ("2026-01-15", "00:00:00", "2026-01-15", "00:00:00-05:00"),
        ("2026-01-15", "15:30:00Z", "2026-01-15", "10:30:00-05:00"),
        ("2026-01-01", "02:30:00+00:00", "2025-12-31", "21:30:00-05:00"),
        ("2026-12-31", "23:30:00-06:00", "2027-01-01", "00:30:00-05:00"),
        ("2026-01-15", "02:30:00+03:00", "2026-01-14", "18:30:00-05:00"),
        (None, "02:30:00Z", None, "21:30:00-05:00"),
        (None, "10:30:00", None, "10:30:00-05:00"),
        (None, "10:30:00-05:00", None, "10:30:00-05:00"),
        ("2026-01-15", None, "2026-01-15", None),
        (None, None, None, None),
        ("2026-01-15", "15:30:00.123456Z", "2026-01-15", "10:30:00.123456-05:00"),
    ],
)
def test_event_date_and_time_are_normalized_to_colombia(
    soap_response: bytes,
    application_response: bytes,
    date_text: str | None,
    time_text: str | None,
    expected_date: str | None,
    expected_time: str | None,
) -> None:
    root = etree.fromstring(application_response)
    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    for field, value in [("EffectiveDate", date_text), ("EffectiveTime", time_text)]:
        node = response.find(f"{{{CBC}}}{field}")
        assert node is not None
        if value is None:
            response.remove(node)
        else:
            node.text = value
    payload = etree.tostring(root)
    result = parse_invoice_events_response(_replace_payload(soap_response, payload))
    event = result.events[0]
    assert event.date == (date.fromisoformat(expected_date) if expected_date else None)
    assert event.time == (time.fromisoformat(expected_time) if expected_time else None)
    if event.time is not None:
        assert event.time.isoformat() == expected_time
        assert event.time.utcoffset() == timedelta(hours=-5)
    assert result.application_response_xml == payload


def test_unrepresentable_local_date_raises_response_error(
    soap_response: bytes, application_response: bytes
) -> None:
    root = etree.fromstring(application_response)
    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    date_node = response.find(f"{{{CBC}}}EffectiveDate")
    time_node = response.find(f"{{{CBC}}}EffectiveTime")
    assert date_node is not None and time_node is not None
    date_node.text = "0001-01-01"
    time_node.text = "00:00:00Z"
    with pytest.raises(DianResponseError) as error:
        parse_invoice_events_response(
            _replace_payload(soap_response, etree.tostring(root))
        )
    assert isinstance(error.value.__cause__, OverflowError)


def test_missing_event_uuid_is_not_replaced_by_another_identifier(
    soap_response: bytes, application_response: bytes
) -> None:
    root = etree.fromstring(application_response)
    reference = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}DocumentReference")
    assert reference is not None
    node = reference.find(f"{{{CBC}}}UUID")
    assert node is not None
    reference.remove(node)
    result = parse_invoice_events_response(
        _replace_payload(soap_response, etree.tostring(root))
    )
    assert result.events[0].uuid is None
    assert result.events[0].reference_id == "1"
    assert result.document_key == "SYNTHETIC-CUFE"


@pytest.mark.parametrize("mode", ["missing", "nil", "empty"])
def test_missing_payload_and_business_rejection(
    soap_response: bytes, mode: str
) -> None:
    root = etree.fromstring(soap_response)
    result = root.find(f".//{{{WCF}}}GetStatusEventResult")
    assert result is not None
    payload = result.find(f"{{{RESPONSE}}}XmlBase64Bytes")
    valid = result.find(f"{{{RESPONSE}}}IsValid")
    status = result.find(f"{{{RESPONSE}}}StatusCode")
    assert payload is not None and valid is not None and status is not None
    valid.text, status.text = "false", "90"
    if mode == "missing":
        result.remove(payload)
    else:
        payload.text = None
        if mode == "nil":
            payload.set(f"{{{XSI}}}nil", "true")
    parsed = parse_invoice_events_response(etree.tostring(root))
    assert not parsed.is_valid and parsed.status_code == "90"
    assert parsed.events == () and parsed.application_response_xml is None


@pytest.mark.parametrize("mode", ["missing", "nil"])
def test_invoice_query_requires_a_present_result(
    soap_response: bytes, mode: str
) -> None:
    root = etree.fromstring(soap_response)
    response = root.find(f"{{{SOAP}}}Body/{{{WCF}}}GetStatusEventResponse")
    assert response is not None
    result = response.find(f"{{{WCF}}}GetStatusEventResult")
    assert result is not None
    if mode == "missing":
        response.remove(result)
    else:
        result.set(f"{{{XSI}}}nil", "true")
    with pytest.raises(DianResponseError, match="non-null GetStatusEventResult"):
        parse_invoice_events_response(etree.tostring(root))


@pytest.mark.parametrize("payload", [b"<broken", b"<WrongRoot/>", b"\x00\xff"])
def test_reject_invalid_decoded_xml(soap_response: bytes, payload: bytes) -> None:
    with pytest.raises(DianResponseError):
        parse_invoice_events_response(_replace_payload(soap_response, payload))


def test_invalid_base64_is_not_reported_as_no_events(soap_response: bytes) -> None:
    root = etree.fromstring(soap_response)
    node = root.find(f".//{{{RESPONSE}}}XmlBase64Bytes")
    assert node is not None
    node.text = "%%%not-base64%%%"
    with pytest.raises(DianResponseError) as error:
        parse_invoice_events_response(etree.tostring(root))
    assert error.value.__cause__ is not None


@pytest.mark.parametrize("value", [None, "invalid"])
def test_invalid_status_metadata(soap_response: bytes, value: str | None) -> None:
    root = etree.fromstring(soap_response)
    node = root.find(f".//{{{RESPONSE}}}IsValid")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError):
        parse_invoice_events_response(etree.tostring(root))


@pytest.mark.parametrize(
    "field,value",
    [("EffectiveDate", "bad"), ("EffectiveTime", "bad")],
)
def test_invalid_event_fields(
    soap_response: bytes, application_response: bytes, field: str, value: str
) -> None:
    root = etree.fromstring(application_response)
    node = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}{field}")
    assert node is not None
    node.text = value
    with pytest.raises(DianResponseError):
        parse_invoice_events_response(
            _replace_payload(soap_response, etree.tostring(root))
        )


@pytest.mark.parametrize(
    "data",
    [
        b"<wrong/>",
        b"<broken",
        f'<s:Envelope xmlns:s="{SOAP}"><s:Body/></s:Envelope>'.encode(),
        f'<s:Envelope xmlns:s="{SOAP}"><s:Body/><s:Body/></s:Envelope>'.encode(),
    ],
)
def test_unexpected_soap_structure(data: bytes) -> None:
    with pytest.raises(DianResponseError):
        parse_invoice_events_response(data)


def test_fault_preserves_code_and_reason(soap_fault: bytes) -> None:
    with pytest.raises(DianSoapFaultError) as error:
        parse_invoice_events_response(soap_fault)
    assert error.value.code == "s:Sender"
    assert error.value.reason == "Synthetic authentication error"
    assert "authentication" not in str(error.value)


@pytest.mark.parametrize(
    "data",
    [
        b'<!DOCTYPE root [<!ENTITY secret SYSTEM "file:///etc/passwd">]><root>&secret;</root>',
        b'<!DOCTYPE root SYSTEM "https://example.invalid/schema.dtd"><root/>',
    ],
)
def test_reject_dtd_and_external_entities(data: bytes) -> None:
    with pytest.raises(DianResponseError, match="DTD"):
        parse_xml(data)
