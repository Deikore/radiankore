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
    payer=RadianParticipation(party=holder, amount=Decimal("25000.00")),
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

Se exige un único `payer` con importe positivo, no superior al valor actual,
y se comprueba `payer.amount + remaining_value == current_value`, sin redondear.
Un pago parcial deja un saldo positivo menor que el actual; uno total paga el
valor actual completo y deja saldo cero. La fecha efectiva se serializa en
`Response/EffectiveDate` y no puede superar la fecha de emisión normalizada a
Colombia. La referencia exige vencimiento.

El pagador conserva su identidad y el importe explícito del pago. AAF12 exige
un único `SenderParty/PartyLegalEntity` en este perfil.
La extensión `InformacionPagos` contiene `ValorActualTituloValor` y
`ValorPendienteTituloValor`. No se inventa un historial ni se deduce la limitación
de los saldos. AAF19, AAF19b, AAF19c y AAK07 son reglas de rechazo aplicables al
pago; se comprueban también en 051. DIAN es el destinatario generado internamente.

### Migración de `payers` a `payer`

Sustituya `payers=(participación,)` por `payer=participación`. El argumento
`payers` se elimina: la API anterior permitía varios `PartyLegalEntity`, aunque
la tabla de generación §7.2.5.13, p. 227, establece `1..1`. No se suman ni se
fusionan personas para convertir una entrada múltiple en un pago. Declare cada
pago como un evento independiente, con su número y sus saldos correspondientes.

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
