"""RADIAN payment and notification serializers with independent payment restriction."""

from lxml import etree

from radiankore._soap.events.common import _sub_element
from radiankore._soap.events.radian_common import (
    DIAN_PARTY,
    custom_extension,
    document_reference,
    document_response,
    event_root,
    financial_party,
    named_xml_party,
)
from radiankore._soap.namespaces import CBC
from radiankore.environment import Environment
from radiankore.models.events import (
    EconomicRightsNotificationEvent,
    EconomicRightsPaymentEvent,
    InvoicePaymentEvent,
    PaymentReportEvent,
    RadianSoftware,
)


def build_payment(
    event: InvoicePaymentEvent
    | PaymentReportEvent
    | EconomicRightsPaymentEvent
    | EconomicRightsNotificationEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Dispatch paid events separately from notices without changing profile data."""
    if isinstance(event, (InvoicePaymentEvent, EconomicRightsPaymentEvent)):
        return _build_paid_event(event, software=software, environment=environment)
    return _build_notice(event, software=software, environment=environment)


def _build_paid_event(
    event: InvoicePaymentEvent | EconomicRightsPaymentEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Serialize a payment with financial participation and its effective date."""
    if isinstance(event, InvoicePaymentEvent):
        payers = event.payers
        extension = "InformacionPagos"
        description = "Pago de la factura electrónica de venta como título valor"
    else:
        payers = (event.payer,)
        extension = "InformacionPagoTransferencia"
        description = "Pago de la transferencia de derechos económicos"
    first = payers[0].party
    assert first is not None
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=first.tax_number,
        receiver_nit=DIAN_PARTY.tax_number,
        software=software,
        environment=environment,
    )
    custom_extension(
        root,
        extension,
        (
            ("ValorActualTituloValor", event.current_value),
            ("ValorPendienteTituloValor", event.remaining_value),
        ),
    )
    financial_party(root, "SenderParty", payers, event.currency)
    named_xml_party(root, "ReceiverParty", DIAN_PARTY)
    block, response = document_response(
        root, event.code, description, list_id=event.restriction.value
    )
    _sub_element(response, CBC, "EffectiveDate", event.effective_date.isoformat())
    document_reference(block, event.reference)
    return root


def _build_notice(
    event: PaymentReportEvent | EconomicRightsNotificationEvent,
    *,
    software: RadianSoftware,
    environment: Environment,
) -> etree._Element:
    """Serialize debtor-facing notices without manufacturing a payment record."""
    if isinstance(event, PaymentReportEvent):
        extension = "InformacionParaelPago"
        value = event.title_value
        description = "Informe para el pago"
    else:
        extension = "NotificacionPagoDeudor"
        value = event.current_value
        description = (
            "Notificación al deudor sobre la transferencia de los derechos económicos"
        )
    root = event_root(
        event.header,
        code=event.code,
        operation_type=event.operation_type.value,
        reference=event.reference,
        sender_nit=event.sender_party.tax_number,
        receiver_nit=event.receiver_party.tax_number,
        software=software,
        environment=environment,
    )
    custom_extension(root, extension, (("ValorFEV-TV", value),))
    named_xml_party(root, "SenderParty", event.sender_party)
    named_xml_party(root, "ReceiverParty", event.receiver_party)
    block, _ = document_response(root, event.code, description)
    document_reference(block, event.reference)
    return root
