"""WS-Security signing for DIAN customer services."""

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
        context.key = xmlsec.Key.from_memory(
            certificate.private_key.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            ),
            xmlsec.constants.KeyDataFormatPem,
            None,
        )
        context.key.load_cert_from_memory(
            certificate.certificate.public_bytes(Encoding.PEM),
            xmlsec.constants.KeyDataFormatCertPem,
        )
        context.sign(signature)
    except xmlsec.Error as exc:
        raise DianSignatureError("Unable to sign the SOAP request.") from exc
