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
from radiankore._soap.namespaces import AR, CAC, CBC, DS, EXT, STS
from radiankore.catalogs import EventType, RadianOperationType
from radiankore.models.events import (
    InvoiceResponseEvent,
    MandateEvent,
    RadianEvent,
    RadianSoftware,
)

DESCRIPTIONS = {
    "030": "Acuse de recibo de Factura Electrónica de Venta",
    "031": "Reclamo de la Factura Electrónica de Venta",
    "032": "Recibo del bien y/o prestación del servicio",
    "033": "Aceptación expresa",
    "034": "Aceptación Tácita",
    "035": "Aval",
    "036": "Inscripción de la factura electrónica de venta como título valor - RADIAN",
    "037": "Endoso en propiedad",
    "038": "Endoso en garantía",
    "039": "Endoso en procuración",
    "040": "Cancelación de endoso",
    "041": (
        "Limitaciones a la circulación de la factura electrónica de venta como título"
    ),
    "042": (
        "Terminación de las limitaciones a la circulación "
        "de la factura electrónica de venta como título"
    ),
    "043": "Mandato",
    "044": "Terminacion del Mandato",
    "045": "Pago de la factura electrónica de venta como título valor",
    "046": "Informe para el pago",
    "047": "Endoso con efectos de cesión ordinaria",
    "048": "Protesto",
    "049": "Transferencia de los derechos económicos",
    "050": "Notificación al deudor sobre la transferencia de los derechos económicos",
    "051": "Pago de la transferencia de derechos económicos",
}

# RADIAN sections 7.2.4.3-13: the Name/Value sequence is significant.
EXTENSIONS = {
    "035": ("InformacionAvalar", ("ValorFEVavala",)),
    "036": ("ConstanciadePagos", ("ValorFEV-TV", "ValorPagado", "NuevoValorTV")),
    "037": (
        "InformacionNegociacion",
        ("ValorTotalEndoso", "PrecioPagarseFEV", "TasaDescuento", "MedioPago"),
    ),
    "038": ("InformacionNegociacion", ("ValorTotalEndoso",)),
    "039": ("InformacionNegociacion", ("ValorTotalEndoso",)),
    "041": ("InformacionMedidaCautelar", ("MontoMedidaCautelar",)),
    "042": ("InformacionMedidaCautelar", ("ValorDeuda", "ValorLimitación")),
    "045": (
        "InformacionPagos",
        ("ValorActualTituloValor", "ValorPendienteTituloValor"),
    ),
    "046": ("InformacionParaelPago", ("ValorFEV-TV",)),
    "047": (
        "InformacionNegociacion",
        ("ValorTotalEndoso", "PrecioPagarseFEV", "TasaDescuento", "MedioPago"),
    ),
    "048": ("InformacionProtesto", ("ValorFEV-TV", "ValorAceptado", "ValorPendiente")),
    "049": (
        "InformacionTransferenciaDerechos",
        (
            "ValorTransferenciaDerechos",
            "PrecioPagarseFEV",
            "FactordeDescuento",
            "MedioPago",
        ),
    ),
    "050": ("NotificacionPagoDeudor", ("ValorFEV-TV",)),
    "051": (
        "InformacionPagoTransferencia",
        ("ValorActualTituloValor", "ValorPendienteTituloValor"),
    ),
}

VARIANTS = (
    [op.value for op in RadianOperationType]
    + [
        "371-blank",
        "372-blank",
        "038-blank",
        "039-blank",
        "mandate",
    ]
    + ["invoice:" + code for code in ("030", "031", "032", "033", "034")]
)


