# Benchmark real de consulta de eventos

El benchmark local de la [guía async](async.md) mide una carga controlada.
Para documentar tiempos observados contra DIAN, el checkout incluye
`scripts/benchmark_event_queries.py`. Solo invoca `get_invoice_events`; no
prepara ni emite eventos y no realiza reintentos.

La primera medición real fue ejecutada por el usuario el **28 de octubre de
2026** en producción. Los datos agregados se conservan en el
[informe JSON](../benchmarks/dian-events-production-2026-10-28.json).

## Comparación de los nueve ensayos

En total se realizaron **14.400 consultas**, sin excepciones, timeouts ni
reintentos, en 27 muestras de producción. Cada celda resume la mediana de las
tres repeticiones. La mediana de p95 es la mediana de los p95 de cada muestra,
no el p95 global de todas las consultas.

| CUFEs por lote | Concurrencia | Mediana del lote, s | Mediana de consultas correctas/s | Mediana de p95, ms | Errores / timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 5 | 8,559 | 11,68 | 716,75 | 0 / 0 |
| 100 | 10 | 4,636 | 21,57 | 905,46 | 0 / 0 |
| 100 | 20 | 3,268 | 30,60 | 1.250,15 | 0 / 0 |
| 500 | 5 | 44,288 | 11,29 | 550,65 | 0 / 0 |
| 500 | 10 | 21,507 | 23,25 | 553,58 | 0 / 0 |
| 500 | 20 | 11,417 | 43,79 | 675,66 | 0 / 0 |
| 1.000 | 5 | 89,576 | 11,16 | 578,25 | 0 / 0 |
| 1.000 | 10 | 44,782 | 22,33 | 575,33 | 0 / 0 |
| 1.000 | 20 | 22,405 | 44,63 | 571,93 | 0 / 0 |

Con 100 CUFEs, pasar de concurrencia 5 a 10 coincidió con **45,8 % menos
tiempo por lote** y **84,6 % más consultas por segundo**, mientras la mediana
de p95 por consulta aumentó **26,3 %**. Completar el lote antes no implica que
todas las consultas individuales respondan antes.

Con 100 CUFEs, de concurrencia 10 a 20, la mediana de tiempo de lote bajó
**29,5 %** y el throughput aumentó **41,8 %**; la mediana de p95 subió **38,1 %**, hasta
1,25 segundos. En estas observaciones la ganancia al duplicar concurrencia es
menor que en el paso anterior, mientras aumenta la latencia de cola individual.

Con concurrencia 5, pasar de 100 a 500 CUFEs observó 11,68 frente a 11,29
consultas/s de mediana (**3,4 % menos throughput**). El tiempo total aumenta
con el tamaño del lote; las muestras tienen diferente composición y cantidad
de eventos, por lo que no se atribuye el cambio exclusivamente al volumen.

Con 500 CUFEs, la mediana del lote bajó **51,4 %** de concurrencia 5 a 10 y
**46,9 %** de 10 a 20; la reducción de 5 a 20 fue **74,2 %**. Las medianas
de p95 fueron 550,65, 553,58 y 675,66 ms. El p99 de 4,57 s de una repetición
con concurrencia 20 muestra variabilidad en las consultas más lentas que no se
aprecia únicamente comparando los tiempos totales de lote.

Con 1.000 CUFEs, duplicar la concurrencia de 5 a 10 y de 10 a 20 coincidió
con reducciones de tiempo de lote de **50,0 %** en cada paso; de 5 a 20 la
reducción fue **75,0 %**. Las medianas de p95 permanecieron alrededor de
572–578 ms. Esto describe las ejecuciones observadas; no garantiza el mismo
escalado con otras cargas, horarios o concurrencias mayores.

Los informes no conservan identificadores que permitan confirmar si se usaron
exactamente los mismos CUFEs entre ensayos. Además, el total de eventos por
repetición cambió de 430 a 436 entre los dos primeros ensayos y se mantuvo en
436 en el tercero. Por ello la comparación es observacional: no
aísla exclusivamente el efecto de la concurrencia de cambios en documentos,
red o servicio. Los tres ensayos de 500 CUFEs retornaron 2.415 eventos por
repetición, sin que esto pruebe identidad de los documentos entre ejecuciones.
Los tres ensayos de 1.000 CUFEs retornaron 4.938 eventos por repetición, con la
misma limitación para acreditar identidad de los documentos entre ejecuciones.
No hay todavía mediciones de más de 1.000 CUFEs ni concurrencias superiores a 20.

## Muestras individuales

### Resultados reales: 100 CUFEs en producción

