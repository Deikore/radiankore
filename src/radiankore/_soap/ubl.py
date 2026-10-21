"""Pure UBL readers shared by event and reference-note responses."""

from datetime import date, datetime, time, timedelta, timezone

from lxml import etree

from radiankore._soap.namespaces import CAC, CBC
from radiankore._soap.parsing import element_text, is_nil
from radiankore.catalogs import IdentificationType
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import EventParty

_COLOMBIA_TIMEZONE = timezone(timedelta(hours=-5))


def texts(parent: etree._Element, path: str) -> tuple[str, ...]:
    """Collect nonempty stripped descriptions or messages from direct paths."""
    return tuple(
        text for node in parent.findall(path) if (text := (node.text or "").strip())
    )


def _attribute(node: etree._Element | None, name: str) -> str | None:
    if node is None or is_nil(node):
        return None
    return node.get(name, "").strip() or None


def party(parent: etree._Element, name: str) -> EventParty | None:
    """Read a UBL participant without guessing missing identification fields."""
    node = parent.find(f"{{{CAC}}}{name}")
    if node is None:
        return None
    company_id = node.find(f"{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID")
    identification_code = _attribute(company_id, "schemeName")
    try:
        identification_type = (
            IdentificationType(identification_code)
            if identification_code is not None
            else None
        )
    except ValueError as exc:
        raise DianResponseError("Unknown identification type in a UBL party.") from exc
    return EventParty(
        tax_number=element_text(node, f"{{{CAC}}}PartyTaxScheme/{{{CBC}}}CompanyID"),
        name=element_text(node, f"{{{CAC}}}PartyTaxScheme/{{{CBC}}}RegistrationName"),
        verification_digit=_attribute(company_id, "schemeID"),
        identification_type=identification_type,
    )


def effective_datetime(
    date_text: str | None,
    time_text: str | None,
) -> tuple[date | None, time | None]:
    """Normalize optional dates and times to Colombia's fixed UTC-05:00 offset."""
    try:
        event_date = date.fromisoformat(date_text) if date_text else None
        event_time = time.fromisoformat(time_text) if time_text else None
        if event_time is not None:
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=_COLOMBIA_TIMEZONE)
            # A fixed offset permits clock conversion even without an event date.
            local = datetime.combine(
                event_date or date(2000, 1, 1), event_time
            ).astimezone(_COLOMBIA_TIMEZONE)
            if event_date is not None:
                event_date = local.date()
            event_time = local.timetz()
    except (ValueError, OverflowError) as exc:
        raise DianResponseError("Invalid date or time in a UBL response.") from exc
    return event_date, event_time
