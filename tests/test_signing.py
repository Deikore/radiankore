"""Cryptographic verification of serialized requests, not template-only checks."""

from base64 import b64decode
from datetime import datetime, timedelta
from hashlib import sha256

import pytest
import xmlsec
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import DianSignatureError, DigitalCertificate, Environment
from radiankore._soap.envelope import build_signed_request
from radiankore._soap.namespaces import (
    DS,
    SOAP,
    WCF,
    WSA,
    WSSE,
    WSU,
)


def _verify(data: bytes, certificate: DigitalCertificate) -> None:
    root = etree.fromstring(data)
    xmlsec.tree.add_ids(root, ["Id"])
    signature = root.find(f".//{{{DS}}}Signature")
    assert signature is not None
    context = xmlsec.SignatureContext()
    context.key = xmlsec.Key.from_memory(
        certificate.certificate.public_bytes(Encoding.PEM),
        xmlsec.constants.KeyDataFormatCertPem,
        None,
    )
    context.verify(signature)


@pytest.mark.parametrize(
    "operation,parameters",
    [
        ("GetStatusEvent", (("trackId", "SYNTHETIC-CUFE"),)),
        ("GetStatus", (("trackId", 'SYNTHETIC<&"TRACK-ID'),)),
        ("GetXmlByDocumentKey", (("trackId", 'SYNTHETIC<&"KEY'),)),
        ("GetReferenceNotes", (("trackId", 'SYNTHETIC<&"IDENTIFIER'),)),
        ("GetDocumentInfo", (("uuid", 'SYNTHETIC<&"UUID'),)),
        (
            "GetAcquirer",
            (("identificationType", "31"), ("identificationNumber", '000<&"')),
        ),
    ],
)
@pytest.mark.parametrize("environment", list(Environment))
def test_serialized_signature_and_signed_destination(
    digital_certificate: DigitalCertificate,
    environment: Environment,
    operation: str,
    parameters: tuple[tuple[str, str], ...],
) -> None:
    payload = build_signed_request(
        operation,
        parameters,
        action=f"{WCF}/IWcfDianCustomerServices/{operation}",
        certificate=digital_certificate,
        environment=environment,
    )
    _verify(payload, digital_certificate)
    root = etree.fromstring(payload)
    to = root.find(f"{{{SOAP}}}Header/{{{WSA}}}To")
    assert to is not None and to.text == environment.addressing_to
    token = root.find(f".//{{{WSSE}}}BinarySecurityToken")
    assert token is not None
    assert b64decode(token.text or "") == digital_certificate.certificate.public_bytes(
        Encoding.DER
    )
    assert root.findtext(f"{{{SOAP}}}Header/{{{WSA}}}Action") == (
        f"{WCF}/IWcfDianCustomerServices/{operation}"
    )
    operation_node = root.find(f"{{{SOAP}}}Body/{{{WCF}}}{operation}")
    assert operation_node is not None
    assert [
        (etree.QName(node).localname, node.text) for node in operation_node
    ] == list(parameters)
    created = root.findtext(f".//{{{WSU}}}Created")
    expires = root.findtext(f".//{{{WSU}}}Expires")
    assert created is not None and expires is not None
    assert datetime.fromisoformat(expires) - datetime.fromisoformat(
        created
    ) == timedelta(minutes=5)
    security = root.find(f".//{{{WSSE}}}Security")
    assert security is not None and security.get(f"{{{SOAP}}}mustUnderstand") == "true"

    # Verify the digest with hashlib and SignedInfo with cryptography.
    canonical_to = etree.tostring(
        to, method="c14n", exclusive=True, inclusive_ns_prefixes=["soap", "wcf"]
    )
    digest = root.findtext(f".//{{{DS}}}DigestValue")
    assert b64decode(digest or "") == sha256(canonical_to).digest()
    signed_info = root.find(f".//{{{DS}}}SignedInfo")
    assert signed_info is not None
    canonical_info = etree.tostring(
        signed_info,
        method="c14n",
        exclusive=True,
        inclusive_ns_prefixes=["wsa", "soap", "wcf"],
    )
    public_key = digital_certificate.private_key.public_key()
    assert isinstance(public_key, rsa.RSAPublicKey)
    public_key.verify(
        b64decode(root.findtext(f".//{{{DS}}}SignatureValue") or ""),
        canonical_info,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    to.text = "https://example.invalid/tampered"
    with pytest.raises(xmlsec.VerificationError):
        _verify(etree.tostring(root), digital_certificate)


def test_each_request_has_fresh_ids(digital_certificate: DigitalCertificate) -> None:
    payloads = [
        build_signed_request(
            "GetStatusEvent",
            (("trackId", "CUFE"),),
            action=f"{WCF}/IWcfDianCustomerServices/GetStatusEvent",
            certificate=digital_certificate,
            environment=Environment.PRODUCTION,
        )
        for _ in range(2)
    ]
    ids = [
        {
            v
            for node in etree.fromstring(data).iter()
            for k, v in node.attrib.items()
            if k == f"{{{WSU}}}Id"
        }
        for data in payloads
    ]
    assert ids[0] and ids[1] and ids[0].isdisjoint(ids[1])


def test_reject_non_rsa_key(digital_certificate: DigitalCertificate) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    base = digital_certificate.certificate
    certificate = (
        x509.CertificateBuilder()
        .subject_name(base.subject)
        .issuer_name(base.issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(base.not_valid_before_utc)
        .not_valid_after(base.not_valid_after_utc)
        .sign(key, hashes.SHA256())
    )
    with pytest.raises(DianSignatureError, match="RSA"):
        build_signed_request(
            "GetStatusEvent",
            (("trackId", "CUFE"),),
            action=f"{WCF}/IWcfDianCustomerServices/GetStatusEvent",
            certificate=DigitalCertificate(key, certificate),
            environment=Environment.PRODUCTION,
        )


def test_native_signing_error_preserves_cause(
    digital_certificate: DigitalCertificate, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_context() -> None:
        raise xmlsec.Error("synthetic signing failure")

    monkeypatch.setattr(xmlsec, "SignatureContext", fail_context)
    with pytest.raises(DianSignatureError) as error:
        build_signed_request(
            "GetStatusEvent",
            (("trackId", "CUFE"),),
            action=f"{WCF}/IWcfDianCustomerServices/GetStatusEvent",
            certificate=digital_certificate,
            environment=Environment.PRODUCTION,
        )
    assert isinstance(error.value.__cause__, xmlsec.Error)
