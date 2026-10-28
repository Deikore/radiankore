# radiankore

Librería Python de Deikore SAS para consultar servicios de DIAN y emitir eventos
RADIAN con certificado digital PFX/P12. Python >=3.13, clientes asíncrono y
síncrono, licencia MIT.

| | Estado |
| --- | --- |
| Documentación | [![Read the Docs](https://readthedocs.org/projects/radiankore/badge/?version=latest)](https://radiankore.readthedocs.io/) |
| Calidad y pruebas | [![CI](https://github.com/Deikore/radiankore/actions/workflows/ci.yml/badge.svg)](https://github.com/Deikore/radiankore/actions/workflows/ci.yml) |
| Paquete | [![PyPI](https://img.shields.io/pypi/v/radiankore)](https://pypi.org/project/radiankore/) [![Python](https://img.shields.io/pypi/pyversions/radiankore)](https://pypi.org/project/radiankore/) [![MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/Deikore/radiankore/blob/HEAD/LICENSE) |

## Rendimiento observado con DIAN

Consultas reales de eventos en producción, realizadas el **28 de octubre de
2026** con radiankore 0.7.0. Medianas del tiempo total de lote, tres repeticiones
por configuración y dos workers de procesamiento:

| CUFEs por lote | Concurrencia 5 | Concurrencia 10 | Concurrencia 20 |
| ---: | ---: | ---: | ---: |
| 100 | 8,56 s | 4,64 s | 3,27 s |
| 500 | 44,29 s | 21,51 s | 11,42 s |
| 1.000 | 89,58 s | 44,78 s | 22,41 s |

Las **14.400 consultas** terminaron sin excepciones, timeouts ni reintentos.
Son observaciones de estos ensayos, no una capacidad garantizada de DIAN.
Los clientes se crearon por muestra, sin calentamiento; carga del certificado y
cierre se midieron aparte. La
[guía de benchmarks](https://radiankore.readthedocs.io/en/latest/guides/event-query-benchmark.html)
conserva percentiles, condiciones, JSON originales y diferencias entre muestras,
incluido un p99 de 4,57 s. Las
[comparaciones locales](https://radiankore.readthedocs.io/en/latest/ASYNC_ARCHITECTURE_PLAN.html)
separan resultados simulados y objetivos pendientes.

## Instalación

```bash
pip install radiankore
# Con uv:
uv add radiankore
```

Consulte la [instalación](https://radiankore.readthedocs.io/en/latest/installation.html)
para compilar conjuntamente las dependencias de firma cuando sea necesario.

## Consultar eventos con AsyncDianClient

Guarde este ejemplo en un archivo Python y sustituya la ruta y el CUFE por sus
datos. La consulta contacta el ambiente de producción seleccionado explícitamente.

```python
import asyncio
from getpass import getpass

from radiankore import AsyncDianClient, Environment


async def query_events(cufe, password):
    client = await AsyncDianClient.from_file(
        "/ruta/segura/certificado.pfx",
        password=password,
        environment=Environment.PRODUCTION,
    )
    async with client:
        return await client.get_invoice_events(cufe)


if __name__ == "__main__":
    result = asyncio.run(
        query_events("CUFE-DE-LA-FACTURA", getpass("Contraseña del certificado: "))
    )
    print(result.is_valid, result.status_code)
    for event in result.events:
        print(event.id, event.code, event.description, event.date, event.time)
```

El certificado se carga fuera del event loop y `async with` cierra los recursos.
La [guía async](https://radiankore.readthedocs.io/en/latest/guides/async.html)
incluye lotes con `iter_queries`, correlación por CUFE, errores individuales y
un puente para obtener resultados desde código síncrono.

## Preparar y enviar eventos con await

Este ejemplo recibe un modelo público de evento y un `RadianSoftware` construidos
por el consumidor. La
[guía async](https://radiankore.readthedocs.io/en/latest/guides/async.html)
incluye la construcción completa de un acuse 030 con datos ficticios.

```python
from radiankore import AsyncDianClient, Environment


async def send_event(pfx_bytes, password, event, software):
    client = await AsyncDianClient.from_pfx(
        pfx_bytes,
        password=password,
        environment=Environment.HABILITATION,
    )
    async with client:
        prepared = await client.prepare_radian_event(event=event, software=software)
        # Retain and inspect this exact artifact before authorizing transmission.
        result = await client.send_radian_event(prepared)
        return prepared, result
```

La preparación firma y comprime localmente. El envío transmite el ZIP original
una sola vez y exige el mismo ambiente. Ante un fallo después de iniciar el
envío, conserve el artefacto: el resultado puede ser desconocido y no debe
reenviarse automáticamente. `None` no confirma aceptación.

Los [ejemplos por familia](https://radiankore.readthedocs.io/en/latest/operations/radian-emission.html)
describen los modelos de eventos 030–051. La librería no genera facturas.

## Operaciones disponibles

Ambos clientes comparten argumentos y modelos de respuesta; las operaciones de
`AsyncDianClient` se esperan con `await`.

| Método | Operación DIAN | Resultado |
| --- | --- | --- |
| `get_numbering_range(account_code=..., account_code_t=..., software_code=...)` | `GetNumberingRange` | Rangos de numeración autorizados y clave técnica |
| `get_exchange_emails()` | `GetExchangeEmails` | Registros del CSV del directorio de correos |
| `get_status(track_id)` | `GetStatus` | Estado de validación y payloads decodificados |
| `get_invoice_events(cufe)` | `GetStatusEvent` | Eventos asociados a una factura |
| `get_acquirer(identification_type=..., identification_number=...)` | `GetAcquirer` | Nombre y correo del adquiriente |
| `get_document_info(uuid)` | `GetDocumentInfo` | Información, estados, eventos y notas del documento |
| `get_reference_notes(track_id)` | `GetReferenceNotes` | Notas referenciadas y motivos por línea |
| `get_xml_by_document_key(document_key)` | `GetXmlByDocumentKey` | XML original del documento como `bytes` |
| `prepare_radian_event(event=..., software=...)` | Local | XML firmado, CUDE y ZIP de los eventos 030–051 |
| `send_radian_event(prepared)` | `SendEventUpdateStatus` | Emisión del evento RADIAN preparado |


Los resultados utilizan dataclasses inmutables y campos opcionales cuando
corresponda. `AsyncDianClient` reutiliza sus pools durante su vida y admite
consultas concurrentes, con límites configurables y sin reintentos automáticos.

## Cliente síncrono

`DianClient` conserva su API y sus defaults. Para llamadas síncronas directas:

```python
from radiankore import DianClient, Environment


def query_events_sync(pfx_bytes, password, cufe):
    with DianClient.from_pfx(
        pfx_bytes,
        password=password,
        environment=Environment.PRODUCTION,
        reuse_connections=True,
    ) as client:
        return client.get_invoice_events(cufe)
```

Consulte la [API](https://radiankore.readthedocs.io/en/latest/api.html) y
[rendimiento y ciclo de vida](https://radiankore.readthedocs.io/en/latest/guides/performance.html).
El cliente sync cierra por operación salvo que se active su reutilización opcional;
el cliente async se cierra mediante `async with` o `await client.aclose()`.

La [documentación completa](https://radiankore.readthedocs.io/) incluye contratos,
modelos, errores y ejemplos. Para contribuir, consulte
[CONTRIBUTING](https://github.com/Deikore/radiankore/blob/HEAD/CONTRIBUTING.md).
