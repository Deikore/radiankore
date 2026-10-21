"""Known DIAN invoice event codes from versioned official references.

RADIAN 1.1 section 14.2.1 supplies 02 and 04; Eventos-2.1.gc version 1
supplies 035-051. DIAN's electronic invoice annex 1.8 change presentation
supplies 030-034. See docs/references/dian/README.md for source links.
"""

from enum import StrEnum, unique
from typing import Self


@unique
class EventType(StrEnum):
    """Known ResponseCode values with Spanish display labels."""

    DIAN_VALIDATED = "02"
    DIAN_REJECTED = "04"
    INVOICE_ACKNOWLEDGEMENT = "030"
    INVOICE_CLAIM = "031"
    GOODS_OR_SERVICES_RECEIPT = "032"
    EXPRESS_ACCEPTANCE = "033"
    TACIT_ACCEPTANCE = "034"
    GUARANTEE = "035"
    RADIAN_REGISTRATION = "036"
    OWNERSHIP_ENDORSEMENT = "037"
    GUARANTEE_ENDORSEMENT = "038"
    COLLECTION_ENDORSEMENT = "039"
    ENDORSEMENT_CANCELLATION = "040"
    CIRCULATION_RESTRICTION = "041"
    CIRCULATION_RESTRICTION_TERMINATION = "042"
    MANDATE = "043"
    MANDATE_TERMINATION = "044"
    INVOICE_PAYMENT = "045"
    PAYMENT_REPORT = "046"
    ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS = "047"
    PROTEST = "048"
    ECONOMIC_RIGHTS_TRANSFER = "049"
    ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION = "050"
    ECONOMIC_RIGHTS_TRANSFER_PAYMENT = "051"

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
        """Return the catalog label, independent of the XML description."""
        return _LABELS[self]


_LABELS: dict[EventType, str] = {
    EventType.DIAN_VALIDATED: "Documento validado por la DIAN",
    EventType.DIAN_REJECTED: "Documento rechazado por la DIAN",
    EventType.INVOICE_ACKNOWLEDGEMENT: (
        "Acuse de recibo de Factura Electrónica de Venta"
    ),
    EventType.INVOICE_CLAIM: "Reclamo de la Factura Electrónica de Venta",
    EventType.GOODS_OR_SERVICES_RECEIPT: "Recibo del bien o prestación del servicio",
    EventType.EXPRESS_ACCEPTANCE: "Aceptación expresa",
    EventType.TACIT_ACCEPTANCE: "Aceptación Tácita",
    EventType.GUARANTEE: "Aval",
    EventType.RADIAN_REGISTRATION: (
        "Inscripción de la factura electrónica de venta como título valor - RADIAN"
    ),
    EventType.OWNERSHIP_ENDORSEMENT: "Endoso en propiedad",
    EventType.GUARANTEE_ENDORSEMENT: "Endoso en garantía",
    EventType.COLLECTION_ENDORSEMENT: "Endoso en procuración",
    EventType.ENDORSEMENT_CANCELLATION: "Cancelación de endoso",
    EventType.CIRCULATION_RESTRICTION: (
        "Limitaciones a la circulación de la factura electrónica de venta como título"
    ),
    EventType.CIRCULATION_RESTRICTION_TERMINATION: (
        "Terminación de las limitaciones a la circulación de la factura electrónica "
        "de venta como título"
    ),
    EventType.MANDATE: "Mandato",
    EventType.MANDATE_TERMINATION: "Terminación del mandato",
    EventType.INVOICE_PAYMENT: (
        "Pago de la factura electrónica de venta como título valor"
    ),
    EventType.PAYMENT_REPORT: "Informe para el pago",
    EventType.ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS: (
        "Endoso con efectos de cesión ordinaria"
    ),
    EventType.PROTEST: "Protesto",
    EventType.ECONOMIC_RIGHTS_TRANSFER: "Transferencia de los derechos económicos",
    EventType.ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION: (
        "Notificación al deudor sobre la transferencia de los derechos económicos"
    ),
    EventType.ECONOMIC_RIGHTS_TRANSFER_PAYMENT: (
        "Pago de la transferencia de los derechos económicos"
    ),
}
