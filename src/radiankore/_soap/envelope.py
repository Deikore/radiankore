"""Build SOAP requests without downloading a WSDL at runtime."""

from base64 import b64encode
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore._soap.namespaces import (
    BASE64_BINARY,
    DS,
    SOAP,
    WCF,
    WSA,
    WSSE,
    WSU,
    X509_V3,
)
from radiankore._soap.signing import sign_envelope
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment


def build_signed_request(
    operation: str,
    parameters: tuple[tuple[str, str], ...],
    *,
    action: str,
    certificate: DigitalCertificate,
    environment: Environment,
    certificate_lock: AbstractContextManager[object] | None = None,
) -> bytes:
    """Build one operation's SOAP body and sign its fresh request envelope."""
    envelope = etree.Element(
        f"{{{SOAP}}}Envelope",
        nsmap={
            "soap": SOAP,
            "wsa": WSA,
            "wcf": WCF,
            "wsse": WSSE,
            "wsu": WSU,
            "ds": DS,
        },
    )
    header = etree.SubElement(envelope, f"{{{SOAP}}}Header")
    security = etree.SubElement(header, f"{{{WSSE}}}Security")
    security.set(f"{{{SOAP}}}mustUnderstand", "true")
    timestamp = etree.SubElement(security, f"{{{WSU}}}Timestamp")
    now = datetime.now(UTC)
    etree.SubElement(timestamp, f"{{{WSU}}}Created").text = now.isoformat()
    etree.SubElement(timestamp, f"{{{WSU}}}Expires").text = (
        now + timedelta(minutes=5)
    ).isoformat()
    token_id, to_id = f"X509-{uuid4().hex}", f"id-{uuid4().hex}"
    token = etree.SubElement(
        security,
        f"{{{WSSE}}}BinarySecurityToken",
        ValueType=X509_V3,
        EncodingType=BASE64_BINARY,
    )
    token.set(f"{{{WSU}}}Id", token_id)
    with certificate_lock or nullcontext():
        public_der = certificate.certificate.public_bytes(Encoding.DER)
    token.text = b64encode(public_der).decode("ascii")
    etree.SubElement(header, f"{{{WSA}}}Action").text = action
    to = etree.SubElement(header, f"{{{WSA}}}To")
    to.set(f"{{{WSU}}}Id", to_id)
    to.text = environment.addressing_to
    body = etree.SubElement(envelope, f"{{{SOAP}}}Body")
    operation_node = etree.SubElement(body, f"{{{WCF}}}{operation}")
    for name, value in parameters:
        etree.SubElement(operation_node, f"{{{WCF}}}{name}").text = value
    sign_envelope(
        envelope,
        security,
        certificate=certificate,
        to_id=to_id,
        token_id=token_id,
        certificate_lock=certificate_lock,
    )
    return etree.tostring(envelope, encoding="UTF-8", xml_declaration=True)