def assert_profile(root: etree._Element, code: str, environment: Environment) -> None:
    """Check profile-only constraints that the generic UBL schema cannot enforce."""
    assert root.tag == f"{{{AR}}}ApplicationResponse"
    header = [
        f"{{{EXT}}}UBLExtensions",
        *(
            f"{{{CBC}}}{name}"
            for name in (
                "UBLVersionID",
                "CustomizationID",
                "ProfileID",
                "ProfileExecutionID",
                "ID",
                "UUID",
                "IssueDate",
                "IssueTime",
            )
        ),
    ]
    tags = [node.tag for node in root]
    assert tags[:9] == header
    tail = tags[9:]
    while tail and tail[0] == f"{{{CBC}}}Note":
        tail.pop(0)
    assert tail[:2] == [f"{{{CAC}}}SenderParty", f"{{{CAC}}}ReceiverParty"]
    assert tail[2:] and set(tail[2:]) == {f"{{{CAC}}}DocumentResponse"}
    if code not in {"041", "042", "043", "048"}:
        assert len(tail) == 3
    assert root.findtext(f"{{{CBC}}}UBLVersionID") == "UBL 2.1"
    profile = "DIAN 2.1: ApplicationResponse de "
    profile += "" if code in {"030", "031", "032", "033", "034"} else "la "
    assert (
        root.findtext(f"{{{CBC}}}ProfileID") == profile + "Factura Electrónica de Venta"
    )
    assert (
        root.findtext(f"{{{CBC}}}ProfileExecutionID")
        == environment.profile_execution_id
    )
    event_id = root.findtext(f"{{{CBC}}}ID")
    assert event_id is not None and 1 <= len(event_id) <= 50
    uuid = root.find(f"{{{CBC}}}UUID")
    assert uuid is not None and uuid.text is not None and len(uuid.text) == 96
    assert {str(key): str(value) for key, value in uuid.attrib.items()} == {
        "schemeID": environment.profile_execution_id,
        "schemeName": "CUDE-SHA384",
    }
    assert root.findtext(f"{{{CBC}}}IssueTime", "").endswith("-05:00")

    extension_nodes = root.findall(f"{{{EXT}}}UBLExtensions/{{{EXT}}}UBLExtension")
    contents = [node.find(f"{{{EXT}}}ExtensionContent") for node in extension_nodes]
    assert all(node is not None and len(node) == 1 for node in contents)
    apexes = [node[0] for node in contents if node is not None]
    assert sorted(node.tag for node in apexes) == sorted(
        [
            f"{{{STS}}}DianExtensions",
            f"{{{DS}}}Signature",
            *([f"{{{AR}}}CustomTagGeneral"] if code in EXTENSIONS else []),
        ]
    )
    dian = root.find(f".//{{{STS}}}DianExtensions")
    assert dian is not None
    assert [node.tag for node in dian] == [
        f"{{{STS}}}{tag}"
        for tag in (
            "InvoiceSource",
            "SoftwareProvider",
            "SoftwareSecurityCode",
            "AuthorizationProvider",
            "QRCode",
        )
    ]
    auth = dian.find(f"{{{STS}}}AuthorizationProvider/{{{STS}}}AuthorizationProviderID")
    assert auth is not None and auth.text == "800197268"
    assert auth.get("schemeID") == "4" and auth.get("schemeName") == "31"

    if code in EXTENSIONS:
        name, keys = EXTENSIONS[code]
        if code == "048" and root.findtext(f"{{{CBC}}}CustomizationID") == "482":
            keys = keys[:1]
        custom = root.find(f".//{{{AR}}}CustomTagGeneral")
        assert custom is not None and len(custom) == 1
        extension = custom[0]
        assert extension.tag == f"{{{AR}}}{name}"
        assert [node.tag for node in extension] == [
            f"{{{AR}}}{tag}" for _ in keys for tag in ("Name", "Value")
        ]
        assert [node.text for node in extension.findall(f"{{{AR}}}Name")] == list(keys)
        assert all(node.text for node in extension)

    response = root.find(f"{{{CAC}}}DocumentResponse/{{{CAC}}}Response")
    assert response is not None
    assert response.findtext(f"{{{CBC}}}ResponseCode") == code
    assert response.findtext(f"{{{CBC}}}Description") == DESCRIPTIONS[code]
    primary = root.find(f"{{{CAC}}}DocumentResponse")
    assert primary is not None
    references = primary.findall(f"{{{CAC}}}DocumentReference")
    assert references
    for ref in references:
        target = ref.find(f"{{{CBC}}}UUID")
        if code == "043" and target is None:
            continue  # Reference mode ALL: constant ID=1; no fictitious CUFE.
        assert target is not None
        assert target.text is not None and len(target.text) == 96
        previous_event = code in {"040", "042", "044"}
        assert target.get("schemeName") == (
            "CUDE-SHA384" if previous_event else "CUFE-SHA384"
        )
        kind = ref.findtext(f"{{{CBC}}}DocumentTypeCode")
        assert kind in ({"96"} if previous_event else {"01", "02", "03", "04"})
    if code in {"045", "051"}:
        assert len(root.findall(f"{{{CAC}}}SenderParty/{{{CAC}}}PartyLegalEntity")) == 1
        assert response.find(f"{{{CBC}}}EffectiveDate") is not None


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
