"""Independent annex literals and serialized event profile assertions."""

from lxml import etree

from radiankore import Environment
from radiankore._soap.namespaces import AR, CAC, CBC, DS, EXT, STS
from radiankore.catalogs import RadianOperationType

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
    if code == "043":
        operation = root.findtext(f"{{{CBC}}}CustomizationID")
        limited = operation in {"431", "433"}
        mode = response.find(f"{{{CBC}}}ResponseCode")
        assert mode is not None
        for ref in references:
            if mode.get("listID") == "3":
                assert ref.findtext(f"{{{CBC}}}ID") == "1"
                assert ref.find(f"{{{CBC}}}UUID") is None
                assert ref.find(f"{{{CBC}}}DocumentTypeCode") is None
            period = ref.find(f"{{{CAC}}}ValidityPeriod")
            assert period is not None
            assert period.findtext(f"{{{CBC}}}Description") == (
                "Lapso de vigencia del Mandato-Limitado"
                if limited
                else "Lapso de vigencia del Mandato-Ilimitado"
            )
        for block in root.findall(f"{{{CAC}}}DocumentResponse")[1:]:
            assert block.findtext(f"{{{CAC}}}Response/{{{CBC}}}Description") == (
                "Mandato por documento General"
                if operation in {"431", "432"}
                else "Mandato por documento Limitado"
            )
        notes = root.findall(f"{{{CBC}}}Note")
        assert len(notes) >= 2
        assert (
            notes[0].text and " OBRANDO EN NOMBRE Y REPRESENTACION DE " in notes[0].text
        )
        assert notes[1].text and "expresamente manifiesto" in notes[1].text
    if code in {"045", "051"}:
        assert len(root.findall(f"{{{CAC}}}SenderParty/{{{CAC}}}PartyLegalEntity")) == 1
        assert response.find(f"{{{CBC}}}EffectiveDate") is not None
