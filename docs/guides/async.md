# API asíncrona y consultas masivas

Disponible desde **radiankore 0.7.0**. `AsyncDianClient` usa HTTPX
asíncrono para la red y un executor acotado para certificados, firma, XML y ZIP.
`DianClient` conserva su API síncrona, sus defaults y su cierre por operación
salvo que se active su reutilización opcional.

## Construcción y recursos

```python
from radiankore import AsyncDianClient, DianTimeouts, Environment


async def consultar(pfx_bytes: bytes, password: str, cufe: str):
    client = await AsyncDianClient.from_pfx(
        pfx_bytes,
        password=password,
        environment=Environment.HABILITATION,
        concurrency=5,
        processing_workers=2,
        timeouts=DianTimeouts(total=60),
    )
    async with client:
        return await client.get_invoice_events(cufe)
```

El consumidor proporciona material y datos; el ejemplo no se ejecuta contra DIAN
como parte de las pruebas. `await AsyncDianClient.from_file(path, password=...)`
lee un archivo y carga PKCS#12 fuera del event loop. `from_pfx` decodifica bytes
fuera del loop. `AsyncDianClient.from_certificate(certificate, ...)` y el
constructor directo `AsyncDianClient(certificate, ...)` son síncronos y no
realizan I/O. Las fábricas validan opciones antes de leer el certificado.

Los argumentos comunes son `environment`, `timeouts`, `concurrency`,
`processing_workers` y `limiter`. El ambiente predeterminado es producción.
Cada cliente tiene un certificado y ambiente fijos; crearlo no verifica
confianza, revocación, vigencia ni autorización de ese material.

Use `async with` o `await client.aclose()`. El cliente crea de forma diferida dos
pools propios, uno SOAP y otro de descarga. Reutiliza HTTP/1.1 y TLS durante su
vida, con hasta `concurrency` conexiones y conexiones inactivas por pool, y
expiración de keep-alive de 30 segundos. No almacena ni devuelve cookies y no
sigue redirecciones. Respeta la configuración de proxies y CA de HTTPX; la
verificación TLS permanece activada.

El cliente y el limitador se vinculan al primer event loop utilizado y al
proceso de construcción. No se comparten entre loops ni se heredan tras `fork`.
Cree los clientes después de crear procesos. La misma instancia async admite
llamadas concurrentes; no comparta su objeto nativo `DigitalCertificate`
concurrentemente con otro cliente. Para clientes independientes, cargue
independientemente el material. No modifique la clave nativa expuesta.

## Operaciones

Las ocho consultas mantienen los argumentos, validaciones y tipos de respuesta
de la [API síncrona](../api.md), añadiendo `await`:

- `get_invoice_events(cufe)`
- `get_status(track_id)`
- `get_document_info(uuid)`
- `get_reference_notes(track_id)`
- `get_xml_by_document_key(document_key)`
- `get_numbering_range(*, account_code, account_code_t, software_code)`
- `get_acquirer(*, identification_type, identification_number)`
- `get_exchange_emails()`

Se conservan estados de negocio, orden, repeticiones, `Decimal`, fechas, bytes
originales y resultados ausentes. Solo `get_acquirer` traduce HTTP 404 a `None`.
`get_exchange_emails` incluye SOAP, descarga y parsing del CSV en una misma
operación; no entrega un resultado parcial si falla una etapa.

Los modelos, builders y dos perfiles de firma son compartidos. Los árboles XML,
claves y contextos xmlsec son privados por trabajo. La preparación también se
espera porque consume CPU:

```python
async def preparar_y_enviar(client, event, software):
    prepared = await client.prepare_radian_event(event=event, software=software)
    # Inspeccionar/persistir prepared y su ambiente antes del envío explícito.
    result = await client.send_radian_event(prepared)
    return prepared, result
```

Preparar no transmite, no carga archivos y no abre pools HTTP. Enviar utiliza el
ZIP original una sola vez, sin reconstruir XML ni reintentar. `None` no confirma
aceptación. Ante cancelación o fallo después de iniciar el envío, conserve el
artefacto y trate el resultado como desconocido. Una consulta negativa tampoco
prueba que no llegó; confirme evidencia e identidad antes de decidir un reenvío.

## Ejemplo completo: acuse 030 con await

La función siguiente construye participantes, referencia, persona receptora y
software con datos ficticios. El consumidor debe sustituirlos por información y
declaraciones que pueda emitir. Se selecciona habilitación explícitamente;
preparar es local y la llamada a `send_radian_event` sí transmite a DIAN.

