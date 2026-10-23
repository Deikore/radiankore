"""Mandate related catalogs from RADIAN 1.1 annex section 14.2.

Sources:
- Operation types and nature: section 7.2.5.11 (CustomizationID).
- Mandator/mandatee types: sections 14.2.5 and 14.2.8.
- Time scope: section 14.2.7.
- Powers and channels: section 14.2.4.
"""

from enum import StrEnum, unique
from typing import Self


@unique
class MandateOperationType(StrEnum):
    """CustomizationID values for a mandate ApplicationResponse."""

    GENERAL_LIMITED_TIME = "431"
    GENERAL_UNLIMITED_TIME = "432"
    LIMITED_LIMITED_TIME = "433"
    LIMITED_UNLIMITED_TIME = "434"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _OPERATION_LABELS[self]


@unique
class MandateNature(StrEnum):
    """CustomizationID @schemeID values referencing section 14.2.19."""

    SPECIAL = "1"
    GENERAL = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _NATURE_LABELS[self]


@unique
class MandateTime(StrEnum):
    """ValidityPeriod/DescriptionCode values from section 14.2.7."""

    LIMITED = "1"
    UNLIMITED = "2"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _TIME_LABELS[self]


@unique
class MandatorType(StrEnum):
    """Mandator types from section 14.2.5."""

    INVOICE_ISSUER = "Mandante-FE"
    LEGITIMATE_HOLDER = "Mandante-LT"
    GUARANTOR = "Mandante-AV"
    ACQUIRER_DEBTOR = "Mandante-AD"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _MANDATOR_LABELS[self]


@unique
class MandateeType(StrEnum):
    """Mandatee types from section 14.2.8."""

    ELECTRONIC_NEGOTIATION_SYSTEM = "M-SN-e"
    FACTOR = "M-Factor"
    TECHNOLOGY_PROVIDER = "M-PT"
    INVOICE_ISSUER = "M-FE"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _MANDATEE_LABELS[self]


@unique
class MandateChannel(StrEnum):
    """Delivery channel suffixes for mandate powers from section 14.2.4."""

    ELECTRONIC_NEGOTIATION_SYSTEM = "SNE"
    TECHNOLOGY_PROVIDER = "PT"
    FACTOR = "F"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _CHANNEL_LABELS[self]


@unique
class MandatePower(StrEnum):
    """Power codes from section 14.2.4 (Alcance de los Mandatos)."""

    WITH_REPRESENTATION = "MR91"
    GENERAL_DOCUMENT = "ALL17"
    ACKNOWLEDGEMENT = "R01"
    CLAIM = "R02"
    GOODS_OR_SERVICES_RECEIPT = "R03"
    EXPRESS_ACCEPTANCE = "R04"
    TACIT_ACCEPTANCE = "R05"
    GUARANTEE = "R06"
    RADIAN_REGISTRATION = "R07"
    OWNERSHIP_ENDORSEMENT = "R08"
    GUARANTEE_ENDORSEMENT = "R09"
    COLLECTION_ENDORSEMENT = "R10"
    ENDORSEMENT_CANCELLATION = "R11"
    CIRCULATION_RESTRICTION = "R12"
    CIRCULATION_RESTRICTION_TERMINATION = "R13"
    MANDATE = "R14"
    MANDATE_TERMINATION = "R15"
    INVOICE_PAYMENT = "R16"
    PAYMENT_REPORT = "R17"
    ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS = "R18"
    PROTEST = "R19"
    ECONOMIC_RIGHTS_TRANSFER = "R20"
    ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION = "R21"
    ECONOMIC_RIGHTS_TRANSFER_PAYMENT = "R22"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for absent or unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return _POWER_LABELS[self]


_OPERATION_LABELS: dict[MandateOperationType, str] = {
    MandateOperationType.GENERAL_LIMITED_TIME: (
        "Mandato por documento General por Tiempo limitado"
    ),
    MandateOperationType.GENERAL_UNLIMITED_TIME: (
        "Mandato por documento General por Tiempo Ilimitado"
    ),
    MandateOperationType.LIMITED_LIMITED_TIME: (
        "Mandato por documento limitado por tiempo limitado"
    ),
    MandateOperationType.LIMITED_UNLIMITED_TIME: (
        "Mandato por documento limitado por tiempo Ilimitado"
    ),
}

_NATURE_LABELS: dict[MandateNature, str] = {
    MandateNature.SPECIAL: "Mandato por Poder Especial",
    MandateNature.GENERAL: "Mandato por Poder General",
}

_TIME_LABELS: dict[MandateTime, str] = {
    MandateTime.LIMITED: "Tiempo limitado",
    MandateTime.UNLIMITED: "Tiempo Ilimitado",
}

