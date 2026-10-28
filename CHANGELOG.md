# Historial de cambios

## 0.7.0 — 2026-10-28

- Añade `AsyncDianClient` con ocho consultas, preparación local y envío de eventos
  mediante HTTPX asíncrono, pools reutilizados y procesamiento local acotado.
- Añade `iter_queries` y `QueryResult` para streaming con backpressure y tareas
  fijas; conserva índices, duplicados, resultados ausentes y errores por elemento.
- Añade `AsyncDianLimiter` y `DianTimeouts`: límites por cliente y servicio,
  tasa compartida opcional, cooldown Retry-After y plazo total de operación.
- La cancelación conserva las plazas de trabajos nativos hasta su terminación;
  el cierre drena inicializadores, lotes, operaciones, pools y executor.
- Comparte validación, firma, preparación y clasificación HTTP/SOAP con la API
  síncrona, que conserva sus métodos y defaults. `DianTransportError` añade
  `retry_after: float | None`. No hay reintentos ni cambios implícitos de ambiente.
- Incorpora pruebas sintéticas, TCP/TLS local y benchmark reproducible de cinco
  alternativas; tests y CI no contactan DIAN.
- Añade un script y una guía para medir consultas reales de eventos por lotes,
  con informes agregados JSON/Markdown. Su ejecución contra DIAN es explícita;
  documenta mediciones aportadas por el usuario en producción: lotes de 100 CUFEs,
  tres repeticiones por configuración, medianas de 8,56 s con concurrencia 5,
  4,64 s con concurrencia 10 y 3,27 s con concurrencia 20, sin errores. Incluye
  percentiles y límites de la comparación observacional. Los ensayos de 500
  CUFEs obtuvieron medianas de 44,29, 21,51 y 11,42 s con concurrencias 5, 10 y
  20, sin errores; se conserva un p99 de 4,57 s observado con concurrencia 20.
- Amplía las mediciones reales a 1.000 CUFEs: medianas de 89,58, 44,78 y
  22,41 s con concurrencias 5, 10 y 20, respectivamente; 9.000 consultas sin
  excepciones, timeouts ni reintentos.
- Aplica el cooldown `Retry-After` al recibir las cabeceras HTTP, incluso si
  la lectura del cuerpo de error continúa pendiente. Corrige la clasificación
  de timeouts HTTPX en el comparador local.
- Presenta el cliente async como recorrido principal, con ejemplos verificables
  de consulta individual, lotes, puente síncrono y construcción y envío del acuse
  030. Destaca los nueve benchmarks reales y conserva sus datos agregados.

## 0.6.2 — 2026-10-27

- Un resolver compartido reconoce códigos y etiquetas oficiales de identificación
  en `get_document_info`, `get_invoice_events` y `get_reference_notes`, incluidos
  los participantes anidados en documentos, eventos, notas y referencias.
  Resuelve nombres como `Nit` y `Cédula de ciudadanía` normalizando mayúsculas,
  tildes, representación Unicode y espacios, sin coincidencias aproximadas.
- `DocumentParty` y `EventParty` añaden `identification_type_raw: str | None`.
  Este campo conserva el texto recibido antes de normalizarlo, incluidos los
  espacios exteriores, tanto para tipos conocidos como desconocidos.
- Los tipos desconocidos ya no provocan `DianResponseError`: la consulta conserva
  el valor en `identification_type_raw` y devuelve `identification_type=None`.
  Un dato ausente, nulo, vacío o compuesto solo por espacios deja ambos campos
  en `None`.
- Se mantiene `identification_type: IdentificationType | None` en las respuestas.
  El constructor del catálogo y los modelos de emisión conservan sus validaciones
  estrictas; los errores de XML y los demás códigos tipados mantienen su manejo.

### Migración desde 0.6.1

Si capturabas `DianResponseError` por tipos de identificación desconocidos,
comprueba ahora `party.identification_type is None` junto con
`party.identification_type_raw is not None`. Un enum vacío con texto raw indica
un valor recibido que todavía no pertenece al catálogo; ambos campos vacíos
indican un dato no informado. No asumas un código por defecto.

Los consumidores que serializan dataclasses recibirán el campo adicional
`identification_type_raw`; actualiza esquemas externos que rechacen campos nuevos.
La emisión sigue requiriendo un miembro válido de `IdentificationType`.

## 0.6.1 — 2026-10-27

- `DocumentInfo.document_code` conserva como texto los códigos de nota fuera
  de los catálogos FE 1.9 en lugar de generar `DianResponseError` al parsear:
  DIAN puede aceptarlos con notificaciones no bloqueantes y devolverlos en
  `get_document_info` (observado `7` «Otros»). Los códigos conocidos siguen
  resolviendo al enum según `document_type_id` y los modelos solo rechazan
  enums del catálogo contrario y valores que no sean texto.

### Migración desde 0.6.0

`get_document_info` ya no genera `DianResponseError` por códigos de nota
desconocidos: `document_code` puede ser texto para notas. Si capturabas esa
excepción, verifica `isinstance(document.document_code, str)` en su lugar.

