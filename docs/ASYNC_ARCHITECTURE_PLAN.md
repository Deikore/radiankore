# Arquitectura asíncrona de radiankore

Auditoría inicial: 2026-10-28, versión 0.6.2, commit `8fab713`.
Implementación: API adicional de radiankore 0.7.0. Este documento conserva las
decisiones y límites; el contrato de uso está en la [guía async](guides/async.md).
El alcance es la librería y sus recursos de protocolo y concurrencia. El desarrollo y las pruebas usan transporte simulado o localhost; el
usuario aportó posteriormente una medición real de consultas en producción,
documentada en la [guía de benchmark](guides/event-query-benchmark.md).

## 1. Resumen ejecutivo

Arquitectura híbrida: HTTPX asíncrono para red y executor acotado para lectura de
certificados, firma, XML y ZIP. `DianClient` conserva su contrato síncrono.
`AsyncDianClient` incorpora las ocho consultas, preparación y envío, y streaming
con productor y workers fijos. No hay reintentos automáticos.

Cinco límites de la línea base: red síncrona; pools descartados por defecto;
firma y preparación de claves por petición; materialización de payloads; ausencia
de lotes con backpressure. Son hallazgos estructurales, no un perfil de DIAN.

## 2. Diagnóstico inicial

Se revisaron 78 módulos de producción y 33 módulos de pruebas. No había
`async def` de producción, Zeep, requests, aiohttp ni carga WSDL en ejecución.
Python mínimo: 3.13; CI: 3.13–3.15. El certificado ya se cargaba una vez por
cliente y existían fábricas desde memoria y pooling opcional desde 0.6.1.

La línea base completa aprobó 2.287 pruebas en 52,67 s. El ensayo HTTP local
anterior observó 20 → 1 conexiones con un proceso y 80 → 4 con cuatro procesos
al activar reutilización. Ese escenario también recargaba PFX en la variante sin
pool: no separa sus costes ni mide TLS o DIAN.

## 3. Inventario de operaciones bloqueantes

Líneas de esta tabla referidas al commit auditado `8fab713`, antes de extraer helpers.

| Módulo / línea | Clase / operación | Dependencia | Tipo / bloqueo inicial | Estrategia implementada |
| --- | --- | --- | --- | --- |
| `client.py:183` | `DianClient.get_numbering_range` | HTTPX, XML | Mixto, bloqueante | HTTP async y validación compartida |
| `client.py:212` | `get_exchange_emails` | SOAP, GET, ZIP, CSV | Mixto, bloqueante | Dos intercambios async; parsing en executor |
| `client.py:229` | `get_status` | HTTPX, Base64 | Mixto, bloqueante | Transporte async y parser compartido |
| `client.py:245` | `get_invoice_events` | HTTPX, UBL | Mixto, bloqueante | HTTP async y orden numérico conservado |
| `client.py:256` | `get_acquirer` | HTTPX, XML | Mixto, bloqueante | Async; 404 → None solo aquí |
| `client.py:290` | `get_document_info` | HTTPX, XML | Mixto, bloqueante | Parser compartido fuera del loop |
| `client.py:308` | `get_reference_notes` | HTTPX, UBL | Mixto, bloqueante | Orden y payloads independientes |
| `client.py:325` | `get_xml_by_document_key` | HTTPX, Base64 | Mixto, bloqueante | Conservar bytes sin reformatear |
| `client.py:342` | `prepare_radian_event` | lxml, xmlsec, ZIP | CPU, bloqueante | Helper único fuera del loop |
| `client.py:401` | `send_radian_event` | Base64, SOAP | Mixto, bloqueante | Un envío del ZIP original |
| `client.py:433` | `_request` | Firma, HTTPX | Mixto, bloqueante | Separar preparación y espera HTTP |
| `_soap/transport.py:57,91` | `SoapTransport.post/get` | HTTPX | I/O bloqueante | Transporte async independiente |
| `certificate.py:51,82` | `DigitalCertificate.from_pfx/from_file` | cryptography, pathlib | CPU / mixto | Fábricas async fuera del loop |
| `_soap/envelope.py:25` | `build_signed_request` | XML y firma | CPU, bloqueante | Reutilizar en executor |
| `_soap/signing.py:17,77` | `sign_envelope/certificate_key` | xmlsec | CPU, bloqueante | Contextos y claves nuevos |
| `_soap/events/ubl_signing.py:144` | `sign_application_response` | xmlsec | CPU, bloqueante | Árbol privado y lock criptográfico |
| `_soap/events/radian_builder.py:39` | `build_radian_application_response` | Builders | CPU, bloqueante | Conservar dispatcher y familias |
| `_soap/parsing.py:15` | `parse_xml` y lectores | lxml | CPU, bloqueante | Parsers locales sin DTD ni red |
| `_soap/response.py:60` | `parse_invoice_events_response` | XML, Base64 | CPU, bloqueante | Compartido en executor |
| `_soap/exchange_emails_response.py:67,91` | Extracción y CSV | zipfile, csv | CPU / memoria | Procesamiento local acotado |
| `_soap/events/zip.py:7` | `pack_event` | zipfile | CPU, bloqueante | Compartido fuera del loop |

