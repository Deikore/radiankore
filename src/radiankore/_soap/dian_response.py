"""Scalar and binary readers shared by DianResponse operation parsers."""

from lxml import etree

from radiankore._soap.namespaces import ARRAY, RESPONSE
from radiankore._soap.parsing import decode_base64_text, is_nil, read_boolean


def read_is_valid(result: etree._Element, *, operation: str) -> bool | None:
    """Read an optional, non-nillable DianResponse validity flag."""
    return read_boolean(result, RESPONSE, "IsValid", operation=operation)


def read_messages(result: etree._Element) -> tuple[str | None, ...]:
    """Preserve message order, repetitions, empty strings and nullable items."""
    container = result.find(f"{{{RESPONSE}}}ErrorMessage")
    if container is None or is_nil(container):
        return ()
    return tuple(
        None if is_nil(node) else (node.text or "").strip()
        for node in container.findall(f"{{{ARRAY}}}string")
    )


def read_binary(result: etree._Element, name: str) -> bytes | None:
    """Decode one binary field independently, distinguishing absent from empty."""
    node = result.find(f"{{{RESPONSE}}}{name}")
    if node is None or is_nil(node):
        return None
    return decode_base64_text(node.text or "", field_name=name)
