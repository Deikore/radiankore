"""Explicit optional children of the mandatory UBL TaxScheme group."""

from dataclasses import dataclass

from radiankore.catalogs import PartyTaxScheme

__all__ = ["RadianTaxDetails"]


@dataclass(frozen=True, slots=True, kw_only=True)
class RadianTaxDetails:
    """Control optional ID/Name independently; an empty instance keeps the group.

    A PartyTaxScheme enum on a party remains shorthand for its complete pair.
    Profile-specific required children are checked by the containing event.
    """

    code: PartyTaxScheme | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if self.code is not None and not isinstance(self.code, PartyTaxScheme):
            raise TypeError("code must be a PartyTaxScheme or None.")
        if self.name is not None:
            if not isinstance(self.name, str):
                raise TypeError("name must be a string or None.")
            if self.name not in {scheme.label for scheme in PartyTaxScheme}:
                raise ValueError("name must be a catalog tax name.")
            if self.code is not None and self.code.label != self.name:
                raise ValueError(
                    "Tax code and name must belong to the same catalog pair."
                )
