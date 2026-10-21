# Desarrollo

El anexo técnico y los 138 archivos extraídos de la caja de herramientas están en
[docs/references/dian/](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/README.md), con procedencia y estado de
cada material e inventario SHA-256 del contenido extraído. Se mantienen fuera de
las distribuciones instalables.

```text
src/radiankore/
  client.py             API pública y ciclo de vida
  certificate.py        Carga del PFX
  environment.py        Ambientes y destinos
  exceptions.py         Excepciones públicas
  catalogs/             Tipos de identificación y eventos DIAN
  models/responses/     Dataclasses de resultados
                        Estados, eventos, adquirientes, documentos, notas y XML descargado
  _soap/                Sobre, firma, transporte y parser internos
  py.typed              Tipado distribuido a consumidores
tests/                  Certificados sintéticos, XML ficticio y MockTransport
.github/workflows/      Calidad, pruebas y empaquetado
skills/                 Skill reutilizable de arquitectura
```

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
```

Código y docstrings en inglés; documentación en español. Usa cuatro espacios,
`snake_case` para funciones y módulos, `PascalCase` para clases y líneas de 88
caracteres. CI configura Python 3.13, 3.14 y 3.15. El workflow de releases publica
solo después de superar los controles.
Ejecuta `uv lock` al cambiar dependencias o `uv lock --upgrade` para actualizarlas.

## Ejecutar los tests

Desde la raíz del repositorio, instala las dependencias de desarrollo y ejecuta
la suite completa con pytest:

```bash
uv sync --locked
uv run pytest
```

Las pruebas se encuentran en `tests/`, en archivos `test_*.py` con funciones
`test_*`. Usan certificados sintéticos, XML ficticio y `httpx.MockTransport`;
no requieren certificados reales, credenciales ni conexiones con DIAN.
Las consultas de adquirientes se prueban en `tests/test_acquirer.py`; los helpers
SOAP y el transporte se comparten con las consultas de eventos y documentos.
`tests/test_document_info.py` cubre el contrato completo de `GetDocumentInfo`.
`tests/test_reference_notes.py` comprueba metadatos y campos binarios independientes
de `GetReferenceNotes`; `tests/test_reference_notes_payload.py` cubre las notas UBL,
referencias, motivos y fechas. `tests/test_xml_document.py` cubre la descarga,
decodificación exacta y fechas de validación. Las pruebas de firma y transporte
cubren las ocho operaciones.
`tests/test_document_status.py` cubre estados, mensajes y payloads de `GetStatus`.

Para ejecutar un archivo o seleccionar una prueba por nombre:

```bash
uv run pytest tests/test_soap_client.py
uv run pytest tests/test_soap_client.py -k client_remains_usable_after_failed_query
```

Para ver la cobertura y las líneas pendientes de ejecutar en la terminal:

```bash
uv run pytest --cov --cov-report=term-missing
```

No hay umbral mínimo de cobertura configurado. Las pruebas comprueban la carga de
certificados, la firma SOAP, el parseo de respuestas, los ambientes, el cierre
automático de conexiones y el manejo de errores.

## Validación real explícita

Las pruebas automáticas no contactan a DIAN. Para comprobar la integración, ejecuta
el ejemplo con un certificado autorizado, selecciona el ambiente y proporciona un
CUFE conocido de ese ambiente. Compara estado, cantidad y códigos de eventos con
la consulta de referencia. Repite en el otro ambiente solo con datos disponibles
allí. Esta prueba depende de las autorizaciones del certificado y del servicio;
los tests locales no prueban su aceptación real. No ejecutes este paso en CI.

