# Consultar información de un documento

`GetDocumentInfo` devuelve documentos estructurados, con participantes, numeración,
totales, estados, eventos, referencias, notas y validaciones. Reutiliza el mismo
cliente y ambiente:

```python
from http import HTTPStatus

from radiankore import DianClient
from radiankore.models.responses import DocumentInfoResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
result: DocumentInfoResult | None = client.get_document_info("UUID-DEL-DOCUMENTO")
if result is not None:
    if result.status_code is HTTPStatus.NOT_FOUND:
        print("Documento no encontrado")
    if result.status_code is not None:
        print(result.status_code.value, result.status_code.phrase)
    print(result.status_description)
    for document in result.documents:
        if document is None:
            continue
        print(document.uuid, document.description)
        if document.number is not None and document.number.issue_date is not None:
            print(document.number.issue_date.isoformat())
        if document.totals is not None:
            print(document.totals.vat, document.totals.total)
        for validation in document.validations:
            if validation is not None:
                print(
                    validation.is_valid,
                    validation.is_notification,
                    validation.error_message,
                )
        for event in document.events:
            if event is not None:
                print(event.code, event.description)
```

`uuid` debe ser texto no vacío; se recortan espacios exteriores sin imponer un
formato UUID o hexadecimal. Un resultado ausente o nulo devuelve `None`; uno vacío
devuelve `DocumentInfoResult()`. Todos los documentos se obtienen mediante
`result.documents: tuple[DocumentInfo | None, ...]`.

El contenedor `DocumentInfo` ausente, nulo o vacío produce `documents=()`.
Cada `Documento` nulo se conserva como `None`; uno vacío produce `DocumentInfo()`.
Se conservan todas las entradas, su orden XML y sus repeticiones. No se elige un
único documento ni se filtra por el UUID consultado, porque DIAN puede devolver
varios documentos para la misma consulta.

`DocumentInfoResult.status_code` es `HTTPStatus | None`, de la biblioteca estándar
`http`. El campo SOAP `StatusCode` se recorta exteriormente y debe contener tres
dígitos ASCII correspondientes a un miembro de `HTTPStatus`: `"200"` se convierte
en `HTTPStatus.OK` y `"404"` en `HTTPStatus.NOT_FOUND`. Ausente, nulo o vacío vale
`None`; códigos desconocidos o formatos inválidos generan `DianResponseError`
con `ValueError` como causa. Al construir el modelo directamente, usa `HTTPStatus`
o `None`; cadenas, enteros y otros tipos generan `TypeError`.

Este código pertenece al SOAP y es independiente del estado HTTP de la petición:
HTTP 200 con `StatusCode=404` devuelve un resultado con `HTTPStatus.NOT_FOUND`,
mientras que una petición HTTP 404 sigue generando `DianTransportError`. No se
descartan documentos ni se generan excepciones por un estado estándar del SOAP.
Para migrar desde el campo de texto anterior, compara con `HTTPStatus.NOT_FOUND`
en lugar de `"404"`; `.value` devuelve el código entero cuando no sea `None`.

Los modelos están en `models/responses/document_info.py` y se exportan desde
`radiankore.models.responses`:

- `DocumentInfoResult` contiene estado, `documents` y `compressed_document_info`.
- `DocumentInfo` agrupa `DocumentParty`, `DocumentNumber`, `DocumentHolder`,
  `DocumentTotals`, `DocumentState`, `DocumentEvent`, `DocumentReference`,
  `DocumentNote` y `DocumentValidation`.
- `DocumentNote.correction` utiliza `DocumentCorrection`. Participantes, numeración,
  totales y validaciones comparten sus modelos en documentos, eventos y notas.

Las dataclasses son inmutables y usan argumentos por nombre. Los campos escalares
u objetos ausentes o nulos valen `None`; las colecciones son tuplas y conservan el
orden XML. Sus elementos nulos se conservan como `None` cuando el esquema lo permite.
`states` conserva entradas `DocumentState(key, value)`, incluidos códigos repetidos;
`key` es un entero de 32 bits obligatorio y `value` puede ser nulo.

Los importes se convierten directamente a `Decimal`, conservando precisión sin
pasar por `float`. El contrato `xs:double` admite notación científica, `INF`, `-INF`
y `NaN`; el consumidor debe decidir cómo tratar estos valores especiales.

`issue_date`, `signature_date`, `title_registration_date` y `DocumentReference.date`
son `datetime.date | None`. Se acepta exclusivamente `YYYY-MM-DD`, recortando
espacios exteriores. Campos ausentes, nulos o vacíos valen `None`; fechas imposibles,
formatos alternativos y timestamps generan `DianResponseError` con `ValueError`
como causa. Una fecha no incluye hora ni zona horaria. Para obtener texto, usa
`.isoformat()`. Esta política de formato se basa en la respuesta DIAN observada;
el WSDL declara `xs:string` sin especificar formato.

`TotalEImpuestos` corresponde a `DocumentTotals` y sus campos `Iva`/`Total` a
`vat`/`total`. El contenedor `ValidacionesDoc` corresponde a la tupla `validations`:
cada `ValidacionDoc` es un `DocumentValidation` con `is_notification`, `is_valid`,
`error_message`, `name` y `status`. Totales y validaciones están presentes en
documentos y notas; los eventos también contienen validaciones.

