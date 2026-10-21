# Historial de cambios

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
