# Contribuir a radiankore

Usa Python >=3.13 y `uv`. El código y los docstrings se escriben en inglés; la
documentación, en español. Mantén la API pública pequeña y tipada.

## Preparación y comprobaciones

Desde una copia del repositorio:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov --cov-report=term-missing
uv build
```

Si `lxml` y `xmlsec` usan versiones incompatibles de `libxml2`, consulta las
instrucciones de compilación conjunta en [instalación](docs/installation.md).

## Documentación

El README contiene instalación, métodos y ejemplos breves. Los detalles viven en
`docs/`; consulta [cómo compilar y publicar el sitio](docs/readthedocs.md).

```bash
uv run --no-project --with-requirements docs/requirements.txt sphinx-build -W --keep-going -b html docs docs/_build/html
```

## Cambios y pull requests

- Explica el problema, el comportamiento resultante y las validaciones realizadas.
- Enlaza los issues relacionados e indica las comprobaciones que no pudiste ejecutar.
- Añade pruebas de comportamiento y regresiones con datos sintéticos.
- Mantén `uv.lock` actualizado si cambias dependencias o la versión del paquete.
- Documenta los cambios de API y errores en README y en [CHANGELOG](CHANGELOG.md).

Las pruebas usan certificados ficticios y HTTP simulado. No deben contactar DIAN,
utilizar credenciales reales ni incorporar XML de documentos reales. Conserva las
atribuciones de [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES) y los originales de las
referencias técnicas. El código se distribuye bajo [MIT](LICENSE); los materiales
de terceros mantienen sus condiciones originales.

## Versiones y publicación

Consulta [la guía de publicación](docs/publishing.md). Una release de GitHub con
etiqueta `v<VERSION>` ejecuta los controles y publica los artefactos validados
mediante el entorno `pypi` y Trusted Publishing. Las pull requests y los pushes
ordinarios ejecutan CI sin publicar.