## 0.6.0 — 2026-10-25

- Fábricas `DianClient.from_pfx` y `from_certificate` para material en memoria.
- Reutilización opcional de conexiones con transportes SOAP y descarga separados,
  cierre explícito idempotente y gestor de contexto. El valor predeterminado
  conserva el cierre por operación y no se añaden reintentos.
- Pruebas de recursos, conexiones TCP locales y guía de migración y concurrencia.
- Documentación separada en una sección funcional de actores, procesos y eventos,
  y otra técnica con ejemplos Python verificados, autenticación SOAP, firma de
  eventos, consultas, evidencias y operación. Diagramas y referencias navegables.
- Benchmark sintético reproducible de reutilización de clientes y conexiones;
  no mide capacidad ni cuotas del servicio DIAN.

## 0.5.0 — 2026-10-23

- Pruebas de API pública compartidas por el checkout y el wheel instalado;
  firma y ZIP comunes para todas las familias, sin wrappers internos redundantes.
- Restauración de documentación de modelos, catálogos, errores y referencias;
  matriz navegable de fuentes para 030–051 y ejemplos verificados en CI.
- Compilación limpia de Sphinx, contratos documentales y referencias obligatorias
  en el checkout; omisiones de XSD explícitas al probar distribuciones.
- Validación de pago y catálogos de participantes en módulos neutrales, con
  imports compatibles; builders de pago/notificación y fixtures por familia.
  Se preservan los bytes XML y las validaciones específicas de emisión.

- API común `prepare_radian_event()` / `send_radian_event()` para los 22 eventos
  030–051, con un único `PreparedRadianEvent` y builders especializados por familia.
- Componentes y modelos por familia para inscripción, terminación de mandato,
  pagos, endosos y cancelación; catálogos financieros compartidos, CUDE de endosos
  en blanco, participantes múltiples y precisión Decimal sin redondeos implícitos.
- Aval 035, limitación/terminación 041/042, protesto 048 y derechos económicos
  049–051, con adjuntos PDF en memoria, datos notariales, coberturas de aval,
  saldos explícitos y catálogo de falta de aceptación. Reutilizan la API común,
  serialización, catálogos, firmas y transporte sin nuevas dependencias.
- Guías por familia, discrepancias del anexo documentadas y pruebas sintéticas
  de modelos, XML/XSD, firmas, referencias, bytes de ZIP y transporte.

- Emisión de eventos 030–034 mediante `prepare_radian_event()` y
  `send_radian_event()`, con CUDE, XAdES-EPES, QR de factura y ZIP en memoria.
  Modelos inmutables, motivos de reclamo y catálogos compartidos de participantes;
  declaraciones explícitas, verificación de fecha de firma y envío del ZIP original.
- Referencias FE 1.9 y ejemplificaciones oficiales preservadas con SHA-256;
  documentación por evento y pruebas sintéticas de XML, firmas, bytes y transporte.

- Preparación local y envío explícito del mandato RADIAN 043:
  `prepare_radian_event()` devuelve CUDE, XML XAdES-EPES y ZIP en memoria;
  `send_radian_event()` envía el artefacto mediante `SendEventUpdateStatus`.
- Modelos y catálogos para operaciones 431–434, poderes especiales/generales,
  referencias únicas/múltiples/todas y facultades por factura, con validaciones
  antes del envío, normalización UTC−05:00 y soportes PDF.
- `SendEventResult` conserva los campos DianResponse opcionales y sus dos binarios
  independientes; se reutilizan el parsing seguro y los errores existentes.
- Pruebas sintéticas con XSD locales, verificación de firmas UBL/SOAP, integridad
  del ZIP, errores y cierre de conexiones; guía de uso y criterios del anexo.

## 0.4.0 — 2026-10-21

- `ReferenceNote.code` pasa de `str | None` a `DocumentType | None`, restringido
  a `CREDIT_NOTE` y `DEBIT_NOTE`. Para migrar, pasa estos miembros al construir
  notas y compara con `is`; usa `.value` para el código y `.label` para su etiqueta.
  Códigos desconocidos o de otros documentos generan `DianResponseError` al parsear.
  Los motivos de línea en `NoteResponse.code` conservan su contrato de texto.

- Nuevo `DianClient.get_numbering_range()` con `NumberingRangeResult` y
  `NumberingRange`: consulta de rangos autorizados, fechas nativas, límites
  `xs:long` y claves técnicas excluidas de `repr`, conservando estados de negocio.

- Nuevo `DianClient.get_exchange_emails()` y modelo `ExchangeEmailsResult`: consulta
  sin parámetros y descarga inmediata del ZIP del directorio de correos, con
  metadatos SOAP, cierre automático y extracción del único CSV en memoria en
  el campo `csv`, como tupla de diccionarios mediante `csv.DictReader` nativo,
  conservando encabezados, orden y valores de texto.

### Migración desde 0.3.0

`ReferenceNote.code` requiere un miembro de `DocumentType` en lugar de una cadena:

```python
from radiankore.catalogs import DocumentType
from radiankore.models.responses import ReferenceNote

note = ReferenceNote(code=DocumentType.CREDIT_NOTE)
if note.code is DocumentType.CREDIT_NOTE:
    print(note.code.value, note.code.label)
```

Solo se admiten `CREDIT_NOTE`, `DEBIT_NOTE` o `None`. Cadenas y otros tipos generan
`TypeError`; otros miembros de `DocumentType`, `ValueError`. Al leer SOAP, códigos
desconocidos o distintos de `91` y `92` generan `DianResponseError`. Los motivos
por línea (`NoteResponse.code`) siguen siendo texto y las descripciones del XML
se conservan sin sustituirse por etiquetas del catálogo.

Las consultas nuevas no requieren migraciones. `get_exchange_emails()` entrega
`csv` como tupla de diccionarios, sin archivos temporales, con lectura UTF-8 y
encabezados del CSV. `get_numbering_range()` conserva códigos de negocio como
texto; respeta el ambiente elegido, aunque DIAN solo declara disponibilidad
operativa en producción. Consulta las guías de cada operación para sus contratos.

## 0.3.0 — 2026-10-21

- Nuevo catálogo `DocumentType` para `DocumentInfo.document_type_id` y
  `DocumentReference.document_type_id`. Sus códigos son `01`–`04`, `91`, `92` y
  `96`; el parser normaliza `1`–`4` y rechaza códigos desconocidos. Los modelos
  exigen miembros del enum. Usa `.value` para el código canónico y `.label` para
  la etiqueta.
- Nuevos catálogos `CreditNoteReason` y `DebitNoteReason` para
  `DocumentInfo.document_code`, seleccionados por el tipo `91` o `92`.
  Los demás tipos conservan texto. Para notas, los códigos desconocidos generan
  `DianResponseError` y los modelos exigen el enum del motivo correspondiente.
  Sustituye comparaciones con cadenas por miembros de esos enums; `.value`
  devuelve el código de texto y `.label` la descripción oficial.
- Se documentan las fuentes oficiales de tipos y motivos, y las limitaciones
  de los estados, que conservan sus claves enteras y textos originales.
- `DocumentInfoResult.status_code` pasa de `str | None` a `HTTPStatus | None`,
  de la biblioteca estándar `http`, igual que `XmlDocumentResult.status_code`.
  Códigos desconocidos o inválidos generan `DianResponseError`. Sustituye las
  comparaciones con cadenas por miembros de `HTTPStatus` y usa `.value` para
  obtener el código entero. El estado HTTP del transporte conserva su manejo.

### Migración desde 0.2.0

- Importa `HTTPStatus` desde `http` y compara `result.status_code` con miembros
  como `HTTPStatus.OK` o `HTTPStatus.NOT_FOUND`; `.value` devuelve el entero.
- Importa `DocumentType` desde `radiankore.catalogs` y usa miembros como
  `DocumentType.SALES_INVOICE` en documentos y referencias. `.value` devuelve
  el código canónico, incluidos sus ceros iniciales.
- En notas crédito, usa `CreditNoteReason`; en débito, `DebitNoteReason`.
  Compara los miembros con `is`, pues ambos catálogos pueden compartir códigos
  de texto. Para construir los modelos, pasa el enum correspondiente en lugar
  de una cadena. Los códigos de documentos de otros tipos conservan texto.
- `documents` sigue siendo una tupla: conserva orden XML, duplicados y entradas
  nulas. No es necesario migrar a un campo singular. Las descripciones recibidas,
  fechas, importes y estados conservan sus contratos anteriores.

## 0.2.0 — 2026-10-21

- `XmlDocumentResult.status_code` pasa de `str | None` a `HTTPStatus | None`,
  de la biblioteca estándar `http`. Códigos desconocidos o inválidos en el SOAP
  generan `DianResponseError`; las comparaciones con cadenas deben actualizarse.
- `get_acquirer` devuelve `None` ante HTTP 404 sin SOAP Fault. Los demás errores
  HTTP, de red y SOAP conservan sus excepciones.

### Migración desde 0.1.0

En `get_xml_by_document_key`, sustituye comparaciones como
`result.status_code == "404"` por `result.status_code is HTTPStatus.NOT_FOUND`,
importando `HTTPStatus` desde `http`. Usa `result.status_code.value` para obtener
el código entero cuando el campo no sea `None`. Los demás modelos conservan sus
tipos de códigos actuales.

## 0.1.0 — 2026-10-21

- Consultas directas a DIAN: estado de validación, eventos RADIAN, adquirientes,
  información de documentos, notas referenciadas y descarga del XML.
- Certificados PFX/P12, ambientes de producción y habilitación y cierre automático
  de conexiones HTTP.
- Dataclasses inmutables, enums de identificación y eventos, fechas nativas y
  conservación del XML original cuando corresponde.
- Publicación del código bajo licencia MIT, conservando atribuciones de terceros.
- Validación de tipos de CUFE consistente con las demás consultas.