Operación `get_invoice_events`, 100 CUFEs distintos por lote, misma muestra en
tres repeticiones, concurrencia 5 y dos workers de procesamiento. Cada muestra
creó un cliente nuevo, sin calentamiento previo ni tasa máxima configurada,
con timeout total de 60 segundos. La carga del certificado y el cierre quedan
fuera del tiempo de lote. Ejecución entre las 09:55:44 y 09:56:11 de
America/Bogota, el 2026-10-28; el JSON conserva timestamps UTC y orden efectivo
de ejecución: repetición 2, después 1 y finalmente 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,037 | 12,44 | 388,83 | 665,11 | 877,60 | 0 | 0 |
| 2 | 9,432 | 10,60 | 458,87 | 791,95 | 1.049,76 | 0 | 0 |
| 3 | 8,559 | 11,68 | 403,77 | 716,75 | 936,07 | 0 | 0 |

La mediana del tiempo por lote fue **8,56 segundos para 100 CUFEs**, con mediana
de throughput de **11,68 consultas correctas por segundo**. Los percentiles son
por consulta dentro de cada repetición; no son percentiles del tiempo del lote
ni un percentil global de las 300 consultas.

Las 300 consultas devolvieron respuesta sin excepción, con cero timeouts y cero
reintentos. En cada repetición hubo 97 respuestas con `is_valid=True`, tres
respuestas sin eventos y 430 eventos retornados. Son observaciones de la misma
muestra repetida; no representan 300 CUFEs distintos ni 1.290 eventos únicos.
La ausencia de errores de transporte no implica resultado de negocio positivo
para todas las respuestas.

Entorno registrado: radiankore 0.7.0, Python 3.13.12, HTTPX 0.28.1, lxml 6.1.3,
xmlsec 1.3.17 y cryptography 50.0.2, Linux x86_64 con glibc 2.43. La región de
red, proveedor y uso de VPN/proxy no quedaron registrados. Estas tres muestras
describen esta ejecución; no fijan una capacidad garantizada de DIAN. Las
siguientes muestras cubren también 500 y 1.000 CUFEs y concurrencias 10 y 20.
No hay mediciones remotas del cliente síncrono.

Los datos publicados contienen solo métricas agregadas, sin los CUFEs ni el
material utilizado para autenticarse.

### Segundo ensayo: 100 CUFEs con concurrencia 10

Ejecutado por el usuario el mismo 2026-10-28, entre las 10:02:34 y 10:02:48
de America/Bogota. Conserva ambiente de producción, versiones, dos workers CPU,
tres repeticiones, timeout total de 60 segundos y cliente nuevo por muestra,
sin calentamiento ni tasa máxima configurada. Cada lote contiene 100 CUFEs
distintos. El [segundo informe JSON](../benchmarks/dian-events-production-2026-10-28-c10.json)
conserva las métricas y el orden efectivo de ejecución: 2, 1, 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4,636 | 21,57 | 388,64 | 905,46 | 1.073,68 | 0 | 0 |
| 2 | 5,024 | 19,90 | 439,85 | 1.051,41 | 1.118,27 | 0 | 0 |
| 3 | 4,496 | 22,24 | 392,13 | 876,78 | 1.010,37 | 0 | 0 |

Las 300 consultas devolvieron respuesta sin excepción, timeout ni reintento.
Cada repetición retornó 436 eventos, con 97 respuestas `is_valid=True` y tres
respuestas sin eventos. Los totales corresponden a observaciones repetidas de
100 CUFEs, no a 300 documentos distintos.

### Tercer ensayo: 100 CUFEs con concurrencia 20

Ejecutado el 2026-10-28, entre las 10:05:20 y 10:05:31 de America/Bogota,
en producción. Mantiene las versiones y configuración del segundo ensayo,
salvo la concurrencia, que aumenta a 20: dos workers CPU, timeout total de
60 segundos, cliente nuevo por muestra, sin calentamiento ni tasa configurada.
Cada lote contiene 100 CUFEs distintos. El
[tercer informe JSON](../benchmarks/dian-events-production-2026-10-28-c20.json)
conserva el orden de ejecución 2, 1, 3 y todas las métricas agregadas.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3,204 | 31,21 | 484,66 | 1.250,15 | 1.292,97 | 0 | 0 |
| 2 | 3,815 | 26,21 | 561,19 | 1.343,79 | 1.469,42 | 0 | 0 |
| 3 | 3,268 | 30,60 | 415,20 | 1.137,60 | 1.212,63 | 0 | 0 |

