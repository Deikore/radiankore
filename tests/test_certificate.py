"""Tests for real PKCS#12 decoding using synthetic certificate material."""

from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PublicFormat,
    pkcs12,
)

from radiankore import DigitalCertificate, DigitalCertificateError


@pytest.mark.parametrize("password", ["contraseña-de-prueba", b"test-password", None])
def test_load_pfx(
    digital_certificate: DigitalCertificate, password: str | bytes | None
) -> None:
    encoded = password.encode("utf-8") if isinstance(password, str) else password
    encryption = BestAvailableEncryption(encoded) if encoded else NoEncryption()
    data = pkcs12.serialize_key_and_certificates(
        b"test",
        digital_certificate.private_key,
        digital_certificate.certificate,
        None,
        encryption,
    )

    loaded = DigitalCertificate.from_pfx(data, password=password)

    assert loaded.certificate == digital_certificate.certificate
    assert loaded.additional_certificates == ()
    assert loaded.private_key.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    ) == digital_certificate.private_key.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )


def test_load_pfx_from_file(
    tmp_path: Path, digital_certificate: DigitalCertificate
) -> None:
    path = tmp_path / "certificate.pfx"
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"test",
            digital_certificate.private_key,
            digital_certificate.certificate,
            None,
            BestAvailableEncryption(b"test-password"),
        )
    )

    loaded = DigitalCertificate.from_file(path, password="test-password")
    path.unlink()

    assert loaded.certificate == digital_certificate.certificate


def test_preserve_additional_certificates(
    digital_certificate: DigitalCertificate,
) -> None:
    leaf = digital_certificate.certificate
    additional = (
        x509.CertificateBuilder()
        .subject_name(leaf.subject)
        .issuer_name(leaf.issuer)
        .public_key(digital_certificate.private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(leaf.not_valid_before_utc)
        .not_valid_after(leaf.not_valid_after_utc)
        .sign(digital_certificate.private_key, hashes.SHA256())
    )
    data = pkcs12.serialize_key_and_certificates(
        b"test", digital_certificate.private_key, leaf, [additional], NoEncryption()
    )

    loaded = DigitalCertificate.from_pfx(data)

    assert loaded.certificate == leaf
    assert loaded.additional_certificates == (additional,)


@pytest.mark.parametrize("password", [b"wrong-password", None])
def test_reject_wrong_or_missing_password(
    digital_certificate: DigitalCertificate, password: bytes | None
) -> None:
    data = pkcs12.serialize_key_and_certificates(
        b"test",
        digital_certificate.private_key,
        digital_certificate.certificate,
        None,
        BestAvailableEncryption(b"test-password"),
    )

    with pytest.raises(DigitalCertificateError) as error:
        DigitalCertificate.from_pfx(data, password=password)

    assert isinstance(error.value.__cause__, ValueError)
    assert "wrong-password" not in str(error.value)


def test_reject_invalid_pfx() -> None:
    with pytest.raises(DigitalCertificateError) as error:
        DigitalCertificate.from_pfx(b"not-a-pfx", password="secret")

    assert isinstance(error.value.__cause__, ValueError)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("include_key", [True, False])
def test_reject_incomplete_pfx(
    digital_certificate: DigitalCertificate, include_key: bool
) -> None:
    data = pkcs12.serialize_key_and_certificates(
        b"test",
        digital_certificate.private_key if include_key else None,
        None,
        None if include_key else [digital_certificate.certificate],
        NoEncryption(),
    )

    with pytest.raises(DigitalCertificateError, match="must contain"):
        DigitalCertificate.from_pfx(data)


def test_reject_mismatched_key(digital_certificate: DigitalCertificate) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(DigitalCertificateError, match="does not match"):
        DigitalCertificate(other_key, digital_certificate.certificate)


def test_missing_file_propagates_filesystem_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        DigitalCertificate.from_file(tmp_path / "missing.pfx")


def test_certificate_representation_hides_material(
    digital_certificate: DigitalCertificate,
) -> None:
    assert repr(digital_certificate) == "DigitalCertificate()"
