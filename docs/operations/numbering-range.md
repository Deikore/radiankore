# Rangos de numeración: GetNumberingRange

Consulta los rangos de numeración autorizados y sus claves técnicas. La operación
no solicita nuevas autorizaciones ni genera facturas.

```python
from radiankore import DianClient

client = DianClient("/ruta/segura/certificado.pfx", password="password-de-ejemplo")
result = client.get_numbering_range(
    account_code="900000001",
    account_code_t="900000002",
    software_code="identificador-del-software",
)
if result is not None:
    print(result.operation_code, result.operation_description)
    for item in result.ranges:
        if item is not None:
            print(item.resolution_number, item.prefix, item.from_number, item.to_number)
```

## Parámetros y ambiente

Los tres parámetros son obligatorios y se pasan por nombre:

- `account_code`: NIT del facturador, sin separadores ni dígito de verificación.
- `account_code_t`: NIT del dueño del software, con las mismas condiciones.
  En software propio puede coincidir con el del facturador.
- `software_code`: identificador del software asignado por DIAN.

Se exigen cadenas no vacías tras recortar espacios exteriores. Los NIT solo
admiten dígitos ASCII; se conservan los ceros iniciales. La librería no calcula,
verifica ni elimina dígitos de verificación. No se impone formato UUID o longitud
al identificador del software. Tipos incorrectos generan `TypeError`; valores
vacíos o NIT con caracteres inválidos generan `ValueError`, antes de contactar DIAN.

DIAN declara disponibilidad únicamente en producción, aunque ambos WSDL publican
la operación. El cliente respeta el ambiente seleccionado, también en habilitación,
sin fallback ni cambiarlo automáticamente. Producción es predeterminada.
[Anexo técnico DIAN 1.9, sección 7.15](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf).

## Resultado

Los modelos se importan desde `radiankore.models.responses`. Son dataclasses
inmutables con slots y argumentos por nombre.

`NumberingRangeResult` contiene `operation_code: str | None`,
`operation_description: str | None` y `ranges: tuple[NumberingRange | None, ...]`.

| Campo de `NumberingRange` | XML | Tipo |
| --- | --- | --- |
| `resolution_number` | `ResolutionNumber` | `str \| None` |
| `resolution_date` | `ResolutionDate` | `datetime.date \| None` |
| `prefix` | `Prefix` | `str \| None` |
| `from_number` | `FromNumber` | `int \| None` |
| `to_number` | `ToNumber` | `int \| None` |
| `valid_date_from` | `ValidDateFrom` | `datetime.date \| None` |
| `valid_date_to` | `ValidDateTo` | `datetime.date \| None` |
| `technical_key` | `TechnicalKey` | `str \| None`, excluido de `repr` |

Se conservan el orden XML, los duplicados y los elementos nulos. No se filtran
rangos vencidos ni se comprueba que los límites estén ordenados. Los números de
resolución conservan sus ceros iniciales. Las fechas requieren `YYYY-MM-DD`,
conforme al ejemplo SOAP del anexo, sin zona horaria. Los límites son enteros
firmados de 64 bits (`xs:long`); los elementos ausentes valen `None`, pero no
admiten nulo, vacío, decimales ni valores fuera de rango.

Un resultado SOAP ausente o nulo devuelve `None`; uno vacío devuelve
`NumberingRangeResult()`. `ResponseList` ausente, nulo o vacío produce `ranges=()`.
Los campos de texto y fecha ausentes, nulos o vacíos producen `None`.

## Estados y errores

`OperationCode` es un código de negocio, independiente del transporte HTTP:

| Código | Significado documentado por DIAN |
| --- | --- |
| `100` | Acción completada correctamente |
| `301` | No se encontraron rangos para el NIT del facturador |
| `302` | No hay prefijos asociados al software |
| `303` | El software no corresponde al NIT de su dueño |
| `401` | Consulta no autorizada |
| `500` | Error del servicio |

Se devuelve como texto, también para códigos desconocidos, sin convertirlo a
`HTTPStatus`, generar excepciones ni descartar rangos. Un resultado de negocio
`401` es distinto de un HTTP 401 del transporte.

SOAP, fechas o límites numéricos inválidos generan `DianResponseError`.
Los errores HTTP o de red conservan `DianTransportError`; los SOAP Fault conservan
`DianSoapFaultError`. Las conexiones se cierran automáticamente y el certificado
se reutiliza. Las pruebas son sintéticas; la aceptación del certificado requiere
una consulta autorizada contra DIAN.
