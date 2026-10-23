"""Static RADIAN 1.1 catalogs, independent of XML and I/O.

Operation labels follow TiposOperacionRADIAN-2.1.gc. Payment means follow
annex table 14.2.11, not the broader genericode. Currency codes follow the
reference snapshot, except VES (annex table 14.2.16) replaces genericode VES7.
"""

from enum import StrEnum, unique
from typing import Self

from radiankore.catalogs.events import EventType


@unique
class RadianOperationType(StrEnum):
    """CustomizationID values for RADIAN events emitted by the common API."""

    GUARANTEE = "035"
    RESTRICTION_ATTACHMENT = "411"
    RESTRICTION_PAYMENT_ORDER = "412"
    RESTRICTION_TERMINATION_JUDGMENT = "421"
    RESTRICTION_TERMINATION_EARLY = "422"
    PROTEST_NON_ACCEPTANCE = "481"
    PROTEST_NON_PAYMENT = "482"
    ECONOMIC_RIGHTS_PARTIAL_WITH_RECOURSE = "491"
    ECONOMIC_RIGHTS_FULL_WITH_RECOURSE = "492"
    ECONOMIC_RIGHTS_PARTIAL_WITHOUT_RECOURSE = "493"
    ECONOMIC_RIGHTS_FULL_WITHOUT_RECOURSE = "494"
    ECONOMIC_RIGHTS_NOTIFICATION = "050"
    ECONOMIC_RIGHTS_PARTIAL_PAYMENT = "511"
    ECONOMIC_RIGHTS_FULL_PAYMENT = "512"
    REGISTRATION_INITIAL_GENERAL = "361"
    REGISTRATION_INITIAL_DIRECT = "362"
    REGISTRATION_SUBSEQUENT_GENERAL = "363"
    REGISTRATION_SUBSEQUENT_DIRECT = "364"
    OWNERSHIP_WITH_RECOURSE = "371"
    OWNERSHIP_WITHOUT_RECOURSE = "372"
    GUARANTEE_ENDORSEMENT = "038"
    COLLECTION_ENDORSEMENT = "039"
    CANCEL_GUARANTEE_ENDORSEMENT = "401"
    CANCEL_COLLECTION_ENDORSEMENT = "402"
    CANCEL_RETURN_ENDORSEMENT = "403"
    MANDATE_REVOCATION = "441"
    MANDATE_RESIGNATION = "442"
    MANDATE_REJECTION = "443"
    PARTIAL_PAYMENT = "451"
    FULL_PAYMENT = "452"
    PAYMENT_REPORT = "046"
    ORDINARY_ASSIGNMENT_ENDORSEMENT = "047"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _RADIANOPERATIONTYPE_LABELS[self]

    @property
    def event_type(self) -> EventType:
        """Derive ResponseCode without permitting an incompatible caller value."""
        return _OPERATION_EVENTS[self]


