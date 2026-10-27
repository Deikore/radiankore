# Referencias técnicas de DIAN

Material oficial para desarrollar y revisar la integración RADIAN. Estas
referencias no se incluyen en el wheel ni en el sdist de `radiankore`.

## Organización

```text
wsdl/
  production.wsdl         Contrato SOAP con esquemas de producción
  habilitation.wsdl       Contrato SOAP con esquemas de habilitación
radian/
  1.1/anexo-tecnico.pdf    Anexo RADIAN versión 1.1
  toolbox/                Caja de herramientas extraída: 138 archivos originales
    README.md             Procedencia, contenido y mantenimiento
    SHA256SUMS            Integridad de los archivos extraídos
```

## Anexo técnico RADIAN

Los tipos de documento de FE 1.9 se conservan por separado en
[invoicing/1.9](invoicing/1.9/README.md), con tabla oficial de la edición 2026,
genericode original, procedencia y hashes. `DocumentType` toma los siete códigos
de la tabla 13.1.3; el parser de `GetDocumentInfo` admite además los alias `1`–`4`.

- Archivo local: [radian/1.1/anexo-tecnico.pdf](radian/1.1/anexo-tecnico.pdf).
- Fuente oficial: [Anexo 85 — Resolución 000085 de 2022](https://www.dian.gov.co/normatividad/Normatividad/Anexo%2085%20-%20Resoluci%C3%B3n%20000085%20de%202022.pdf).
- Versión indicada en el documento: 1.1.
- Resolución y fecha: 000085 del 8 de abril de 2022.
- Fecha de incorporación al repositorio: 2026-10-20 (UTC).
- Procedencia de esta copia: archivo aportado por el mantenedor.
- Fecha de descarga original: no registrada.
- Estado: copia local incorporada y cotejada el 2026-10-20 con el anexo de la
  caja descargada por el usuario; ambos archivos son idénticos byte por byte.
- SHA-256 de la copia conservada:

```text
f7e75b3fdbe93ae3167918f27fde2cbd370a5cffc175b14481793f9c38e7c9cc
```

La consulta `GetStatusEvent` utiliza la sección 8.8 como referencia documental.
Las condiciones del material de terceros se aclaran en
[THIRD_PARTY_NOTICES](../../../THIRD_PARTY_NOTICES).

## Caja de herramientas

Fuente: [Caja de herramientas RADIAN](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Caja-de-herramientas-RADIAN.zip).
El usuario incorporó el contenido extraído: 138 archivos originales con XSD,
Schematron, listas de valores, ejemplos XML y documentación de apoyo. Consulta
[radian/toolbox/README.md](radian/toolbox/README.md) para el inventario y la procedencia,
y [SHA256SUMS](radian/toolbox/SHA256SUMS) para verificar su integridad.
La caja contiene el anexo RADIAN 1.1; su versión global y fecha exacta de descarga
no están registradas. El ZIP no se conserva y no se dispone de su hash.

## Contratos de los servicios web

Los WSDL completos de producción y habilitación están en [wsdl/](wsdl/README.md).
Su índice registra URLs, fecha de incorporación, hashes y el contrato de
las ocho operaciones implementadas: GetNumberingRange, GetExchangeEmails, GetStatus, GetStatusEvent, GetAcquirer,
GetDocumentInfo, GetReferenceNotes y GetXmlByDocumentKey. Los esquemas de ambos
ambientes coinciden y no requieren descargas adicionales. La librería comparte
sobre, firma y transporte con parsers por operación.

## Catálogos de códigos

`radiankore.catalogs` mantiene constantes Python revisadas a partir de estas
fuentes; no carga los documentos durante la ejecución:

| Catálogo público | Fuente | Versión y cobertura |
| --- | --- | --- |
| `DocumentType` | [Tabla FE 1.9 13.1.3 y genericode](invoicing/1.9/README.md) | Caja de herramientas FE 1.9, edición 2026; siete códigos: `01`, `02`, `03`, `04`, `91`, `92`, `96` |
| `CreditNoteReason`, `DebitNoteReason` | [Tablas FE 1.9 13.2.4 y 13.2.5](invoicing/1.9/README.md) | Edición 2026; motivos de crédito `1`–`6` y débito `1`–`4`; aplicación a `DocumentCode` basada en observación del mantenedor. Observado `7` «Otros» en notas crédito aceptadas con notificación «El Código informado no se encuentra en la lista»; los códigos fuera de catálogo se conservan como texto |
| `IdentificationType` | [TipoIdFiscal-2.1.gc](radian/toolbox/Listas%20de%20valores/TipoIdFiscal-2.1.gc) y anexo RADIAN §14.2.13 | Lista versión 1, modificada el 03-04-2022; 11 códigos: `11`, `12`, `13`, `21`, `22`, `31`, `41`, `42`, `47`, `50`, `91` |
| `IdentificationType` | [Guía DIAN para completar información de adquirientes](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Guia-Herramienta-para-el-Consumo-de-Web-Services.pdf), tabla de `identificationType` | Añade `48`: PPT (Permiso Protección Temporal). Referencia web consultada el 2026-10-20; sin copia local ni hash |
| `EventType` | [Eventos-2.1.gc](radian/toolbox/Listas%20de%20valores/Eventos-2.1.gc) | Lista versión 1, modificada el 03-04-2022; códigos `035`–`051` |
| `EventType` | Anexo RADIAN 1.1 §14.2.1 | Códigos `02` y `04` |
| `EventType` | [Presentación DIAN: control de cambios del anexo técnico 1.8](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Presentacion-Control-de-Cambios-Anexo-Tecnico-1-8.pdf), tabla «Eventos Título Valor» | Códigos `030`–`034`; referencia web consultada el 2026-10-20, sin copia local ni hash |

Las etiquetas toman la columna `name` de los archivos `.gc`, quitando espacios
exteriores. En el catálogo de eventos, la columna `Description` contiene roles
responsables y no se utiliza como etiqueta. Los textos de eventos recibidos por
SOAP se conservan por separado en `InvoiceEvent.description`.

La etiqueta del código `91` se presenta como `NUIP`, sin el asterisco de nota.
El anexo §14.2.13 restringe su uso al adquiriente; el enum no impone esta regla.
`TipoIdTributario-2.1.gc` corresponde a tributos como IVA e INC y no define los
tipos de identificación de `CompanyID/@schemeName`.

Los modelos exponen directamente `IdentificationType | None` y `EventType | None`.
El parser convierte códigos conocidos a sus miembros; los ausentes o vacíos
producen `None`. Los códigos desconocidos generan `DianResponseError` con la causa
original; para aceptarlos es necesario revisar y actualizar el catálogo.

Los métodos `IdentificationType.from_code()` y `EventType.from_code()` ofrecen
resolución opcional fuera del parser: devuelven `None` ante códigos ausentes,
vacíos o desconocidos. Las listas son referencias versionadas y no una validación
exhaustiva de las reglas que DIAN pueda incorporar.

## Mantenimiento

Conserva los originales intactos y las versiones anteriores. Al incorporar material
registra URL, versión identificada, fecha de publicación si existe, fecha de descarga
y SHA-256. Si un enlace cambia de contenido, guarda una nueva versión y documenta
qué operaciones o contratos se basan en ella.

Mantén interpretaciones y diferencias observadas en notas separadas de los archivos
oficiales. Los ejemplos adaptados para pruebas deben ser ficticios y vivir en
`tests/fixtures/`. Solo los recursos necesarios en ejecución deben incorporarse a
`src/radiankore/resources/`, con una comprobación de su empaquetado.

## Referencias de emisión 030–034

El [inventario FE 1.9](invoicing/1.9/README.md#emisión-de-eventos-030034) incorpora
el anexo completo, tablas de eventos y reclamos, genericode y cinco ejemplificaciones
de la edición 2026. Las copias RADIAN existentes siguen intactas. La guía de emisión
registra diferencias de perfil, descripción 032 y etiquetas de reclamo.

`InvoiceClaimReason` usa la tabla FE 13.3.12 para los códigos `01`–`04`.
`OrganizationType` usa `TipoOrganizacion-2.1.gc` y RADIAN §14.2.14;
`PartyTaxScheme` usa los cuatro pares código/nombre de RADIAN §14.2.15:
`01`/IVA, `04`/INC, `ZA`/IVA e INC y `ZZ`/No aplica. No se usa el catálogo general
de impuestos de facturación para representar el régimen tributario de una parte.
El catálogo de eventos existente se reutiliza; sus etiquetas de consulta no se
cambian para adaptarlas a los literales de emisión.

## Implementación de eventos RADIAN 036–040 y 044–047

Los originales de RADIAN 1.1 y su caja se consultaron sin modificaciones.
Las referencias de las nuevas familias son:

| Familia | Requisitos / generación | Validación / extensiones |
| --- | --- | --- |
| Terminación 044 | 7.2.1.4.3 / 7.2.5.12 | 9.2.13 |
| Inscripción 036 | 7.2.1.1 / 7.2.5.4 | 9.2.5 / 7.2.4.4 y 9.2.3.4 |
| Pago 045 e informe 046 | 7.2.1.5–7.2.1.6 / 7.2.5.13–7.2.5.14 | 9.2.14–9.2.15 / 7.2.4.8–7.2.4.9 |
| Endosos 037–039/047 y cancelación 040 | 7.2.1.2 / 7.2.5.5–7.2.5.8 y 7.2.5.15 | 9.2.6–9.2.9 y 9.2.16 / 7.2.4.5 y 9.2.3.5 |

Los modelos usan 18 operaciones de tabla 14.1.2 y del genericode correspondiente.
Se revisaron las 20 ejemplificaciones disponibles, incluidas las cuatro de
inscripción con extensión `.xml`/`.XML`. Las operaciones 403 y 443 figuran en
tabla y genericode, pero no tienen ejemplificación propia en la caja.

CUDE general: §12.1.1. Endosos en blanco: §12.1.3, sin identidad del endosante y
con `listID=2`. El vector publicado utiliza `030` como dato de demostración;
los documentos reales usan el código de endoso correspondiente.

Las diferencias se documentan fuera de los originales en las guías por familia:
condición de limitación frente a parcial/total en 045, AAI07b y aritmética de tasas,
`listID` omitido en muestra 047, campos de venta vacíos en 038/039 y códigos fiscales
erróneos en muestras de inscripción. `CurrencyCode` toma `VES` de tabla 14.2.16,
frente a `VES7` del genericode. Los medios de pago usan los 14 códigos explícitos
de tabla 14.2.11, sin extenderlos automáticamente a los 77 del genericode general.


## Cobertura completa de la emisión

El [mapa navegable de eventos](../../event-reference-map.md) registra todos los
códigos de participantes 030–051, secciones/páginas, modelos, guías y ejemplos.
Los eventos 02/04 son emitidos por DIAN. Hay dos anexos con el mismo nombre:
FE 1.9 (753 páginas, `invoicing/1.9/anexo-tecnico.pdf`) y RADIAN 1.1
(482 páginas, `radian/1.1/anexo-tecnico.pdf`). RADIAN incluye 046–051 en
§§7.2.5.14–19, pp. 231–289; no termina en el evento 045.

A la incorporación anterior se añaden aval 035, limitación/terminación 041/042,
protesto 048 y derechos económicos 049–051: 14 operaciones y 16 muestras.
La API RADIAN común suma 32 operaciones y 36 XML de referencia para sus 16 clases,
además de las fuentes particulares de 030–034 y del mandato 043.
`AcceptanceFailureType` usa §14.2.20 y `Falta de aceptacion.gc`.
Las nuevas guías explican adjuntos, referencias CUFE/CUDE, cero en aval, AAI05a,
roles de 051 y la condición de aceptación de 481 frente a 482.
Esta nota no modifica los originales ni sus inventarios SHA-256.
