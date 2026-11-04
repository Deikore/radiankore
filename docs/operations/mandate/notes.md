# Notas, XML y migración de mandatos

Este es el contrato de **0.7.4**; las declaraciones estructuradas sustituyen
las entradas manuales de 0.7.3. El integrador suministra hechos y el SDK
redacta los textos. La generación no verifica la verdad de los hechos jurídicos.
Consulte la [matriz de conformidad](../../technical/mandate-conformance.md) para
las discrepancias del anexo; las alternativas editoriales no se transmiten.

## Entradas y valores predeterminados

| Modelo / campo | Obligatoriedad y efecto |
| --- | --- |
| `MandateDeclaration.declarant` | Obligatorio, miembro explícito de `mandatee_party.representatives`; no se deduce del certificado ni se selecciona por orden |
| `contract_form` | Obligatorio, `VERBAL` o `WRITTEN`; genera `verbal` o `escrito` |
| `chamber_of_commerce_city` | Predeterminado `None`; obligatorio para mandatario jurídico y ausente para natural |
| `MandateTerminationDeclaration.effective_date` | Obligatorio, fecha nativa; se incorpora al texto, no a un elemento EffectiveDate en 044 |
| `ratify_acts` | Predeterminado `False`; `True` solo en revocación 441 |
| `no_pending_acts` | Predeterminado `None`; no afirma ausencia de actos pendientes. En renuncia 442 debe ser explícitamente `True`; en 441/443 se omite |
| `representation` | Predeterminado `None` en 044; si se aporta, identifica exactamente ambas partes originales y su nota ocupa la primera posición |
| `additional_notes` | Predeterminado `()` en 043/044; solo propósito `ADDITIONAL`, texto no vacío hasta 5.000 caracteres, orden y duplicados intactos |

043 siempre genera dos notas: representación breve y declaración de persona
natural o jurídica. `event.notes` es una propiedad de solo lectura que devuelve
esas notas y luego las observaciones. No suministre declaraciones manuales con
`EventNote`. Las demás personas del XML no redactan automáticamente otra nota.

La duración sale de `operation_type` y `validity_period`. En 431/433 termina en
«por el tiempo consignado en este documento.»; en 432/434 termina en «sin
limitaciones de tiempo.». No hay un texto libre alternativo para la duración.
La naturaleza especial/general determina los soportes, no el tipo de declaración.

## XML de las dos notas de 043

Los fragmentos siguientes proceden de los casos indicados con la base común;
no forman un documento listo para transmitir. `cbc` y `cac` son los prefijos UBL
del documento completo. Las identidades y la ciudad se toman de los campos
indicados, sin completar alternativas editoriales.

### M433-S-ONE-N

La primera nota usa los nombres de ambas partes. La segunda usa el declarante,
contrato escrito y duración limitada, sin ciudad ni acreditación de sociedad.

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Luis Sintético OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Luis Sintético, identificado con el documento Cédula de ciudadanía No. 100000002, expresamente manifiesto que obro en nombre y representación de Mandante Sintético SAS, de conformidad con el contrato de mandato escrito existente entre las partes y con las facultades señaladas en el presente documento y por el tiempo consignado en este documento.</cbc:Note>
```

### M433-S-ONE-J

La primera nota usa los nombres de ambas partes. La segunda usa el declarante,
contrato escrito y duración limitada, junto con sociedad y ciudad de Cámara de Comercio.

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Mandatario Sintético SAS OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Luis Sintético, identificado con el documento Cédula de ciudadanía No. 100000002, en mi calidad de representante legal de la sociedad Mandatario Sintético SAS, según consta en el certificado de existencia y representación legal expedido por la Cámara de Comercio de Bogotá, expresamente manifiesto que obro en nombre y representación de Mandante Sintético SAS, de conformidad con el contrato de mandato escrito existente entre las partes y con las facultades señaladas en el presente documento y por el tiempo consignado en este documento.</cbc:Note>
```

## XML de soportes