@unique
class AcceptanceFailureType(StrEnum):
    """CustomizationID @schemeID for non-acceptance protests, table 14.2.20."""

    PARTIAL = "1"
    TOTAL = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the official Spanish acceptance-failure description."""
        return {
            self.PARTIAL: "Falta de aceptación parcial",
            self.TOTAL: "Falta de aceptación total",
        }[self]


@unique
class EndorsementForm(StrEnum):
    """ResponseCode @listID from table 14.2.3."""

    COMPLETE = "1"
    BLANK = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _ENDORSEMENTFORM_LABELS[self]


@unique
class PaymentRestriction(StrEnum):
    """Table 14.2.9; independent of partial/full payment."""

    UNRESTRICTED = "1"
    RESTRICTED = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _PAYMENTRESTRICTION_LABELS[self]


@unique
class FactorType(StrEnum):
    """CompanyLegalFormCode from table 14.2.2."""

    FACTORING = "1"
    CONFIRMING = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _FACTORTYPE_LABELS[self]


@unique
class PaymentMeans(StrEnum):
    """Payment means admitted by table 14.2.11."""

    CASH = "10"
    CREDIT_CARD = "48"
    DEBIT_CARD = "49"
    BANK_DEBIT_TRANSFER = "47"
    BANK_DEPOSIT = "42"
    BILL_OF_EXCHANGE = "44"
    ACH_DEBIT = "3"
    CHEQUE = "20"
    CERTIFIED_CHEQUE = "25"
    BANK_CHEQUE = "23"
    LOCAL_CHEQUE = "26"
    BONDS = "71"
    AWAITING_ACCEPTANCE_BILL = "24"
    VOUCHERS = "72"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _PAYMENTMEANS_LABELS[self]


@unique
class CurrencyCode(StrEnum):
    """Versioned RADIAN currency codes; VES follows annex table 14.2.16."""

    AED = "AED"
    AFN = "AFN"
    ALL = "ALL"
    AMD = "AMD"
    ANG = "ANG"
    AOA = "AOA"
    ARS = "ARS"
    AUD = "AUD"
    AWG = "AWG"
    AZN = "AZN"
    BAM = "BAM"
    BBD = "BBD"
    BDT = "BDT"
    BGN = "BGN"
    BHD = "BHD"
    BIF = "BIF"
    BMD = "BMD"
    BND = "BND"
    BOB = "BOB"
    BOV = "BOV"
    BRL = "BRL"
    BSD = "BSD"
    BTN = "BTN"
    BWP = "BWP"
    BYR = "BYR"
    BZD = "BZD"
    CAD = "CAD"
    CDF = "CDF"
    CHE = "CHE"
    CHF = "CHF"
    CHW = "CHW"
    CLF = "CLF"
    CLP = "CLP"
    CNY = "CNY"
    COP = "COP"
    COU = "COU"
    CRC = "CRC"
    CUC = "CUC"
    CUP = "CUP"
    CVE = "CVE"
    CZK = "CZK"
    DJF = "DJF"
    DKK = "DKK"
    DOP = "DOP"
    DZD = "DZD"
    EGP = "EGP"
    ERN = "ERN"
    ETB = "ETB"
    EUR = "EUR"
    FJD = "FJD"
    FKP = "FKP"
    GBP = "GBP"
    GEL = "GEL"
    GHS = "GHS"
    GIP = "GIP"
    GMD = "GMD"
    GNF = "GNF"
    GTQ = "GTQ"
    GYD = "GYD"
    HKD = "HKD"
    HNL = "HNL"
    HRK = "HRK"
    HTG = "HTG"
    HUF = "HUF"
    IDR = "IDR"
    ILS = "ILS"
    INR = "INR"
    IQD = "IQD"
    IRR = "IRR"
    ISK = "ISK"
    JMD = "JMD"
    JOD = "JOD"
    JPY = "JPY"
    KES = "KES"
    KGS = "KGS"
    KHR = "KHR"
    KMF = "KMF"
    KPW = "KPW"
    KRW = "KRW"
    KWD = "KWD"
    KYD = "KYD"
    KZT = "KZT"
    LAK = "LAK"
    LBP = "LBP"
    LKR = "LKR"
    LRD = "LRD"
    LSL = "LSL"
    LYD = "LYD"
    MAD = "MAD"
    MDL = "MDL"
    MGA = "MGA"
    MKD = "MKD"
    MMK = "MMK"
    MNT = "MNT"
    MOP = "MOP"
    MRO = "MRO"
    MUR = "MUR"
    MVR = "MVR"
    MWK = "MWK"
    MXN = "MXN"
    MXV = "MXV"
    MYR = "MYR"
    MZN = "MZN"
    NAD = "NAD"
    NGN = "NGN"
    NIO = "NIO"
    NOK = "NOK"
    NPR = "NPR"
    NZD = "NZD"
    OMR = "OMR"
    PAB = "PAB"
    PEN = "PEN"
    PGK = "PGK"
    PHP = "PHP"
    PKR = "PKR"
    PLN = "PLN"
    PYG = "PYG"
    QAR = "QAR"
    RON = "RON"
    RSD = "RSD"
    RUB = "RUB"
    RWF = "RWF"
    SAR = "SAR"
    SBD = "SBD"
    SCR = "SCR"
    SDG = "SDG"
    SEK = "SEK"
    SGD = "SGD"
    SHP = "SHP"
    SLL = "SLL"
    SOS = "SOS"
    SRD = "SRD"
    SSP = "SSP"
    STD = "STD"
    SVC = "SVC"
    SYP = "SYP"
    SZL = "SZL"
    THB = "THB"
    TJS = "TJS"
    TMT = "TMT"
    TND = "TND"
    TOP = "TOP"
    TRY = "TRY"
    TTD = "TTD"
    TWD = "TWD"
    TZS = "TZS"
    UAH = "UAH"
    UGX = "UGX"
    USD = "USD"
    USN = "USN"
    UYI = "UYI"
    UYU = "UYU"
    UZS = "UZS"
    VEF = "VEF"
    VES = "VES"
    VND = "VND"
    VUV = "VUV"
    WST = "WST"
    XAF = "XAF"
    XAG = "XAG"
    XAU = "XAU"
    XBA = "XBA"
    XBB = "XBB"
    XBC = "XBC"
    XBD = "XBD"
    XCD = "XCD"
    XDR = "XDR"
    XOF = "XOF"
    XPD = "XPD"
    XPF = "XPF"
    XPT = "XPT"
    XSU = "XSU"
    XTS = "XTS"
    XUA = "XUA"
    XXX = "XXX"
    YER = "YER"
    ZAR = "ZAR"
    ZMW = "ZMW"
    ZWL = "ZWL"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve exact codes; absent and unknown values return None."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the label from the versioned reference."""
        return _CURRENCYCODE_LABELS[self]


