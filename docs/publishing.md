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
(por ejemplo, `v0.7.0` para `0.7.0`) y publique una release de GitHub desde esa
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

## Release 0.7.0

El manifiesto y el lockfile identifican `0.7.0`; `CHANGELOG.md` registra la API
asíncrona y la compatibilidad síncrona conservada. El README presenta primero
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

Un commit local no publica el paquete. La etiqueta `v0.7.0` y la release de
GitHub se crean después de revisar las validaciones; publicar esa release activa
el workflow. Mantenga los artefactos de construcción y los registros de pruebas
fuera del commit.
