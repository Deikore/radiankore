# Consultar datos de un adquiriente

`GetAcquirer` permite consultar nombre o razón social y correo electrónico de un
comprador. Utilice el mismo cliente, certificado y ambiente de las demás consultas:

```python
from radiankore import DianClient
from radiankore.catalogs import IdentificationType
from radiankore.models.responses import AcquirerResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
acquirer: AcquirerResult | None = client.get_acquirer(
    identification_type=IdentificationType.NIT,
    identification_number="000123456",
)
if acquirer is not None:
    print(acquirer.name, acquirer.email, acquirer.status_code, acquirer.message)
```

Ambos argumentos son obligatorios. El tipo debe ser un miembro de
`IdentificationType`, incluido `IdentificationType.PPT` (`"48"`); el número debe
ser `str`. Tipos incorrectos generan `TypeError`. Se quitan espacios exteriores y
un número vacío genera `ValueError`, antes de firmar o abrir conexiones. No se
modifican ceros iniciales ni se calcula o añade dígito de verificación.

`AcquirerResult` es una dataclass inmutable, con slots y argumentos por nombre.
Sus cuatro campos son opcionales:

| Campo | Elemento XML |
| --- | --- |
| `name` | `ReceiverName` |
| `email` | `ReceiverEmail` |
| `status_code` | `StatusCode` |
| `message` | `Message` |

Campos ausentes, nulos o vacíos valen `None`; los textos se recortan exteriormente.
Un resultado ausente o declarado nulo devuelve `None`. Un resultado presente pero
vacío devuelve `AcquirerResult()` con sus cuatro campos en `None`. Esto no se
interpreta automáticamente como «no encontrado».

Si DIAN responde HTTP 404 a `GetAcquirer`, el método devuelve `None`. Los demás
errores HTTP y de red conservan sus excepciones. Un SOAP Fault también se propaga,
incluso cuando llega con HTTP 404.

El WSDL no define el significado de los códigos de estado. Se devuelven tal como
se reciben, sin inferir éxito ni convertir estados de negocio en excepciones.
Los fallos SOAP, HTTP, de red o de estructura XML usan las excepciones públicas.
La respuesta es XML SOAP directo y no requiere decodificar Base64 ni procesar UBL.
