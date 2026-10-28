# Repository Guidelines

## Estructura y alcance

`radiankore` es una librería Python >=3.13 con clientes síncrono y asíncrono.
Consulta ocho operaciones SOAP de DIAN, descritas en README, y emite el evento
de mandato (043), los eventos de factura 030–034 y los demás eventos RADIAN
035–042/044–051 mediante `SendEventUpdateStatus`. No genera facturas.

En `src/radiankore/`, `client.py` y `async_client.py` coordinan consultas y emisión, `certificate.py`
carga certificados y `environment.py` selecciona ambientes. `_soap/` contiene
firma, transporte y parsers; `_soap/events/` contiene el builder, firma UBL,
empaquetado ZIP y parser de emisión, con builders separados por familia y componentes de dominio compartidos. `models/responses/` y
`models/events/` albergan dataclasses públicas; `catalogs/` contiene enums.
Las pruebas están en `tests/` y workflows en `.github/workflows/`.

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

## RTK en Codex

- Usar el hook global de RTK y ejecutar los comandos normalmente, sin duplicar
  hooks locales ni añadir RTK a las dependencias de la librería o de CI.
- Mantener `uv run ruff ...`, `uv run mypy ...` y `uv run pytest ...`: RTK inserta
  el filtro específico dentro del entorno del proyecto. En RTK 1.1.0,
  `uv run --no-sync ...` usa el filtro genérico de `uv` y conserva la salida
  completa cuando el comando termina correctamente.
- Mantener las pruebas específicas durante la iteración y ejecutar la cobertura
  completa al cerrar cambios amplios. RTK no sustituye ninguna comprobación.
- Consultar el ahorro de este repositorio con `rtk gain --project`.
- Recuperar detalles mediante la ruta indicada por RTK; usar `rtk bypass <comando>`
  únicamente cuando la salida filtrada sea inutilizable.

## Estilo y contratos

Código y docstrings en inglés; documentación en español. Usa cuatro espacios,
88 caracteres, `snake_case`, `PascalCase` y exports públicos explícitos.
Mantén dataclasses inmutables, con slots y argumentos por nombre, sin procesamiento
XML ni HTTP dentro de los modelos.

Reutiliza `_request` y los lectores compartidos. El certificado se carga una vez.
`DianClient` cierra conexiones por operación salvo pooling opcional;
`AsyncDianClient` conserva pools propios y se cierra con `async with` o `aclose()`.
Mantén la firma, lectura de certificados, XML y ZIP fuera del event loop y
conserva el cupo de cada trabajo nativo cancelado hasta su terminación física.
Producción es predeterminada.
Los eventos 030–051 usan `prepare_radian_event` y `send_radian_event`, con un
único `PreparedRadianEvent`. Se preparan sin I/O y se envían explícitamente con
el ZIP original y el mismo ambiente; valida facultades, soportes, XSD y firmas serializadas en tests.
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
Los benchmarks reales contienen solo métricas agregadas; no añadas CUFEs ni
credenciales y no ejecutes el benchmark remoto como parte de tests o CI.

## Publicación

Mantén autoría Deikore SAS, licencia MIT y notas de terceros separadas.
La release `v<VERSION>` debe coincidir con `pyproject.toml` y el changelog.
El workflow publica artefactos validados mediante Trusted Publishing, entorno
`pypi`; nunca desde pull requests. Sigue [publicación](docs/publishing.md).
