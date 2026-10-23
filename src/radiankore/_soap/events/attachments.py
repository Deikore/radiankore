"""Serialize in-memory PDF evidence with exact, profile-specific DIAN metadata."""

from base64 import b64encode

from lxml import etree

from radiankore._soap.events.common import _sub_element
from radiankore._soap.namespaces import CAC, CBC
from radiankore.models.events.attachments import RadianPdfAttachment


def attach_pdf(
    reference: etree._Element, evidence: RadianPdfAttachment, *, protest: bool = False
) -> None:
    """Encode once; DIAN's PDF and encoding literals deliberately follow its profile."""
    node = _sub_element(
        _sub_element(reference, CAC, "Attachment"),
        CBC,
        "EmbeddedDocumentBinaryObject",
        b64encode(evidence.content_bytes).decode("ascii"),
    )
    for name, value in (
        ("format", "Archivo. PDF"),
        ("mimeCode", "PDF"),
        ("encodingCode", "base 64, UTF-8" if protest else "base64, UTF-8"),
        ("characterSetCode", "UTF-8"),
        ("filename", evidence.filename),
    ):
        node.set(name, value)
