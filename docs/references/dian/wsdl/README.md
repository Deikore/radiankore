# Contratos SOAP de DIAN

Copias públicas descargadas por el usuario e incorporadas el 2026-10-20. Las
copias locales no se incluyen en wheel ni sdist.
El cliente no carga WSDL ni descarga esquemas durante la ejecución.

| Ambiente | Archivo | URL de origen | Tamaño |
| --- | --- | --- | --- |
| Producción | [production.wsdl](production.wsdl) | [singleWsdl](https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?singleWsdl) | 93 418 bytes |
| Habilitación | [habilitation.wsdl](habilitation.wsdl) | [singleWsdl](https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?singleWsdl) | 61 727 bytes |

SHA-256:

```text
bdfc77b42bc76dc44319ee11d425ae0bd0fe15f0fc6ce941c93c8a236bea6734  production.wsdl
da576f42d725b3c8626bc146c26d6eb4c510d849c160290eb04dae0340f5d7b8  habilitation.wsdl
```

La revisión del 2026-10-21 registra la copia local actual de producción. El
inventario inicial indicaba 61 719 bytes y SHA-256
`f92a7e6ec77b21ad6a91cf38ceb54fed22ec754140b417506dfb53d6da0a53f4`.
No se modificó ningún WSDL durante esta revisión. La estructura de los esquemas
actuales de ambos ambientes se comparó ignorando espacios de formato y coincide.

Ambos documentos tienen raíz `wsdl:definitions`, incluyen todos los namespaces
importados y carecen de referencias externas por `schemaLocation` o `location`.
Sus esquemas coinciden; cada servicio publica el endpoint de su ambiente.

## GetAcquirer

- SOAP 1.2, document/literal, binding `WSHttpBinding_IWcfDianCustomerServices`.
- Acción: `http://wcf.dian.colombia/IWcfDianCustomerServices/GetAcquirer`.
- Cuerpo: `GetAcquirer`, con `identificationType` e `identificationNumber` en ese
  orden; ambos `xs:string`, opcionales y nillables en el WSDL. La API de la librería
  exige ambos para formular una consulta con identificación.
- Respuesta: `GetAcquirerResponse/GetAcquirerResult`, en `http://wcf.dian.colombia`.
  El resultado es opcional y nillable.
- Tipo: `AdquirienteResponse`, en
  `http://schemas.datacontract.org/2004/07/Gosocket.Dian.Services.Utils.Common`.
- Campos en secuencia: `Message`, `ReceiverEmail`, `ReceiverName`, `StatusCode`;
  todos `xs:string`, opcionales y nillables.
- No se definen enumeraciones ni significados para los valores de `StatusCode`.
- Comparte el binding y su política de seguridad con `GetStatusEvent`: HTTPS,
  WS-Addressing, timestamp y token X.509 con firma del encabezado `To`.

La presencia de una operación en el WSDL no demuestra su aceptación con un
certificado específico. La validación real requiere una consulta autorizada;
las pruebas automáticas utilizan exclusivamente datos sintéticos.

## GetDocumentInfo

Comparte SOAP 1.2, binding, seguridad y destino por ambiente con las otras consultas.
Acción: `http://wcf.dian.colombia/IWcfDianCustomerServices/GetDocumentInfo`.
El cuerpo contiene `uuid` (`xs:string`, opcional y nillable); la librería exige
texto no vacío sin imponer un formato de identificador.

`GetDocumentInfoResponse/GetDocumentInfoResult` es opcional y nillable. Su tipo
`DocumentInfoResponse` pertenece a
`http://schemas.datacontract.org/2004/07/DocumentInfoResponse` y contiene:

| Campo | Tipo |
| --- | --- |
| `CompressedDocumentInfo` | `xs:string` |
| `DocumentInfo` | `ArrayOfDocumento` |
| `StatusCode`, `StatusDescription` | `xs:string` |

Estos cuatro campos son opcionales y nillables. No se documentan significados de
estado ni algoritmo de compresión; conserva el texto comprimido sin interpretarlo.

`Documento` contiene código, descripción, tipo, UUID, emisor, receptor, numeración,
tenedor, totales, estados, eventos, referencias, notas (`DocumentTags`) y validaciones.
Las estructuras reutilizadas son `Entidad`, `NumeroDocumento`, `LegitimoTenedor`,
`TotalEImpuestos`, `Evento`, `ReferenciaDocumento`, `Nota`, `ConceptoCorreccion` y
`ValidacionDoc`. Cada tipo usa su namespace `http://schemas.datacontract.org/2004/07/`
seguido del nombre del tipo; respeta esta separación al leer los hijos anidados.

