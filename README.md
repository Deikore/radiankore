# radiankore

Librería Python de Deikore SAS para consultar servicios de DIAN y eventos RADIAN
con certificado digital PFX/P12. Python >=3.13, API síncrona y licencia MIT.

| | Estado |
| --- | --- |
| Documentación | [![Read the Docs](https://readthedocs.org/projects/radiankore/badge/?version=latest)](https://radiankore.readthedocs.io/) |
| Calidad y pruebas | [![CI](https://github.com/Deikore/radiankore/actions/workflows/ci.yml/badge.svg)](https://github.com/Deikore/radiankore/actions/workflows/ci.yml) |
| Paquete | [![PyPI](https://img.shields.io/pypi/v/radiankore)](https://pypi.org/project/radiankore/) [![Python](https://img.shields.io/pypi/pyversions/radiankore)](https://pypi.org/project/radiankore/) [![MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/Deikore/radiankore/blob/HEAD/LICENSE) |

## Instalación

```bash
pip install radiankore
# Con uv:
uv add radiankore
```

Disponible tras la primera publicación en PyPI. Si necesitas compilar las
dependencias de firma, consulta la
[guía de instalación](https://radiankore.readthedocs.io/).

## Métodos disponibles

| Método | Operación DIAN | Resultado |
| --- | --- | --- |
| `get_status(track_id)` | `GetStatus` | Estado de validación y payloads decodificados |
| `get_invoice_events(cufe)` | `GetStatusEvent` | Eventos asociados a una factura |
| `get_acquirer(identification_type=..., identification_number=...)` | `GetAcquirer` | Nombre y correo del adquiriente |
| `get_document_info(uuid)` | `GetDocumentInfo` | Información, estados, eventos y notas del documento |
| `get_reference_notes(track_id)` | `GetReferenceNotes` | Notas referenciadas y motivos por línea |
| `get_xml_by_document_key(document_key)` | `GetXmlByDocumentKey` | XML original del documento como `bytes` |

No genera facturas ni envía eventos. Los resultados utilizan dataclasses
inmutables y campos opcionales cuando corresponda.

## Consultar eventos

```python
from radiankore import DianClient, Environment

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
    environment=Environment.PRODUCTION,
)

result = client.get_invoice_events("CUFE-DE-LA-FACTURA")
for event in result.events:
    print(event.id, event.code, event.description, event.date, event.time)
```

Producción es el ambiente predeterminado; usa `Environment.HABILITATION` para
habilitación. Cada consulta cierra sus conexiones automáticamente y puedes
reutilizar el cliente sin volver a cargar el certificado.

## Otras consultas

```python
from pathlib import Path

from radiankore.catalogs import IdentificationType

status = client.get_status("CUFE-O-TRACK-ID")
if status is not None:
    print(status.is_valid, status.status_code, status.messages)

acquirer = client.get_acquirer(
    identification_type=IdentificationType.NIT,
    identification_number="000123456",
)
if acquirer is not None:
    print(acquirer.name, acquirer.email)

document = client.get_document_info("UUID-DEL-DOCUMENTO")
if document is not None:
    for item in document.documents:
        if item is not None:
            print(item.uuid, item.totals)

notes = client.get_reference_notes("CUFE-O-TRACK-ID")
if notes is not None:
    for note in notes.notes:
        print(note.code, note.description)

xml = client.get_xml_by_document_key("CLAVE-DEL-DOCUMENTO")
if xml is not None and xml.document_xml is not None:
    Path("documento.xml").write_bytes(xml.document_xml)
```

La [documentación completa](https://radiankore.readthedocs.io/) incluye contratos,
modelos, errores y ejemplos por operación. Para contribuir, consulta
[CONTRIBUTING](https://github.com/Deikore/radiankore/blob/HEAD/CONTRIBUTING.md).