Los modelos, catálogos, CUDE y builders por familia siguen siendo síncronos.
No se duplican builders de mandato, factura, endoso, pagos, garantías,
restricciones, protestos, transferencias o terminaciones.

## 4. Compatibilidad de dependencias

| Dependencia | Versión de auditoría | Compatibilidad / decisión |
| --- | --- | --- |
| Python | 3.13.12 | Mínimo 3.13; conservar matriz CI 3.13–3.15 |
| HTTPX | 0.28.1 | API async nativa; conservar >=0.28 |
| httpcore / AnyIO | 1.0.9 / 4.15.1 | Transporte async; DNS puede utilizar hilos del loop |
| lxml | 6.1.3 | Síncrona; libera GIL en ciertas operaciones; no ejecutarla en el loop |
| xmlsec | 1.3.17 | Firma síncrona; contextos privados, sin caché nativa |
| cryptography | 50.0.2 | PKCS#12 y material nativo fuera del loop |
| requests / aiohttp / Zeep | No instalados | No incorporarlos |
| zipfile / csv / Base64 | Estándar | Offloading para payloads |

No se añaden dependencias de ejecución. Los mínimos declarados son distintos
del lock: verificar cada entorno y no inferir soporte de todo el rango a partir
de una instalación reciente. Las comprobaciones efectivas se registran al final.

Zeep no aporta una mejora a la arquitectura actual: su cliente async conserva
carga WSDL síncrona y construcción, WS-Security y procesamiento de respuestas
locales. En el tag 4.3.1 inspeccionado, el transporte predeterminado usa `proxies=`,
retirado en HTTPX 0.28. No se propone una migración SOAP a Zeep.