Las 300 consultas devolvieron respuesta sin excepción, timeout ni reintento.
Cada repetición retornó 436 eventos, con 97 respuestas `is_valid=True` y tres
respuestas sin eventos, como en el ensayo con concurrencia 10. La mediana del
lote fue **3,27 segundos**, con mediana de throughput de **30,60 consultas/s**.

### Cuarto ensayo: 500 CUFEs con concurrencia 5

Ejecutado el 2026-10-28, entre las 10:08:15 y 10:10:35 de America/Bogota,
en producción. Amplía el lote a 500 CUFEs distintos y conserva concurrencia 5,
dos workers CPU, tres repeticiones y el resto de configuración y versiones de
los ensayos anteriores: cliente nuevo por muestra, sin calentamiento ni tasa
configurada, timeout total de 60 segundos por consulta. El
[cuarto informe JSON](../benchmarks/dian-events-production-2026-10-28-n500-c5.json)
registra el orden efectivo de ejecución 2, 1, 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 42,580 | 11,74 | 410,89 | 536,34 | 923,94 | 0 | 0 |
| 2 | 52,612 | 9,50 | 517,59 | 678,44 | 957,10 | 0 | 0 |
| 3 | 44,288 | 11,29 | 420,62 | 550,65 | 1.095,36 | 0 | 0 |

Las 1.500 consultas devolvieron respuesta sin excepción, timeout ni reintento.
Cada repetición retornó 2.415 eventos, con 497 respuestas `is_valid=True` y
tres respuestas sin eventos. No representan 1.500 CUFEs distintos: se repitió
la misma muestra de 500. La mediana del lote fue **44,29 segundos**, con
mediana de throughput de **11,29 consultas/s** y mediana de p95 de **550,65 ms**.

### Quinto ensayo: 500 CUFEs con concurrencia 10

Ejecutado el 2026-10-28, entre las 10:11:50 y 10:12:55 de America/Bogota,
en producción. Mantiene las versiones y configuración del ensayo de 500 CUFEs
con concurrencia 5, salvo el aumento a concurrencia 10. El
[quinto informe JSON](../benchmarks/dian-events-production-2026-10-28-n500-c10.json)
conserva las métricas y el orden de ejecución 2, 1, 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 21,507 | 23,25 | 411,43 | 553,58 | 905,09 | 0 | 0 |
| 2 | 22,571 | 22,15 | 426,13 | 605,26 | 1.000,66 | 0 | 0 |
| 3 | 21,005 | 23,80 | 402,65 | 509,80 | 934,27 | 0 | 0 |

Mediana de **21,51 segundos por lote**, **23,25 consultas/s** y **553,58 ms**
de p95. Las 1.500 consultas devolvieron respuesta sin excepción, timeout ni
reintento. Cada repetición consultó 500 CUFEs distintos y retornó 2.415 eventos,
con 497 respuestas `is_valid=True` y tres sin eventos.

### Sexto ensayo: 500 CUFEs con concurrencia 20

Ejecutado el 2026-10-28, entre las 10:13:33 y 10:14:09 de America/Bogota,
en producción, con la misma configuración salvo concurrencia 20. El
[sexto informe JSON](../benchmarks/dian-events-production-2026-10-28-n500-c20.json)
conserva el orden efectivo de ejecución 2, 1, 3 y las métricas de cada muestra.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 13,183 | 37,93 | 401,34 | 915,13 | 4.566,29 | 0 | 0 |
| 2 | 11,288 | 44,30 | 414,49 | 590,81 | 1.210,05 | 0 | 0 |
| 3 | 11,417 | 43,79 | 407,27 | 675,66 | 1.190,52 | 0 | 0 |

Mediana de **11,42 segundos por lote**, **43,79 consultas/s** y **675,66 ms**
de p95. Las 1.500 consultas devolvieron respuesta sin excepción, timeout ni
reintento. Cada repetición consultó 500 CUFEs distintos y retornó 2.415 eventos,
con 497 respuestas `is_valid=True` y tres sin eventos. La repetición 1 registró
un p99 de **4,57 segundos**: se conserva este resultado aunque no haya errores.

### Séptimo ensayo: 1.000 CUFEs con concurrencia 5

