"""Secure XML and SOAP parsing shared by all DIAN operations."""

import base64
import binascii
from http import HTTPStatus

from lxml import etree

from radiankore._soap.namespaces import SOAP, WCF, XSI
from radiankore.exceptions import DianResponseError, DianSoapFaultError


def parse_xml(data: bytes) -> etree._Element:
    """Parse untrusted bytes without resolving entities or loading external data."""
    try:
        root = etree.fromstring(
            data,
            parser=etree.XMLParser(
                resolve_entities=False,
                load_dtd=False,
                no_network=True,
                huge_tree=False,
                recover=False,
            ),
        )
    except etree.XMLSyntaxError as exc:
        raise DianResponseError("Invalid XML in the DIAN response.") from exc
    info = root.getroottree().docinfo
    if info.internalDTD is not None or info.externalDTD is not None:
        raise DianResponseError("DTD declarations are not allowed in DIAN responses.")
    return root


def soap_body(data: bytes) -> etree._Element:
    """Return the SOAP 1.2 body, raising a typed error for a SOAP Fault."""
    root = parse_xml(data)
    bodies = root.findall(f"{{{SOAP}}}Body")
    if root.tag != f"{{{SOAP}}}Envelope" or len(bodies) != 1:
        raise DianResponseError("Expected a SOAP 1.2 envelope with one body.")
    body = bodies[0]
    fault = body.find(f"{{{SOAP}}}Fault")
    if fault is not None:
        raise DianSoapFaultError(
            code=element_text(fault, f"{{{SOAP}}}Code/{{{SOAP}}}Value") or "",
            reason=element_text(fault, f"{{{SOAP}}}Reason/{{{SOAP}}}Text") or "",
        )
    return body


def element_text(parent: etree._Element, path: str) -> str | None:
    """Read stripped text, treating missing, nil and empty elements as absent."""
    node = parent.find(path)
    if node is None or is_nil(node):
        return None
    return (node.text or "").strip() or None


def is_nil(node: etree._Element) -> bool:
    """Return whether an element explicitly declares an XML Schema nil value."""
    return node.get(f"{{{XSI}}}nil") in {"true", "1"}


def read_http_status(
    parent: etree._Element, namespace: str, name: str
) -> HTTPStatus | None:
    """Map optional SOAP text to HTTPStatus independently of HTTP transport."""
    value = element_text(parent, f"{{{namespace}}}{name}")
    if value is None:
        return None
    try:
        if len(value) != 3 or not value.isascii() or not value.isdecimal():
            raise ValueError("HTTP status must contain three ASCII digits.")
        return HTTPStatus(int(value))
    except ValueError as exc:
        raise DianResponseError(
            f"Invalid HTTP status {name} in DIAN response."
        ) from exc


def soap_result(data: bytes, operation: str) -> etree._Element | None:
    """Extract one operation result, allowing missing or explicitly nil results."""
    body = soap_body(data)
    responses = body.findall(f"{{{WCF}}}{operation}Response")
    if len(responses) != 1:
        raise DianResponseError(f"Expected one {operation}Response in the SOAP body.")
    results = responses[0].findall(f"{{{WCF}}}{operation}Result")
    if len(results) > 1:
        raise DianResponseError(f"Expected at most one {operation}Result.")
    if not results or is_nil(results[0]):
        return None
    return results[0]


def decode_base64_text(value: str, *, field_name: str) -> bytes:
    """Decode Base64 allowing XML whitespace, without interpreting its content."""
    compact = value.translate(str.maketrans("", "", " \t\r\n"))
    try:
        return base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DianResponseError(f"Invalid Base64 in {field_name}.") from exc
