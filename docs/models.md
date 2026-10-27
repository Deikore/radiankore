# Modelos públicos

Los modelos de eventos están en `src/radiankore/models/responses/invoice_events.py`
y se importan desde `radiankore.models.responses`:

- `InvoiceEventsResult`: estado DIAN, `messages`, `document_key`, `file_name`,
  tupla `events` y `application_response_xml` decodificado como `bytes | None`.
- `InvoiceEvent`: `id`, `code`, `description`, `reference_id`, `date`, `time`,
  `uuid`, `issuer` y `recipient`.
- `EventParty`: `tax_number`, `name`, `verification_digit`, `identification_type`
  e `identification_type_raw`.

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

## Índice de resultados por operación

Todos se importan desde `radiankore.models.responses`. Los contratos completos
se encuentran en las guías de cada operación, con opcionalidad y origen XML:

| Consulte o envío | Modelos | Contrato |
| --- | --- | --- |
| Eventos | `InvoiceEventsResult`, `InvoiceEvent`, `EventParty` | [Eventos](operations/events.md) |
| Numeración | `NumberingRangeResult`, `NumberingRange` | [Rangos](operations/numbering-range.md) |
| Correos | `ExchangeEmailsResult` | [Directorio](operations/exchange-emails.md) |
| Validación | `DocumentStatusResult` | [Estado](operations/status.md) |
| Adquiriente | `AcquirerResult` | [Adquirientes](operations/acquirer.md) |
| Información del documento | `DocumentInfoResult`, `DocumentInfo`, `DocumentNumber`, `DocumentParty`, `DocumentHolder`, `DocumentReference`, `DocumentNote`, `DocumentEvent`, `DocumentCorrection`, `DocumentState`, `DocumentTotals`, `DocumentValidation` | [Información](operations/document-info.md) |
| Notas referenciadas | `ReferenceNotesResult`, `ReferenceNote`, `NoteDocumentReference`, `NoteLineResponse`, `NoteResponse` | [Notas](operations/reference-notes.md) |
| XML original | `XmlDocumentResult` | [XML](operations/xml-document.md) |
| Emisión de eventos | `SendEventResult` | [Envío](operations/radian-emission.md) |

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
| `identification_type` | `PartyTaxScheme/CompanyID/@schemeName` | Enum reconocido o `None` |
| `identification_type_raw` | `PartyTaxScheme/CompanyID/@schemeName` | Texto original o `None` |

Dentro de `DocumentResponse`, `Response` es obligatorio (`1..1`) y
`DocumentReference` es obligatorio y repetible (`1..n`). El modelo representa la
primera referencia: de ella obtiene tanto `id` como `uuid`. El parser genera
`DianResponseError` si falta `Response`, `DocumentReference` o un `ID` no vacío.

`PartyTaxScheme` es opcional y repetible (`0..n`) dentro de cada participante.
Se lee el primer `CompanyID` de estos esquemas y sus atributos de identificación;
para `name` se lee el primer `RegistrationName` disponible. Un participante
presente se conserva aunque falte su identificación. Los atributos opcionales
vacíos se representan con `None`; se quitan los espacios exteriores y se conservan
los ceros iniciales. Para tipos de identificación, el campo `identification_type_raw`
conserva el texto original antes de normalizarlo, incluidos los espacios exteriores.
`identification_type` reconoce códigos y etiquetas oficiales, normalizando
mayúsculas, tildes, Unicode y espacios; un valor desconocido queda solo en el campo
raw y el enum vale `None`. Si falta el dato, es nulo o contiene solo espacios,
ambos campos valen `None`. Estas reglas también se aplican a `DocumentParty` y a
las notas asociadas. Los dos modelos mantienen sus campos tipados e inmutables.

`code` se convierte a `EventType`; un código de evento desconocido sigue generando
`DianResponseError` con el `ValueError` original como causa. No se calcula ni valida
el dígito.

Estas reglas cubren los campos representados por los modelos; el parser no realiza
validación integral contra XSD ni valida las reglas de emisión RADIAN.

`is_valid=False` representa el resultado de negocio de DIAN, no una excepción.
Los mensajes pueden existir con `is_valid=True`. Un payload ausente o nulo deja
`events=()` y conserva el estado; XML o Base64 inválidos nunca se ocultan como una
lista vacía. El XML guardado permite consultar datos UBL aún no modelados.

## Directorio de correos

`ExchangeEmailsResult` conserva `success`, `status_code` y `message` de SOAP,
la URL temporal en `download_url` y los registros en `csv`, una tupla de diccionarios leídos con `csv.DictReader`.
Ambos campos de contenido se excluyen de `repr`. Consulte el
[contrato de GetExchangeEmails](operations/exchange-emails.md).

## Rangos de numeración

`NumberingRangeResult` conserva los códigos de negocio como texto y todos los
rangos en una tupla, incluyendo orden, duplicados y entradas nulas.
`NumberingRange` contiene la resolución, prefijo, límites enteros, fechas nativas
y clave técnica excluida de `repr`. Consulte el
[contrato de GetNumberingRange](operations/numbering-range.md).

