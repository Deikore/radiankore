"""Correction reasons from DIAN FE 1.9 (2026), tables 13.2.4 and 13.2.5.

The catalogs are distinct even where their string codes overlap. SOAP parsers
select one using DocumentType; labels never replace received descriptions.
"""

from enum import StrEnum, unique
from typing import Self


@unique
class CreditNoteReason(StrEnum):
    """Credit note correction reasons with Spanish labels from table 13.2.4."""

    PARTIAL_RETURN_OR_SERVICE_REJECTION = "1"
    INVOICE_CANCELLATION = "2"
    DISCOUNT_OR_REDUCTION = "3"
    PRICE_ADJUSTMENT = "4"
    PROMPT_PAYMENT_DISCOUNT = "5"
    VOLUME_DISCOUNT = "6"

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
        """Return the official description with outer whitespace removed."""
        return _CREDIT_LABELS[self]


@unique
class DebitNoteReason(StrEnum):
    """Debit note correction reasons with Spanish labels from table 13.2.5."""

    INTEREST = "1"
    RECEIVABLE_EXPENSES = "2"
    VALUE_CHANGE = "3"
    OTHER = "4"

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
        """Return the official description with outer whitespace removed."""
        return _DEBIT_LABELS[self]


_CREDIT_LABELS: dict[CreditNoteReason, str] = {
    CreditNoteReason.PARTIAL_RETURN_OR_SERVICE_REJECTION: (
        "Devolución parcial de los bienes y/o no aceptación parcial del servicio"
    ),
    CreditNoteReason.INVOICE_CANCELLATION: "Anulación de factura electrónica",
    CreditNoteReason.DISCOUNT_OR_REDUCTION: "Rebaja  o descuento parcial o total",
    CreditNoteReason.PRICE_ADJUSTMENT: "Ajuste de precio",
    CreditNoteReason.PROMPT_PAYMENT_DISCOUNT: "Descuento comercial por pronto pago",
    CreditNoteReason.VOLUME_DISCOUNT: "Descuento comercial por volumen de ventas",
}

_DEBIT_LABELS: dict[DebitNoteReason, str] = {
    DebitNoteReason.INTEREST: "Intereses",
    DebitNoteReason.RECEIVABLE_EXPENSES: "Gastos por cobrar",
    DebitNoteReason.VALUE_CHANGE: "Cambio del valor",
    DebitNoteReason.OTHER: "Otros",
}
