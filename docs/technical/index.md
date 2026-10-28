# Documentación técnica

Esta parte explica cómo utilizar radiankore para consultar documentos y preparar
y enviar eventos. Los ejemplos utilizan datos ficticios. Cada operación indica
sus entradas, resultados, validaciones y errores.

Para iniciar una integración, consulte el [cliente async](../guides/async.md).
Para evaluar tamaños de lote y concurrencias, revise los
[benchmarks reales de eventos](../guides/event-query-benchmark.md), con 14.400
consultas medidas en producción y sus informes agregados originales.

Para comprender las condiciones del acto que va a implementar, consulte primero
la [documentación funcional](../functional/index.md). Un ejemplo ejecutable no
sustituye la comprobación de facultades o antecedentes de negocio.

```{toctree}
:maxdepth: 1
:caption: Instalación y configuración

../installation
../environments
../guides/preparation
../guides/async
```

```{toctree}
:maxdepth: 1
:caption: Rendimiento y benchmarks

../guides/event-query-benchmark
../guides/performance
```

```{toctree}
:maxdepth: 1
:caption: Consultas y descarga

../guides/queries
../operations/status
../operations/events
../operations/document-info
../operations/reference-notes
../operations/xml-document
../operations/numbering-range
../operations/acquirer
../operations/exchange-emails
```

```{toctree}
:maxdepth: 2
:caption: Preparación y envío de eventos

../operations/radian-emission
../operations/invoice-emission
../operations/mandate
../guides/journeys
```

```{toctree}
:maxdepth: 1
:caption: Comunicación y operación

../guides/communication-and-signatures
../guides/operations
```

```{toctree}
:maxdepth: 1
:caption: Referencia técnica

../api
../models
../catalogs
../errors
../technical-references
../event-reference-map
../guides/evidence
```

```{toctree}
:maxdepth: 1
:caption: Mantenimiento del proyecto

../development
../ASYNC_ARCHITECTURE_PLAN
../publishing
../readthedocs
../changelog
```
