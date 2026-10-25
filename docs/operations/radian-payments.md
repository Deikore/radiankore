# Pago 045 e informe para el pago 046

Contexto funcional: [045](../functional/events/045.md); [046](../functional/events/046.md).

Esta guía describe la implementación y sus validaciones técnicas.

Utilice los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).

## Registrar un pago

```python
from radiankore.catalogs import CurrencyCode, PaymentRestriction, RadianOperationType
from radiankore.models.events import InvoicePaymentEvent, RadianParticipation

event = InvoicePaymentEvent(
    header=header,
    operation_type=RadianOperationType.PARTIAL_PAYMENT,
    reference=invoice,
    payers=(RadianParticipation(party=holder, amount=Decimal("25000.00")),),
    restriction=PaymentRestriction.RESTRICTED,
    effective_date=stamp.date(),
    current_value=Decimal("100000.00"),
    remaining_value=Decimal("75000.00"),
    currency=CurrencyCode.COP,
)
```

`operation_type` y `restriction` son independientes:

| Dato | Valores | XML |
| --- | --- | --- |
| Tipo de pago | `PARTIAL_PAYMENT` / `FULL_PAYMENT` | `CustomizationID` 451 / 452 |
| Limitación | `UNRESTRICTED` / `RESTRICTED` | `ResponseCode/@listID` 1 / 2 |

Ambas condiciones de limitación pueden acompañar a cualquiera de los dos tipos
de pago. La muestra de pago total usa `listID=2`, pero eso no significa «pago total»:
la tabla 14.2.9 y `TipoPago.gc` identifican la limitación, no la cantidad pagada.

Se exige valor actual positivo; un pago parcial deja un saldo positivo menor
que el actual, y uno total deja saldo cero. La fecha efectiva se serializa en
`Response/EffectiveDate` y no puede superar la fecha de emisión normalizada a
Colombia. La referencia exige vencimiento.

Los participantes conservan identidad y valor de participación en su orden.
La extensión `InformacionPagos` contiene `ValorActualTituloValor` y
`ValorPendienteTituloValor`. No se inventa un historial ni se deduce la limitación
de los saldos. Las notificaciones de suma de participaciones no se convierten
en rechazos locales. DIAN es el destinatario generado internamente.

La muestra de pago parcial deja saldo cero, contradiciendo la operación declarada;
el modelo exige que se seleccione explícitamente pago total para ese saldo.

## Informar para el pago

```python
from radiankore.models.events import PaymentReportEvent

event = PaymentReportEvent(
    header=header,
    sender_party=holder,
    receiver_party=debtor,
    reference=invoice,
    title_value=Decimal("100000.00"),
)
```

El código y operación de este modelo son fijos, `046`. El destinatario es el
adquirente/deudor, no DIAN. El vencimiento es obligatorio y la extensión
`InformacionParaelPago` contiene `ValorFEV-TV`. No lleva restricción ni fecha
efectiva de pago. El consumidor verifica el plazo del informe y los antecedentes;
la librería no calcula días hábiles ni obtiene la factura por su cuenta.

Fuentes: §§7.2.1.5–7.2.1.6, 7.2.4.8–7.2.4.9, 7.2.5.13–7.2.5.14,
9.2.14–9.2.15 y tablas 14.1.2/14.2.9.