```python
from datetime import datetime, timedelta, timezone

from radiankore import AsyncDianClient, Environment
from radiankore.catalogs import (
    EventType,
    IdentificationType,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events import (
    InvoiceEventDocumentReference,
    InvoiceEventParty,
    InvoiceEventPerson,
    InvoiceResponseEvent,
    RadianSoftware,
)


async def send_acknowledgement(pfx_bytes: bytes, password: str):
    client = await AsyncDianClient.from_pfx(
        pfx_bytes,
        password=password,
        environment=Environment.HABILITATION,
    )
    async with client:
        buyer = InvoiceEventParty(
            name="Adquirente sintético",
            tax_number="900000001",
            identification_type=IdentificationType.NIT,
            verification_digit="1",
            organization_type=OrganizationType.LEGAL_PERSON,
            tax_scheme=PartyTaxScheme.VAT,
        )
        seller = InvoiceEventParty(
            name="Facturador sintético",
            tax_number="900000002",
            identification_type=IdentificationType.NIT,
            verification_digit="2",
            organization_type=OrganizationType.NATURAL_PERSON,
            tax_scheme=PartyTaxScheme.NOT_APPLICABLE,
        )
        person = InvoiceEventPerson(
            identification_number="100000003",
            identification_type=IdentificationType.CITIZENSHIP_CARD,
            first_name="Persona",
            family_name="Sintética",
            job_title="Recepción",
            organization_department="Compras",
        )
        reference = InvoiceEventDocumentReference(
            document_number="FE-PRUEBA-1",
            uuid="a" * 96,
        )
        stamp = datetime.now(timezone(timedelta(hours=-5)))

        acknowledgement = InvoiceResponseEvent(
            code=EventType.INVOICE_ACKNOWLEDGEMENT,
            event_number="ACUSE-1",
            issue_date=stamp.date(),
            issue_time=stamp.timetz(),
            sender_party=buyer,
            receiver_party=seller,
            document_reference=reference,
            issuer_person=person,
        )
        software = RadianSoftware(
            software_id="00000000-0000-4000-8000-000000000001",
            pin="pin-sintético",
            provider_tax_number="900000002",
            provider_verification_digit="2",
            signer_role="thirdparty",
        )
        prepared = await client.prepare_radian_event(
            event=acknowledgement,
            software=software,
        )
        # Persist or inspect this exact artifact before authorizing transmission.
        result = await client.send_radian_event(prepared)
        return prepared, result
```

La función recibe el PFX y su contraseña desde el consumidor; no los conserva en
logs ni hace reintentos. Devuelve tanto `PreparedRadianEvent` como la respuesta
para conservar CUDE, ambiente y bytes exactos. Un timeout o cancelación después
de iniciar el envío puede dejar el resultado desconocido: consulte la
[operación y reconciliación](operations.md) antes de decidir un reenvío.
Las [guías de factura](../operations/invoice-emission.md),
[mandato](../operations/mandate.md) y
[otras familias](../operations/radian-emission.md) describen los demás modelos;
se utilizan con la misma pareja de métodos esperables.

## Timeouts y cancelación

`DianTimeouts` es una dataclass inmutable y con argumentos por nombre:

| Campo | Segundos predeterminados | Alcance |
| --- | ---: | --- |
| `connect` | 5 | Conexión TCP/TLS |
| `read` | 30 | Espera por datos HTTP |
| `write` | 30 | Escritura HTTP |
| `pool` | 5 | Espera por conexión del pool |
| `total` | 60 | Admisión, procesamiento local, red y parsing |

`total=None` desactiva únicamente el plazo total. Cantidades y timeouts deben
ser positivos y finitos; los booleanos no son cantidades válidas.

Un plazo total vencido produce `DianTransportError` con `TimeoutError` como
causa. Los errores HTTPX mantienen su causa y `status_code` cuando corresponde.
Un SOAP Fault interpretable mantiene prioridad sobre el código HTTP. Los
errores de certificados y de XML conservan sus clases existentes.

`CancelledError` se propaga; no se transforma en un resultado de lote. Cancelar
la espera no detiene una firma nativa ya iniciada: su plaza se conserva hasta
que termine físicamente. Los streams HTTP se cierran al interrumpirlos.

`aclose()` es idempotente, impide nuevas operaciones, cancela coordinadores de
lotes, drena operaciones activas e inicializadores, y cierra pools y executor.
El cierre no bloquea el hilo del loop mientras espera trabajos nativos.
Cancelar a quien espera `aclose()` deja continuar el cierre; vuelva a esperarlo
para unirse a él. Un trabajo nativo detenido indefinidamente puede prolongar el
cierre: no existe interrupción forzada segura de esa función.

