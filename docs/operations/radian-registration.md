# Inscripción de factura 036

Usa los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).

```python
from radiankore.catalogs import RadianOperationType
from radiankore.models.events import RadianRegistrationEvent, RegistrationPaymentState

event = RadianRegistrationEvent(
    header=header,
    operation_type=RadianOperationType.REGISTRATION_INITIAL_DIRECT,
    sender_party=holder,
    reference=invoice,
    payment_state=RegistrationPaymentState(
        invoice_value=Decimal("100000.00"),
        paid_value=Decimal("25000.00"),
        remaining_value=Decimal("75000.00"),
    ),
    direct_buyer=buyer,
)
```

| Operación | Miembro | Comprador directo |
| --- | --- | --- |
| 361 | `REGISTRATION_INITIAL_GENERAL` | Se omite |
| 362 | `REGISTRATION_INITIAL_DIRECT` | Obligatorio |
| 363 | `REGISTRATION_SUBSEQUENT_GENERAL` | Se omite |
| 364 | `REGISTRATION_SUBSEQUENT_DIRECT` | Obligatorio |

El destinatario es DIAN. La referencia contiene número de factura, CUFE y fecha
original de vencimiento. El comprador directo se serializa en
`DocumentResponse/IssuerParty/PartyLegalEntity`; no reemplaza al destinatario DIAN.

La extensión `CustomTagGeneral/ConstanciadePagos` incluye los tres pares ordenados
`ValorFEV-TV`, `ValorPagado` y `NuevoValorTV`. Sus valores son explícitos y deben
satisfacer `paid_value + remaining_value == invoice_value`, sin redondeo.
Un valor pagado igual a cero se indica con `Decimal("0.00")`, sin omitirlo.

Aunque la tabla de generación presenta `ValorPagado` como opcional, las reglas
de rechazo AAX06/AAX07 lo exigen; el modelo lo requiere. Las muestras de negociación
directa contienen un `schemeName` erróneo para DIAN: se genera `31`, NIT `800197268`,
DV `4`, en lugar de reproducirlo.

El consumidor verifica inscripción previa, titularidad, antecedentes 030/032/033
o 034 y condiciones de pago aplicables. Esas condiciones y la representación
pueden declararse en `header.notes`; no se consultan antecedentes automáticamente.

Fuentes: §§7.2.1.1, 7.2.4.4, 7.2.5.4, 9.2.3.4, 9.2.5 y operaciones de tabla 14.1.2.