Fuentes oficiales: [HTTPX async](https://www.python-httpx.org/async/),
[timeouts](https://www.python-httpx.org/advanced/timeouts/),
[pools](https://www.python-httpx.org/advanced/resource-limits/),
[lxml threading](https://lxml.de/FAQ.html#can-i-use-threads-to-concurrently-access-the-lxml-api),
[xmlsec 1.3.17](https://github.com/xmlsec/python-xmlsec/blob/1.3.17/src/ds.c),
[Zeep AsyncClient](https://docs.python-zeep.org/en/master/client.html#the-asyncclient),
[transporte Zeep 4.3.1](https://github.com/mvantellingen/python-zeep/blob/4.3.1/src/zeep/transports.py).

## 5. Comparación de alternativas

| Alternativa | Complejidad | Recursos y escalabilidad | Riesgo / migración |
| --- | --- | --- | --- |
| HTTP async con CPU en el loop | Media | Pocos hilos; pausas proporcionales al procesamiento local | Conserva bloqueo del loop; comparador `native` |
| Adaptador async de cliente sync | Baja al inicio | Un hilo y cliente exclusivo por intercambio activo | Cancelar espera no detiene el hilo; comparador `adapter` |
| Híbrida elegida | Media–alta | Conexiones y procesamiento con límites independientes | Gestión explícita de cierre; comparte dominio y parsers |

Las tres permiten conservar una clase sync independiente. La opción híbrida
requiere más pruebas de recursos, pero evita multiplicar hilos por latencia de
red y no reescribe el protocolo. La ganancia final depende del trabajo y debe
medirse; con una tasa externa baja, las alternativas pueden igualarse.

## 6. Arquitectura recomendada e implementada

```text
DianClient -------------> helpers de operación, firma y parsers compartidos
AsyncDianClient -> admisión -> executor acotado -> HTTPX async -> executor
iter_queries -> productor + workers fijos -> colas acotadas -> AsyncDianClient
```

`_soap/operations.py` comparte validaciones y preparación; `_soap/http.py`
comparte clasificación de HTTP/SOAP. `_async_runtime.py` conserva plazas hasta
que termina el trabajo nativo. `_soap/async_transport.py` posee los pools y sus
inicializadores. `_async_bulk.py` contiene coordinación estructurada del streaming.
Los árboles XML no atraviesan etapas del loop: los trabajos devuelven bytes o
modelos. No se envuelve la API sync en `asyncio.run()` ni se hereda de ella.

## 7. Interfaces públicas

Nuevos exports: `AsyncDianClient`, `AsyncDianLimiter`, `DianTimeouts` y
`QueryResult[T, R]`. `from_certificate` no realiza I/O; `from_file` y `from_pfx`
son async. Las ocho consultas y las dos operaciones de eventos se esperan.
`aclose` y el context manager async poseen el ciclo de vida.

Defaults: ambiente producción, concurrencia 5, dos workers locales,
connect/read/write/pool 5/30/30/5 s y plazo total 60 s. El total admite None.
La nueva API siempre reutiliza conexiones; la sync no cambia sus defaults.
No se depreca `DianClient`. La versión de esta incorporación es 0.7.0.

## 8. Conexiones y concurrencia

Dos pools HTTP/1.1 separados; máximo de conexiones y keep-alive igual a
concurrencia; expiración 30 s. TLS verificado, sin redirecciones ni cookies.
La política `CookieJar` rechaza almacenamiento y devolución, evitando limpiar
estado compartido alrededor de awaits.

El límite por cliente engloba operaciones completas. Un limitador compartido
controla intercambios HTTP globales, tasa opcional y límites por servicio dentro
de un loop/proceso. La tasa está desactivada por defecto. No se conoce una cuota
DIAN que permita recomendar 5, 25 o 200 como valores seguros ante producción.
`Retry-After` pausa nuevas solicitudes sin repetir la fallida.

El streaming conserva índices y duplicados, produce en orden de finalización y
usa dos colas de 2 × workers. No materializa entradas ni resultados completos.
Cada respuesta individual sigue siendo residente en memoria.

## 9. Seguridad e idempotencia

Un árbol, clave xmlsec y contexto nuevos por firma; acceso a certificado
serializado dentro del cliente. No compartir material nativo entre clientes
concurrentes ni agregar caché PEM/clave. Conservar los perfiles SOAP y XAdES,
bytes originales y límite de 500.000 bytes de XML firmado. No ejecutar shutdown
global de xmlsec al cerrar un cliente ni registrar secretos o XML completo.

Emisión significa un intento explícito: una respuesta perdida, cancelación o
resultado ausente puede ser desconocido. Conservar CUDE, ambiente y artefacto;
consultar estado con identidad coincidente. GetStatusEvent requiere CUFE de la
factura y no confirma genéricamente cada evento por CUDE. La cobertura de
reconciliación por familia necesita validación autorizada. El anexo RADIAN 1.1
§§8.7–8.8 no acredita ejecución exactamente una vez ni idempotencia por reenvío.

Los reintentos permanecen en el consumidor, solo para consultas transitorias,
con máximo de tres intentos, presupuesto total, backoff exponencial con full
jitter y respeto de Retry-After. Firma, certificado y payload inválidos no son
motivos para repetir automáticamente. La librería nunca reenvía.

## 10. Responsabilidades del consumidor

Persistencia, permisos, selección empresarial de certificados y recuperación
durable corresponden al consumidor. La librería resuelve protocolo, firma,
parsing, transporte y gestión de recursos locales.

## 11. Estrategia de pruebas

Mantener regresión sync y fixtures sintéticos. Verificar paridad de consultas,
404 de adquiriente, ausencias, estados negativos, errores HTTP/SOAP y causas.
Verificar firmas serializadas de familias de eventos y ZIP original enviado.
Probar cookies, pools, límites compartidos, cancelación en admisión/CPU/HTTP,
inicialización abandonada, doble cierre, loops/procesos y fuentes que fallan.

Streaming: 100, 1.000, 10.000 y 100.000 elementos; fuente y consumidor lentos,
duplicados, éxito None, error individual, cancelación y salida con colas llenas.
TCP y TLS se prueban con localhost real; MockTransport no demuestra pooling.
Validación final: Ruff, formato, mypy, suite con referencias y wheel aislado.

## 12. Benchmarks

`scripts/benchmark_async.py` compara sync secuencial reutilizable, clientes
exclusivos por hilo, adaptador async, transporte async con CPU en el loop y
arquitectura híbrida. Servidor y cada muestra corren en procesos separados;
calentamiento y PKCS#12 quedan fuera de latencia/CPU medidas. Se desactiva Nagle
en el servidor local para evitar que delayed ACK distorsione peticiones pequeñas.

Matriz configurable: volúmenes 100/1.000/10.000/100.000; concurrencias
1/5/10/25/50/100/200; latencias 1/50/100/200 ms; distintos tamaños de respuesta;
HTTP y TLS. Escenarios: correcto, saturación, XML inválido, desconexión y timeout.
Las combinaciones grandes son manuales; este comparador local no ejecuta carga
contra DIAN. La medición remota utiliza un script separado y ejecución explícita.
`--operation` selecciona consultas, ZIP/CSV, preparación local o emisión de un
artefacto sintético. El presupuesto CPU también es configurable.

Métricas: tiempo, ops/s, p50/p95/p99, CPU, RSS, conexiones, hilos, errores,
timeouts, reintentos y retraso del loop con reservorio fijo. Las muestras de
latencia se escriben temporalmente; el pico RSS se captura antes de leerlas para
percentiles. Una prueba normal exige cero errores inesperados y cero reintentos.

Objetivos inicialmente propuestos, sujetos a medición: >=5× frente a secuencial
con 100 ms y concurrencia 25; >=90 % de throughput frente a hilos con dos workers
locales; aumento RSS <=20 % de 10k a 100k a concurrencia fija; lag p99 <20 ms;
regresión p95 <=15 % con concurrencia 1. No son garantías de DIAN ni resultados
atribuibles a la librería antes de medir.

## 13. Roadmap y rollback

| Etapa | Cambios / módulos | Riesgo y validación | Complejidad / rollback |
| --- | --- | --- | --- |
| 0. Baseline | Auditoría y ensayo sync | Separar pooling y PFX | Baja; sin efecto funcional |
| 1. Helpers | operations y HTTP compartidos | Preservar validación y errores; regresión sync | Media; revertir extracción |
| 2. Recursos | Runtime, limitador, transporte async | Fugas y carreras; pruebas de cancelación y TCP/TLS | Alta; API nueva aislada |
| 3. Consultas | Ocho métodos async | Paridad de resultados y errores | Media; mantener sync disponible |
| 4. Streaming | Colas, productor y workers | Deadlocks/memoria; 100k y consumidor lento | Alta; consultas independientes del helper |
| 5. Eventos | Preparación compartida y envío único | Firmas/duplicados; familias y bytes originales | Alta; conservar ruta sync |
| 6. Release | Docs, versión, benchmarks y distribución | Medir objetivos y probar wheel | Alta; consumidor puede mantener 0.6.2 |

El consumidor puede continuar usando la API síncrona sin migrar sus llamadas.
La publicación sigue el flujo de release descrito en la guía de mantenimiento.

## 14. Riesgos y decisiones pendientes

Cuotas y aceptación remota no verificadas; cancelación nativa no forzable;
memoria por payload y expansión ZIP no incrementales; costes CPU dependientes de
certificado/host; validación de todas las dependencias mínimas separada del lock.
La confianza, revocación y vigencia del certificado no se añaden silenciosamente.
No se promete un deadline físico del trabajo criptográfico ya iniciado.

La URL publicada stable de la documentación no fue accesible durante la auditoría;
se usaron código y documentación locales y fuentes oficiales de dependencias.
No se requiere Zeep ni reescritura de modelos para resolver estas incertidumbres.

## 15. Aceptación y evidencia de cierre

La implementación incluye ocho consultas y eventos async, compatibilidad sync,
firma y parsing fuera del loop, lotes acotados y cancelación sin liberar plazas
físicas prematuramente. Las pruebas verifican firmas, bytes originales y ausencia
de reintentos; la matriz de validación conserva Python 3.13–3.15 y wheel instalado.

### Verificación de la implementación, 2026-10-28

Las ocho consultas, preparación y envío async, limitador compartido y streaming
están implementados. La API sync conserva sus métodos y defaults. Todas las
pruebas usan material sintético y transporte simulado o localhost.

| Comprobación | Resultado observado |
| --- | --- |
| Wheel instalado, Python 3.13.12 | 2.433 pruebas aprobadas con cobertura, 123,87 s |
| Wheel instalado, Python 3.14.4 | 2.433 pruebas aprobadas, 111,70 s |
| Wheel instalado, Python 3.15.0 | 2.433 pruebas aprobadas, 102,52 s |
| Ruff / formato | Sin errores; 220 archivos con formato correcto |
| mypy estricto | Sin errores en 131 archivos |
| Cobertura SDK, Python 3.13 | 98 %, incluyendo ramas; medida sobre el wheel instalado |
| Sphinx/MyST | Compilación final con `-E -W --keep-going` al cierre de la revisión |
| Distribución | Wheel y sdist construidos; Twine aprobado; `py.typed` y fuentes SDK actuales verificados |
| Material sensible | Wheel y sdist sin certificados ni referencias originales |
| Eventos próximos al límite | Preparación con 480.000 bytes de contenido sintético: cinco comparadores sin errores |
| ZIP/CSV y emisión | Cinco comparadores locales ejecutados sin errores; descarga con TLS |

La revisión final también verificó los ejemplos publicados: consulta individual,
lotes con errores y duplicados, puente síncrono y acuse 030 completo, con SOAP
y XAdES verificables y envío único del ZIP original. Se corrigió el cooldown
Retry-After para aplicarlo antes de leer un cuerpo de error lento y la
clasificación de timeouts HTTPX en el comparador local.

Las suites se ejecutaron desde `/tmp` con `python -I`, importando el paquete
instalado del wheel. En 3.13 se reutilizaron las dependencias nativas compiladas
del entorno local; el SDK probado provino del wheel, no del checkout editable.
En 3.14 y 3.15 se compilaron lxml y xmlsec con la misma libxml2 del sistema.
Los tiempos de pruebas no son una comparación de rendimiento entre versiones.

La matriz local valida el lock actual. No demuestra todas las combinaciones
admitidas por los rangos mínimos de dependencias ni una ejecución remota de CI.
La validación DIAN por familia queda pendiente de una sesión de habilitación
autorizada. La versión es 0.7.0; la publicación requiere el workflow de release.
Los benchmarks de consultas no sustituyen esa validación por familia.

### Rendimiento local medido

Referencia: 100 consultas por muestra, latencia artificial de 100 ms, respuesta
de aproximadamente 10 kB, tres repeticiones, concurrencia 25 salvo secuencial.
Se muestra la mediana de cada métrica entre repeticiones. Material sintético,
HTTPX 0.28.1, lxml 6.1.3, xmlsec 1.3.17 y cryptography 50.0.2; los JSON
conservan Python, plataforma, CPU, percentiles y métricas por etapa.

| Variante | HTTP ops/s | TLS ops/s | Hilos cliente | Lag p99 HTTP, ms |
| --- | ---: | ---: | ---: | ---: |
| Sync secuencial con pooling | 9,32 | 9,27 | 1 | No aplica |
| Cliente sync exclusivo por hilo | 179,37 | 163,35 | 26 | No aplica |
| Adaptador async sobre hilos | 164,77 | 167,71 | 26 | 7,23 |
| Transporte async, CPU en el loop | 90,62 | 81,12 | 1 | 65,45 |
| Async híbrido, dos workers CPU | 149,73 | 141,36 | 3 | 5,21 |

Datos: [HTTP](benchmarks/async-http.json) y [TLS](benchmarks/async-tls.json).
Los ensayos iniciales bajo contención de procesos de diagnóstico se descartaron
para esta comparación; la tabla corresponde a ejecuciones posteriores aisladas.

En esta referencia el híbrido alcanza 16,1× el throughput secuencial HTTP,
mantiene lag p99 por debajo de 20 ms y su p95 con concurrencia 1 es 113,31 ms
frente a 110,54 ms sync (+2,5 %, inferior al objetivo de 15 %). No alcanza el
objetivo del 90 % frente a hilos en lotes de 100: obtiene 83,5 % en HTTP y
86,5 % con TLS. Conserva tres hilos en lugar de 26 y evita el lag de procesar
XML/firma en el loop. El objetivo pendiente no se presenta como cumplido.

Una [comprobación de 1.000 consultas](benchmarks/async-steady.json), también con
100 ms, concurrencia 25 y tres repeticiones, observó 218,61 ops/s en hilos y
153,73 ops/s en el híbrido (70,3 %). Aumentar el lote no resuelve ese objetivo en
este host. Se conserva el default de dos workers; la elección reduce hilos y
mantiene el loop disponible, pero no demuestra paridad de throughput con 25
clientes síncronos exclusivos.

En el [ensayo de memoria](benchmarks/async-memory.json), 10.000 y 100.000
consultas HTTP reales locales con concurrencia 25 utilizaron picos RSS de
66.044 y 76.360 KiB (+15,6 %), tres hilos y cero errores o reintentos. Ambas
muestras excluyen el cálculo de percentiles del pico medido. Este ensayo se
ejecutó con actividad concurrente del host; sus tiempos y lag no se usan como
referencia de rendimiento aislado. Es una observación de memoria con payload
fijo, no una garantía para respuestas arbitrariamente grandes.

Reproducción desde el checkout, con el host sin otras cargas intensivas:

```bash
uv run python scripts/benchmark_async.py --counts 100 --concurrency 1 25 \
  --repetitions 3 --latency-ms 100 --output /tmp/async-http.json
uv run python scripts/benchmark_async.py --counts 100 --concurrency 25 \
  --repetitions 3 --latency-ms 100 --tls --output /tmp/async-tls.json
uv run python scripts/benchmark_async.py --counts 10000 100000 \
  --concurrency 25 --modes hybrid --repetitions 1 --latency-ms 0 \
  --output /tmp/async-memory.json
uv run python scripts/benchmark_async.py --counts 1000 --concurrency 25 \
  --modes threads hybrid --repetitions 3 --latency-ms 100 \
  --output /tmp/async-steady.json
```

Las pruebas de escala también verifican un máximo fijo de tareas con 100.000
entradas. Las combinaciones restantes de la matriz, todas las versiones mínimas
de dependencias y los límites remotos de DIAN permanecen sin verificar.

### Referencia real aportada por el usuario

El 2026-10-28 se ejecutaron tres lotes de 100 CUFEs en producción, con
concurrencia 5 y dos workers CPU. Los tiempos fueron 8,037, 9,432 y 8,559 s:
mediana 8,56 s por lote, sin excepciones, timeouts ni reintentos en 300 consultas.
Cada repetición devolvió 430 eventos de la misma muestra. Un segundo ensayo
con 100 CUFEs y concurrencia 10 observó tiempos de 4,636, 5,024 y 4,496 s:
mediana 4,64 s, también sin excepciones, timeouts ni reintentos. Retornó 436
eventos por repetición. Un tercer ensayo con concurrencia 20 midió 3,204,
3,815 y 3,268 s, mediana 3,27 s, también con 436 eventos por repetición y sin
excepciones, timeouts ni reintentos. La mediana de p95 en los tres ensayos fue
716,75, 905,46 y 1.250,15 ms, respectivamente. Los
informes no identifican los CUFEs entre ensayos; esta comparación observacional
no aísla el efecto de la concurrencia. Un cuarto ensayo amplió la muestra a
500 CUFEs con concurrencia 5: tiempos de 42,580, 52,612 y 44,288 s, mediana
44,29 s y 11,29 consultas/s, p95 mediano de 550,65 ms. Las 1.500 consultas
no tuvieron excepciones, timeouts ni reintentos; cada repetición retornó
2.415 eventos. Otros dos ensayos de 500 CUFEs con concurrencias 10 y 20
observaron medianas de lote de 21,51 y 11,42 s, throughput de 23,25 y
43,79 consultas/s y p95 mediano de 553,58 y 675,66 ms, respectivamente.
Cada configuración completó 1.500 consultas sin excepciones, timeouts ni
reintentos y retornó 2.415 eventos por repetición. Una muestra con concurrencia
20 registró p99 de 4,57 s. Tres ensayos adicionales de 1.000 CUFEs con
concurrencias 5, 10 y 20 observaron medianas de 89,58, 44,78 y 22,41 s,
throughput de 11,16, 22,33 y 44,63 consultas/s y p95 mediano de 578,25,
575,33 y 571,93 ms, respectivamente. Completaron 9.000 consultas sin
excepciones, timeouts ni reintentos; cada repetición retornó 4.938 eventos.
No se ha medido todavía el cliente sync contra DIAN. La
[guía de benchmark real](guides/event-query-benchmark.md) conserva las métricas,
condiciones y el JSON agregado. No sustituye la validación de emisiones ni
acredita cuotas, idempotencia o comportamiento de todas las familias de eventos.