## Concurrencia y tasa compartidas

```python
from radiankore import AsyncDianClient, AsyncDianLimiter

limiter = AsyncDianLimiter(
    concurrency=10,
    requests_per_second=2,
    service_limits={
        "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc": 5,
    },
)
# Pasar limiter=limiter a varios clientes del mismo proceso y loop.
```

Los números son ejemplos de configuración, no cuotas verificadas de DIAN.
El SDK no establece una tasa predeterminada. `concurrency=5` en el cliente limita
operaciones completas; `processing_workers=2` limita trabajos locales enviados
al executor, incluyendo los cuyo consumidor se canceló. No crea un hilo por
consulta ni una cola ilimitada de trabajos nativos.

Un `AsyncDianLimiter` compartido limita intercambios HTTP entre clientes y
permite una tasa global de inicios. `service_limits` utiliza el endpoint SOAP
exacto o el origen de descarga terminado en `/`; nunca la URL firmada completa.
La configuración se fija al construirlo. No coordina procesos o máquinas.

Un `Retry-After` válido de una respuesta HTTP de error pausa nuevos intentos al
servicio afectado. `DianTransportError.retry_after` devuelve segundos o `None`.
Se aceptan delta-seconds y HTTP-date; valores inválidos se ignoran. El SDK
propaga el fallo original sin repetir la solicitud. Las esperas por tasa y
cooldown consumen el plazo total. Se renueva un sobre que haya envejecido durante
esa espera; no se reutilizan firmas SOAP entre solicitudes.

Los reintentos pertenecen al consumidor: solo para consultas transitorias,
recomendamos un presupuesto total, hasta tres intentos, backoff exponencial con
full jitter y respeto de `retry_after`. No reintente automáticamente certificados,
firmas, XML inválido, SOAP Faults ni emisiones. No registre excepciones completas,
XML, URLs firmadas o material criptográfico; evite logs detallados de HTTPX que
puedan exponer URLs de descarga.

## Streaming con backpressure

```python
from collections.abc import AsyncIterator, Iterable
from contextlib import aclosing

from radiankore import AsyncDianClient


async def resultados(client: AsyncDianClient, cufes: Iterable[str]):
    async with aclosing(
        client.iter_queries(cufes, client.get_invoice_events)
    ) as stream:
        async for result in stream:
            if result.error is not None:
                # Clasificar sin registrar datos privados de la excepción.
                yield result.index, "error"
            else:
                yield result.index, result.value
```

`iter_queries(items, query, *, workers=None, buffer_size=None)` acepta un
`Iterable[T]` que avance sin I/O bloqueante o un `AsyncIterable[T]`.
`query` recibe un elemento y devuelve un awaitable. Su uso previsto son consultas;
una función con efectos externos sigue siendo responsabilidad del consumidor.

Por defecto hay tantos workers como concurrencia del cliente y dos colas de
`2 * workers` elementos cada una. Un productor y un coordinador completan el
conjunto fijo de tareas; no se crean 100.000 tareas para 100.000 entradas.

`QueryResult[T, R]` es una dataclass inmutable con `index`, `item`, `value` y
`error`. El índice original correlaciona duplicados y los resultados llegan en
orden de finalización. `error is None` indica éxito, incluso si `value is None`.
Las excepciones individuales de `query` son resultados; errores de la fuente
interrumpen el lote. Los payloads y excepciones no aparecen en `repr`.

Use `aclosing` al salir anticipadamente: cierra productor y workers aun cuando
las colas estén llenas. El cliente también cancela sus lotes al cerrarse. No
acumule resultados si necesita memoria independiente del tamaño del lote.
El consumo del SDK depende de buffers, operaciones activas, tamaño de cada
respuesta y servicios con cooldown, no de una lista de entradas materializada.
Cada respuesta individual aún se decodifica completa en memoria; streaming de
consultas no equivale a streaming de XML, CSV o ZIP dentro de una respuesta.

## Obtener resultados por CUFE desde código síncrono

Este ejemplo devuelve una lista de `QueryResult` correlacionados por `item`
(CUFE) e `index`, sin perder duplicados. Los errores individuales permanecen en
`error`; los resultados llegan en orden de finalización. La lista es una decisión
del consumidor: para memoria independiente del lote, use el streaming anterior.

