# radiankore

Documentación para comprender los procesos de factura electrónica y RADIAN,
y para integrarlos mediante la biblioteca Python radiankore.

Desde 0.7.0, `AsyncDianClient` permite consultas concurrentes y preparación y
envío de eventos con `await`. Comience por la [guía async](guides/async.md).

## Rendimiento medido en producción

En los ensayos del 28 de octubre de 2026, consultar 1.000 CUFEs con concurrencia
20 tardó **22,41 segundos de mediana**. Los nueve escenarios sumaron 14.400
consultas sin excepciones, timeouts ni reintentos. Los resultados describen
estas ejecuciones, no una capacidad garantizada del servicio.

La [comparación de benchmarks reales](guides/event-query-benchmark.md) muestra
los tamaños de lote, concurrencias, percentiles y datos originales. Las
[comparaciones locales](ASYNC_ARCHITECTURE_PLAN.md) distinguen simulaciones y
objetivos de rendimiento pendientes.

## Dos recorridos de lectura

**Documentación funcional.** Explica los conceptos, los actores, las condiciones
y los efectos de los eventos. Está dirigida a quienes necesitan comprender o
definir el proceso de negocio. No requiere conocimientos de programación.

**Documentación técnica.** Explica la instalación, la configuración, las consultas,
la preparación y el envío de eventos. Incluye ejemplos de Python y la referencia
necesaria para desarrollar y mantener una integración.

```{toctree}
:maxdepth: 1

functional/index
technical/index
```

Para una primera lectura, comience por la parte funcional. Si ya conoce el proceso,
puede acceder directamente a la implementación técnica correspondiente.
