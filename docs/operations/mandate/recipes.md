# Recetas complementarias de mandato

Cada receta es independiente: copie la [base común](participants.md#base-común),
el caso [M433-S-MULTIPLE-J](433.md#m433-s-multiple-j) y **solo la receta elegida**.
`replace` construye un nuevo modelo inmutable y vuelve a validar sus condiciones.
Después use la [preparación](../mandate.md#ejemplo-de-preparación-y-envío).
Estas variantes no multiplican los 48 casos del catálogo principal.

## REC-VERBAL — Contrato verbal

La forma del contrato solo cambia la declaración; sigue siendo obligatorio
adjuntar el PDF de soporte. `VERBAL` genera el literal `verbal` y `WRITTEN`
`escrito`. El integrador debe aportar evidencia coherente con el acuerdo.

```python
event = replace(
    event,
    declaration=replace(event.declaration, contract_form=MandateContractForm.VERBAL),
)
```

## REC-ROLES — Roles de ambas partes

`role` describe la función de cada parte y no sustituye `organization_type`, el
canal de una facultad ni el proveedor de software. Esta receta construye las 16
parejas de los cuatro roles del mandante y los cuatro del mandatario. Seleccione
la pareja jurídicamente aplicable antes de preparar; aquí `event` conserva la
primera. Cambiar el rol no certifica la habilitación remota de la parte.

```python
role_examples = {
    (mandator_role.value, mandatee_role.value): replace(
        event,
        sender_party=replace(mandator, role=mandator_role),
        mandatee_party=replace(mandatee_legal, role=mandatee_role),
    )
    for mandator_role in MandatorType
    for mandatee_role in MandateeType
}
event = role_examples[("Mandante-FE", "M-SN-e")]
```

## REC-CHANNELS — Canales SNE, F y PT

Los códigos son `SNE` (sistema de negociación electrónica), `F` (factor) y `PT`
(proveedor tecnológico). Cada pareja de `scope.powers` tiene su propio canal.
R01–R05 solo admiten SNE/F; R06–R22 admiten los tres. Se usa R14 para construir
las tres variantes válidas; elija una para preparar. Los canales también pueden
aplicarse a ALL17 en 431/432, conservando una sola pareja de facultad/canal.

```python
channel_examples = {
    channel.value: replace(
        event,
        scope=MandateScope(
            powers=(
                (MandatePower.WITH_REPRESENTATION, channel),
                (MandatePower.MANDATE, channel),
            )
        ),
    )
    for channel in MandateChannel
}
event = channel_examples["F"]
```

## REC-POWERS — Catálogo completo R01–R22

En 433/434, MR91 debe ir primero y debe seguirlo al menos una facultad
particular. ALL17 corresponde a 431/432. El texto XML de códigos une las parejas
con `;`, por ejemplo `MR91-SNE;R14-SNE`, sin espacios añadidos.

| Código | Miembro de `MandatePower` | Facultad | Canales |
| --- | --- | --- | --- |
| R01 | `ACKNOWLEDGEMENT` | Acuse de recibo | SNE, F |
| R02 | `CLAIM` | Reclamo | SNE, F |
| R03 | `GOODS_OR_SERVICES_RECEIPT` | Recibo del bien o servicio | SNE, F |
| R04 | `EXPRESS_ACCEPTANCE` | Aceptación expresa | SNE, F |
| R05 | `TACIT_ACCEPTANCE` | Aceptación tácita | SNE, F |
| R06 | `GUARANTEE` | Aval | SNE, F, PT |
| R07 | `RADIAN_REGISTRATION` | Inscripción en RADIAN | SNE, F, PT |
| R08 | `OWNERSHIP_ENDORSEMENT` | Endoso en propiedad | SNE, F, PT |
| R09 | `GUARANTEE_ENDORSEMENT` | Endoso en garantía | SNE, F, PT |
| R10 | `COLLECTION_ENDORSEMENT` | Endoso en procuración | SNE, F, PT |
| R11 | `ENDORSEMENT_CANCELLATION` | Cancelación de endoso | SNE, F, PT |
| R12 | `CIRCULATION_RESTRICTION` | Limitación a la circulación | SNE, F, PT |
| R13 | `CIRCULATION_RESTRICTION_TERMINATION` | Terminación de limitación | SNE, F, PT |
| R14 | `MANDATE` | Mandato | SNE, F, PT |
| R15 | `MANDATE_TERMINATION` | Terminación del mandato | SNE, F, PT |
| R16 | `INVOICE_PAYMENT` | Pago de factura | SNE, F, PT |
| R17 | `PAYMENT_REPORT` | Informe para el pago | SNE, F, PT |
| R18 | `ENDORSEMENT_WITH_ORDINARY_ASSIGNMENT_EFFECTS` | Endoso con efectos de cesión ordinaria | SNE, F, PT |
| R19 | `PROTEST` | Protesto | SNE, F, PT |
| R20 | `ECONOMIC_RIGHTS_TRANSFER` | Cesión de derechos económicos | SNE, F, PT |
| R21 | `ECONOMIC_RIGHTS_TRANSFER_NOTIFICATION` | Notificación de cesión | SNE, F, PT |
| R22 | `ECONOMIC_RIGHTS_TRANSFER_PAYMENT` | Pago de cesión | SNE, F, PT |

Esta receta incluye todas con SNE. El límite del texto de códigos es 600
caracteres, incluidos canales y separadores. No se ordenan ni deduplican
facultades aportadas por el consumidor.

```python
event = replace(
    event,
    scope=MandateScope(
        powers=(
            (
                MandatePower.WITH_REPRESENTATION,
                MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
            ),
            *(
                (power, MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM)
                for power in MandatePower
                if power.value.startswith("R")
            ),
        )
    ),
)
```

## REC-INVOICE-SCOPES — Facultades distintas por factura

Solo 433/434 admiten `MandateDocumentReference.scope`. La referencia sin override
usa `event.scope`. Alcances iguales comparten `DocumentResponse`; los grupos
siguen su primera aparición y cada grupo conserva el orden de sus referencias.
El bloque principal conserva todas las referencias en su orden original.
Para 434 copie la base común, [M434-S-MULTIPLE-J](434.md#m434-s-multiple-j)
y este mismo bloque; el período del caso ya es ilimitado.

```python
event = replace(
    event,
    document_references=(
        invoice_one,
        replace(
            invoice_two,
            scope=MandateScope(
                powers=(
                    (MandatePower.WITH_REPRESENTATION, MandateChannel.FACTOR),
                    (MandatePower.GUARANTEE, MandateChannel.FACTOR),
                )
            ),
        ),
    ),
)
```

## REC-REPRESENTATIVES — Varios representantes

Se conservan todos y su orden. La segunda persona del mandatario será declarante
porque se selecciona explícitamente, aunque figure después en XML.

```python
second_person = replace(
    mandatee_representative,
    identification_number="100000003",
    first_name="Marta",
)
event = replace(
    event,
    sender_party=replace(
        mandator, representatives=(mandator_representative, second_person)
    ),
    mandatee_party=replace(
        mandatee_legal, representatives=(mandatee_representative, second_person)
    ),
    declaration=replace(event.declaration, declarant=second_person),
)
```

## REC-NOTARIES — Varios notarios

GENERAL exige emisores notariales en ambos soportes, y fecha de escritura en el
contrato. `issuers` conserva orden y repeticiones. `office_number` es número de
notaría; no lo sustituya por departamento empresarial. SPECIAL no lleva notarios.

```python
second_notary = MandateNotary(
    identification_number="900000006",
    verification_digit="9",
    first_name="Pedro",
    family_name="Ficticio",
    job_title="Notario",
    office_number="13",
)
event = replace(
    event,
    nature=MandateNature.GENERAL,
    attached_contract=replace(contract_general, issuers=(notary, second_notary)),
    attached_validity_note=replace(validity_note, issuers=(notary, second_notary)),
)
```

## REC-REPEATED-REFERENCES — Referencias repetidas

Se preservan las dos apariciones en el bloque principal y en su grupo de alcance.
`MULTIPLE` cuenta entradas, sin deduplicarlas.

```python
event = replace(event, document_references=(invoice_one, invoice_one))
```

## REC-TWENTY — Límite de 20 facturas

`MULTIPLE` admite 2–20 referencias. La número 21 produce `ValueError`;
`ONE` exige una y `ALL` exige `()`. ALL genera una referencia XML con `ID=1`, sin
UUID ni DocumentTypeCode: no se simula enumerando facturas ficticias.

```python
event = replace(
    event,
    document_references=tuple(
        MandateDocumentReference(document_number=f"FE{i}", uuid=f"{i:096x}")
        for i in range(1, 21)
    ),
)
```

## REC-NOTES — Observaciones repetidas

Solo se admite `EventNoteKind.ADDITIONAL`. Ambas ocurrencias siguen las dos
notas generadas de 043. En 044 se usa el mismo `additional_notes` después de las
notas propias de la operación; nunca `header.notes`.

```python
observation = EventNote(kind=EventNoteKind.ADDITIONAL, text="Observación ficticia.")
event = replace(event, additional_notes=(observation, observation))
```
