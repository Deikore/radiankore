# Repository Guidelines

## Estructura y alcance

`radiankore` es una librería síncrona Python >=3.13.
Consulta seis operaciones SOAP de DIAN, descritas en README. No genera facturas
ni envía eventos.

En `src/radiankore/`, `client.py` coordina consultas, `certificate.py`
carga certificados y `environment.py` selecciona ambientes. `_soap/` contiene
firma, transporte y parsers; `models/responses/`, dataclasses públicas; `catalogs/`,
enums. Las pruebas están en `tests/` y workflows en `.github/workflows/`.

README contiene instalación, métodos y ejemplos breves; los contratos están en
[docs](docs/index.md) y [referencias DIAN](docs/references/dian/README.md). Conserva los originales y sus inventarios;
las referencias se excluyen de wheel y sdist. No modifiques `.agents/`, `.codex/`,
`.aws/` ni `.git/` en contribuciones ordinarias.

## Instalación y comandos

`.python-version` selecciona 3.13.

- `uv sync --locked`: instala dependencias y el paquete editable.
- `uv run ruff check .`: comprueba lint.
- `uv run ruff format --check .`: verifica formato; omite `--check` para aplicarlo.
- `uv run mypy`: comprueba tipado estricto.
- `uv run pytest --cov --cov-report=term-missing`: ejecuta pruebas y cobertura.
- `uv build`: genera wheel y sdist.

Actualiza `uv.lock` al cambiar dependencias o versión. `lxml` y `xmlsec` requieren
bibliotecas `libxml2` compatibles; sigue la instalación documentada.

## Estilo y contratos

Código y docstrings en inglés; documentación en español. Usa cuatro espacios,
88 caracteres, `snake_case`, `PascalCase` y exports públicos explícitos.
Mantén dataclasses inmutables, con slots y argumentos por nombre, sin procesamiento
XML ni HTTP dentro de los modelos.

Reutiliza `_request` y los lectores compartidos. El certificado se carga una vez;
cada consulta cierra sus conexiones. Producción es predeterminada.
No introduzcas reintentos, fallback entre ambientes ni reformateo después de firmar.

Preserva los contratos por operación: eventos ordenados numéricamente por
ReferenceID; notas en orden XML; ninguna deduplicación. Usa fechas nativas y
normalización colombiana donde corresponda; ValidationDate conserva su zona.
No uses enums de eventos para notas ni conviertas estados de negocio en excepciones. Conserva precisión Decimal y bytes originales.

## Pruebas y contribuciones

Usa pytest, archivos `test_*.py`, certificados sintéticos y MockTransport.
No contactes DIAN desde tests ni CI. Añade regresiones;
verifica firmas serializadas, errores y cierre de conexiones. Sin umbral mínimo de
cobertura. CI contempla Python 3.13–3.15 y pruebas del wheel instalado.

Usa commits imperativos y pull requests con propósito, issues y validaciones.
Sigue [CONTRIBUTING](CONTRIBUTING.md); nunca incluyas secretos ni documentos reales.

## Documentación

Sphinx/MyST/Furo compila docs/; sigue [la guía](docs/readthedocs.md).
No incorpores referencias originales al sitio ni detalles extensos al README.

## Publicación

Mantén autoría Deikore SAS, licencia MIT y notas de terceros separadas.
La release `v<VERSION>` debe coincidir con `pyproject.toml` y el changelog.
El workflow publica artefactos validados mediante Trusted Publishing, entorno
`pypi`; nunca desde pull requests. Sigue [publicación](docs/publishing.md).