- Las fechas son `xs:string`; el contrato no define formato ni zona horaria.
  La librería exige `YYYY-MM-DD` según la respuesta observada y devuelve
  `datetime.date | None`. Otros formatos o fechas imposibles generan
  `DianResponseError`; los campos ausentes, nulos o vacíos producen `None`.
- `Iva` y `Total` son `xs:double` opcionales, no nillables. Se leen como Decimal.
- `IsNotification` e `IsValida` son `xs:boolean` opcionales, no nillables.
- `Estado` usa `Arrays/ArrayOfKeyValueOfintstring`: entradas no nillables,
  `Key` obligatorio `xs:int` y `Value` obligatorio `xs:string` nillable.
- Las otras colecciones permiten elementos nulos. Se conserva el orden y las
  entradas repetidas, sin convertir estados a diccionario.
- Los códigos XML son cadenas. Vincular `Entidad/TipoDoc` y `Evento/Codigo` con
  catálogos estrictos es una decisión explícita de la librería; los demás códigos
  se conservan como texto sin inventar enumeraciones.

Las pruebas usan un XML sintético completo. La aceptación del certificado y el
contenido real de esta operación requieren validación autorizada contra DIAN.

Una respuesta real aportada por el usuario contiene `Entidad/TipoDoc` como `Nit`,
aunque el catálogo de identificación usa `31`. El parser de GetDocumentInfo acepta
ese nombre sin distinguir mayúsculas y lo convierte a `IdentificationType.NIT`;
conserva el soporte de códigos numéricos y rechaza nombres desconocidos. El WSDL
solo declara `xs:string` y no garantiza que se devuelvan códigos numéricos.

## GetReferenceNotes

La solicitud, respuesta y tipo `DianResponse` coinciden en los WSDL de producción
y habilitación. La operación comparte binding SOAP 1.2, política de seguridad y
selección de ambiente con las demás consultas.

- Acción: `http://wcf.dian.colombia/IWcfDianCustomerServices/GetReferenceNotes`.
- Solicitud: `GetReferenceNotes/trackId`, `xs:string`, opcional y nillable en el
  WSDL. La librería exige texto no vacío.
- Respuesta: `GetReferenceNotesResponse/GetReferenceNotesResult`, opcional y nillable,
  de tipo `DianResponse`, namespace
  `http://schemas.datacontract.org/2004/07/DianResponse`.

| Elemento | Tipo XSD | Campo Python |
| --- | --- | --- |
| `ErrorMessage` | `Arrays/ArrayOfstring`, nillable | `messages` |
| `IsValid` | `xs:boolean`, no nillable | `is_valid` |
| `StatusCode` | `xs:string`, nillable | `status_code` |
| `StatusDescription` | `xs:string`, nillable | `status_description` |
| `StatusMessage` | `xs:string`, nillable | `status_message` |
| `XmlBase64Bytes` | `xs:base64Binary`, nillable | `xml_base64_bytes` |
| `XmlBytes` | `xs:base64Binary`, nillable | `xml_bytes` |
| `XmlDocumentKey` | `xs:string`, nillable | `document_key` |
| `XmlFileName` | `xs:string`, nillable | `file_name` |

Todos son opcionales (`minOccurs="0"`). `ArrayOfstring` permite elementos `string`
nulos; la librería conserva orden, nulos, vacíos y repeticiones. Ambos campos
binarios se decodifican por separado, conservando `None` frente a `b""`, sin fallback.
El WSDL no describe su formato interno ni los significados de estados. La muestra
aportada por el usuario contiene UBL ApplicationResponse en XmlBase64Bytes; se
interpreta automáticamente como notas, conservando los bytes, incluso con
IsValid=false. XmlBytes no se interpreta ni reemplaza al otro campo. No hay
descompresión. DocumentNote pertenece al contrato distinto de GetDocumentInfo.