_MANDATOR_LABELS: dict[MandatorType, str] = {
    MandatorType.INVOICE_ISSUER: "Mandante Facturador Electrónico",
    MandatorType.LEGITIMATE_HOLDER: "Mandante Legítimo Tenedor",
    MandatorType.GUARANTOR: "Mandante Avalista",
    MandatorType.ACQUIRER_DEBTOR: "Mandante Adquirente/Deudor",
}

_MANDATEE_LABELS: dict[MandateeType, str] = {
    MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM: (
        "Mandatario Sistema de Negociación Electrónica"
    ),
    MandateeType.FACTOR: "Mandatario Factor",
    MandateeType.TECHNOLOGY_PROVIDER: "Mandatario Proveedor Tecnológico",
    MandateeType.INVOICE_ISSUER: "Mandatario Facturador Electrónico",
}

_CHANNEL_LABELS: dict[MandateChannel, str] = {
    MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM: "Sistema de Negociación Electrónica",
    MandateChannel.TECHNOLOGY_PROVIDER: "Proveedor Tecnológico",
    MandateChannel.FACTOR: "Factor",
}

_POWER_LABELS: dict[MandatePower, str] = {
    MandatePower.WITH_REPRESENTATION: "Mandato con Representación",
    MandatePower.GENERAL_DOCUMENT: "Mandato por documento General",
    MandatePower.ACKNOWLEDGEMENT: (
        "Registrar, firmar y consultar ApplicationResponse - Acuse de recibo de la FEV"
    ),
    MandatePower.CLAIM: (
        "Registrar, firmar y consultar ApplicationResponse - Reclamo contra la FEV"
    ),
    MandatePower.GOODS_OR_SERVICES_RECEIPT: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Recibo del bien o prestación del servicio"
    ),
    MandatePower.EXPRESS_ACCEPTANCE: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Aceptación expresa de la FEV"
    ),
    MandatePower.TACIT_ACCEPTANCE: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Aceptación Tácita de la FEV"
    ),
    MandatePower.GUARANTEE: (
        "Registrar, firmar y consultar ApplicationResponse - Aval"
    ),
    MandatePower.RADIAN_REGISTRATION: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Inscripción en el RADIAN de la factura electrónica de venta "
        "como título valor que circula en el territorio nacional"
    ),
    MandatePower.OWNERSHIP_ENDORSEMENT: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Endoso en Propiedad (con o sin responsabilidad)"
    ),
    MandatePower.GUARANTEE_ENDORSEMENT: (
        "Registrar, firmar y consultar ApplicationResponse - Endoso en Garantía"
    ),
    MandatePower.COLLECTION_ENDORSEMENT: (
        "Registrar, firmar y consultar ApplicationResponse - Endoso en Procuración"
    ),
    MandatePower.ENDORSEMENT_CANCELLATION: (
        "Registrar, firmar y consultar ApplicationResponse - Cancelación de endoso"
    ),
    MandatePower.CIRCULATION_RESTRICTION: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Limitaciones a la circulación de la factura electrónica de venta "
        "como título"
    ),
    MandatePower.CIRCULATION_RESTRICTION_TERMINATION: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Terminación de las limitaciones a la circulación de la factura "
        "electrónica de venta como título"
    ),
    MandatePower.MANDATE: (
        "Registrar, firmar y consultar ApplicationResponse - Mandato"
    ),
    MandatePower.MANDATE_TERMINATION: (
        "Registrar, firmar y consultar ApplicationResponse - Terminación del Mandato"
    ),
    MandatePower.INVOICE_PAYMENT: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Pago de la factura electrónica de venta como título valor"
    ),
    MandatePower.PAYMENT_REPORT: (
        "Registrar, firmar y consultar ApplicationResponse - Informe para el pago"
    ),
    MandatePower.ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Endoso con efectos de cesión ordinaria"
    ),
    MandatePower.PROTEST: (
        "Registrar, firmar y consultar ApplicationResponse - Protesto"
    ),
    MandatePower.ECONOMIC_RIGHTS_TRANSFER: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Transferencia de los derechos económicos"
    ),
    MandatePower.ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Notificación al deudor sobre la transferencia de los derechos "
        "económicos"
    ),
    MandatePower.ECONOMIC_RIGHTS_TRANSFER_PAYMENT: (
        "Registrar, firmar y consultar ApplicationResponse - "
        "Pago de la transferencia de los derechos económicos"
    ),
}


@unique
class MandateReferenceType(StrEnum):
    """Invoice reference cardinality from ReferenciaDocumento-e.gc."""

    ONE = "1"
    MULTIPLE = "2"
    ALL = "3"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code, returning None for unknown values."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish catalog label."""
        return {
            self.ONE: "Una factura",
            self.MULTIPLE: "Varias facturas",
            self.ALL: "Todas las facturas",
        }[self]
