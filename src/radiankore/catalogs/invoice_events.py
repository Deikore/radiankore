"""FE 1.9 claim reasons and shared RADIAN 1.1 party catalogs.

Claim labels use referenced table 13.3.12 (2026), not the conflicting genericode.
Organization and party tax schemes follow RADIAN 1.1 sections 14.2.14-14.2.15.
"""

from enum import StrEnum, unique
from typing import Self

# Preserve historical submodule imports as the same enum objects.
from radiankore.catalogs.parties import OrganizationType as OrganizationType
from radiankore.catalogs.parties import PartyTaxScheme as PartyTaxScheme


@unique
class InvoiceClaimReason(StrEnum):
    """ResponseCode @listID for event 031; unrelated to note correction reasons."""

    DOCUMENT_INCONSISTENCIES = "01"
    GOODS_NOT_DELIVERED = "02"
    GOODS_PARTIALLY_DELIVERED = "03"
    SERVICE_NOT_PROVIDED = "04"

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
        """Return the official table label with outer whitespace removed."""
        return _CLAIM_LABELS[self]


_CLAIM_LABELS = {
    InvoiceClaimReason.DOCUMENT_INCONSISTENCIES: "Documento con inconsistencias",
    InvoiceClaimReason.GOODS_NOT_DELIVERED: "Mercancía no entregada",
    InvoiceClaimReason.GOODS_PARTIALLY_DELIVERED: "Mercancía  entregada parcialmente",
    InvoiceClaimReason.SERVICE_NOT_PROVIDED: "Servicio no prestado",
}
