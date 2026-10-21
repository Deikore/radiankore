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
| `CreditNoteReason`, `DebitNoteReason` | [Tablas FE 1.9 13.2.4 y 13.2.5](invoicing/1.9/README.md) | Edición 2026; motivos de crédito `1`–`6` y débito `1`–`4`; aplicación a `DocumentCode` basada en observación del mantenedor |
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
