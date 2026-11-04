"""Independent profile checks from FE 1.9 and RADIAN 1.1, beyond lax UBL XSDs.

Sources and exceptions are recorded in docs/technical/xml-conformance.md. Wire
literals below are transcribed from AAH04, not imported from production catalogs.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import operations
from radiankore._soap.namespaces import AR, CAC, CBC, STS
from radiankore.catalogs import EventType
from radiankore.models.events import (
    InvoiceResponseEvent,
    MandateEvent,
    RadianEvent,
    RadianSoftware,
)
from tests.profile_support import VARIANTS, assert_profile


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("environment", list(Environment))
def test_signed_profiles_against_annex_constraints(
    variant: str,
    environment: Environment,
    radian_event_factory: Callable[[str], RadianEvent],
    invoice_event_factory: Callable[[EventType], InvoiceResponseEvent],
    mandate_event: MandateEvent,
    digital_certificate: DigitalCertificate,
    radian_software: RadianSoftware,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            return datetime(2026, 10, 22, 18, tzinfo=UTC)

    monkeypatch.setattr(operations, "datetime", Clock)
    event: RadianEvent
    if variant.startswith("invoice:"):
        event = invoice_event_factory(EventType(variant.split(":")[1]))
    elif variant == "mandate":
        event = mandate_event
    else:
        event = radian_event_factory(variant)
    with DianClient.from_certificate(
        digital_certificate, environment=environment
    ) as client:
        prepared = client.prepare_radian_event(event=event, software=radian_software)
    verify_event_signature(prepared.xml_bytes, digital_certificate)
    assert_profile(
        etree.fromstring(prepared.xml_bytes), prepared.code.value, environment
    )


@pytest.mark.parametrize(
    "mutation", ["literal", "payment_count", "extension_name", "extension_order"]
)
def test_profile_oracle_detects_errors_accepted_by_generic_xsd(
    mutation: str,
    radian_event_factory: Callable[[str], RadianEvent],
    digital_certificate: DigitalCertificate,
    radian_software: RadianSoftware,
    radian_schema: etree.XMLSchema | None,
) -> None:
    variant = {"literal": "371", "payment_count": "451"}.get(mutation, "035")
    with DianClient.from_certificate(digital_certificate) as client:
        prepared = client.prepare_radian_event(
            event=radian_event_factory(variant), software=radian_software
        )
    root = etree.fromstring(prepared.xml_bytes)
    if mutation == "literal":
        node = root.find(
            f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response/{{{CBC}}}Description"
        )
        assert node is not None
        node.text = "Endoso en Propiedad"
    elif mutation == "payment_count":
        node = root.find(f"{{{CAC}}}SenderParty")
        assert node is not None
        legal = node.find(f"{{{CAC}}}PartyLegalEntity")
        assert legal is not None
        node.append(etree.fromstring(etree.tostring(legal)))
    else:
        node = root.find(f".//{{{AR}}}InformacionAvalar")
        assert node is not None
        if mutation == "extension_name":
            node[0].text = "ValorIncorrecto"
        else:
            node.insert(0, node[-1])
    if radian_schema is not None:
        radian_schema.assertValid(root)
    with pytest.raises(AssertionError):
        assert_profile(root, prepared.code.value, Environment.PRODUCTION)


def test_original_dian_schema_conflict_does_not_change_statutory_dv(
    radian_event_factory: Callable[[str], RadianEvent],
    digital_certificate: DigitalCertificate,
    radian_software: RadianSoftware,
) -> None:
    path = Path(__file__).resolve().parents[1] / (
        "docs/references/dian/radian/toolbox/XSD/maindoc/DIAN_UBL_Structures.xsd"
    )
    if not path.is_file():
        pytest.skip("Original DIAN references are excluded from distributions.")
    with DianClient.from_certificate(digital_certificate) as client:
        prepared = client.prepare_radian_event(
            event=radian_event_factory("035"), software=radian_software
        )
    root = etree.fromstring(prepared.xml_bytes)
    dian = root.find(f".//{{{STS}}}DianExtensions")
    assert dian is not None
    schema = etree.XMLSchema(etree.parse(str(path)))
    assert not schema.validate(dian)
    errors = str(schema.error_log)
    assert "attribute 'schemeID'" in errors
    assert "AuthorizationProviderID" in errors
    # AAB34 requires DV=4; the preserved XSD wrongly enumerates identity types here.
    assert_profile(root, "035", Environment.PRODUCTION)
