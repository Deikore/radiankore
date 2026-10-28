"""Local operation helpers shared by synchronous and asynchronous clients."""

from base64 import b64encode
from datetime import datetime

from lxml import etree

from radiankore._soap.events import (
    build_radian_application_response,
    pack_event,
    sign_application_response,
)
from radiankore._soap.events.cude import colombian_issue_datetime
from radiankore._soap.namespaces import CBC
from radiankore.catalogs import EventType, IdentificationType
from radiankore.certificate import DigitalCertificate
from radiankore.environment import Environment
from radiankore.models.events import (
    InvoiceResponseEvent,
    MandateEvent,
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)


def text(value: str, name: str) -> str:
    """Validate an opaque identifier without guessing a format."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty.")
    return value


def numbering_parameters(
    account_code: str, account_code_t: str, software_code: str
) -> tuple[tuple[str, str], ...]:
    """Validate the numbering operation's ordered parameters."""
    parameters = []
    for name, wire_name, value in (
        ("account_code", "accountCode", account_code),
        ("account_code_t", "accountCodeT", account_code_t),
        ("software_code", "softwareCode", software_code),
    ):
        value = text(value, name)
        if name != "software_code" and not (value.isascii() and value.isdecimal()):
            raise ValueError(f"{name} must contain only ASCII digits.")
        parameters.append((wire_name, value))
    return tuple(parameters)


def acquirer_parameters(
    identification_type: IdentificationType, identification_number: str
) -> tuple[tuple[str, str], ...]:
    """Validate an acquirer without altering its identification number."""
    if not isinstance(identification_type, IdentificationType):
        raise TypeError("identification_type must be an IdentificationType.")
    return (
        ("identificationType", identification_type.value),
        ("identificationNumber", text(identification_number, "identification_number")),
    )


def event_parameters(
    prepared: PreparedRadianEvent, environment: Environment
) -> tuple[tuple[str, str], ...]:
    """Use the original artifact, never rebuild or silently change environments."""
    if not isinstance(prepared, PreparedRadianEvent):
        raise TypeError("prepared must be a PreparedRadianEvent.")
    if prepared.environment is not environment:
        raise ValueError("Prepared event environment does not match the client.")
    return (("contentFile", b64encode(prepared.zip_bytes).decode("ascii")),)


def prepare_event(
    event: RadianEvent,
    software: RadianSoftware,
    certificate: DigitalCertificate,
    environment: Environment,
    signing_time: datetime | None,
) -> PreparedRadianEvent:
    """Build, sign, serialize and ZIP one local artifact without I/O."""
    if not isinstance(software, RadianSoftware):
        raise TypeError("software must be a RadianSoftware.")
    if isinstance(event, InvoiceResponseEvent):
        assert signing_time is not None
        stamp = colombian_issue_datetime(event.issue_date, event.issue_time)
        signing_stamp = colombian_issue_datetime(
            signing_time.date(), signing_time.timetz()
        )
        if stamp.date() != signing_stamp.date():
            raise ValueError(
                "Invoice event issue_date must match the signing date in Colombia."
            )
    root = build_radian_application_response(
        event,
        software=software,
        environment=environment,
    )
    sign_application_response(
        root,
        certificate=certificate,
        signer_role=software.signer_role,
        signing_time=signing_time,
    )
    if isinstance(event, MandateEvent):
        code = EventType.MANDATE
        event_number = event.event_number
    else:
        code = event.code
        event_number = (
            event.event_number
            if isinstance(event, InvoiceResponseEvent)
            else event.header.event_number
        )
    cude, xml_bytes, zip_bytes = serialize_event(root)
    return PreparedRadianEvent(
        code=code,
        event_number=event_number,
        cude=cude,
        environment=environment,
        xml_bytes=xml_bytes,
        zip_bytes=zip_bytes,
    )


def serialize_event(root: etree._Element) -> tuple[str, bytes, bytes]:
    """Serialize once and enforce the existing signed XML size limit."""
    xml_bytes = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    if len(xml_bytes) > 500_000:
        raise ValueError("Signed event XML exceeds DIAN's 500,000-byte limit.")
    cude = root.findtext(f"{{{CBC}}}UUID")
    assert cude is not None
    return cude, xml_bytes, pack_event(xml_bytes, xml_name=f"ar_{cude}.xml")