`DocumentEvent` usa
`EventType` y `DocumentParty` usa `IdentificationType`. En esta operación,
`TipoDoc` admite códigos numéricos y el texto `Nit` observado en respuestas DIAN
(sin distinguir mayúsculas); se convierte a `IdentificationType.NIT` (`"31"`).
Los demás valores desconocidos generan `DianResponseError`. Esta conversión es
local al parser: los modelos siguen exigiendo enums. `DocumentEvent` es un contrato
distinto de `InvoiceEvent`.

`compressed_document_info` conserva exactamente el texto recibido, incluidos espacios
y cadenas vacías, y se excluye de `repr`. No se decodifica ni sustituye `documents`:
el WSDL no especifica el formato de compresión. La respuesta estructurada se procesa
sin depender de ese campo. Consulte el [contrato local](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md#getdocumentinfo).

## Tipos de documento

`DocumentInfo.document_type_id` y `DocumentReference.document_type_id` usan
`DocumentType | None`, exportado desde `radiankore.catalogs`. Sus códigos canónicos
son `01`, `02`, `03`, `04`, `91`, `92` y `96`; consulta el [catálogo](../catalogs.md).
El parser admite además `1`, `2`, `3` y `4`, que normaliza a `01`–`04`, y recorta
espacios exteriores. Valores ausentes, nulos o vacíos producen `None`; códigos
no conocidos generan `DianResponseError` con `ValueError` como causa.
Los modelos aceptan únicamente `DocumentType` o `None`; otros tipos generan
`TypeError`. `document_type_name` conserva el texto recibido, independiente de
la etiqueta del catálogo. El parser no deduce el tipo a partir del nombre.

## Motivos de notas crédito y débito

`DocumentInfo.document_code` tiene tipo
`CreditNoteReason | DebitNoteReason | str | None`. Para
`DocumentType.CREDIT_NOTE` (`91`) se convierte a `CreditNoteReason`; para
`DocumentType.DEBIT_NOTE` (`92`), a `DebitNoteReason`.
Los códigos coincidentes pueden significar cosas distintas: `2` representa
anulación de factura en crédito y gastos por cobrar en débito.

```python
from radiankore.catalogs import CreditNoteReason, DocumentType
from radiankore.models.responses import DocumentInfo

document = DocumentInfo(
    document_type_id=DocumentType.CREDIT_NOTE,
    document_code=CreditNoteReason.INVOICE_CANCELLATION,
)
if document.document_code is CreditNoteReason.INVOICE_CANCELLATION:
    print(document.document_code.value, document.document_code.label)
```

El parser resuelve primero `DocumentTypeId`, independientemente del orden XML.
Recorta espacios exteriores en `DocumentCode`; ausente, nulo o vacío produce
`None`. Para notas, códigos desconocidos o formatos no canónicos como `01`
generan `DianResponseError` con `ValueError` como causa. No se deducen motivos
a partir del nombre, la descripción ni el estado HTTP.

Para otros tipos de documento, o sin `DocumentTypeId`, el código conserva texto
sin interpretar. Al construir notas directamente, pasa el enum correspondiente
o `None`: cadenas, enteros y enums de otro catálogo generan `TypeError`.
En los demás documentos, usa texto o `None`, sin enums de motivos.

Las tablas oficiales 13.2.4 y 13.2.5 describen conceptos de corrección de UBL.
Su aplicación a `DocumentCode` se basa en la observación aportada por el
mantenedor; el WSDL declara una cadena sin enumeración. Consulte los
[catálogos y sus fuentes](../catalogs.md#motivos-de-notas).
`description` mantiene el texto SOAP y no se sustituye por `.label`.
`DocumentCorrection.code`, los códigos de `get_reference_notes` y `states`
conservan sus contratos actuales.

## Estados del documento

`states` sigue siendo una tupla de pares `DocumentState(key, value)`. El WSDL
solo define un entero y un texto; no se encontró un catálogo oficial que vincule
las claves numéricas con sus significados. Se conservan orden, duplicados y
claves no conocidas sin traducir ni sustituir el texto recibido.

La respuesta real aportada por el mantenedor mostró estas correspondencias:

| Clave observada | Texto recibido |
| --- | --- |
| `2` | Título Valor |
| `7` | Disponibilizada |
| `8` | Endosada |

Estas observaciones no constituyen un catálogo oficial exhaustivo. No se usan
como enum ni se confunden con `EventType` o con `HTTPStatus`.

## Migración

Itera `result.documents`, comprobando cada entrada porque puede ser `None`.
Compara los tipos con `DocumentType.SALES_INVOICE` o `DocumentType.CREDIT_NOTE`;
usa `.value` para obtener el código canónico y `.label` para su etiqueta en español.
Para motivos de notas, sustituye comparaciones de `document_code` con cadenas
por miembros de `CreditNoteReason` o `DebitNoteReason`, según el tipo. Ambos enums
son `StrEnum` y pueden compartir valores de texto; compara con `is` para
distinguir el motivo y su catálogo.
