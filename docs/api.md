# API pública

## Cliente y certificado

```python
from radiankore import DianClient, DigitalCertificate, Environment
```

`DianClient(certificate_path, *, password=None, environment=Environment.PRODUCTION,
timeout=30.0)` recibe una ruta `str | os.PathLike[str]`. La contraseña admite
`str | bytes | None`. El ambiente admite `Environment` o su valor de texto; el
timeout debe ser positivo y finito. Cargar el cliente no realiza conexiones.

La propiedad `certificate` expone el material ya cargado y `environment` el
ambiente seleccionado. No hay gestión de cierre a cargo del consumidor.
`DigitalCertificate.from_file()` y `from_pfx()` también permiten cargar material
independientemente; consulta [errores y certificado](errors.md).

| Método | Retorno | Detalle |
| --- | --- | --- |
| `get_status(track_id: str)` | `DocumentStatusResult \| None` | [Validación](operations/status.md) |
| `get_invoice_events(cufe: str)` | `InvoiceEventsResult` | [Eventos](operations/events.md) |
| `get_acquirer(*, identification_type: IdentificationType, identification_number: str)` | `AcquirerResult \| None` | [Adquirientes](operations/acquirer.md) |
| `get_document_info(uuid: str)` | `DocumentInfoResult \| None` | [Información](operations/document-info.md) |
| `get_reference_notes(track_id: str)` | `ReferenceNotesResult \| None` | [Notas](operations/reference-notes.md) |
| `get_xml_by_document_key(document_key: str)` | `XmlDocumentResult \| None` | [XML original](operations/xml-document.md) |

Los identificadores deben ser texto no vacío tras recortar espacios exteriores.
Los errores de tipo generan `TypeError`; los valores vacíos, `ValueError`.
No se imponen formatos UUID ni hexadecimal a los identificadores de consulta.

## Modelos y catálogos

Las dataclasses se importan desde `radiankore.models.responses`; sus campos se
construyen por nombre y las colecciones son tuplas. Cada guía de operación detalla
su modelo, opcionalidad, correspondencia XML y tratamiento de errores.

```python
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfoResult,
    DocumentStatusResult,
    InvoiceEventsResult,
    ReferenceNotesResult,
    XmlDocumentResult,
)
from radiankore.catalogs import EventType, IdentificationType
```

Los enums, sus etiquetas y las reglas para códigos desconocidos se describen en
[catálogos](catalogs.md). `_soap` y los nombres privados son detalles internos.
