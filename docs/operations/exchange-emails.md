# Directorio de correos: GetExchangeEmails

Consulte el directorio de correos registrados para recibir facturas electrónicas.
No recibe identificación, CUFE ni otros parámetros. Utilice el certificado y el
ambiente del cliente; producción es predeterminada.

```python
from radiankore import DianClient

client = DianClient("/ruta/segura/certificado.pfx", password="password-de-ejemplo")
result = client.get_exchange_emails()
if result is not None:
    print(result.success, result.status_code, result.message)
    if result.csv is not None:
        for row in result.csv:
            print(row)
```

## Descarga y resultado

Desde noviembre de 2024, `CsvBase64Bytes` contiene una URL codificada en Base64,
no el CSV directamente. La URL vence a los **10 segundos**: el cliente la decodifica
como UTF-8 y descarga el ZIP inmediatamente, dentro de la misma llamada.
[Comunicado oficial de DIAN](https://www.dian.gov.co/Prensa/Paginas/NG-Optimizacion-del-metodo-GetExchangeEmails-del-Webservice.aspx).

`ExchangeEmailsResult`, importado desde `radiankore.models.responses`, es una
dataclass inmutable con slots y argumentos por nombre:

| Campo | Origen | Tipo |
| --- | --- | --- |
| `success` | `Success` | `bool \| None` |
| `status_code` | `StatusCode` | `str \| None` |
| `message` | `Message` | `str \| None` |
| `download_url` | `CsvBase64Bytes`, decodificado | `str \| None` |
| `csv` | Filas del CSV extraído, usando sus encabezados como claves | `tuple[dict[str, str], ...] \| None` |

El código SOAP se conserva como texto: el WSDL no define su equivalencia con
`HTTPStatus`. `success=False` no genera una excepción ni descarta una URL válida.
El ZIP debe contener exactamente un archivo con extensión `.csv` (sin distinguir
mayúsculas), que puede estar dentro de un directorio. Otras entradas se ignoran.
Se descomprime solo ese archivo en memoria, sin escribir archivos al disco. Se
lee como UTF-8 (con o sin BOM), mediante `csv.DictReader` de la biblioteca estándar.
La primera fila contiene los encabezados: sus nombres y los valores se conservan
como texto, incluidos ceros iniciales y campos vacíos. `csv.Sniffer` detecta coma,
punto y coma, tabulador o barra vertical en los primeros 65 536 caracteres; si no
puede determinar el separador, se utiliza coma. No se convierten tipos ni se
ordenan o deduplican filas. Un archivo vacío o con solo encabezados produce `()`.
Encabezados vacíos o repetidos, filas con distinto número de columnas, UTF-8
inválido o errores de sintaxis CSV generan `DianResponseError`.

La tupla conserva el orden; los diccionarios de sus filas son mutables. La URL y
los registros se excluyen de `repr`.

Resultado SOAP ausente o nulo devuelve `None`; uno vacío devuelve
`ExchangeEmailsResult()`. URL ausente, nula, vacía o compuesta solo por espacios
decodificados deja `csv=None` y no realiza GET.

## Errores y conexiones

Se aceptan URLs absolutas HTTPS sin credenciales ni fragmento. Base64, UTF-8,
URL o booleano inválidos generan `DianResponseError`. Un ZIP corrupto, cifrado,
con compresión no soportada, sin CSV o con varios CSV también genera
`DianResponseError`, sin devolver un resultado parcial. `Success` es opcional pero
no nillable: admite `true`, `false`, `1` y `0`; si está ausente vale `None`.

La descarga usa el timeout configurado en `DianClient`, sin encabezados SOAP,
certificado, redirecciones ni reintentos automáticos. Ambas conexiones se cierran
antes de retornar, también ante errores. Fallos HTTP, de red o timeout generan
`DianTransportError`, con el estado HTTP cuando existe; no se retorna un resultado
parcial. Si vence la URL, el consumidor puede iniciar otra consulta completa.
Los SOAP Fault conservan `DianSoapFaultError`.

Las pruebas son sintéticas. La aceptación del certificado y el contenido real del
archivo requieren una consulta autorizada contra DIAN.
