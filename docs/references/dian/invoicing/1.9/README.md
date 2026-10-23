# Tipos de documento y motivos de notas — Factura Electrónica 1.9

Copias originales para documentos, motivos de notas y emisión de eventos 030–034.
No se incluyen en la
distribución de la librería ni en el sitio de documentación.

- Fuente: [Caja de herramientas FE 1.9, edición 2026](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Caja-de-herramientas-FE_V19_v2026.zip).
- Publicada desde el [portal técnico de DIAN](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/documentacion-tecnica/).
- Versión identificada: FE 1.9, directorio `Caja de herramientas FE_V19_(v2026)`.
- Fecha de descarga e incorporación: 2026-10-21 (UTC).
- Fecha exacta de publicación de esta edición: no indicada en la página consultada.
- SHA-256 del ZIP descargado, conservado temporalmente fuera del repositorio:
  `036eac8ca529ee7d13601eebcd77f89394bcd83fb1220f723616292d30685b39`.

## Archivos preservados

| Copia local | Ruta dentro del ZIP |
| --- | --- |
| [13.1.3-Tipo-de-Documento.xlsx](13.1.3-Tipo-de-Documento.xlsx) | `Anexo Tecnico/Tablas Referenciadas/13.1.3 Tipo de Documento.xlsx` |
| [TipoDocumento-2.1.gc](TipoDocumento-2.1.gc) | `Listas de valores/TipoDocumento-2.1.gc` |
| [13.2.4-Concepto-Correccion-Notas-Credito.xlsx](13.2.4-Concepto-Correccion-Notas-Credito.xlsx) | `Anexo Tecnico/Tablas Referenciadas/13.2.4 Concepto de Corrección para Notas crédito cac DiscrepancyResponse cbc ResponseCode.xlsx` |
| [13.2.5-Concepto-Correccion-Notas-Debito.xlsx](13.2.5-Concepto-Correccion-Notas-Debito.xlsx) | `Anexo Tecnico/Tablas Referenciadas/13.2.5. Concepto de Corrección para Notas débito cac DiscrepancyResponsecbc ResponseCode.xlsx` |

Las rutas están bajo el directorio de la edición. Solo se simplificaron nombres
locales de tablas; los bytes originales se conservaron sin cambios. Los hashes
están en [SHA256SUMS](SHA256SUMS).

## Interpretación aplicada

La tabla 13.1.3 enumera `01`, `02`, `03`, `04`, `91`, `92` y `96`.
El genericode enumera solamente los seis primeros, con diferencias en las
descripciones de facturas. El catálogo Python toma los códigos y las etiquetas
de la tabla 13.1.3; `96` corresponde a eventos `ApplicationResponse`.

La tabla distingue los tipos de documento de los códigos de eventos y limita
algunos usos a referencias documentales. El enum es un catálogo de consulta:
no valida reglas de emisión ni autoriza usos de cada documento.

Por decisión del contrato público, `GetDocumentInfo` aplica este catálogo a
`DocumentTypeId` de documentos y referencias, normalizando `1`–`4` a `01`–`04`
solo en el parser. El WSDL declara texto sin una enumeración. No se presume que
`DocumentCode` o `Estado/Key` utilicen este mismo catálogo.

Las tablas 13.2.4 y 13.2.5 enumeran los conceptos de corrección de notas crédito
(`1`–`6`) y débito (`1`–`4`). Sus códigos coinciden parcialmente pero tienen
significados diferentes. Los enums conservan cada descripción con espacios
exteriores eliminados. Su aplicación a `DocumentInfo.document_code`, seleccionada
por el tipo `91` o `92`, se basa en la observación aportada por el mantenedor:
las tablas describen `cac:DiscrepancyResponse/cbc:ResponseCode` y el WSDL no
vincula explícitamente ese catálogo con `DocumentCode`. Para otros tipos de
documento, `document_code` conserva texto sin interpretar.

Las fuentes revisadas no proporcionaron una enumeración para `Estado/Key`.
Las observaciones sobre estados se documentan en la guía de la operación,
separadas de estas copias oficiales. Este material conserva sus condiciones
originales; la licencia MIT del código no modifica las de las referencias.

## Emisión de eventos 030–034

El 2026-10-22 se incorporaron fuentes adicionales sin alterar las copias previas.
El ZIP FE 2026 conserva el SHA-256 indicado arriba. Los originales añadidos son:

| Copia local | Ruta en el ZIP FE 2026 |
| --- | --- |
| `13.3.1-Eventos-de-un-Documento-Electronico.xlsx` | `Anexo Tecnico/Tablas Referenciadas/13.3.1 Eventos de un Documento Electrónico.xlsx` |
| `13.3.12-Concepto-de-Reclamo.xlsx` | `Anexo Tecnico/Tablas Referenciadas/13.3.12. Concepto de Reclamo @listID.xlsx` |
| `Concepto-de-Reclamo.gc` | `Listas de valores/Concepto de Reclamo.gc` |
| `examples/*.xml` (cinco archivos) | `Ejemplificaciones/XMLs de ejemplo/Eventos RADIAN/` (mismos nombres) |

Los archivos se extrajeron sin modificar sus bytes. Todos tienen su SHA-256 en
`SHA256SUMS`. No son fixtures ni recursos de ejecución.

También se añadió `anexo-tecnico.pdf`, descargado el 2026-10-22 de la
[fuente oficial FE 1.9](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf).
Versión 1.9, Resolución 000165 del 01/NOV/2023, 753 páginas.
SHA-256: `1b4022ac112232cd525a455432b2bdfc977d2edcf14c1c7aa26f8ba93fe47ded`.

Las secciones 6.5.4–6.5.5, 8.5–8.6 y 11.5 sustentan estructura, validaciones y
CUDE. El anexo RADIAN 1.1 conserva sus propias ejemplificaciones y extensiones;
no dedica secciones de generación individuales a estos cinco eventos.

Interpretaciones y diferencias se documentan aparte en
[la guía de emisión](../../../../operations/invoice-emission.md): prevalecen los
literales de rechazo sobre las muestras inconsistentes. Los motivos usan la tabla
13.3.12, incluyendo su espaciado interior original. El genericode discrepa para
`02` y `03`; la ejemplificación FE 2026 de reclamo coincide con la tabla para `02`.
No se cambia el catálogo público de descripciones recibidas en consultas.
