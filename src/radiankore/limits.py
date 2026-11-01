"""Configurable bounds for decoded HTTP bodies and expanded CSV data."""

from dataclasses import dataclass

__all__ = ["DianResponseLimits"]


@dataclass(frozen=True, slots=True, kw_only=True)
class DianResponseLimits:
    """Limit response bytes per operation; None disables only that field.

    HTTP bounds apply after HTTP content decoding. The CSV bound applies after
    ZIP decompression, before UTF-8 decoding. These are not resident-memory caps
    or documented DIAN quotas. Omitting client configuration enables defaults.
    """

    soap_bytes: int | None = 16 * 1024 * 1024
    download_bytes: int | None = 64 * 1024 * 1024
    csv_bytes: int | None = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        for name in ("soap_bytes", "download_bytes", "csv_bytes"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer or None.")
            if value <= 0:
                raise ValueError(f"{name} must be positive.")
