# Endosos 037–039/047 y cancelación 040

Usa los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).

## Endoso completo

```python
from dataclasses import replace

from radiankore.catalogs import EndorsementForm, PaymentMeans, RadianOperationType
from radiankore.models.events import (
    EndorsementEvent,
    NegotiationTerms,
    RadianParticipation,
)

event = EndorsementEvent(
    header=header,
    operation_type=RadianOperationType.OWNERSHIP_WITH_RECOURSE,
    reference=invoice,
    form=EndorsementForm.COMPLETE,
    endorsers=(RadianParticipation(party=holder, amount=Decimal("100000.00")),),
    endorsees=(RadianParticipation(party=buyer, amount=Decimal("100000.00")),),
    negotiation=NegotiationTerms(
        total_value=Decimal("100000.00"),
        price=Decimal("95000.00"),
        discount_rate=Decimal("5"),
        payment_means=PaymentMeans.CASH,
    ),
    debtors=(debtor,),
)
```

| Evento / operación | Miembro | Condiciones |
| --- | --- | --- |
| 037 / 371 | `OWNERSHIP_WITH_RECOURSE` | Endoso en propiedad con responsabilidad |
| 037 / 372 | `OWNERSHIP_WITHOUT_RECOURSE` | Sin responsabilidad; declaración explícita en notas |
| 038 / 038 | `GUARANTEE_ENDORSEMENT` | Garantía; valor total, sin precio, tasa ni medio de pago |
| 039 / 039 | `COLLECTION_ENDORSEMENT` | Procuración; valor total, sin precio, tasa ni medio de pago |
| 047 / 047 | `ORDINARY_ASSIGNMENT_ENDORSEMENT` | Cesión ordinaria; completo y posterior al vencimiento |

Para 038 y 039, sustituye la negociación por
`NegotiationTerms(total_value=Decimal("100000.00"))`. La referencia puede omitir
vencimiento y la tupla `debtors` puede quedar vacía en estos perfiles, conforme a
sus cardinalidades. Para 037 y 047, vencimiento, deudores y negociación completa
son obligatorios.

037 no se admite después del vencimiento; 047 debe elegirse explícitamente para
fecha posterior, sin conversión automática. Por ejemplo, para construir un caso
sintético 047 con los datos comunes:

```python
ordinary_assignment = replace(
    event,
    operation_type=RadianOperationType.ORDINARY_ASSIGNMENT_ENDORSEMENT,
    reference=replace(invoice, due_date=stamp.date() - timedelta(days=1)),
)
```

Prepara `ordinary_assignment` para el caso 047; `event` conserva el endoso 037
para los ejemplos siguientes. Para garantía y procuración, construye alternativas:

```python
guarantee_endorsement = replace(
    event,
    operation_type=RadianOperationType.GUARANTEE_ENDORSEMENT,
    negotiation=NegotiationTerms(total_value=Decimal("100000.00")),
)
collection_endorsement = replace(
    guarantee_endorsement,
    operation_type=RadianOperationType.COLLECTION_ENDORSEMENT,
)
without_recourse = replace(
    event,
    operation_type=RadianOperationType.OWNERSHIP_WITHOUT_RECOURSE,
)
```

## Participantes y precisión

`endorsers` y `endorsees` son tuplas no vacías de `RadianParticipation`. Permiten
varios participantes con sus valores individuales, preservando orden y duplicados.
Todos comparten la moneda de `NegotiationTerms.currency`, predeterminada COP.
`factor_type=FactorType.FACTORING` o `CONFIRMING`, cuando aplique, genera
`CompanyLegalFormCode`. Este dato no se infiere de la identificación.

Los totales de endosantes para 037/047 deben sumar `total_value` (AAI05a).
La diferencia de suma de endosatarios es notificación AAG20 y no se eleva a error
local. Las identidades se serializan en `PartyTaxScheme` y sus participaciones en
`PartyLegalEntity`, conservando el emparejamiento por orden. Los deudores se ubican
en `DocumentReference/IssuerParty`, como en la estructura de generación y las muestras.

La extensión `InformacionNegociacion` contiene `ValorTotalEndoso`; para 037/047
incluye además `PrecioPagarseFEV`, `TasaDescuento` y `MedioPago`, en ese orden.
Los campos opcionales de venta no se emiten vacíos para 038/039 aunque algunas
muestras los incluyan así.

El precio y la tasa son `Decimal` explícitos. La tasa se expresa como porcentaje
0–100. AAI07b y los textos de generación de la tasa no coinciden con la aritmética
de las ejemplificaciones: no se recalculan valores ni se impone esa fórmula
contradictoria como rechazo local. Su aceptación se verifica en DIAN.

## Endoso en blanco

Después de construir un evento 037, 038 o 039, omite las identidades de los
endosantes y conserva sus participaciones:

```python
event = replace(
    event,
    form=EndorsementForm.BLANK,
    endorsers=tuple(replace(p, party=None) for p in event.endorsers),
)
```

Este bloque es una alternativa para 037/038/039; no se aplica al ejemplo 047.
El endosatario conserva su identificación; su nombre puede omitirse en blanco.
La firma sigue usando el certificado del cliente. `ResponseCode/@listID` será `2`
y el CUDE omitirá la identificación del endosante, incorporando `2` según §12.1.3.
No se usa el CUDE general rellenando un NIT vacío. Los completos usan `listID=1`.
Para 047 se genera `listID=1` exigido por la regla de validación AAH10, aunque su
muestra lo omita.

## Cancelar un endoso

```python
from radiankore.models.events import EndorsementCancellationEvent, RadianEventReference

event = EndorsementCancellationEvent(
    header=header,
    operation_type=RadianOperationType.CANCEL_GUARANTEE_ENDORSEMENT,
    sender_party=holder,
    receiver_party=buyer,
    reference=RadianEventReference(
        document_number="ENDOSO-EJEMPLO-1",
        uuid="c" * 96,
    ),
)
```

401 cancela garantía; 402 cancela procuración; 403 corresponde a tacha por endoso
en retorno. Sus miembros son `CANCEL_GUARANTEE_ENDORSEMENT`,
`CANCEL_COLLECTION_ENDORSEMENT` y `CANCEL_RETURN_ENDORSEMENT`.

La referencia apunta al evento anterior con CUDE y tipo `96`, no a la factura.
El receptor se suministra explícitamente y las notas deben contener la declaración
y motivo aplicables. La caja solo aporta muestras de 401/402; para 403 se usa la
estructura común 040 y el código de tabla 14.1.2, sin inventar extensiones.

Fuentes: §§7.2.1.2, 7.2.4.5, 7.2.5.5–7.2.5.8, 7.2.5.15,
9.2.3.5, 9.2.6–9.2.9, 9.2.16, 12.1.1–12.1.3 y tablas 14.1.2–14.2.3.
