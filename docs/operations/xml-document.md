# Descargar el XML de un documento

`GetXmlByDocumentKey` recibe la clave de un documento y devuelve sus bytes originales
junto con el código, mensaje y fecha de validación de `EventResponse`:

```python
from http import HTTPStatus
from pathlib import Path

from radiankore import DianClient
from radiankore.models.responses import XmlDocumentResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
result: XmlDocumentResult | None = client.get_xml_by_document_key("CLAVE-DEL-DOCUMENTO")
if result is not None:
    if result.status_code is HTTPStatus.NOT_FOUND:
        print("Documento no encontrado")
    if result.status_code is not None:
        print(result.status_code.value, result.status_code.phrase)
    print(result.message, result.validation_date)
    if result.document_xml is not None:
        Path("documento.xml").write_bytes(result.document_xml)
```

La clave debe ser `str` no vacío tras recortar espacios exteriores; se envía como
`trackId` sin imponer un formato hexadecimal o UUID. Tipos incorrectos generan
`TypeError` y texto vacío genera `ValueError` antes de abrir conexiones. Se reutiliza
el certificado y el ambiente del cliente, con producción por defecto.

`XmlDocumentResult` es una dataclass inmutable con slots y argumentos por nombre,
definida en `models/responses/xml_document.py` y exportada desde
`radiankore.models.responses`:

| Campo | Elemento XML | Tipo |
| --- | --- | --- |
| `status_code` | `Code` | `HTTPStatus \| None` |
| `message` | `Message` | `str \| None` |
| `validation_date` | `ValidationDate` | `date \| datetime \| None` |
| `document_xml` | `XmlBytesBase64`, decodificado | `bytes \| None` |

El resultado ausente o nulo devuelve `None`; uno presente y vacío devuelve
`XmlDocumentResult()`. Código y mensaje ausentes, nulos o vacíos valen `None`;
se recortan espacios exteriores. `Code` debe contener tres dígitos ASCII y se
convierte con `HTTPStatus(int(value))`, de la biblioteca estándar `http`:
`"200"` corresponde a `HTTPStatus.OK` y `"404"` a `HTTPStatus.NOT_FOUND`.
Códigos desconocidos o formatos inválidos generan `DianResponseError`, conservando
`ValueError` como causa. La construcción directa de `XmlDocumentResult` exige
`HTTPStatus` o `None`; cadenas, enteros y otros tipos generan `TypeError`.

El código del SOAP es independiente del estado HTTP del transporte. Una petición
HTTP 200 con `<Code>404</Code>` devuelve un resultado con `HTTPStatus.NOT_FOUND`;
una petición HTTP 404 sigue generando `DianTransportError`. Un estado estándar
como `HTTPStatus.NOT_FOUND` dentro del resultado no genera una excepción.

Este campo antes era `str | None`: sustituye las comparaciones con cadenas por
miembros de `HTTPStatus`, y usa `.value` si necesitas el entero correspondiente.

`ValidationDate` acepta fechas ISO mediante `date.fromisoformat()` y timestamps
ISO mediante `datetime.fromisoformat()`, conservando hora, fracciones y zona si
vienen. Una fecha sola devuelve `date`, sin inventar una hora; un timestamp sin
zona mantiene `tzinfo=None`. No se convierte a Colombia ni se asume zona local.
Ausente, nulo o vacío produce `None`; formatos inválidos generan `DianResponseError`
con `ValueError` como causa. Esta política es provisional: el WSDL declara una
cadena y no especifica su formato; falta contrastarla con una muestra real.

`XmlBytesBase64` se asume Base64 del documento. Se decodifica admitiendo espacios
XML y se guarda en `document_xml`, excluido de `repr`. Se conservan exactamente
encoding, declaración XML, espacios y saltos de línea. Un campo ausente/nulo vale
`None`; presente vacío vale `b""`. Base64 inválido genera `DianResponseError` con
la causa original. Los bytes no se convierten a texto, no se reformatean ni se
descomprimen, y no se exige un tipo raíz ni se verifica la firma del documento.
Consulta el [contrato SOAP local](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md#getxmlbydocumentkey).
