"""In-memory certificate material loaded from PKCS#12 (PFX/P12) containers."""

from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Self, cast

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    pkcs12,
)


class DigitalCertificateError(ValueError):
    """Certificate material cannot be decoded or is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True, eq=False)
class DigitalCertificate:
    """Own a matching private key, leaf certificate, and additional certificates.

    Prefer ``from_pfx`` or ``from_file`` for loading PKCS#12 containers. Direct
    construction supports already decoded material. Passwords and source bytes
    are not retained, and certificate material is excluded from representations.
    Loading does not validate trust, revocation, validity dates, or DIAN policy.
    """

    private_key: pkcs12.PKCS12PrivateKeyTypes = field(repr=False)
    certificate: x509.Certificate = field(repr=False)
    additional_certificates: tuple[x509.Certificate, ...] = field(
        default=(), repr=False
    )

    def __post_init__(self) -> None:
        """Reject a certificate whose public key does not match the private key."""
        key_public_bytes = self.private_key.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        cert_public_bytes = self.certificate.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        if key_public_bytes != cert_public_bytes:
            raise DigitalCertificateError(
                "The private key does not match the certificate."
            )

    @classmethod
    def from_pfx(cls, data: bytes, *, password: str | bytes | None = None) -> Self:
        """Decode a PFX/P12 container, requiring a private key and leaf certificate.

        String passwords are encoded as UTF-8; use bytes for other encodings.
        Use ``None`` for an unencrypted container. Decoding failures raise
        ``DigitalCertificateError`` with the original exception as their cause.
        """
        encoded_password = (
            password.encode("utf-8") if isinstance(password, str) else password
        )
        try:
            private_key, certificate, additional = pkcs12.load_key_and_certificates(
                data, encoded_password
            )
        except (ValueError, UnsupportedAlgorithm) as exc:
            raise DigitalCertificateError(
                "Unable to load PKCS#12 data; check the container and password."
            ) from exc

        if private_key is None or certificate is None:
            raise DigitalCertificateError(
                "PKCS#12 data must contain a private key and its certificate."
            )
        # The loader's annotations are broader than the documented PKCS#12 key types.
        return cls(
            cast(pkcs12.PKCS12PrivateKeyTypes, private_key),
            certificate,
            tuple(additional),
        )

    @classmethod
    def from_file(
        cls, path: str | PathLike[str], *, password: str | bytes | None = None
    ) -> Self:
        """Read a PFX/P12 file and close it before returning the decoded material.

        Filesystem errors propagate as ``OSError`` subclasses. Decoding errors
        raise ``DigitalCertificateError``, as with ``from_pfx``.
        """
        return cls.from_pfx(Path(path).read_bytes(), password=password)
