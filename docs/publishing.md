# Publicar radiankore en PyPI

El workflow [publish.yml](https://github.com/Deikore/radiankore/blob/HEAD/.github/workflows/publish.yml) publica las
distribuciones de una release de GitHub después de superar CI. No necesita tokens
API almacenados en GitHub: utiliza [Trusted Publishing de PyPI](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Configuración inicial

1. Utilice una cuenta de PyPI con autenticación de dos factores y acceso al proyecto.
2. En PyPI, registre un **pending publisher** si el proyecto aún no existe, o un
   Trusted Publisher si ya existe. Utilice exactamente:
   - Nombre PyPI: `radiankore`.
   - Propietario GitHub: `Deikore`.
   - Repositorio: `radiankore`.
   - Workflow: `publish.yml`.
   - Entorno: `pypi`.
3. Cree el entorno `pypi` en GitHub. Configure las reglas de releases y revisores que
   desee el mantenedor. El nombre debe coincidir exactamente con el registrado en PyPI.
4. Verifique que licencia, URLs públicas, versión y README describan lo publicado.
   La disponibilidad definitiva del nombre la determina PyPI al crear/publicar.

Esta configuración en PyPI y GitHub es necesaria: añadir el workflow al repositorio
no registra automáticamente el publisher ni publica una versión.

## Preparar una versión

Actualice `project.version` en `pyproject.toml`, ejecute `uv lock` y mueva las notas
correspondientes del changelog a la versión fechada. Compruebe:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-report=term-missing
uv run --no-project --with-requirements docs/requirements.txt sphinx-build -E -W --keep-going -b html docs docs/_build/html
uv build
uvx twine check dist/*
```

Utilice una carpeta `dist/` limpia para que contenga únicamente los dos artefactos de
la versión que va a publicar. Compruebe que wheel y sdist incluyen `py.typed`,
licencia MIT y notas de material de terceros, y excluyen certificados, configuración local y
las referencias técnicas de DIAN. Pruebe la instalación del wheel fuera del árbol
fuente; CI también ejecuta la suite completa contra el wheel instalado.

## Crear la release

Cree una etiqueta `v<VERSION>` que coincida exactamente con `project.version`
(por ejemplo, `v0.7.2` para `0.7.2`) y publique una release de GitHub desde esa
etiqueta. El workflow:

1. Verifica la correspondencia de etiqueta y versión.
2. Ejecuta calidad, la matriz Python 3.13–3.15, construcción, revisión con Twine y
   pruebas del wheel instalado.
3. Descarga el artefacto `radiankore-dist` de esa misma ejecución y lo publica en
   PyPI con permisos OIDC exclusivos del job de publicación.

El job de publicación no reconstruye el paquete. Revise la ejecución completa y
la página del proyecto en PyPI antes de anunciar la versión. Los números de versión
publicados no se reutilizan; las correcciones se publican como una versión nueva.
La integración real con DIAN requiere comprobaciones autorizadas aparte de CI.

## Release 0.7.2

El manifiesto, el lockfile y el changelog deben identificar `0.7.2`; la etiqueta
debe ser `v0.7.2`. Esta versión completa los modelos de eventos 030–051 y su
documentación de correspondencia XML, notas y cardinalidades.

Las notas de release deben destacar los cambios incompatibles:

- `notes` recibe `tuple[EventNote, ...]`; los propósitos se clasifican con
  `EventNoteKind`. Las notas adicionales no sustituyen declaraciones obligatorias.
- `MandateParty.representative` pasa a `representatives`; los soportes de mandato
  reciben `issuers` en lugar de `issuer`.
- Restricciones 041/042 y protestos 048 reciben sus referencias y evidencias
  mediante los componentes de `responses`.
- `factor_type` solo se admite para endosatarios 037/047.

Enlace el [inventario y la migración de notas](operations/event-notes.md) y la
[matriz completa de entradas](technical/event-input-matrix.md). Compruebe las
2795 pruebas y los ejemplos documentales con certificados sintéticos y transporte
simulado; no emita eventos reales como parte de la publicación.

El tag debe apuntar al mismo commit que pasó CI. Después de publicar la release,
revise el workflow y verifique una instalación de `radiankore==0.7.2` desde PyPI
en un entorno limpio. No reutilice ni modifique la etiqueta `v0.7.1`.

## Antecedente: release 0.7.1

El manifiesto y el lockfile deben identificar `0.7.1`, y la etiqueta debe ser
`v0.7.1`. Esta versión incorpora la revisión XML de 030–051 y las correcciones
de preparación asíncrona, cierre de pools y admisión por servicio.

Las notas de release deben destacar dos cambios de migración:

- `InvoicePaymentEvent` utiliza `payer` en lugar de `payers`, con un único pago
  y comprobación de importes y saldo. Consulte la
  [migración de 045](operations/radian-payments.md).
- `DianResponseLimits` activa topes de 16/64/128 MiB para SOAP, ZIP y CSV
  expandido. Omitir `response_limits` o pasar `None` activa los predeterminados;
  los campos individuales aceptan `None` para desactivar un tope. Consulte
  [la configuración](guides/response-limits.md).

Compruebe que el tag apunta al mismo commit que pasó CI. La publicación en
PyPI utiliza exclusivamente los artefactos producidos por la validación del
workflow de esa release. Verifique después una instalación de
`radiankore==0.7.1` en un entorno limpio, sin depender del checkout.

## Antecedente: release 0.7.0

La versión `0.7.0` introdujo la API asíncrona conservando la API síncrona.
El README presenta primero
`AsyncDianClient`; la [guía async](guides/async.md) incluye consultas individuales,
lotes, puente síncrono y construcción y envío de un acuse 030.

Los [benchmarks reales](guides/event-query-benchmark.md) conservan nueve
configuraciones, 27 muestras y 14.400 consultas observadas en producción.
Revise las tablas contra sus JSON y compruebe que solo se distribuyen métricas
agregadas. El [informe técnico](ASYNC_ARCHITECTURE_PLAN.md) separa resultados
locales y objetivos pendientes, incluido el objetivo de throughput frente a hilos.

Antes de etiquetar, valide el wheel instalado en Python 3.13–3.15, los ejemplos
publicados contra transporte simulado y la documentación con advertencias como
errores. Los scripts de benchmark son herramientas del checkout, no comandos
instalados con el wheel. No ejecute mediciones remotas en CI.

Un commit local no publica el paquete. La etiqueta `v0.7.2` y la release de
GitHub se crean después de revisar las validaciones; publicar esa release activa
el workflow. Mantenga los artefactos de construcción y los registros de pruebas
fuera del commit.