Ejecutado el 2026-10-28, entre las 10:15:53 y 10:20:32 de America/Bogota,
en producción. Mantiene las versiones y configuración de los ensayos previos:
dos workers CPU, tres repeticiones, cliente nuevo por muestra, sin calentamiento
ni tasa configurada y timeout total de 60 segundos por consulta. Cada lote
contiene 1.000 CUFEs distintos. El
[séptimo informe JSON](../benchmarks/dian-events-production-2026-10-28-n1000-c5.json)
conserva las métricas y el orden efectivo de ejecución 2, 1, 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 87,885 | 11,38 | 419,96 | 575,26 | 787,68 | 0 | 0 |
| 2 | 101,302 | 9,87 | 481,19 | 722,51 | 865,70 | 0 | 0 |
| 3 | 89,576 | 11,16 | 433,63 | 578,25 | 818,08 | 0 | 0 |

Mediana de **89,58 segundos por lote**, **11,16 consultas/s** y **578,25 ms**
de p95. Las 3.000 consultas devolvieron respuesta sin excepción, timeout ni
reintento. Cada repetición retornó 4.938 eventos, con 997 respuestas
`is_valid=True` y tres sin eventos. El timeout de 60 segundos se aplica a cada
consulta, no al lote completo, que puede superar ese tiempo.

### Octavo ensayo: 1.000 CUFEs con concurrencia 10

Ejecutado el 2026-10-28, entre las 10:20:59 y 10:23:14 de America/Bogota,
en producción, con la misma configuración salvo concurrencia 10. El
[octavo informe JSON](../benchmarks/dian-events-production-2026-10-28-n1000-c10.json)
registra el orden de ejecución 2, 1, 3 y las métricas completas.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 45,108 | 22,17 | 431,51 | 584,87 | 854,01 | 0 | 0 |
| 2 | 44,782 | 22,33 | 428,24 | 569,19 | 861,97 | 0 | 0 |
| 3 | 44,695 | 22,37 | 429,22 | 575,33 | 885,52 | 0 | 0 |

Mediana de **44,78 segundos por lote**, **22,33 consultas/s** y **575,33 ms**
de p95. Las 3.000 consultas devolvieron respuesta sin excepción, timeout ni
reintento. Cada repetición consultó 1.000 CUFEs distintos y retornó 4.938
eventos, con 997 respuestas `is_valid=True` y tres sin eventos.

### Noveno ensayo: 1.000 CUFEs con concurrencia 20

Ejecutado el 2026-10-28, entre las 10:23:39 y 10:24:46 de America/Bogota,
en producción, con la misma configuración salvo concurrencia 20. El
[noveno informe JSON](../benchmarks/dian-events-production-2026-10-28-n1000-c20.json)
conserva el orden efectivo de ejecución 2, 1, 3.

| Repetición | Total del lote, s | Consultas correctas/s | p50, ms | p95, ms | p99, ms | Errores | Timeouts |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 22,405 | 44,63 | 419,87 | 575,95 | 1.002,60 | 0 | 0 |
| 2 | 22,783 | 43,89 | 423,68 | 571,93 | 1.023,92 | 0 | 0 |
| 3 | 22,199 | 45,05 | 417,07 | 568,63 | 944,15 | 0 | 0 |

Mediana de **22,41 segundos por lote**, **44,63 consultas/s** y **571,93 ms**
de p95. Las 3.000 consultas devolvieron respuesta sin excepción, timeout ni
reintento. Cada repetición consultó 1.000 CUFEs distintos y retornó 4.938
eventos, con 997 respuestas `is_valid=True` y tres sin eventos. Los tres ensayos
de este tamaño suman 9.000 consultas; las repeticiones no representan 9.000
CUFEs distintos ni eventos únicos adicionales.

## Preparar la muestra

Use Python >=3.13, las dependencias instaladas del proyecto, un certificado
propio y CUFEs que pueda consultar en el ambiente elegido. Guarde los CUFEs en
un archivo UTF-8 privado, uno por línea, fuera del repositorio. Para probar
lotes de 10, 50 y 100 hacen falta al menos 100 entradas. Se ignoran líneas
vacías y se conservan duplicados; cada tamaño utiliza el prefijo del archivo.

Las facturas con distinta cantidad de eventos pueden tener costes diferentes.
Use la misma muestra para comparar configuraciones y registre, por separado,
una descripción general: rango aproximado de eventos por factura, región del
equipo, conexión de red y si usa VPN o proxy. No publique CUFEs, NIT, XML ni
identificadores del certificado. No asuma que un CUFE de producción existe en
habilitación.

## Ejecutar

Desde la raíz del checkout:

```bash
uv run python scripts/benchmark_event_queries.py run \
  --cufes-file /ruta/privada/cufes.txt \
  --certificate /ruta/privada/certificado.pfx \
  --environment production \
  --counts 10 50 100 \
  --concurrency 1 5 \
  --repetitions 3 \
  --output /tmp/eventos-dian.json
```

