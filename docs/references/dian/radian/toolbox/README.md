# Caja de herramientas RADIAN

Contenido descargado y extraído por el usuario desde la
[caja de herramientas oficial de DIAN](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Caja-de-herramientas-RADIAN.zip).
Se conserva la estructura original de la extracción, incluidos nombres con espacios,
acentos y las codificaciones presentes en los nombres recibidos.

## Procedencia y estado

- Estado: contenido extraído disponible, con 138 archivos originales inventariados.
- Fecha de registro del contenido y de sus hashes: 2026-10-20 (UTC).
- Fecha exacta de descarga y publicación del ZIP: no registradas.
- Versión global de la caja: no registrada; no debe deducirse únicamente del anexo.
- Versión del anexo incluido: RADIAN 1.1, Resolución 000085 del 8 de abril de 2022.
- ZIP de origen: no conservado en el repositorio; su SHA-256 no está disponible.
- Integridad de los archivos extraídos: registrada en [SHA256SUMS](SHA256SUMS).

Los hashes permiten detectar cambios posteriores a este registro. No equivalen a un
hash del ZIP ni a una comprobación contra un manifiesto publicado por DIAN.

## Contenido

| Directorio original | Archivos | Material |
| --- | ---: | --- |
| [Anexo RADIAN/](<Anexo RADIAN/>) | 2 | Anexo técnico y matriz de sujetos, eventos y roles en Excel. |
| [XSD/](XSD/) | 20 | Esquemas principales y comunes UBL 2.1 y estructuras DIAN. |
| [Schemes/](Schemes/) | 7 | Reglas Schematron de estructura y listas de códigos. |
| [Listas de valores/](<Listas de valores/>) | 19 | Listas de eventos, ambientes y otros valores de referencia. |
| [Ejemplificaciones/](Ejemplificaciones/) | 66 | Ejemplos XML de eventos RADIAN. |
| [Documentos de apoyo - Ingles/](<Documentos de apoyo - Ingles/>) | 24 | Documentación Schematron y utilidades XSLT, XSD, Java y scripts. |

El [anexo incluido en la caja](Anexo%20RADIAN/Anexo%20Te%CC%81cnico%20-RADIAN%20%E2%80%93%20Versio%CC%81n%201.1%20-%20Resolucio%CC%81n%20000085%20de%202022.pdf) coincide byte por byte con
[la copia de referencia RADIAN 1.1](../1.1/anexo-tecnico.pdf). Ambas copias se
mantienen para conservar la estructura original de la caja y la ruta documental
ya utilizada por el proyecto.

No hay archivos WSDL en esta extracción; los endpoints y el perfil SOAP se documentan
en el README principal y en la implementación.

## Verificación y mantenimiento

Desde este directorio, verifica los archivos registrados con:

```bash
sha256sum --check SHA256SUMS
```

El inventario incluye solo los archivos originales extraídos; excluye este README y
el propio `SHA256SUMS`. Al incorporar una nueva entrega, consérvala por separado y
registra procedencia, versión identificable, fechas y hashes antes de actualizar los
índices. No regeneres el inventario para ocultar modificaciones de los originales.

Estas referencias quedan fuera del wheel y del sdist. Los ejemplos adaptados para
pruebas deben ser ficticios y guardarse en `tests/fixtures/`. Los recursos necesarios
en ejecución se incorporarán explícitamente al paquete con sus pruebas de empaquetado.
No ejecutes las utilidades de la caja como parte de su incorporación documental.
