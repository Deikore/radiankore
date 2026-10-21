# Consultar el estado de validación de un documento

`GetStatus` consulta el resultado de validación del documento en DIAN. Es distinto
de `GetStatusEvent`, que consulta los eventos asociados a una factura en RADIAN.
El método recibe el CUFE o track ID y utiliza el certificado y ambiente del cliente:

```python
from radiankore import DianClient
from radiankore.models.responses import DocumentStatusResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
status: DocumentStatusResult | None = client.get_status("CUFE-O-TRACK-ID")
if status is not None:
    print(status.is_valid, status.status_code, status.status_description)
    print(status.status_message, status.messages)
    print(status.document_key, status.file_name)
    if status.xml_base64_bytes is not None:
        print("Bytes de XmlBase64Bytes:", len(status.xml_base64_bytes))
    if status.xml_bytes is not None:
        print("Bytes de XmlBytes:", len(status.xml_bytes))
```

`track_id` debe ser `str` no vacío tras recortar espacios exteriores. Se envía como
`trackId`, sin imponer formato hexadecimal ni UUID. Tipos incorrectos generan
`TypeError`; texto vacío genera `ValueError` antes de abrir conexiones.

`DocumentStatusResult` es una dataclass inmutable con slots y argumentos por nombre,
definida en `models/responses/document_status.py` y exportada desde
`radiankore.models.responses`. Representa todos los campos de `DianResponse`:

| Campo | Elemento XML | Tipo |
| --- | --- | --- |
| `is_valid` | `IsValid` | `bool \| None` |
| `status_code` | `StatusCode` | `str \| None` |
| `status_description` | `StatusDescription` | `str \| None` |
| `status_message` | `StatusMessage` | `str \| None` |
| `messages` | `ErrorMessage/string` | `tuple[str \| None, ...]` |
| `document_key` | `XmlDocumentKey` | `str \| None` |
| `file_name` | `XmlFileName` | `str \| None` |
| `xml_base64_bytes` | `XmlBase64Bytes`, decodificado | `bytes \| None` |
| `xml_bytes` | `XmlBytes`, decodificado | `bytes \| None` |

Un resultado ausente o nulo devuelve `None`; uno presente y vacío devuelve
`DocumentStatusResult()`. Los textos escalares ausentes, nulos o vacíos valen
`None`; se recortan espacios exteriores. `IsValid` ausente queda en `None`; presente
admite `true`, `false`, `1` y `0`. Un valor nulo o inválido genera `DianResponseError`.
`messages` conserva orden, repeticiones, elementos nulos y cadenas vacías; recorta
espacios exteriores. Su contenedor ausente, nulo o vacío produce `()`.

`is_valid=False` es un resultado de negocio: no genera una excepción ni descarta
mensajes o payloads. Los códigos se conservan como texto sin inferir su significado.
La validación del documento no demuestra que existan aceptación o endosos RADIAN.

Ambos campos binarios se decodifican independientemente, sin fallback, usando
Base64 estricto con espacios XML permitidos. Se conservan exactamente sus bytes y
se excluyen de `repr`. Ausente o nulo produce `None`; presente vacío produce `b""`.
Base64 inválido genera `DianResponseError` conservando la causa. No se interpreta,
reformatea ni descomprime el contenido, ni se exige una raíz XML particular.
El modelado de reglas internas del `ApplicationResponse` queda fuera de este método.
Consulta el [contrato SOAP local](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md#getstatus).
