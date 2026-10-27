"""Resolve identification evidence without broadening outbound catalog inputs."""

import unicodedata

from radiankore.catalogs import IdentificationType


def _label_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    unaccented = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(unaccented.split())


_LABELS = {_label_key(kind.label): kind for kind in IdentificationType}


def resolve_identification(
    value: str | None,
) -> tuple[IdentificationType | None, str | None]:
    """Resolve codes or catalog labels, retaining nonempty original XML text."""
    if value is None or not value.strip():
        return None, None
    known = IdentificationType.from_code(value.strip())
    if known is None:
        known = _LABELS.get(_label_key(value))
    return known, value
