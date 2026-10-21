"""Read GetNumberingRange without interpreting DIAN business statuses."""

import re

from lxml import etree

from radiankore._soap.namespaces import NUMBER_RANGE, NUMBER_RANGE_LIST
from radiankore._soap.parsing import element_text, is_nil, read_date, soap_result
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import NumberingRange, NumberingRangeResult


def _long(node: etree._Element, name: str) -> int | None:
    child = node.find(f"{{{NUMBER_RANGE}}}{name}")
    if child is None:
        return None
    try:
        value = (child.text or "").strip()
        if is_nil(child) or re.fullmatch(r"[+-]?[0-9]+", value) is None:
            raise ValueError("Expected a non-nillable xs:long.")
        number = int(value)
        if not -(2**63) <= number < 2**63:
            raise ValueError("Value is outside the xs:long range.")
        return number
    except ValueError as exc:
        raise DianResponseError(f"Invalid {name} in numbering range.") from exc


def _range(node: etree._Element) -> NumberingRange:
    return NumberingRange(
        resolution_number=element_text(node, f"{{{NUMBER_RANGE}}}ResolutionNumber"),
        resolution_date=read_date(
            node, NUMBER_RANGE, "ResolutionDate", context="numbering range"
        ),
        prefix=element_text(node, f"{{{NUMBER_RANGE}}}Prefix"),
        from_number=_long(node, "FromNumber"),
        to_number=_long(node, "ToNumber"),
        valid_date_from=read_date(
            node, NUMBER_RANGE, "ValidDateFrom", context="numbering range"
        ),
        valid_date_to=read_date(
            node, NUMBER_RANGE, "ValidDateTo", context="numbering range"
        ),
        technical_key=element_text(node, f"{{{NUMBER_RANGE}}}TechnicalKey"),
    )


def parse_numbering_range_response(data: bytes) -> NumberingRangeResult | None:
    """Return optional metadata and all ranges without sorting or filtering them."""
    result = soap_result(data, "GetNumberingRange")
    if result is None:
        return None
    container = result.find(f"{{{NUMBER_RANGE_LIST}}}ResponseList")
    ranges = (
        tuple(
            None if is_nil(node) else _range(node)
            for node in container.findall(f"{{{NUMBER_RANGE}}}NumberRangeResponse")
        )
        if container is not None and not is_nil(container)
        else ()
    )
    return NumberingRangeResult(
        operation_code=element_text(result, f"{{{NUMBER_RANGE_LIST}}}OperationCode"),
        operation_description=element_text(
            result, f"{{{NUMBER_RANGE_LIST}}}OperationDescription"
        ),
        ranges=ranges,
    )