_RADIANOPERATIONTYPE_LABELS = {
    RadianOperationType.GUARANTEE: "Aval",
    RadianOperationType.RESTRICTION_ATTACHMENT: (
        "Auto que decreta medida cautelar por embargo"
    ),
    RadianOperationType.RESTRICTION_PAYMENT_ORDER: (
        "Auto que decreta medida cautelar por mandamiento de pago"
    ),
    RadianOperationType.RESTRICTION_TERMINATION_JUDGMENT: (
        "Terminación de limitación por sentencia"
    ),
    RadianOperationType.RESTRICTION_TERMINATION_EARLY: (
        "Terminación de limitación por terminación anticipada"
    ),
    RadianOperationType.PROTEST_NON_ACCEPTANCE: "Protesto por falta de aceptación",
    RadianOperationType.PROTEST_NON_PAYMENT: "Protesto por falta de pago",
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITH_RECOURSE: (
        "Transferencia parcial de los derechos económicos con responsabilidad"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_WITH_RECOURSE: (
        "Transferencia total de los derechos económicos con responsabilidad"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITHOUT_RECOURSE: (
        "Transferencia parcial de los derechos económicos sin responsabilidad"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_WITHOUT_RECOURSE: (
        "Transferencia total de los derechos económicos sin responsabilidad"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_NOTIFICATION: (
        "Notificación al deudor sobre la transferencia de los derechos económicos"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_PAYMENT: (
        "Pago parcial de la transferencia de los derechos económicos"
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_PAYMENT: (
        "Pago total de la transferencia de los derechos económicos"
    ),
    RadianOperationType.REGISTRATION_INITIAL_GENERAL: (
        "Primera inscripción de la factura electrónica de venta como "
        "título valor para Negociación General"
    ),
    RadianOperationType.REGISTRATION_INITIAL_DIRECT: (
        "Primera inscripción de la factura electrónica de venta como "
        "título valor para Negociación Directa Previa"
    ),
    RadianOperationType.REGISTRATION_SUBSEQUENT_GENERAL: (
        "Inscripción posterior de la factura electrónica de venta como "
        "título valor para Negociación General"
    ),
    RadianOperationType.REGISTRATION_SUBSEQUENT_DIRECT: (
        "Inscripción posterior de la factura electrónica de venta como "
        "título valor para Negociación Directa Previa"
    ),
    RadianOperationType.OWNERSHIP_WITH_RECOURSE: (
        "Endoso con responsabilidad del endosante"
    ),
    RadianOperationType.OWNERSHIP_WITHOUT_RECOURSE: (
        "Endoso sin responsabilidad del endosante"
    ),
    RadianOperationType.GUARANTEE_ENDORSEMENT: "Endoso en Garantía",
    RadianOperationType.COLLECTION_ENDORSEMENT: "Endoso en Procuración",
    RadianOperationType.CANCEL_GUARANTEE_ENDORSEMENT: (
        "Cancelación del Endoso en Garantia"
    ),
    RadianOperationType.CANCEL_COLLECTION_ENDORSEMENT: (
        "Cancelación del Endoso en Procuracion"
    ),
    RadianOperationType.CANCEL_RETURN_ENDORSEMENT: (
        "Tacha de Endosos por Endoso en Retorno"
    ),
    RadianOperationType.MANDATE_REVOCATION: (
        "Terminacion del Mandato por Revocacion del Mandante"
    ),
    RadianOperationType.MANDATE_RESIGNATION: (
        "Terminacion del Mandato por Renuncia del mandatario"
    ),
    RadianOperationType.MANDATE_REJECTION: (
        "Terminacion del Mandato por Rechazo del mandante"
    ),
    RadianOperationType.PARTIAL_PAYMENT: "Notificación de pago parcial",
    RadianOperationType.FULL_PAYMENT: (
        "Pago de la factura electrónica de venta como título valor"
    ),
    RadianOperationType.PAYMENT_REPORT: "Informe para el pago",
    RadianOperationType.ORDINARY_ASSIGNMENT_ENDORSEMENT: (
        "Endoso con efectos de cesión ordinaria"
    ),
}


_ENDORSEMENTFORM_LABELS = {
    EndorsementForm.COMPLETE: "Completo",
    EndorsementForm.BLANK: "En blanco",
}


_PAYMENTRESTRICTION_LABELS = {
    PaymentRestriction.UNRESTRICTED: "Sin limitacion",
    PaymentRestriction.RESTRICTED: "con limitacion",
}


_FACTORTYPE_LABELS = {
    FactorType.FACTORING: "Factoring",
    FactorType.CONFIRMING: "Confirming",
}


_PAYMENTMEANS_LABELS = {
    PaymentMeans.CASH: "Efectivo",
    PaymentMeans.CREDIT_CARD: "Tarjeta Crédito",
    PaymentMeans.DEBIT_CARD: "Tarjeta Débito",
    PaymentMeans.BANK_DEBIT_TRANSFER: "Transferencia Débito Bancaria",
    PaymentMeans.BANK_DEPOSIT: "Consignación bancaria",
    PaymentMeans.BILL_OF_EXCHANGE: "Nota cambiaria",
    PaymentMeans.ACH_DEBIT: "Débito ACH",
    PaymentMeans.CHEQUE: "Cheque",
    PaymentMeans.CERTIFIED_CHEQUE: "Cheque certificado",
    PaymentMeans.BANK_CHEQUE: "Cheque bancario de gerencia",
    PaymentMeans.LOCAL_CHEQUE: "Cheque Local",
    PaymentMeans.BONDS: "Bonos",
    PaymentMeans.AWAITING_ACCEPTANCE_BILL: "Nota cambiaria esperando aceptación",
    PaymentMeans.VOUCHERS: "Vales",
}


_CURRENCYCODE_LABELS = {
    CurrencyCode.AED: "Dírham de los Emiratos Árabes Unidos",
    CurrencyCode.AFN: "Afgani",
    CurrencyCode.ALL: "Lek",
    CurrencyCode.AMD: "Dram armenio",
    CurrencyCode.ANG: "Florín antillano neerlandés",
    CurrencyCode.AOA: "Kwanza",
    CurrencyCode.ARS: "Peso argentino",
    CurrencyCode.AUD: "Dólar australiano",
    CurrencyCode.AWG: "Florín arubeño",
    CurrencyCode.AZN: "Manat azerbaiyano",
    CurrencyCode.BAM: "Marco convertible",
    CurrencyCode.BBD: "Dólar de Barbados",
    CurrencyCode.BDT: "Taka",
    CurrencyCode.BGN: "Lev búlgaro",
    CurrencyCode.BHD: "Dinar bareiní",
    CurrencyCode.BIF: "Franco de Burundi",
    CurrencyCode.BMD: "Dólar bermudeño",
    CurrencyCode.BND: "Dólar de Brunéi",
    CurrencyCode.BOB: "Boliviano",
    CurrencyCode.BOV: "MVDOL",
    CurrencyCode.BRL: "Real brasileño",
    CurrencyCode.BSD: "Dólar bahameño",
    CurrencyCode.BTN: "Ngultrum",
    CurrencyCode.BWP: "Pula",
    CurrencyCode.BYR: "Rublo bielorruso",
    CurrencyCode.BZD: "Dólar beliceño",
    CurrencyCode.CAD: "Dólar canadiense",
    CurrencyCode.CDF: "Franco congoleño",
    CurrencyCode.CHE: "Euro WIR",
    CurrencyCode.CHF: "Franco suizo",
    CurrencyCode.CHW: "Franco WIR",
    CurrencyCode.CLF: "Unidad de fomento",
    CurrencyCode.CLP: "Peso chileno",
    CurrencyCode.CNY: "Yuan chino",
    CurrencyCode.COP: "Peso colombiano",
    CurrencyCode.COU: "Unidad de valor real",
    CurrencyCode.CRC: "Colón costarricense",
    CurrencyCode.CUC: "Peso convertible",
    CurrencyCode.CUP: "Peso cubano",
    CurrencyCode.CVE: "Escudo caboverdiano",
    CurrencyCode.CZK: "Corona checa",
    CurrencyCode.DJF: "Franco yibutiano",
    CurrencyCode.DKK: "Corona danesa",
    CurrencyCode.DOP: "Peso dominicano",
    CurrencyCode.DZD: "Dinar argelino",
    CurrencyCode.EGP: "Libra egipcia",
    CurrencyCode.ERN: "Nakfa",
    CurrencyCode.ETB: "Birr etíope",
    CurrencyCode.EUR: "Euro",
    CurrencyCode.FJD: "Dólar fiyiano",
    CurrencyCode.FKP: "Libra malvinense",
    CurrencyCode.GBP: "Libra esterlina",
    CurrencyCode.GEL: "Lari",
    CurrencyCode.GHS: "Cedi ghanés",
    CurrencyCode.GIP: "Libra de Gibraltar",
    CurrencyCode.GMD: "Dalasi",
    CurrencyCode.GNF: "Franco guineano",
    CurrencyCode.GTQ: "Quetzal",
    CurrencyCode.GYD: "Dólar guyanés",
    CurrencyCode.HKD: "Dólar de Hong Kong",
    CurrencyCode.HNL: "Lempira",
    CurrencyCode.HRK: "Kuna",
    CurrencyCode.HTG: "Gourde",
    CurrencyCode.HUF: "Forinto",
    CurrencyCode.IDR: "Rupia indonesia",
    CurrencyCode.ILS: "Nuevo shéquel israelí",
    CurrencyCode.INR: "Rupia india",
    CurrencyCode.IQD: "Dinar iraquí",
    CurrencyCode.IRR: "Rial iraní",
    CurrencyCode.ISK: "Corona islandesa",
    CurrencyCode.JMD: "Dólar jamaiquino",
    CurrencyCode.JOD: "Dinar jordano",
    CurrencyCode.JPY: "Yen",
    CurrencyCode.KES: "Chelín keniano",
    CurrencyCode.KGS: "Som",
    CurrencyCode.KHR: "Riel",
    CurrencyCode.KMF: "Franco comorense",
    CurrencyCode.KPW: "Won norcoreano",
    CurrencyCode.KRW: "Won",
    CurrencyCode.KWD: "Dinar kuwaití",
    CurrencyCode.KYD: "Dólar de las Islas Caimán",
    CurrencyCode.KZT: "Tenge",
    CurrencyCode.LAK: "Kip",
    CurrencyCode.LBP: "Libra libanesa",
    CurrencyCode.LKR: "Rupia de Sri Lanka",
    CurrencyCode.LRD: "Dólar liberiano",
    CurrencyCode.LSL: "Loti",
    CurrencyCode.LYD: "Dinar libio",
    CurrencyCode.MAD: "Dírham marroquí",
    CurrencyCode.MDL: "Leu moldavo",
    CurrencyCode.MGA: "Ariary malgache",
    CurrencyCode.MKD: "Denar",
    CurrencyCode.MMK: "Kyat",
    CurrencyCode.MNT: "Tugrik",
    CurrencyCode.MOP: "Pataca",
    CurrencyCode.MRO: "Uguiya",
    CurrencyCode.MUR: "Rupia de Mauricio",
    CurrencyCode.MVR: "Rufiyaa",
    CurrencyCode.MWK: "Kwacha",
    CurrencyCode.MXN: "Peso mexicano",
    CurrencyCode.MXV: "Unidad de Inversión (UDI) mexicana",
    CurrencyCode.MYR: "Ringgit malayo",
    CurrencyCode.MZN: "Metical mozambiqueño",
    CurrencyCode.NAD: "Dólar namibio",
    CurrencyCode.NGN: "Naira",
    CurrencyCode.NIO: "Córdoba",
    CurrencyCode.NOK: "Corona noruega",
    CurrencyCode.NPR: "Rupia nepalí",
    CurrencyCode.NZD: "Dólar neozelandés",
    CurrencyCode.OMR: "Rial omaní",
    CurrencyCode.PAB: "Balboa",
    CurrencyCode.PEN: "Sol",
    CurrencyCode.PGK: "Kina",
    CurrencyCode.PHP: "Peso filipino",
    CurrencyCode.PKR: "Rupia pakistaní",
    CurrencyCode.PLN: "Złoty",
    CurrencyCode.PYG: "Guaraní",
    CurrencyCode.QAR: "Riyal qatarí",
    CurrencyCode.RON: "Leu rumano",
    CurrencyCode.RSD: "Dinar serbio",
    CurrencyCode.RUB: "Rublo ruso",
    CurrencyCode.RWF: "Franco ruandés",
    CurrencyCode.SAR: "Riyal saudí",
    CurrencyCode.SBD: "Dólar de las Islas Salomón",
    CurrencyCode.SCR: "Rupia seychelense",
    CurrencyCode.SDG: "Dinar sudanés",
    CurrencyCode.SEK: "Corona sueca",
    CurrencyCode.SGD: "Dólar de Singapur",
    CurrencyCode.SHP: "Libra de Santa Elena",
    CurrencyCode.SLL: "Leone",
    CurrencyCode.SOS: "Chelín somalí",
    CurrencyCode.SRD: "Dólar surinamés",
    CurrencyCode.SSP: "Libra sursudanesa",
    CurrencyCode.STD: "Dobra",
    CurrencyCode.SVC: "Colon Salvadoreño",
    CurrencyCode.SYP: "Libra siria",
    CurrencyCode.SZL: "Lilangeni",
    CurrencyCode.THB: "Baht",
    CurrencyCode.TJS: "Somoni tayiko",
    CurrencyCode.TMT: "Manat turcomano",
    CurrencyCode.TND: "Dinar tunecino",
    CurrencyCode.TOP: "Paʻanga",  # noqa: RUF001 - official genericode spelling
    CurrencyCode.TRY: "Lira turca",
    CurrencyCode.TTD: "Dólar de Trinidad y Tobago",
    CurrencyCode.TWD: "Nuevo dólar taiwanés",
    CurrencyCode.TZS: "Chelín tanzano",
    CurrencyCode.UAH: "Grivna",
    CurrencyCode.UGX: "Chelín ugandés",
    CurrencyCode.USD: "Dólar estadounidense",
    CurrencyCode.USN: "Dólar estadounidense (Siguiente día)",
    CurrencyCode.UYI: "Peso en Unidades Indexadas (Uruguay)",
    CurrencyCode.UYU: "Peso uruguayo",
    CurrencyCode.UZS: "Som uzbeko",
    CurrencyCode.VEF: "Bolívar",
    CurrencyCode.VES: "Bolívar soberano",
    CurrencyCode.VND: "Dong vietnamita",
    CurrencyCode.VUV: "Vatu",
    CurrencyCode.WST: "Tala",
    CurrencyCode.XAF: "Franco CFA de África Central",
    CurrencyCode.XAG: "Plata (una onza troy)",
    CurrencyCode.XAU: "Oro (una onza troy)",
    CurrencyCode.XBA: "Unidad compuesta europea (EURCO) (Unidad del mercado de bonos)",
    CurrencyCode.XBB: (
        "Unidad Monetaria europea (E.M.U.-6) (Unidad del mercado de bonos)"
    ),
    CurrencyCode.XBC: (
        "Unidad europea de cuenta 9 (E.U.A.-9) (Unidad del mercado de bonos)"
    ),
    CurrencyCode.XBD: (
        "Unidad europea de cuenta 17 (E.U.A.-17) (Unidad del mercado de bonos)"
    ),
    CurrencyCode.XCD: "Dólar del Caribe Oriental",
    CurrencyCode.XDR: "Derechos especiales de giro",
    CurrencyCode.XOF: "Franco CFA de África Occidental",
    CurrencyCode.XPD: "Paladio (una onza troy)",
    CurrencyCode.XPF: "Franco CFP",
    CurrencyCode.XPT: "Platino (una onza troy)",
    CurrencyCode.XSU: "SUCRE",
    CurrencyCode.XTS: "Reservado para pruebas",
    CurrencyCode.XUA: "Unidad de cuenta BAD",
    CurrencyCode.XXX: "Sin divisa",
    CurrencyCode.YER: "Rial yemení",
    CurrencyCode.ZAR: "Rand",
    CurrencyCode.ZMW: "Kwacha zambiano",
    CurrencyCode.ZWL: "Dólar zimbabuense",
}

_OPERATION_EVENTS = {
    RadianOperationType.GUARANTEE: EventType.GUARANTEE,
    RadianOperationType.RESTRICTION_ATTACHMENT: EventType.CIRCULATION_RESTRICTION,
    RadianOperationType.RESTRICTION_PAYMENT_ORDER: EventType.CIRCULATION_RESTRICTION,
    RadianOperationType.RESTRICTION_TERMINATION_JUDGMENT: (
        EventType.CIRCULATION_RESTRICTION_TERMINATION
    ),
    RadianOperationType.RESTRICTION_TERMINATION_EARLY: (
        EventType.CIRCULATION_RESTRICTION_TERMINATION
    ),
    RadianOperationType.PROTEST_NON_ACCEPTANCE: EventType.PROTEST,
    RadianOperationType.PROTEST_NON_PAYMENT: EventType.PROTEST,
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITH_RECOURSE: (
        EventType.ECONOMIC_RIGHTS_TRANSFER
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_WITH_RECOURSE: (
        EventType.ECONOMIC_RIGHTS_TRANSFER
    ),
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITHOUT_RECOURSE: (
        EventType.ECONOMIC_RIGHTS_TRANSFER
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_WITHOUT_RECOURSE: (
        EventType.ECONOMIC_RIGHTS_TRANSFER
    ),
    RadianOperationType.ECONOMIC_RIGHTS_NOTIFICATION: (
        EventType.ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION
    ),
    RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_PAYMENT: (
        EventType.ECONOMIC_RIGHTS_TRANSFER_PAYMENT
    ),
    RadianOperationType.ECONOMIC_RIGHTS_FULL_PAYMENT: (
        EventType.ECONOMIC_RIGHTS_TRANSFER_PAYMENT
    ),
    RadianOperationType.REGISTRATION_INITIAL_GENERAL: EventType.RADIAN_REGISTRATION,
    RadianOperationType.REGISTRATION_INITIAL_DIRECT: EventType.RADIAN_REGISTRATION,
    RadianOperationType.REGISTRATION_SUBSEQUENT_GENERAL: EventType.RADIAN_REGISTRATION,
    RadianOperationType.REGISTRATION_SUBSEQUENT_DIRECT: EventType.RADIAN_REGISTRATION,
    RadianOperationType.OWNERSHIP_WITH_RECOURSE: EventType.OWNERSHIP_ENDORSEMENT,
    RadianOperationType.OWNERSHIP_WITHOUT_RECOURSE: EventType.OWNERSHIP_ENDORSEMENT,
    RadianOperationType.GUARANTEE_ENDORSEMENT: EventType.GUARANTEE_ENDORSEMENT,
    RadianOperationType.COLLECTION_ENDORSEMENT: EventType.COLLECTION_ENDORSEMENT,
    RadianOperationType.CANCEL_GUARANTEE_ENDORSEMENT: (
        EventType.ENDORSEMENT_CANCELLATION
    ),
    RadianOperationType.CANCEL_COLLECTION_ENDORSEMENT: (
        EventType.ENDORSEMENT_CANCELLATION
    ),
    RadianOperationType.CANCEL_RETURN_ENDORSEMENT: EventType.ENDORSEMENT_CANCELLATION,
    RadianOperationType.MANDATE_REVOCATION: EventType.MANDATE_TERMINATION,
    RadianOperationType.MANDATE_RESIGNATION: EventType.MANDATE_TERMINATION,
    RadianOperationType.MANDATE_REJECTION: EventType.MANDATE_TERMINATION,
    RadianOperationType.PARTIAL_PAYMENT: EventType.INVOICE_PAYMENT,
    RadianOperationType.FULL_PAYMENT: EventType.INVOICE_PAYMENT,
    RadianOperationType.PAYMENT_REPORT: EventType.PAYMENT_REPORT,
    RadianOperationType.ORDINARY_ASSIGNMENT_ENDORSEMENT: (
        EventType.ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS
    ),
}
