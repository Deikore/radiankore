"""Independent verification of serialized SOAP and UBL signatures."""

import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import DigitalCertificate
from radiankore._soap.namespaces import DS


def verify_signature(data: bytes, certificate: DigitalCertificate) -> None:
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
