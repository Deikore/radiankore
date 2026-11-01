# Límites de respuestas y descompresión

Desde **0.7.1**, ambos clientes limitan las respuestas y el CSV de
`get_exchange_emails` de forma predeterminada. `DianResponseLimits` se importa
desde `radiankore`; es una dataclass inmutable, con slots y argumentos por nombre.

| Campo | Predeterminado | Qué se cuenta |
| --- | ---: | --- |
| `soap_bytes` | 16 MiB (`16 * 1024 * 1024`) | Cuerpo SOAP después de la decodificación HTTP, incluida compresión HTTP |
| `download_bytes` | 64 MiB (`64 * 1024 * 1024`) | ZIP descargado después de la decodificación HTTP |
| `csv_bytes` | 128 MiB (`128 * 1024 * 1024`) | Miembro CSV descomprimido, antes de decodificar UTF-8 |

Los límites se aplican por respuesta o CSV, no al acumulado de consultas del
cliente. Son una política de la librería, no cuotas publicadas por DIAN.
Buffers, árboles XML, texto y diccionarios requieren memoria adicional:
estos valores no representan un límite exacto de memoria residente.

## Configuración compartida

Todos los constructores y fábricas de ambos clientes aceptan
`response_limits: DianResponseLimits | None = None`. Omitirlo o pasar `None`
**activa los valores predeterminados**. El tipo de configuración se valida antes
de leer o decodificar el certificado.

El consumidor proporciona el certificado ya cargado y el CUFE; estas funciones
solo hacen consultas cuando se invocan:

```python
from radiankore import (
    AsyncDianClient,
    DianClient,
    DianResponseLimits,
    DigitalCertificate,
)

limits = DianResponseLimits(
    soap_bytes=32 * 1024 * 1024,
    csv_bytes=None,
)
# El ZIP conserva su límite predeterminado de 64 MiB.


def query_with_limits(certificate: DigitalCertificate, cufe: str):
    with DianClient.from_certificate(certificate, response_limits=limits) as client:
        return client.get_invoice_events(cufe)


async def query_with_limits_async(certificate: DigitalCertificate, cufe: str):
    async with AsyncDianClient.from_certificate(
        certificate, response_limits=limits
    ) as client:
        return await client.get_invoice_events(cufe)
```

Cada campo admite un entero positivo en bytes, o `None` para desactivar
únicamente ese límite. `DianResponseLimits(csv_bytes=None)` conserva los topes
SOAP y ZIP. Booleanos y otros tipos generan `TypeError`; cero y negativos,
`ValueError`. No existe configuración global mutable.

Para desactivar explícitamente los tres límites:

```python
unlimited = DianResponseLimits(
    soap_bytes=None,
    download_bytes=None,
    csv_bytes=None,
)
```

La configuración no cambia las protecciones propias del parser XML, los
timeouts ni el límite de 500.000 bytes de XML firmado para emisión.

## Lectura y errores

Los cuerpos HTTP se acumulan en bloques de hasta 64 KiB, comprobando el límite
antes de incorporar cada bloque. Se cuentan bytes efectivamente decodificados;
una cabecera `Content-Length` ausente o incorrecta no evita la comprobación.

El ZIP debe contener exactamente un CSV. Se comprueba su tamaño declarado antes
de abrirlo y se limita también la lectura efectiva del miembro. Solo se
descomprime ese CSV, sin escribir archivos al disco. Se preservan el orden,
los encabezados y los valores originales de las filas aceptadas.

| Exceso | Excepción |
| --- | --- |
| Cuerpo SOAP o ZIP descargado | `DianTransportError` |
| CSV descomprimido | `DianResponseError` |

Un exceso detiene el procesamiento y cierra el stream, sin resultado parcial ni
URLs firmadas o contenido en el mensaje de error. Un pool reutilizable sigue
disponible para operaciones posteriores. Si el cuerpo excede el tope no llega
a interpretarse como SOAP Fault ni respuesta de negocio. Los cuerpos que caben
conservan los contratos habituales de parsing y errores.

## Migración desde 0.7.0

Antes no había topes configurables de respuesta. Una carga que supere los
predeterminados ahora genera una excepción. Aumente el campo correspondiente o
desactívelo expresamente cuando la aplicación necesite aceptar esa carga.
No se alteran datos ni se recortan respuestas para hacerlas caber.

En aplicaciones concurrentes, dimensione conjuntamente topes y concurrencia:
varias respuestas pueden coexistir en memoria. El procesamiento XML, ZIP y CSV
asíncrono permanece fuera del event loop y conserva su cupo físico si se cancela
la espera.