En [M433-G-ONE-J](433.md#m433-g-one-j), el primer `LineResponse` del bloque
principal contiene el contrato y el segundo la nota de vigencia. Los siguientes
fragmentos se extraen de ese caso: emisor del contrato, respuesta con fecha de
escritura y respuesta de la nota de vigencia. La fecha efectiva del mandato sigue
siendo 22-10-2026, distinta de la escritura del 20-10-2026.

<!-- xml-path: cac:DocumentResponse[1]/cac:LineResponse[1]/cac:LineReference/cac:DocumentReference/cac:IssuerParty -->

```xml
<cac:IssuerParty>
  <cac:Person>
    <cbc:ID schemeName="31" schemeID="4">900000004</cbc:ID>
    <cbc:FirstName>Clara</cbc:FirstName>
    <cbc:FamilyName>Ficticia</cbc:FamilyName>
    <cbc:JobTitle>Notaria</cbc:JobTitle>
    <cbc:OrganizationDepartment>12</cbc:OrganizationDepartment>
  </cac:Person>
</cac:IssuerParty>
```

<!-- xml-path: cac:DocumentResponse[1]/cac:LineResponse[1]/cac:Response -->

```xml
<cac:Response>
  <cbc:Description>Este documento corresponde al contrato de mandato firmado por las partes</cbc:Description>
  <cbc:EffectiveDate>2026-10-20</cbc:EffectiveDate>
</cac:Response>
```

<!-- xml-path: cac:DocumentResponse[1]/cac:LineResponse[2]/cac:Response -->

```xml
<cac:Response>
  <cbc:Description>Este documento corresponde a la nota de vigencia del contrato de mandato</cbc:Description>
</cac:Response>
```

Los bytes originales de cada PDF van codificados en base64 en
`LineReference/DocumentReference/Attachment/EmbeddedDocumentBinaryObject`.
Sus atributos son `format="PDF"`, `mimeCode="PDF"`, `encodingCode="base64, PDF"`,
`characterSetCode="base64, PDF"` y `filename="Contrato de Mandato, PDF"` o
`"Nota de Vigencia, PDF"`. `document_id` produce el `cbc:ID` del soporte.
No se muestra el contenido binario porque depende del archivo aportado.
En SPECIAL no se genera IssuerParty notarial, fecha de escritura ni segundo soporte.

## Notas de 044

Los [ocho casos de terminación](../radian-termination.md#orden-de-las-notas)
publican todas sus notas en XML y la tabla de posiciones. Con representación,
la ratificación de 441 o la constancia de 442 ocupa Note[2] y la terminación queda
después; sin representación, terminación va primero y la condicional después.
443 solo añade representación si se aporta, seguida de terminación.
En los ocho casos las observaciones adicionales se agregan al final.

## Migración

1. En 043 retire el argumento `notes`; construya `MandateDeclaration` con el
   declarante elegido, forma del contrato y ciudad solo si el mandatario es jurídico.
   Ya no agregue `MandateRepresentation.as_note()` manualmente: 043 la genera.
2. En 044 deje `header.notes=()`, aporte `MandateTerminationDeclaration` con fecha
   efectiva y seleccione los hechos aplicables a 441/442/443. Traslade la
   representación opcional a `declaration.representation`.
3. Traslade únicamente observaciones a `additional_notes=(EventNote(...),)` con
   propósito `ADDITIONAL`. Las declaraciones de otros propósitos se rechazan ahí.
4. Lea `event.notes` para revisar la redacción. No asigne esta propiedad ni copie
   textos generados de vuelta al constructor.
5. Para GENERAL use `MandateNotary` en ambos `issuers`, fecha de escritura en el
   contrato y PDF de vigencia. Para SPECIAL omita esos tres datos notariales.
   Los representantes empresariales siguen siendo `MandatePerson`.

## Errores habituales

Cada función siguiente demuestra una entrada inválida y produce `ValueError`
**al invocarla**. Copie una base común nueva y el caso
[M433-S-MULTIPLE-J](433.md#m433-s-multiple-j) antes de cada bloque.
Son ejemplos de diagnóstico; corríjalos antes de preparar o enviar.

### ERR-DECLARANT — Declarante ajeno

Una persona puede estar en el XML del mandante sin ser representante del
mandatario. Debe seleccionarse entre los de este último.

```python
def invalid_declarant():
    return replace(
        event,
        declaration=replace(event.declaration, declarant=mandator_representative),
    )
```

### ERR-CITY-LEGAL — Falta ciudad jurídica

```python
def invalid_legal_city():
    return replace(
        event, declaration=replace(event.declaration, chamber_of_commerce_city=None)
    )
```

### ERR-CITY-NATURAL — Ciudad incompatible con persona natural

Cambiar solo la organización deja una ciudad jurídica incompatible; omítala.

```python
def invalid_natural_city():
    return replace(
        event,
        mandatee_party=mandatee_natural,
        declaration=replace(event.declaration, declarant=natural_person),
    )
```

### ERR-SUPPORT — Soportes generales ausentes

El poder general requiere contrato con fecha de escritura y notarios, y nota de
vigencia con notarios. El contrato especial no satisface esas condiciones.

```python
def invalid_support():
    return replace(event, nature=MandateNature.GENERAL)
```

### ERR-DV — DV incorrecto

Los modelos de mandato comprueban el DV de NIT sin corregir el dato.

```python
def invalid_digit():
    return replace(mandator, verification_digit="9")
```

### ERR-PT — Canal prohibido

```python
def invalid_channel():
    return MandateScope(
        powers=((MandatePower.ACKNOWLEDGEMENT, MandateChannel.TECHNOLOGY_PROVIDER),)
    )
```

### ERR-COUNT — Factura 21

```python
def invalid_count():
    return replace(event, document_references=(invoice_one,) * 21)
```

### ERR-TERMINATION — Declaraciones incompatibles

442 exige `no_pending_acts=True` y no admite ratificación. 443 no admite ninguna
constancia ni ratificación. 441 permite ratificar, pero no `no_pending_acts`,
incluso si se intentara aportar `False`. La receta muestra una ratificación
incompatible con 443; la tabla de condiciones es obligatoria en las tres operaciones.

```python
def invalid_termination():
    return MandateTerminationEvent(
        header=RadianEventHeader(
            event_number="TERMINACION-INVALIDA",
            issue_date=date(2026, 10, 23),
            issue_time=time(11, 0),
        ),
        operation_type=RadianOperationType.MANDATE_REJECTION,
        mandator_party=mandator,
        mandatee_party=mandatee_legal,
        reference=original_mandate,
        declaration=MandateTerminationDeclaration(
            effective_date=date(2026, 10, 24), ratify_acts=True
        ),
    )
```
