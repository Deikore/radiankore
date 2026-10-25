# Referencias técnicas

Los contratos se contrastan con los WSDL de producción y habilitación, el anexo
RADIAN 1.1 y la caja de herramientas publicada por DIAN. Las copias y su procedencia
están en el
[índice del repositorio](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/README.md).

- [Contrato y correspondencias SOAP](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md).
- [Anexo RADIAN oficial](https://www.dian.gov.co/normatividad/Normatividad/Anexo%2085%20-%20Resoluci%C3%B3n%20000085%20de%202022.pdf).
- [Caja de herramientas RADIAN](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Caja-de-herramientas-RADIAN.zip).
- [Tipos de documento FE 1.9, edición 2026: fuentes y hashes](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/invoicing/1.9/README.md).

Los materiales originales no se modifican para adaptar el comportamiento del SDK.
Los parsers no realizan validación integral contra XSD ni verifican las firmas de
las respuestas recibidas. Las limitaciones específicas figuran en cada operación.

Las referencias técnicas de terceros se conservan en GitHub y no se incluyen en el
sitio generado ni en wheel o sdist. Su licencia no cambia por la licencia MIT del
código; consulta
[THIRD_PARTY_NOTICES](https://github.com/Deikore/radiankore/blob/HEAD/THIRD_PARTY_NOTICES).

## Localizar los eventos

Hay dos anexos distintos llamados `anexo-tecnico.pdf`: Factura Electrónica 1.9
(753 páginas) y RADIAN 1.1 (482 páginas). FE sustenta los eventos 030–034;
RADIAN describe 035–051. El anexo RADIAN continúa después del evento 045:
046 empieza en la página 231 y 051 en la 280.

La [matriz completa de eventos y fuentes](event-reference-map.md) enlaza cada
código 030–051 con su modelo, guía, sección, página, ejemplos y pruebas.
Incluye también las respuestas 02/04, generadas por DIAN, y las operaciones
403/443 que no tienen ejemplo propio en la caja.

## Interpretaciones y comprobaciones

Las guías por familia separan reglas oficiales, decisiones locales y discrepancias.
La validación XSD y de firmas en las pruebas no equivale a aceptación de negocio
por DIAN. El Schematron distribuido usa XSLT 3 e incluye una lista ausente de
la caja: no se afirma su ejecución integral. Se comprueban explícitamente los
XPath aplicables y las limitaciones se detallan en la guía de emisión.

Las referencias originales y sus hashes permanecen en el repositorio; no se
copian al sitio ni a las distribuciones. Su incorporación y procedencia están en
el índice enlazado arriba. Las fechas de incorporación no son fechas de vigencia
normativa ni prueban que no existan revisiones posteriores de DIAN.

La [matriz de evidencia de integración](guides/evidence.md) conecta fuentes,
implementación, pruebas y discrepancias de comunicación y firma.
