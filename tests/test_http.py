"""Retry-After syntax, UTC normalization and finite cooldowns."""

from datetime import UTC, datetime

import pytest

from radiankore._soap import http


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, None),
        (" 12 ", 12.0),
        ("Thu, 22 Oct 2026 18:00:30 GMT", 30.0),
        ("Thu, 22 Oct 2026 18:00:30", 30.0),
        ("Thu, 22 Oct 2026 17:59:00 GMT", 0.0),
        ("invalid", None),
        ("", None),
        ("-1", None),
        ("1.5", None),
        ("9" * 400, None),
    ],
)
def test_retry_after_is_a_finite_nonnegative_delay(
    monkeypatch: pytest.MonkeyPatch, header: str | None, expected: float | None
) -> None:
    class Clock:
        @staticmethod
        def now(tz: object) -> datetime:
            assert tz is UTC
            return datetime(2026, 10, 22, 18, tzinfo=UTC)

    monkeypatch.setattr(http, "datetime", Clock)
    assert http.retry_after(header) == expected
