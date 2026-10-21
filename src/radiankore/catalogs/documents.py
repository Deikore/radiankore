"""Document types from DIAN FE 1.9 (2026), referenced table 13.1.3.

The table includes 96 (ApplicationResponse), absent from TipoDocumento-2.1.gc.
See docs/references/dian/invoicing/1.9/README.md for preserved official sources.
"""

from enum import StrEnum, unique
from typing import Self


@unique
class DocumentType(StrEnum):
    """Canonical DIAN document codes with Spanish display labels."""

    SALES_INVOICE = "01"
    EXPORT_INVOICE = "02"
    PAPER_INVOICE_TRANSMISSION = "03"
    DIAN_CONTINGENCY_INVOICE = "04"
    CREDIT_NOTE = "91"
    DEBIT_NOTE = "92"
    APPLICATION_RESPONSE = "96"

    @classmethod
    def from_code(cls, code: str | None) -> Self | None:
        """Resolve an exact code without applying SOAP parser aliases."""
        if code is None:
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @property
    def label(self) -> str:
        """Return the Spanish label from referenced table 13.1.3."""
        return _LABELS[self]


_LABELS: dict[DocumentType, str] = {
    DocumentType.SALES_INVOICE: "Factura electrónica de Venta",
    DocumentType.EXPORT_INVOICE: "Factura electrónica de venta -exportación",
    DocumentType.PAPER_INVOICE_TRANSMISSION: (
        "Instrumento electrónico de transmisión \u2013 tipo 03"
    ),
    DocumentType.DIAN_CONTINGENCY_INVOICE: "Factura electrónica de Venta - tipo 04",
    DocumentType.CREDIT_NOTE: "Nota Crédito",
    DocumentType.DEBIT_NOTE: "Nota Débito",
    DocumentType.APPLICATION_RESPONSE: "Eventos (ApplicationResponse)",
}
