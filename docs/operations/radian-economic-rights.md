# Derechos económicos 049–051

Contexto funcional: [049](../functional/events/049.md); [050](../functional/events/050.md); [051](../functional/events/051.md).

Esta guía describe la implementación y sus validaciones técnicas.

Utilice los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).
Las tres clases referencian la factura por CUFE/tipo `01` y requieren vencimiento.
No se reemplaza esta referencia por el CUDE de la transferencia.

## Transferencia 049

```python
from dataclasses import replace

from radiankore.catalogs import PaymentMeans, RadianOperationType
from radiankore.models.events import (
    EconomicRightsTransferEvent,
    EconomicRightsTransferTerms,
    RadianParticipation,
)

event = EconomicRightsTransferEvent(
    header=header,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITH_RECOURSE,
    reference=invoice,
    transferors=(RadianParticipation(party=holder, amount=Decimal("50000.00")),),
    transferees=(RadianParticipation(party=buyer, amount=Decimal("50000.00")),),
    debtors=(debtor,),
    terms=EconomicRightsTransferTerms(
        transferred_value=Decimal("50000.00"),
        price=Decimal("47500.00"),
        discount_factor=Decimal("5"),
        payment_means=PaymentMeans.CASH,
    ),
)
```

| Operación | Miembro | Alcance |
| --- | --- | --- |
| 491 | `ECONOMIC_RIGHTS_PARTIAL_WITH_RECOURSE` | Parcial con responsabilidad |
| 492 | `ECONOMIC_RIGHTS_FULL_WITH_RECOURSE` | Total con responsabilidad |
| 493 | `ECONOMIC_RIGHTS_PARTIAL_WITHOUT_RECOURSE` | Parcial sin responsabilidad |
| 494 | `ECONOMIC_RIGHTS_FULL_WITHOUT_RECOURSE` | Total sin responsabilidad |

Para las otras operaciones construya alternativas explícitas. En un caso total,
el consumidor aporta el valor total real de los derechos; en este ejemplo es
100.000, y los campos financieros se suministran nuevamente:

```python
partial_without_recourse = replace(
    event,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_WITHOUT_RECOURSE,
)
full_with_recourse = replace(
    event,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_FULL_WITH_RECOURSE,
    transferors=(RadianParticipation(party=holder, amount=Decimal("100000.00")),),
    transferees=(RadianParticipation(party=buyer, amount=Decimal("100000.00")),),
    terms=replace(
        event.terms,
        transferred_value=Decimal("100000.00"),
        price=Decimal("95000.00"),
    ),
)
full_without_recourse = replace(
    full_with_recourse,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_FULL_WITHOUT_RECOURSE,
)
```

| Entrada | Correspondencia | Regla local |
| --- | --- | --- |
| `transferors` / `transferees` | `SenderParty` / `ReceiverParty`, identidades antes de participaciones | Tuplas no vacías, moneda única; cedentes positivos |
| `debtors` | `DocumentReference/IssuerParty/PartyTaxScheme` | Tupla no vacía; no infiere deudor a partir del cesionario |
| `terms.transferred_value` | `InformacionTransferenciaDerechos/ValorTransferenciaDerechos` | Positivo; igual a suma de cedentes, AAI05a |
| `terms.price` | `PrecioPagarseFEV` | Decimal explícito no negativo |
| `terms.discount_factor` | `FactordeDescuento` | Porcentaje 0–100, hasta siete caracteres |
| `terms.payment_means` | `MedioPago` | Catálogo compartido de tabla 14.2.11 |

La extensión contiene los cuatro pares Name/Value en ese orden. No utiliza el
literal `TasaDescuento` de los endosos. La diferencia de suma de cesionarios
es notificación AAG20. Aunque AAF19 de cedentes también es notificación,
**AAI05a de la extensión exige la suma como rechazo** y se valida localmente.
Las muestras 491/493 contienen importes incompatibles con esa regla: no se copian.

La fórmula de precio AAI07b y el texto del factor no coinciden con la aritmética
de las muestras. Se preservan los valores explícitos sin imponer esa fórmula;
su aceptación se comprueba en habilitación. El modelo no dispone del valor
original de los derechos y no puede comprobar por sí mismo que la selección de
transferencia parcial/total corresponda a los antecedentes reales.

## Notificación al deudor 050

```python
from radiankore.models.events import EconomicRightsNotificationEvent

event = EconomicRightsNotificationEvent(
    header=header,
    sender_party=holder,
    receiver_party=debtor,
    reference=invoice,
    current_value=Decimal("50000.00"),
)
```

Operación/código fijos 050. El receptor es el deudor, no DIAN. La extensión
`NotificacionPagoDeudor` conserva el literal `ValorFEV-TV`: generación AAZB05
y validación AAZ05 describen su valor como **valor actual del título**.
Se exige `Decimal` positivo de hasta 20 caracteres. El consumidor aporta el valor
que corresponda a los derechos y antecedentes; la librería no lo obtiene de 049.

## Pago 051

```python
from radiankore.catalogs import PaymentRestriction
from radiankore.models.events import EconomicRightsPaymentEvent

event = EconomicRightsPaymentEvent(
    header=header,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_PARTIAL_PAYMENT,
    reference=invoice,
    payer=RadianParticipation(party=debtor, amount=Decimal("25000.00")),
    restriction=PaymentRestriction.RESTRICTED,
    effective_date=stamp.date(),
    current_value=Decimal("100000.00"),
    remaining_value=Decimal("75000.00"),
)
full_payment = replace(
    event,
    operation_type=RadianOperationType.ECONOMIC_RIGHTS_FULL_PAYMENT,
    payer=RadianParticipation(party=debtor, amount=Decimal("100000.00")),
    remaining_value=Decimal("0.00"),
)
```

`payer` es una sola participación: AAF12 de §7.2.5.19 tiene cardinalidad 1..1.
Se exige importe positivo, no superior al actual (AAF19/AAF19b), y saldo igual
a actual menos pagado (AAK07), con precisión propia. El pago total 512 exige
importe igual al actual (AAF19c) y saldo cero; el parcial 511 deja saldo positivo.

El receptor es DIAN. `Response/EffectiveDate` no supera la fecha de emisión
colombiana. `InformacionPagoTransferencia` emite `ValorActualTituloValor` y
`ValorPendienteTituloValor`. `currency` es COP por defecto.
Las operaciones 511/512 son independientes del `listID` de limitación 1/2,
tomado de `PaymentRestriction`. Se admiten las cuatro combinaciones.

La generación y tabla de roles identifican al pagador como adquirente/deudor/
aceptante; el listado de negocio alterna denominaciones con el cesionario.
La librería exige identidad explícita y no la deduce del certificado. El archivo
de matriz sujeto–evento–rol es anterior y no cubre todas estas clases: no se usa
para inventar requisitos ausentes de sus tablas específicas.

Fuentes: §§7.2.1.10–12, 7.2.4.11–13, 7.2.5.17–19, 9.2.3.11–13 y 9.2.18–20;
tabla 14.1.2 y las siete ejemplificaciones de 049–051.
