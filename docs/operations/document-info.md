# Consultar información de un documento

`GetDocumentInfo` devuelve documentos estructurados, con participantes, numeración,
totales, estados, eventos, referencias, notas y validaciones. Reutiliza el mismo
cliente y ambiente:

```python
from radiankore import DianClient
from radiankore.models.responses import DocumentInfoResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
result: DocumentInfoResult | None = client.get_document_info("UUID-DEL-DOCUMENTO")
if result is not None:
    print(result.status_code, result.status_description)
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
devuelve `DocumentInfoResult()`. Los códigos de estado no se interpretan como éxito,
error o ausencia de documento.

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
sin depender de ese campo. Consulta el [contrato local](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md#getdocumentinfo).
