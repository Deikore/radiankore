"""Tests for eager certificate loading through the public client API."""

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.serialization import (
    NoEncryption,
    pkcs12,
)

from radiankore import DianClient, DigitalCertificate, DigitalCertificateError


@pytest.mark.parametrize("use_string_path", [True, False])
@pytest.mark.parametrize("password", ["test-password", b"test-password"])
def test_client_loads_certificate_from_path(
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    use_string_path: bool,
    password: str | bytes,
) -> None:
    path = str(encrypted_pfx_path) if use_string_path else encrypted_pfx_path

    client = DianClient(certificate_path=path, password=password)
    loaded = client.certificate
    encrypted_pfx_path.unlink()

    assert client.certificate is loaded
    assert loaded.certificate == digital_certificate.certificate
    assert (
        loaded.private_key.public_key() == digital_certificate.private_key.public_key()
    )


def test_client_loads_unencrypted_certificate_without_password(
    tmp_path: Path, digital_certificate: DigitalCertificate
) -> None:
    path = tmp_path / "unencrypted.p12"
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"test",
            digital_certificate.private_key,
            digital_certificate.certificate,
            None,
            NoEncryption(),
        )
    )

    client = DianClient(path)

    assert client.certificate.certificate == digital_certificate.certificate


@pytest.mark.parametrize("password", ["wrong-password", None])
def test_client_rejects_wrong_or_missing_password_immediately(
    encrypted_pfx_path: Path, password: str | None
) -> None:
    with pytest.raises(DigitalCertificateError):
        DianClient(encrypted_pfx_path, password=password)


def test_client_rejects_invalid_pfx_immediately(tmp_path: Path) -> None:
    path = tmp_path / "invalid.pfx"
    path.write_bytes(b"not-a-pfx")

    with pytest.raises(DigitalCertificateError):
        DianClient(path, password="secret")


def test_client_propagates_missing_file_immediately(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        DianClient(tmp_path / "missing.pfx")
