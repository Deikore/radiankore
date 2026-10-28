"""WS-Security signing for DIAN customer services."""

from contextlib import AbstractContextManager, nullcontext

import xmlsec
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from lxml import etree

from radiankore._soap.namespaces import DS, EC, WSSE, X509_V3
from radiankore.certificate import DigitalCertificate
from radiankore.exceptions import DianSignatureError


def sign_envelope(
    envelope: etree._Element,
    security: etree._Element,
    *,
    certificate: DigitalCertificate,
    to_id: str,
    token_id: str,
    certificate_lock: AbstractContextManager[object] | None = None,
) -> None:
    """Sign wsa:To in place using the DIAN authentication profile."""
    if not isinstance(certificate.private_key, rsa.RSAPrivateKey):
        raise DianSignatureError("DIAN SOAP signing requires an RSA private key.")
    try:
        signature = xmlsec.template.create(
            envelope,
            xmlsec.constants.TransformExclC14N,
            xmlsec.constants.TransformRsaSha256,
            ns="ds",
        )
        security.insert(2, signature)
        canonicalization = signature.find(
            f"{{{DS}}}SignedInfo/{{{DS}}}CanonicalizationMethod"
        )
        if canonicalization is None:
            raise DianSignatureError("Unable to construct the signature template.")
        etree.SubElement(
            canonicalization,
            f"{{{EC}}}InclusiveNamespaces",
            nsmap={"ec": EC},
            PrefixList="wsa soap wcf",
        )
        reference = xmlsec.template.add_reference(
            signature, xmlsec.constants.TransformSha256, uri=f"#{to_id}"
        )
        transform = xmlsec.template.add_transform(
            reference, xmlsec.constants.TransformExclC14N
        )
        etree.SubElement(
            transform,
            f"{{{EC}}}InclusiveNamespaces",
            nsmap={"ec": EC},
            PrefixList="soap wcf",
        )
        key_info = xmlsec.template.ensure_key_info(signature)
        token_reference = etree.SubElement(
            key_info, f"{{{WSSE}}}SecurityTokenReference"
        )
        etree.SubElement(
            token_reference,
            f"{{{WSSE}}}Reference",
            URI=f"#{token_id}",
            ValueType=X509_V3,
        )
        xmlsec.tree.add_ids(envelope, ["Id"])
        context = xmlsec.SignatureContext()
        context.key = certificate_key(certificate, certificate_lock=certificate_lock)
        context.sign(signature)
    except xmlsec.Error as exc:
        raise DianSignatureError("Unable to sign the SOAP request.") from exc


def certificate_key(
    certificate: DigitalCertificate,
    *,
    certificate_lock: AbstractContextManager[object] | None = None,
) -> xmlsec.Key:
    """Snapshot material under the caller's lock, then load a private native key.

    Neither the temporary PEM bytes nor the resulting xmlsec key are cached.
    Independent xmlsec contexts may sign concurrently after this snapshot.
    """
    with certificate_lock or nullcontext():
        private_pem = certificate.private_key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )
        public_pem = certificate.certificate.public_bytes(Encoding.PEM)
    key = xmlsec.Key.from_memory(private_pem, xmlsec.constants.KeyDataFormatPem, None)
    key.load_cert_from_memory(public_pem, xmlsec.constants.KeyDataFormatCertPem)
    return key
