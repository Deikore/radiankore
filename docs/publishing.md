# Publicar radiankore en PyPI

El workflow [publish.yml](https://github.com/Deikore/radiankore/blob/HEAD/.github/workflows/publish.yml) publica las
distribuciones de una release de GitHub después de superar CI. No necesita tokens
API almacenados en GitHub: utiliza [Trusted Publishing de PyPI](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Configuración inicial

1. Usa una cuenta de PyPI con autenticación de dos factores y acceso al proyecto.
2. En PyPI, registra un **pending publisher** si el proyecto aún no existe, o un
   Trusted Publisher si ya existe. Usa exactamente:
   - Nombre PyPI: `radiankore`.
   - Propietario GitHub: `Deikore`.
   - Repositorio: `radiankore`.
   - Workflow: `publish.yml`.
   - Entorno: `pypi`.
3. Crea el entorno `pypi` en GitHub. Configura las reglas de releases y revisores que
   desee el mantenedor. El nombre debe coincidir exactamente con el registrado en PyPI.
4. Verifica que licencia, URLs públicas, versión y README describan lo publicado.
   La disponibilidad definitiva del nombre la determina PyPI al crear/publicar.

Esta configuración en PyPI y GitHub es necesaria: añadir el workflow al repositorio
no registra automáticamente el publisher ni publica una versión.

## Preparar una versión

Actualiza `project.version` en `pyproject.toml`, ejecuta `uv lock` y mueve las notas
correspondientes del changelog a la versión fechada. Comprueba:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-report=term-missing
uv build
uvx twine check dist/*
```

Usa una carpeta `dist/` limpia para que contenga únicamente los dos artefactos de
la versión que vas a publicar. Comprueba que wheel y sdist incluyen `py.typed`,
licencia MIT y notas de material de terceros, y excluyen certificados, configuración local y
las referencias técnicas de DIAN. Prueba la instalación del wheel fuera del árbol
fuente; CI también ejecuta la suite completa contra el wheel instalado.

## Crear la release

Crea una etiqueta `v<VERSION>` que coincida exactamente con `project.version`
(por ejemplo, `v0.3.0` para `0.3.0`) y publica una release de GitHub desde esa
etiqueta. El workflow:

1. Verifica la correspondencia de etiqueta y versión.
2. Ejecuta calidad, la matriz Python 3.13–3.15, construcción, revisión con Twine y
   pruebas del wheel instalado.
3. Descarga el artefacto `radiankore-dist` de esa misma ejecución y lo publica en
   PyPI con permisos OIDC exclusivos del job de publicación.

El job de publicación no reconstruye el paquete. Revisa la ejecución completa y
la página del proyecto en PyPI antes de anunciar la versión. Los números de versión
publicados no se reutilizan; las correcciones se publican como una versión nueva.
La integración real con DIAN requiere comprobaciones autorizadas aparte de CI.
