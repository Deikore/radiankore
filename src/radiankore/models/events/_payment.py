"""Pure payment date and balance rules shared across RADIAN model families."""

import datetime as dt
from decimal import Decimal, localcontext

from radiankore._datetime import colombian_issue_datetime
from radiankore.catalogs import PaymentRestriction
from radiankore.models.events.radian_common import (
    RadianEventHeader,
    decimal_value,
    native_date,
)


def payment_values(
    *,
    header: RadianEventHeader,
    restriction: PaymentRestriction,
    effective_date: dt.date,
    current_value: Decimal,
    remaining_value: Decimal,
    paid_amount: Decimal,
    partial: bool,
) -> None:
    """Share payment date/balance rules without conflating payment and restriction."""
    if not isinstance(restriction, PaymentRestriction):
        raise TypeError("restriction must be a PaymentRestriction.")
    native_date(effective_date, "effective_date")
    issue_date = colombian_issue_datetime(header.issue_date, header.issue_time).date()
    if effective_date > issue_date:
        raise ValueError("effective_date must not follow the Colombian issue_date.")
    decimal_value(current_value, "current_value", positive=True)
    decimal_value(remaining_value, "remaining_value")
    if partial and not (0 < remaining_value < current_value):
        raise ValueError("Partial payments require a positive, reduced balance.")
    if not partial and remaining_value != 0:
        raise ValueError("Full payments require a zero remaining_value.")
    decimal_value(paid_amount, "paid amount", positive=True)
    if paid_amount > current_value:
        raise ValueError("Paid amount must not exceed current_value (AAF19b).")
    if not partial and paid_amount != current_value:
        raise ValueError("Full payment must equal current_value (AAF19c).")
    with localcontext() as context:
        context.prec = 50
        if paid_amount + remaining_value != current_value:
            raise ValueError(
                "Paid amount plus remaining_value must equal current_value (AAK07)."
            )
