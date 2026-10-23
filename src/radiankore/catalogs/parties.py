"""Shared participant organization and tax catalogs from RADIAN 1.1."""

from enum import StrEnum, unique
from typing import Self


@unique
class OrganizationType(StrEnum):
    """CompanyID @schemeVersionID; never inferred from identification type."""

    LEGAL_PERSON = "1"
    NATURAL_PERSON = "2"

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
        """Return the Spanish organization label."""
        return _ORGANIZATION_LABELS[self]


@unique
class PartyTaxScheme(StrEnum):
    """PartyTaxScheme/TaxScheme codes, distinct from invoice tax totals."""

    VAT = "01"
    CONSUMPTION_TAX = "04"
    VAT_AND_CONSUMPTION_TAX = "ZA"
    NOT_APPLICABLE = "ZZ"

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
        """Return the matching TaxScheme/Name from RADIAN table 14.2.15."""
        return _TAX_LABELS[self]


_ORGANIZATION_LABELS = {
    OrganizationType.LEGAL_PERSON: "Persona Jurídica",
    OrganizationType.NATURAL_PERSON: "Persona Natural",
}
_TAX_LABELS = {
    PartyTaxScheme.VAT: "IVA",
    PartyTaxScheme.CONSUMPTION_TAX: "INC",
    PartyTaxScheme.VAT_AND_CONSUMPTION_TAX: "IVA e INC",
    PartyTaxScheme.NOT_APPLICABLE: "No aplica",
}