Según los XSD UBL locales, ApplicationResponse admite DocumentResponse 0..n.
Cada uno requiere Response 1..1 y DocumentReference 1..n; cada referencia requiere
ID 1..1 y permite UUID 0..1. IssuerParty y RecipientParty son opcionales.
LineResponse admite 0..n, con LineReference 1..1 (LineID obligatorio) y Response
1..n. Por ello se modelan todas las notas, referencias y respuestas por línea,
sin ordenar ni deduplicar. Los campos aún no modelados permanecen accesibles en
los bytes originales; no se realiza validación integral XSD ni de firma recibida.

El modelo usa ReferenceNote, NoteDocumentReference, NoteLineResponse y NoteResponse.
`ReferenceNote.code` se convierte a `DocumentType.CREDIT_NOTE` o
`DocumentType.DEBIT_NOTE`, o `None` si falta. Otros códigos generan
`DianResponseError`. Es una política de la librería sobre el código principal;
los motivos de línea (`NoteResponse.code`) siguen siendo texto, sin usar EventType.
Fechas efectivas YYYY-MM-DD se convierten a date y horas a time en UTC-05:00,
ajustando el día cuando sea necesario. Payload ausente/nulo/vacío produce notes=();
uno no vacío malformado, con DTD o raíz incorrecta genera DianResponseError.

Las pruebas son sintéticas; el contenido real y la aceptación del certificado
requieren validación autorizada contra DIAN.

## GetXmlByDocumentKey

Los contratos de solicitud y respuesta coinciden en ambos ambientes. Comparte
binding SOAP 1.2, firma, política de seguridad y selección de endpoint.

- Acción: `http://wcf.dian.colombia/IWcfDianCustomerServices/GetXmlByDocumentKey`.
- Solicitud: `GetXmlByDocumentKey/trackId`, `xs:string`, opcional y nillable en el
  WSDL. La API exige una clave de documento no vacía.
- Resultado: `GetXmlByDocumentKeyResponse/GetXmlByDocumentKeyResult`, opcional y
  nillable, de tipo `EventResponse`, namespace
  `http://schemas.datacontract.org/2004/07/EventResponse`.

| Elemento | Tipo XSD | Campo Python |
| --- | --- | --- |
| `Code` | `xs:string` | `status_code` |
| `Message` | `xs:string` | `message` |
| `ValidationDate` | `xs:string` | `validation_date` |
| `XmlBytesBase64` | `xs:string` | `document_xml`, bytes decodificados |

Los cuatro elementos son opcionales y nillables. No se especifican formatos de
fecha ni significados para códigos de negocio. La librería acepta provisionalmente
fechas ISO como date y timestamps ISO como datetime, conservando hora y zona sin
normalización. Valores ausentes, nulos o vacíos producen None; fechas inválidas
producen DianResponseError conservando ValueError.

Por indicación del usuario, XmlBytesBase64 se interpreta como Base64 del documento,
aunque el XSD solo declara string. Se reutiliza la decodificación estricta y se
conservan los bytes exactos, sin convertirlos a texto ni reformatear, descomprimir,
exigir tipo raíz o verificar la firma. Campo ausente/nulo produce None; presente
vacío produce b"". El contenido se excluye de repr. Un resultado ausente/nulo
devuelve None; uno vacío XmlDocumentResult().

Las pruebas usan datos sintéticos. Quedan pendientes una muestra real que confirme
ValidationDate y una consulta autorizada que compruebe aceptación por DIAN.

## GetStatus

Los contratos de solicitud, respuesta y DianResponse coinciden en producción y
habilitación. La operación consulta el resultado de validación del documento;
GetStatusEvent consulta los eventos asociados a una factura. Comparten el tipo
exterior DianResponse, pero el propósito y el contenido no son intercambiables.

- Acción: `http://wcf.dian.colombia/IWcfDianCustomerServices/GetStatus`.
- Solicitud: `GetStatus/trackId`, `xs:string`, opcional y nillable en el WSDL;
  la librería exige texto no vacío, sin imponer formato hexadecimal ni UUID.
- Resultado: `GetStatusResponse/GetStatusResult`, opcional y nillable, de tipo
  `DianResponse`, namespace `http://schemas.datacontract.org/2004/07/DianResponse`.

DocumentStatusResult representa los nueve campos del contrato: IsValid, StatusCode,
StatusDescription, StatusMessage, ErrorMessage, XmlDocumentKey, XmlFileName,
XmlBase64Bytes y XmlBytes. Todos son opcionales; IsValid no es nillable y los demás
sí. ErrorMessage contiene ArrayOfstring con elementos nulos permitidos.

