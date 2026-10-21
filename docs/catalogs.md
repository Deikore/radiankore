# Catálogos DIAN

`radiankore.catalogs` exporta `DocumentType`, `IdentificationType`, `EventType`,
`CreditNoteReason` y `DebitNoteReason`, enums `StrEnum`
con códigos de texto en `.value` y etiquetas en español en `.label`. Puedes
iterarlos para mostrar las opciones disponibles:

```python
from radiankore.catalogs import EventType, IdentificationType
from radiankore.models.responses import EventParty, InvoiceEvent

for option in IdentificationType:
    print(option.value, option.label)

party = EventParty(identification_type=IdentificationType.NIT)
if party.identification_type is not None:
    print(party.identification_type.value, party.identification_type.label)

event = InvoiceEvent(
    id="EVENT-1",
    code=EventType.EXPRESS_ACCEPTANCE,
    description="Synthetic XML description",
)
if event.code is EventType.EXPRESS_ACCEPTANCE:
    print(event.code.value, event.code.label)
```

`identification_type` tiene tipo `IdentificationType | None` y `code` tiene tipo
`EventType | None`. Ambos campos contienen directamente miembros del enum o
`None` si faltan o están vacíos en el XML. Al construir las dataclasses, pasa el
enum correspondiente o `None`; una cadena u otro tipo genera `TypeError`.

El parser quita espacios exteriores y utiliza los constructores estrictos de los
enums. Un código desconocido genera `DianResponseError`; no se devuelve como texto
ni se sustituye por `None`. El valor original de cada código conocido está en
`.value`, incluidos sus ceros iniciales. La etiqueta del catálogo es independiente
de `event.description`, que conserva las descripciones del XML. Los miembros
`StrEnum` se serializan como códigos de texto mediante `json.dumps()`.

Para resolver códigos fuera del parser, `IdentificationType.from_code()` y
`EventType.from_code()` son utilidades opcionales: devuelven el enum o `None` ante
valores ausentes, vacíos o desconocidos. No normalizan códigos: `"30"` y `" 030 "`
no se convierten en `"030"`. Los constructores directos, como
`IdentificationType("31")`, generan `ValueError` ante códigos desconocidos.

El catálogo de identificación incluye los 11 códigos de `TipoIdFiscal-2.1.gc`
y el código `48` (PPT) de la guía de integración de `GetAcquirer`.
El de eventos combina `02`, `04` y `030`–`051` de las fuentes documentadas en el
[índice de referencias](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/README.md#catálogos-de-códigos).
Son catálogos de referencia versionados, sin descargas ni lectura de documentos
durante la ejecución. No se presume que incluyan futuros códigos de DIAN.
La etiqueta `NUIP` no incluye la llamada de nota del anexo: el código `91` está
reservado allí para el adquiriente. Estos catálogos no validan roles ni números
de identificación.

## Tipos de documento

`DocumentType` se aplica a `DocumentInfo.document_type_id` y
`DocumentReference.document_type_id` en `GetDocumentInfo`:

| Miembro | Código | Significado |
| --- | --- | --- |
| `SALES_INVOICE` | `01` | Factura electrónica de venta |
| `EXPORT_INVOICE` | `02` | Factura electrónica de venta de exportación |
| `PAPER_INVOICE_TRANSMISSION` | `03` | Instrumento electrónico de transmisión, tipo 03 |
| `DIAN_CONTINGENCY_INVOICE` | `04` | Factura electrónica de venta, tipo 04 / contingencia DIAN |
| `CREDIT_NOTE` | `91` | Nota crédito |
| `DEBIT_NOTE` | `92` | Nota débito |
| `APPLICATION_RESPONSE` | `96` | Eventos ApplicationResponse |

La tabla 13.1.3 de la caja de herramientas FE 1.9, edición 2026, aporta los siete
códigos y sus etiquetas. El genericode relacionado solo contiene seis: omite `96`.
Consulta las [copias y procedencia](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/invoicing/1.9/README.md).

```python
from radiankore.catalogs import DocumentType
from radiankore.models.responses import DocumentInfo

document = DocumentInfo(document_type_id=DocumentType.SALES_INVOICE)
if document.document_type_id is DocumentType.SALES_INVOICE:
    print(document.document_type_id.value, document.document_type_id.label)
```

El parser normaliza únicamente `1`–`4` a `01`–`04`. Los modelos exigen miembros
del enum o `None`. `DocumentType.from_code()` resuelve solo códigos canónicos:
devuelve `None` para `"1"`, `" 01 "`, valores desconocidos y ausentes. El catálogo
no valida reglas de emisión ni se aplica a `DocumentCode` o a los estados.

## Motivos de notas

Los conceptos de corrección proceden de las tablas oficiales 13.2.4 y 13.2.5
de la caja de herramientas FE 1.9, edición 2026. Se conservan copias originales,
procedencia y hashes en el [índice de referencias](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/invoicing/1.9/README.md).

| `CreditNoteReason` | Código | Motivo |
| --- | --- | --- |
| `PARTIAL_RETURN_OR_SERVICE_REJECTION` | `1` | Devolución parcial de bienes o no aceptación parcial del servicio |
| `INVOICE_CANCELLATION` | `2` | Anulación de factura electrónica |
| `DISCOUNT_OR_REDUCTION` | `3` | Rebaja o descuento parcial o total |
| `PRICE_ADJUSTMENT` | `4` | Ajuste de precio |
| `PROMPT_PAYMENT_DISCOUNT` | `5` | Descuento comercial por pronto pago |
| `VOLUME_DISCOUNT` | `6` | Descuento comercial por volumen de ventas |

| `DebitNoteReason` | Código | Motivo |
| --- | --- | --- |
| `INTEREST` | `1` | Intereses |
| `RECEIVABLE_EXPENSES` | `2` | Gastos por cobrar |
| `VALUE_CHANGE` | `3` | Cambio del valor |
| `OTHER` | `4` | Otros |

`DocumentInfo.document_code` contiene el enum elegido por `document_type_id`
para notas, o texto para otros documentos. `.label` conserva la descripción
oficial recortando espacios exteriores. `.from_code()` resuelve únicamente
códigos exactos; devuelve `None` para valores desconocidos, ausentes, `"01"`
o `" 1 "`. El parser recorta espacios antes de convertir y rechaza códigos
desconocidos para notas. El modelo exige un enum del catálogo correspondiente.

Estos enums no se aplican a `DocumentCorrection.code` ni a las respuestas de
`get_reference_notes`. Los códigos se superponen: usa `is` al comparar miembros
para distinguir crédito de débito, además de comprobar el tipo del documento.