Este comando hace **960 solicitudes SOAP**: `(10 + 50 + 100) × 2 × 3`.
El script muestra ese presupuesto antes de solicitar la contraseña mediante
`getpass`; no la recibe como argumento ni la escribe en los informes. Elegir
`production` o `habilitation` es obligatorio. No se ejecuta este comando en CI.

Para comenzar con una medición más pequeña:

```bash
uv run python scripts/benchmark_event_queries.py run \
  --cufes-file /ruta/privada/cufes.txt \
  --certificate /ruta/privada/certificado.pfx \
  --environment production \
  --counts 100 --concurrency 5 --repetitions 1 \
  --output /tmp/eventos-dian-100.json
```

Son 100 solicitudes. `--requests-per-second 2` permite fijar una tasa de
inicios compartida entre muestras; su espera forma parte del tiempo medido.
`--total-timeout 60` y `--processing-workers 2` son los valores predeterminados.
Estos números no representan cuotas verificadas de DIAN. El limitador conserva
los cooldowns `Retry-After` entre muestras; nunca repite la petición fallida.

Cada muestra utiliza un cliente nuevo. Por defecto no hay calentamiento: la
primera consulta incluye inicialización TLS y establecimiento de conexiones.
`--warmup 5` agrega cinco consultas previas por muestra; se registran aparte y
también cuentan en el presupuesto mostrado. No garantiza que todas las
conexiones del pool estén calientes. Las muestras se intercalan en orden
aleatorio reproducible, con `--seed 42` por defecto; repetir consultas puede
verse afectado por cachés o cambios del servicio.

## Qué mide y qué devuelve

Se generan `/tmp/eventos-dian.json` y `/tmp/eventos-dian.md`. El JSON conserva
fecha UTC, ambiente, versiones, configuración, orden efectivo de muestras y:

- Tiempo total de cada lote y consultas correctas por segundo.
- p50, p95 y p99 por consulta correcta, en milisegundos; también percentiles de
  todos los intentos, incluidos los que terminan con excepción.
- Errores por clase y timeouts, incluidos los traducidos por el SDK.
- Respuestas con negocio válido, respuestas sin eventos y total de eventos.
- Tiempo de carga del certificado, cierre y calentamiento, por separado.

Una consulta correcta significa que devolvió una respuesta sin excepción;
no implica `is_valid=True`, existencia de eventos ni aceptación de un envío.
Los percentiles de éxito son nulos si todas las consultas fallan. p50 utiliza
la mediana y p95/p99 el método de rango más cercano; p99 con 10 muestras no es
una estimación estable de la cola de latencias.

La latencia empieza cuando un worker invoca la operación pública: incluye
admisión del cliente, tasa/cooldown, firma, red y parsing. El tiempo de lote
incluye el recorrido del iterador y el consumo de resultados. **No se mide
aisladamente el tiempo interno del servidor DIAN.** La carga inicial PKCS#12,
calentamiento, cierre y escritura del informe quedan fuera del tiempo del lote.

El informe no almacena CUFEs, sus hashes, rutas de entrada, contraseña, XML,
URLs firmadas, mensajes de excepciones ni datos del certificado. Solo conserva
métricas agregadas. El benchmark retiene duraciones para calcular percentiles;
no debe usarse para acreditar el consumo de memoria del SDK.

Los resultados se guardan después de cada muestra completa. Si se interrumpe la
ejecución, `complete` permanece en `false`: las consultas de la muestra en curso
pueden haber llegado a DIAN aunque no aparezcan en el informe. Los fallos de
certificado/configuración detienen la ejecución; errores de consulta quedan
contabilizados y permiten continuar.

## Incorporar resultados a la documentación

Revise el JSON y la tabla generada. Publique las filas reales con su fecha,
ambiente, tamaño de muestra, concurrencia, versión, política de calentamiento,
tasa y condiciones generales del host/red. Muestre errores y timeouts junto a
las latencias; no elimine muestras fallidas ni mezcle ambientes. Conserve las
repeticiones por separado o calcule explícitamente su mediana: no promedie
percentiles como si fueran un percentil global.

La tabla puede regenerarse sin credenciales ni red:

```bash
uv run python scripts/benchmark_event_queries.py render /tmp/eventos-dian.json
```

Tras revisar y anonimizar las condiciones del entorno, añada el JSON a
`docs/benchmarks/` y la tabla a esta página, indicando su contexto. No se incluye
una tabla con cifras inventadas. Las comparaciones locales y sus límites siguen
documentados en el [informe de arquitectura](../ASYNC_ARCHITECTURE_PLAN.md).