La librería conserva mensajes en orden, con vacíos, nulos y repeticiones. Ambos
payloads se decodifican por separado, sin fallback ni análisis de XML interno,
reformateo o descompresión, y se excluyen de repr. Ausente/nulo produce None;
presente vacío produce b"". IsValid=false y códigos desconocidos no generan
excepciones ni descartan contenido. Los errores técnicos preservan sus causas.
Un resultado ausente/nulo devuelve None; uno presente vacío DocumentStatusResult().

Los lectores comunes se comparten con GetReferenceNotes sin reutilizar sus modelos
ni cambiar los requisitos públicos de GetStatusEvent. No se realiza validación de
reglas internas, XSD o firma del payload. Las pruebas usan únicamente datos sintéticos;
la aceptación real del certificado requiere una consulta autorizada contra DIAN.

## GetExchangeEmails

Los contratos coinciden en ambos ambientes: SOAP 1.2, document/literal y la misma
política de seguridad del cliente. La solicitud `GetExchangeEmails` tiene una
secuencia vacía, sin parámetros. Acción:
`http://wcf.dian.colombia/IWcfDianCustomerServices/GetExchangeEmails`.

El resultado `GetExchangeEmailsResponse/GetExchangeEmailsResult` es opcional y
nillable. Su tipo `ExchangeEmailResponse` usa el namespace
`http://schemas.datacontract.org/2004/07/ExchangeEmailResponse`.

- `CsvBase64Bytes`, `Message`, `StatusCode`: `xs:string`, opcionales y nillables.
- `Success`: `xs:boolean`, opcional y no nillable.

El WSDL no especifica significado de códigos ni formato del contenido codificado.
El [comunicado DIAN del 1 de noviembre de 2024](https://www.dian.gov.co/Prensa/Paginas/NG-Optimizacion-del-metodo-GetExchangeEmails-del-Webservice.aspx)
anuncia que desde el 8 de noviembre se entrega una URL en Base64, válida por
10 segundos, para descargar un ZIP con el CSV. Se implementa ese comportamiento,
sin fallback al CSV histórico ni nombres fijos de columnas o archivos internos.
Se extrae en memoria el único miembro CSV y se lee como UTF-8 con `csv.DictReader`.
Los encabezados se usan como claves y los valores se conservan como texto.
La codificación UTF-8 es una política de la librería pendiente de confirmar con
una muestra real; no se escriben archivos al disco.

## GetNumberingRange

Los contratos de ambos ambientes coinciden: SOAP 1.2, document/literal, con la
misma firma y política de seguridad. Acción:
`http://wcf.dian.colombia/IWcfDianCustomerServices/GetNumberingRange`.
La solicitud contiene `accountCode`, `accountCodeT` y `softwareCode`, en ese orden,
como `xs:string`, opcionales y nillables. La API exige los tres para consultar.

`GetNumberingRangeResponse/GetNumberingRangeResult` es opcional y nillable. Su
tipo `NumberRangeResponseList`, namespace
`http://schemas.datacontract.org/2004/07/NumberRangeResponseList`, contiene
`OperationCode`, `OperationDescription` y `ResponseList`, opcionales y nillables.
Los códigos son cadenas de negocio, sin equivalencia con HTTPStatus.

`ResponseList` contiene `NumberRangeResponse` repetible y nillable, namespace
`http://schemas.datacontract.org/2004/07/NumberRangeResponse`. Sus ocho elementos
son opcionales: `ResolutionNumber`, `ResolutionDate`, `Prefix`, `ValidDateFrom`,
`ValidDateTo` y `TechnicalKey` son cadenas nillables; `FromNumber` y `ToNumber`
son `xs:long` no nillables. No se implementan los campos históricos adicionales
que aparecen en la tabla resumida del anexo.

El [anexo FE 1.9, sección 7.15, páginas 356–360](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf)
explica los NIT sin dígito de verificación y el identificador del software; su
ejemplo SOAP usa fechas `YYYY-MM-DD`, leídas como fechas nativas. Documenta
`100` para éxito, `301`, `302`, `303`, `401` y `500` para resultados de negocio.
Declara disponibilidad únicamente en producción. La librería respeta el ambiente
seleccionado, sin fallback, y conserva estados desconocidos, orden y nulos.
