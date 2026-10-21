# Modelos de respuesta

Los modelos de eventos están en `src/radiankore/models/responses/invoice_events.py`
y se importan desde `radiankore.models.responses`:

- `InvoiceEventsResult`: estado DIAN, `messages`, `document_key`, `file_name`,
  tupla `events` y `application_response_xml` decodificado como `bytes | None`.
- `InvoiceEvent`: `id`, `code`, `description`, `reference_id`, `date`, `time`,
  `uuid`, `issuer` y `recipient`.
- `EventParty`: `tax_number`, `name`, `verification_digit` e `identification_type`.

Son inmutables, tienen slots y se construyen por argumentos con nombre. Los campos
opcionales ausentes valen `None` y las colecciones son tuplas. El XML se excluye de
`repr`. Los eventos se ordenan por el valor numérico ascendente de `reference_id`
(`1`, `2`, `10`). Las referencias iguales conservan su orden en el XML; las ausentes
o no numéricas quedan al final, en su orden original. Se conservan las referencias
como texto y todos los eventos repetidos, sin deduplicarlos.
Fechas y horas utilizan los tipos de la biblioteca estándar. Las horas se
normalizan al desplazamiento de Colombia, UTC−05:00.

`description` es un único texto: une las descripciones XML no vacías con saltos de
línea y vale `""` si no hay ninguna. `uuid` e `id` provienen de
`DocumentReference/UUID` y `DocumentReference/ID`; `reference_id` es el
dato independiente de `Response/ReferenceID`. Los identificadores conservan su
texto, sin convertirse al tipo `uuid.UUID`.

`date` y `time` se leen de `Response/EffectiveDate` y `Response/EffectiveTime`
en la respuesta de consulta. Una hora con zona se convierte a UTC−05:00 y la fecha
se ajusta si la conversión cambia el día. Por ejemplo, `2026-01-15 02:30:00Z`
produce `date=2026-01-14` y `time=21:30:00-05:00`. Una hora sin zona se interpreta
como hora de Colombia, conservando su valor y añadiendo `-05:00`.

Si falta la fecha, se convierte solo la hora y `date` permanece en `None`. Si falta
la hora, `time` permanece en `None` y la fecha se conserva. No se sustituyen por
`IssueDate` o `IssueTime` del contenedor. Se utiliza un desplazamiento fijo UTC−05:00,
sin depender de la zona del equipo. El XML original se conserva sin modificaciones.

`messages` conserva los textos de
`ErrorMessage`, incluidas notificaciones de resultados válidos. `document_key`
y `file_name` conservan los valores de `XmlDocumentKey` y `XmlFileName` de DIAN.

## Obligatoriedad y correspondencia XML

Los campos modelados siguen las cardinalidades de los XSD de la caja de
herramientas. Estas cardinalidades no sustituyen las reglas de negocio RADIAN.

| Campo | Origen XML | Obligatoriedad XSD |
| --- | --- | --- |
| `id` | `DocumentReference/ID` | Obligatorio (`1..1`) en cada referencia |
| `code` | `Response/ResponseCode` | Opcional (`0..1`) |
| `uuid` | `DocumentReference/UUID` | Opcional (`0..1`) |
| `reference_id` | `Response/ReferenceID` | Opcional (`0..1`) |
| `date`, `time` | `Response/EffectiveDate`, `Response/EffectiveTime` | Opcionales (`0..1`) |
| `description` | `Response/Description` | Opcional y repetible (`0..n`) |
| `issuer`, `recipient` | `IssuerParty`, `RecipientParty` | Opcionales (`0..1`) |
| `tax_number` | `PartyTaxScheme/CompanyID` | Opcional (`0..1` por esquema) |
| `name` | `PartyTaxScheme/RegistrationName` | Opcional (`0..1` por esquema) |
| `verification_digit` | `PartyTaxScheme/CompanyID/@schemeID` | Opcional |
| `identification_type` | `PartyTaxScheme/CompanyID/@schemeName` | Opcional |

Dentro de `DocumentResponse`, `Response` es obligatorio (`1..1`) y
`DocumentReference` es obligatorio y repetible (`1..n`). El modelo representa la
primera referencia: de ella obtiene tanto `id` como `uuid`. El parser genera
`DianResponseError` si falta `Response`, `DocumentReference` o un `ID` no vacío.

`PartyTaxScheme` es opcional y repetible (`0..n`) dentro de cada participante.
Se lee el primer `CompanyID` de estos esquemas y sus atributos de identificación;
para `name` se lee el primer `RegistrationName` disponible. Un participante
presente se conserva aunque falte su identificación. Los atributos opcionales
vacíos se representan con `None`; se quitan los espacios exteriores y se conservan
los ceros iniciales. `identification_type` se convierte a `IdentificationType` y
`code` a `EventType`. Si un código no pertenece al catálogo correspondiente, el
parser genera `DianResponseError` con el `ValueError` original como causa. No se
calcula ni valida el dígito.

Estas reglas cubren los campos representados por los modelos; el parser no realiza
validación integral contra XSD ni valida las reglas de emisión RADIAN.

`is_valid=False` representa el resultado de negocio de DIAN, no una excepción.
Los mensajes pueden existir con `is_valid=True`. Un payload ausente o nulo deja
`events=()` y conserva el estado; XML o Base64 inválidos nunca se ocultan como una
lista vacía. El XML guardado permite consultar datos UBL aún no modelados.

## Directorio de correos

`ExchangeEmailsResult` conserva `success`, `status_code` y `message` de SOAP,
la URL temporal en `download_url` y los registros en `csv`, una tupla de diccionarios leídos con `csv.DictReader`.
Ambos campos de contenido se excluyen de `repr`. Consulta el
[contrato de GetExchangeEmails](operations/exchange-emails.md).

## Rangos de numeración

`NumberingRangeResult` conserva los códigos de negocio como texto y todos los
rangos en una tupla, incluyendo orden, duplicados y entradas nulas.
`NumberingRange` contiene la resolución, prefijo, límites enteros, fechas nativas
y clave técnica excluida de `repr`. Consulta el
[contrato de GetNumberingRange](operations/numbering-range.md).
