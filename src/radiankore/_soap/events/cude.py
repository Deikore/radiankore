"""CUDE generation for invoice and RADIAN ApplicationResponse documents.

References: RADIAN 1.1 annex sections 12.1.1, 12.1.3 and 12.1.4.
"""

import datetime as dt
from hashlib import sha384

from radiankore._datetime import colombian_issue_datetime as colombian_issue_datetime


def compute_application_response_cude(
    event_number: str,
    issue_date: dt.date,
    issue_time: dt.time,
    issuer_nit: str,
    software_pin: str,
    *,
    document_number: str,
    document_type_code: str = "01",
    receiver_nit: str,
    response_code: str,
) -> str:
    """Return the SHA-384 CUDE using the actual parties and referenced document.

    The general concatenation order defined in section 12.1.1 is::

        Num_DE + Fec_Emi + Hor_Emi + NitFE + DocAdq + ResponseCode +
        ID + DocumentTypeCode + SoftwarePIN

    ``Hor_Emi`` always uses the Colombia offset ``-05:00``.
    """
    stamp = colombian_issue_datetime(issue_date, issue_time)
    issue_date = stamp.date()
    time_text = stamp.timetz().isoformat(timespec="seconds")
    composition = (
        f"{event_number}"
        f"{issue_date.isoformat()}"
        f"{time_text}"
        f"{issuer_nit}"
        f"{receiver_nit}"
        f"{response_code}"
        f"{document_number}"
        f"{document_type_code}"
        f"{software_pin}"
    )
    return sha384(composition.encode("utf-8")).hexdigest()


def compute_mandate_cude(
    event_number: str,
    issue_date: dt.date,
    issue_time: dt.time,
    issuer_nit: str,
    software_pin: str,
    *,
    document_number: str,
    document_type_code: str = "01",
    receiver_nit: str = "800197268",
    response_code: str = "043",
) -> str:
    """Retain the mandate helper's existing signature and default values."""
    return compute_application_response_cude(
        event_number,
        issue_date,
        issue_time,
        issuer_nit,
        software_pin,
        document_number=document_number,
        document_type_code=document_type_code,
        receiver_nit=receiver_nit,
        response_code=response_code,
    )


def compute_blank_endorsement_cude(
    event_number: str,
    issue_date: dt.date,
    issue_time: dt.time,
    receiver_nit: str,
    response_code: str,
    document_number: str,
    software_pin: str,
) -> str:
    """Apply RADIAN 1.1 section 12.1.3: omit NitFE and include listID 2."""
    stamp = colombian_issue_datetime(issue_date, issue_time)
    composition = (
        event_number
        + stamp.date().isoformat()
        + stamp.timetz().isoformat(timespec="seconds")
        + receiver_nit
        + response_code
        + "2"
        + document_number
        + "01"
        + software_pin
    )
    return sha384(composition.encode("utf-8")).hexdigest()