```python
import asyncio
from contextlib import aclosing

from radiankore import AsyncDianClient, Environment


async def query_many(pfx_bytes, password, cufes):
    client = await AsyncDianClient.from_pfx(
        pfx_bytes,
        password=password,
        environment=Environment.PRODUCTION,
        concurrency=5,
    )
    async with client:
        async with aclosing(
            client.iter_queries(cufes, client.get_invoice_events)
        ) as stream:
            return [result async for result in stream]


def query_many_sync(pfx_bytes, password, cufes):
    return asyncio.run(query_many(pfx_bytes, password, cufes))


def print_event_results(results):
    for query in results:
        if query.error is not None:
            print(query.index, query.item, type(query.error).__name__)
        elif query.value is not None:
            print(query.index, query.item, query.value.status_code)
            for event in query.value.events:
                print(event.code, event.description, event.uuid)
```

Llame `query_many_sync(pfx_bytes, password, cufes)` con su lista, por ejemplo de
100 CUFEs reales, desde un script o función síncrona. Use `await query_many(...)`
cuando ya exista un event loop activo en el mismo hilo. El puente crea y cierra
el cliente dentro de una única ejecución de `asyncio.run()`: no reutilice ese
cliente entre llamadas. Si convierte la lista en un diccionario por `item`, los
CUFEs repetidos ocuparán una sola clave; mantenga `index` para conservarlos todos.

## Validación y rendimiento

Las pruebas usan certificados sintéticos, MockTransport y servidores localhost
HTTP y TLS. Comprueban compatibilidad síncrona, las familias de eventos, firmas
serializadas, límites, cierre, cancelación y lotes de 100.000 elementos.

El benchmark reproducible compara cliente sync caliente, hilos, adaptador async,
transporte async con CPU en el loop y arquitectura híbrida:

```bash
uv run python scripts/benchmark_async.py --counts 100 --concurrency 1 25 \
  --repetitions 3 --latency-ms 100 --output /tmp/async-http.json
uv run python scripts/benchmark_async.py --counts 100 --concurrency 25 \
  --repetitions 3 --latency-ms 100 --tls --output /tmp/async-tls.json
```

El servidor y cada medición corren en procesos separados. Incluye calentamiento,
latencias, CPU, RSS anterior al análisis de percentiles, conexiones, errores,
hilos, reintentos y muestreo acotado del retraso del loop. La carga PKCS#12 queda
fuera de la región medida. `--counts 100 1000 10000 100000` y concurrencias
`1 5 10 25 50 100 200` habilitan ejecuciones extensas. `--scenario` permite
`saturation`, `malformed` y `disconnect`; un `--timeout` menor que la latencia
simulada permite provocar timeouts. Nunca redirija este benchmark a DIAN.

`--operation emails --tls` incorpora descarga ZIP y parsing CSV; `--operation
prepare` mide preparación XAdES/ZIP sin red y `--operation emit` prepara fuera
de la región medida y envía el artefacto sintético al servidor local.
`--payload-bytes 480000 --operation prepare` permite explorar XML cerca del
límite; el límite real sigue incluyendo firma y metadatos. Estas variantes usan
los modelos ficticios del checkout. `--processing-workers` permite comparar
presupuestos CPU, manteniendo dos por defecto. Las latencias comienzan cuando
el worker invoca la operación; el tiempo total incluye el lote completo.

Los [resultados locales y criterios](../ASYNC_ARCHITECTURE_PLAN.md) distinguen
objetivos y mediciones, incluido el objetivo pendiente frente a hilos.

Para obtener tiempos observados con sus CUFEs y certificado, consulte el
[benchmark real de consulta de eventos](event-query-benchmark.md). Genera JSON
y tabla Markdown con métricas agregadas; requiere una ejecución explícita contra
el ambiente DIAN elegido y no forma parte de CI.

Las mediciones reales publicadas consultaron 100 CUFEs por lote en producción,
con tres repeticiones por configuración: mediana de 8,56 segundos con
concurrencia 5, 4,64 segundos con concurrencia 10 y 3,27 segundos con
concurrencia 20, sin excepciones ni timeouts. La mediana de p95 por consulta
aumentó de 717 a 905 y 1.250 ms, respectivamente. Los ensayos de 500 CUFEs
obtuvieron medianas de 44,29, 21,51 y 11,42 segundos con concurrencias 5, 10 y
20, respectivamente, también sin excepciones ni timeouts. Una repetición con
500 CUFEs y concurrencia 20 registró p99 de 4,57 segundos. Para 1.000 CUFEs,
las medianas fueron 89,58, 44,78 y 22,41 segundos con concurrencias 5, 10 y 20,
sin excepciones ni timeouts en las 9.000 consultas de estos tres ensayos. La
[guía de benchmark](event-query-benchmark.md) conserva las filas, diferencias
entre muestras y límites de esta comparación observacional.
