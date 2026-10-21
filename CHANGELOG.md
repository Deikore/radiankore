# Historial de cambios

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