## Mandato y contratos compartidos

El [mandato 043](operations/mandate.md) usa `MandateEvent` y sus componentes de
participantes, facultades, vigencia y adjuntos. Se importa desde
`radiankore.models.events` junto con `PreparedRadianEvent` y `RadianSoftware`.
La guía documenta sus campos y variantes. `RadianSoftware.pin` y los bytes de
los artefactos preparados se excluyen de `repr`.

Las [entradas RADIAN por familia](operations/radian-emission.md#modelos-y-variantes)
son quince modelos, incluidos factura y mandato, unidos por `RadianEvent`;
sus componentes se enumeran abajo.
Las respuestas de envío usan `SendEventResult`, con estado, mensajes y bytes
originales, según [la guía de envío](operations/mandate.md).

## Entradas de emisión 030–034

Importa desde `radiankore.models.events`:

| Modelo | Campos |
| --- | --- |
| `InvoiceResponseEvent` | `code`, `event_number`, `issue_date`, `issue_time`, `sender_party`, `document_reference`; opcionales `receiver_party`, `issuer_person`, `claim_reason`, `notes=()` |
| `InvoiceEventParty` | `name`, `tax_number`, `identification_type`, `organization_type`; `verification_digit=None`, `tax_scheme=PartyTaxScheme.VAT` |
| `InvoiceEventPerson` | `identification_number`, `identification_type`, `first_name`, `family_name`; `verification_digit=None`, `job_title=None`, `organization_department=None` |
| `InvoiceEventDocumentReference` | `document_number`, `uuid`; `document_type=DocumentType.SALES_INVOICE` |

Son dataclasses inmutables con slots y argumentos por nombre. Las entradas
comprueban enums y combinaciones antes de firmar; no procesan XML ni HTTP.
030/032 exigen persona receptora; 031 exige motivo; 034 exige notas y genera
DIAN como destinatario. La organización nunca se infiere del tipo de documento.
Las notas son tuplas, conservando orden y duplicados. Los binarios preparados
se excluyen de `repr`. Se reutilizan `RadianSoftware` y `SendEventResult`.
Los límites, declaraciones y correspondencias XML están en la
[guía de emisión](operations/invoice-emission.md).


## Componentes de emisión RADIAN

Los modelos nuevos se importan desde `radiankore.models.events`. Son inmutables,
con slots y argumentos por nombre, sin XML ni HTTP en sus validaciones.

| Modelo | Campos principales |
| --- | --- |
| `RadianEventHeader` | `event_number`, `issue_date`, `issue_time`, `notes=()` |
| `RadianParty` | `tax_number`, `identification_type`, `organization_type`, `name=None`, `verification_digit=None`, `tax_scheme=PartyTaxScheme.VAT` |
| `RadianPerson` | Identificación, nombres/apellidos; DV, cargo, nacionalidad y departamento opcionales |
| `RadianInvoiceReference` | `document_number`, `uuid`, `due_date=None`; tipo derivado `01` |
| `RadianEventReference` | `document_number`, `uuid`; tipo derivado `96` |
| `RadianParticipation` | `amount: Decimal`, `party=None`, `factor_type=None` |
| `RegistrationPaymentState` | `invoice_value`, `paid_value`, `remaining_value` |
| `NegotiationTerms` | `total_value`; `price=None`, `discount_rate=None`, `payment_means=None`, `currency=CurrencyCode.COP` |
| `GuaranteeCommitment` | `party`, `amount`; cero significa cobertura total, campo de hasta 25 caracteres |
| `GuaranteeBeneficiary` | `party`, `amount=None`; obligatorio para varios avalados |
| `EconomicRightsTransferTerms` | `transferred_value`, `price`, `discount_factor`, `payment_means`, `currency=CurrencyCode.COP` |
| `RadianPdfAttachment` | `filename`, `content_bytes`; bytes inmutables de PDF, ocultos en `repr` |
| `ProtestNotary` | `first_name`, `family_name`, `job_title`; no inventa identificación |
| `ProtestAct` | `notary_number`, `effective_date`, `notaries`, `attachment` |
| `PreparedRadianEvent` | `code`, `event_number`, `cude`, `environment`, `xml_bytes`, `zip_bytes` |

La posibilidad de omitir identidad/nombre se restringe al endoso en blanco;
los demás perfiles exigen participantes completos. El vencimiento se exige
por el modelo de evento donde corresponda. Las tuplas conservan orden y duplicados.
`RadianEvent` es la unión de quince modelos específicos para los eventos 030–051.
`InvoiceResponseEvent` recibe `code`; las demás familias lo derivan del modelo o
de la operación, y el mandato usa el código fijo 043.
`PreparedRadianEvent` valida códigos emitibles 030–051, conserva el ambiente y
exige bytes inmutables y un CUDE hexadecimal de 96 caracteres.
Los campos financieros conservan `Decimal`, y el artefacto excluye los binarios
de `repr`. La [guía](operations/radian-emission.md) documenta los campos de cada
familia y los errores de composición.
