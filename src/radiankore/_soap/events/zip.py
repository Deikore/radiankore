"""ZIP packaging for RADIAN event ApplicationResponse documents."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


def pack_event(xml_bytes: bytes, *, xml_name: str) -> bytes:
    """Return a ZIP archive containing exactly one ApplicationResponse XML.

    DIAN's ``SendEventUpdateStatus`` expects the ``contentFile`` parameter to
    be the bytes of a ZIP with a single UBL ApplicationResponse inside.
    """
    if not xml_name.endswith(".xml") or any(c in xml_name for c in "/\\"):
        raise ValueError("xml_name must be a plain XML filename.")
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(xml_name, xml_bytes)
    return buffer.getvalue()
