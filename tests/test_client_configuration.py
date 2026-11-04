"""Reject invalid options before loading certificates or opening connections."""

from collections.abc import Callable

import pytest

from radiankore import AsyncDianClient, AsyncDianLimiter, DianClient


@pytest.mark.parametrize(
    "factory,options,message",
    [
        (DianClient.from_certificate, {}, "DigitalCertificate"),
        (AsyncDianClient.from_certificate, {}, "DigitalCertificate"),
        (AsyncDianClient, {"timeouts": object()}, "timeouts"),
        (AsyncDianClient, {"limiter": object()}, "limiter"),
        (DianClient, {"reuse_connections": 1}, "reuse_connections"),
    ],
)
def test_invalid_client_options(
    factory: Callable[..., object], options: dict[str, object], message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        factory(None, **options)


@pytest.mark.parametrize("service", ["", 1])
def test_limiter_service_keys_are_nonempty_strings(service: object) -> None:
    with pytest.raises(ValueError, match="Service keys"):
        AsyncDianLimiter(service_limits={service: 1})  # type: ignore[dict-item]


def test_limiter_exposes_immutable_configuration() -> None:
    services = {"service": 2}
    limiter = AsyncDianLimiter(
        concurrency=3, requests_per_second=4, service_limits=services
    )
    services["service"] = 99
    assert limiter.concurrency == 3
    assert limiter.requests_per_second == 4
    assert limiter.service_limits == {"service": 2}
    with pytest.raises(TypeError):
        limiter.service_limits["service"] = 99
