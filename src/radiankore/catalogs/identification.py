"""Identification codes from DIAN's TipoIdFiscal-2.1 catalog, version 1.

The RADIAN 1.1 annex, section 14.2.13, lists the original eleven codes. PPT
comes from DIAN's GetAcquirer integration guide. This snapshot does not validate
document numbers or enforce participant-role restrictions.
"""

from enum import StrEnum, unique
from typing import Self


@unique
class IdentificationType(StrEnum):
    """Known CompanyID/schemeName codes with Spanish display labels."""

    CIVIL_REGISTRY = "11"
    IDENTITY_CARD = "12"
    CITIZENSHIP_CARD = "13"
    FOREIGNER_CARD = "21"
    FOREIGNER_IDENTITY_CARD = "22"
    NIT = "31"
    PASSPORT = "41"
    FOREIGN_IDENTIFICATION_DOCUMENT = "42"
    PEP = "47"
    PPT = "48"
    FOREIGN_NIT = "50"
    NUIP = "91"

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
        """Return the Spanish catalog label, excluding explanatory footnotes."""
        return _LABELS[self]


_LABELS: dict[IdentificationType, str] = {
    IdentificationType.CIVIL_REGISTRY: "Registro civil",
    IdentificationType.IDENTITY_CARD: "Tarjeta de identidad",
    IdentificationType.CITIZENSHIP_CARD: "Cédula de ciudadanía",
    IdentificationType.FOREIGNER_CARD: "Tarjeta de extranjería",
    IdentificationType.FOREIGNER_IDENTITY_CARD: "Cédula de extranjería",
    IdentificationType.NIT: "NIT",
    IdentificationType.PASSPORT: "Pasaporte",
    IdentificationType.FOREIGN_IDENTIFICATION_DOCUMENT: (
        "Documento de identificación extranjero"
    ),
    IdentificationType.PEP: "PEP",
    IdentificationType.PPT: "PPT",
    IdentificationType.FOREIGN_NIT: "NIT de otro país",
    IdentificationType.NUIP: "NUIP",
}
