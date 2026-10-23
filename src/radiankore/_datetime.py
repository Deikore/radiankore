"""Pure Colombian date/time normalization shared by domain and serialization."""

import datetime as dt

_COLOMBIA_TIMEZONE = dt.timezone(offset=-dt.timedelta(hours=5))


def colombian_issue_datetime(issue_date: dt.date, issue_time: dt.time) -> dt.datetime:
    """Normalize date and time together, including an offset-induced day change."""
    value = dt.datetime.combine(issue_date, issue_time)
    if value.tzinfo is None:
        value = value.replace(tzinfo=_COLOMBIA_TIMEZONE)
    return value.astimezone(_COLOMBIA_TIMEZONE).replace(microsecond=0)
