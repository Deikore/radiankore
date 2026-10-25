# Evidencia, fuentes y límites de verificación

Revisión documental: **24 de octubre de 2026**, contra el código de radiankore
**0.5.0**, RADIAN **1.1**, Factura Electrónica **1.9** y los WSDL guardados en el
repositorio. Esta fecha identifica la revisión, no una vigencia normativa garantizada.
La [página oficial de documentación RADIAN](https://micrositios.dian.gov.co/sistema-de-facturacion-electronica/documentacion-tecnica-radian/)
publica los accesos al anexo y caja de herramientas. Para cambios normativos consulte
además el [normograma DIAN](https://normograma.dian.gov.co/dian/compilacion/docs/resolucion_dian_0085_2022.htm):
el marco de 2022 tiene referencias de compilación posteriores; no se afirma que su
texto original permanezca íntegramente sin cambios.

## Correspondencia entre afirmación, implementación y prueba

Las rutas siguientes son relativas al repositorio y permiten auditar esta versión.
Los materiales originales y sus hashes siguen en el
[índice de procedencia](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/README.md).
No se incorporan al sitio ni a las distribuciones y no se modifican para hacer
coincidir un ejemplo con el SDK.

| Tema | Fuente / alcance | Implementación | Evidencia local |
| --- | --- | --- | --- |
| Convenciones de tablas | RADIAN §6 pp.18–20 | Interpretación de campos de modelos | Pruebas de modelos/catálogos |
| Negocio y actores | RADIAN §7.2.1 pp.31–53 y matriz sujeto-evento-rol de la caja | Componentes de `models/events/` | `test_radian_models.py`, `test_remaining_radian_models.py` |
| Contratos de consulta | WSDL producción/habilitación y guías por operación | `client.py`, `_soap/` parsers | Pruebas por operación y ejemplos publicados |
| SOAP y conexión | RADIAN §8 pp.290–299, §9.4 pp.442–443; políticas WSDL | `_soap/envelope.py`, `_soap/signing.py`, `_soap/transport.py` | `test_signing.py`, `test_soap_client.py`, `test_client.py` |
| XAdES-EPES | RADIAN §9.3 y §11 pp.445–456 | `_soap/events/ubl_signing.py` | Firmas serializadas en `test_mandate_xml.py`, `test_radian_xml.py` y demás pruebas XML |
| CUDE y código software | RADIAN §12 pp.457–464 | `_soap/events/cude.py` y builders | Pruebas XML/CUDE por familia |
| Todos los eventos 030–051 | FE 1.9 para 030–034; RADIAN 1.1 para 035–051 | Quince modelos públicos | [Matriz por evento](../event-reference-map.md) |
| Preparado, bytes y transmisión | Contrato público del SDK | `client.py`, `_soap/events/zip.py` | `test_send_radian_event.py`, `test_send_invoice_event.py`, `test_send_mandate_event.py` |
| Ejemplos canónicos | Bloques Python de las páginas publicadas | API pública | `test_documentation_examples.py` ejecuta bloques, sin copiar su implementación |
| Sitio y referencia pública | MyST/Sphinx/Furo | `docs/conf.py` sin importar SDK | Build con warnings como errores y `test_documentation.py` |

## Qué se comprueba fuera de DIAN

Las pruebas usan PFX sintéticos y HTTPX MockTransport. Comprueban argumentos,
modelos, variantes, respuestas válidas/nulas/rechazadas/malformadas, errores SOAP,
bytes originales, cierre de conexiones y firmas serializadas. La suite contiene
validación XSD cuando están disponibles las referencias. Los ejemplos publicados
de las familias son preparados y sus firmas se verifican, sin transmitir a DIAN.

Eso **no demuestra** autorización real, confianza de la cadena, vigencia, revocación,
aceptación jurídica ni compatibilidad actual de cada participante con DIAN.
Tampoco verifica firmas de respuestas dentro de los parsers.
Las comprobaciones de habilitación real deben usar participantes y software
autorizados y registrar resultados separados de esta evidencia local.

## Discrepancias y datos no confirmados

- El anexo describe autenticación mutua TLS; el WSDL conservado desactiva la
  exigencia de certificado cliente y HTTPX no configura `cert=`. El namespace
  To del SignedParts WSDL tampoco coincide con el WS-Addressing 2005/08 usado
  por el SDK. No se ocultan estas diferencias con una afirmación de cumplimiento.
- La política de firma tiene URL y digest constantes en el SDK. Su valor se
  documenta como implementación; la disponibilidad y hash de la descarga se
  registran separadamente más abajo, sin cambiar automáticamente la constante.
- El Schematron usa XSLT 3 y referencia una lista no distribuida. Las pruebas XSD,
  XPath y firma no equivalen a ejecutar ese conjunto integral de reglas.
- Hay erratas en ejemplificaciones, identificadores sintéticos y estructuras
  antiguas. Las operaciones 403/443 no tienen XML propio en la caja conservada:
  su cobertura local procede de catálogos, perfil común y casos sintéticos.
- `CompressedDocumentInfo` no tiene formato de compresión documentado en el WSDL.
  La interpretación de algunos campos de respuestas procede de muestras observadas;
  cada guía declara esa procedencia y los límites de formato correspondientes.

## Mantener esta documentación

Cuando cambie una firma, modelo o parser, actualice primero la guía de operación,
sus bloques ejecutables y la prueba pertinente. Conserve las URLs actuales y
actualice la matriz si cambia una fuente. No duplique ejemplos ejecutables en
scripts independientes que puedan quedar desincronizados.

Pruebas dirigidas: `uv run pytest tests/test_documentation.py tests/test_documentation_examples.py`.
Compilación independiente de dependencias nativas:

```bash
uv run --no-project --with-requirements docs/requirements.txt sphinx-build -E -W --keep-going -b html docs docs/_build/html
```

El build no importa el SDK ni ejecuta los ejemplos contra DIAN. Consulte
[desarrollo](../development.md) para lint, tipado y suite completa; y
[Read the Docs](../readthedocs.md) para la publicación del sitio.

## Comprobación de la política de firma

El 24 de octubre de 2026 se descargó por HTTPS la URL de política documentada.
El recurso entregó un PDF de **1.272.898 bytes**. El SHA-256 de esos bytes, en
Base64, fue `dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y=`, coincidente con la
constante del SDK. Se comprobó el archivo completo, no su texto extraído ni una
representación HTML. Esto verifica esa descarga puntual; no acredita vigencia
jurídica ni garantiza que el recurso no cambie en el futuro.

Para repetir la comprobación en una copia temporal, sin alterar las referencias:

```bash
curl --fail --location --max-time 30 --output /tmp/dian-signature-policy.pdf https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf
openssl dgst -sha256 -binary /tmp/dian-signature-policy.pdf | openssl base64 -A
```

Una diferencia requiere revisar procedencia y versión antes de modificar el perfil;
no actualice el digest automáticamente ni sustituya un original preservado.
