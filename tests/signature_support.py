"""Independent verification of serialized SOAP and UBL signatures."""

import xmlsec
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore import DigitalCertificate
from radiankore._soap.namespaces import DS, WSU


def verify_signature(data: bytes, certificate: DigitalCertificate) -> None:
    root = etree.fromstring(data)
    signature = root.find(f".//{{{DS}}}Signature")
    assert signature is not None
    context = xmlsec.SignatureContext()
    register_references(context, root)
    context.key = xmlsec.Key.from_memory(
        certificate.certificate.public_bytes(Encoding.PEM),
        xmlsec.constants.KeyDataFormatCertPem,
        None,
    )
    context.verify(signature)


def register_references(context: xmlsec.SignatureContext, root: etree._Element) -> None:
    """Resolve signed references independently before native verification."""
    attributes = ("Id", "ID", f"{{{WSU}}}Id")
    for reference in root.findall(f".//{{{DS}}}SignedInfo/{{{DS}}}Reference"):
        uri = reference.get("URI", "")
        if not uri.startswith("#"):
            continue
        for element in root.iter():
            for attribute in attributes:
                if element.get(attribute) == uri[1:]:
                    name = etree.QName(attribute)
                    context.register_id(element, name.localname, name.namespace)
