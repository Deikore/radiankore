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
| `get_numbering_range(*, account_code: str, account_code_t: str, software_code: str)` | `NumberingRangeResult \| None` | [Numeración](operations/numbering-range.md) |
| `get_exchange_emails()` | `ExchangeEmailsResult \| None` | [Directorio de correos](operations/exchange-emails.md) |
| `get_status(track_id: str)` | `DocumentStatusResult \| None` | [Validación](operations/status.md) |
| `get_invoice_events(cufe: str)` | `InvoiceEventsResult` | [Eventos](operations/events.md) |
| `get_acquirer(*, identification_type: IdentificationType, identification_number: str)` | `AcquirerResult \| None` | [Adquirientes](operations/acquirer.md) |
| `get_document_info(uuid: str)` | `DocumentInfoResult \| None` | [Información](operations/document-info.md) |
| `get_reference_notes(track_id: str)` | `ReferenceNotesResult \| None` | [Notas](operations/reference-notes.md) |
| `prepare_radian_event(*, event: RadianEvent, software: RadianSoftware)` | `PreparedRadianEvent` | [Preparación RADIAN](operations/radian-emission.md) |
| `send_radian_event(prepared: PreparedRadianEvent)` | `SendEventResult \| None` | [Envío RADIAN](operations/radian-emission.md) |
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
    ExchangeEmailsResult,
    InvoiceEventsResult,
    NumberingRange,
    NumberingRangeResult,
    ReferenceNotesResult,
    XmlDocumentResult,
)
from radiankore.catalogs import EventType, IdentificationType
```

`DocumentInfoResult.documents` conserva todos los documentos en una tupla,
incluidos orden, repeticiones y entradas nulas.
`DocumentInfo.document_type_id` y `DocumentReference.document_type_id` usan
`DocumentType`, importado desde `radiankore.catalogs`.
`DocumentInfo.document_code` usa `CreditNoteReason` para notas crédito,
`DebitNoteReason` para débito y texto para otros documentos, además de `None`.

`ReferenceNote.code` usa `DocumentType.CREDIT_NOTE`, `DocumentType.DEBIT_NOTE`
o `None`; `NoteResponse.code` conserva los motivos de línea como texto.

Los enums, sus etiquetas y las reglas para códigos desconocidos se describen en
[catálogos](catalogs.md). `_soap` y los nombres privados son detalles internos.

Los modelos de entrada y artefactos de mandato se importan desde
`radiankore.models.events`. El cliente carga el certificado una vez y lo reutiliza
para firmar UBL y SOAP. Preparar no contacta DIAN; enviar exige el mismo ambiente y
no reconstruye el ZIP. Consulta las [reglas y el ejemplo](operations/mandate.md).


Para emitir 030–034, importa `InvoiceResponseEvent`, `InvoiceEventParty`,
`InvoiceEventPerson`, `InvoiceEventDocumentReference` y `PreparedRadianEvent`
desde `radiankore.models.events`. `InvoiceResponseEvent` es una entrada validada;
`radiankore.models.responses.InvoiceEvent` sigue siendo un registro de consulta.
Consulta el [contrato y los cinco ejemplos](operations/invoice-emission.md).


`RadianEvent` une quince modelos: `InvoiceResponseEvent`, `MandateEvent`,
`MandateTerminationEvent`, `RadianRegistrationEvent`,
`InvoicePaymentEvent`, `PaymentReportEvent`, `EndorsementEvent`,
`EndorsementCancellationEvent`, `GuaranteeEvent`, `CirculationRestrictionEvent`,
`CirculationRestrictionTerminationEvent`, `ProtestEvent`,
`EconomicRightsTransferEvent`, `EconomicRightsNotificationEvent` y
`EconomicRightsPaymentEvent`. Se importan con sus componentes y `PreparedRadianEvent`
desde `radiankore.models.events`. Todos los eventos 030–051 usan la misma pareja
de métodos y el mismo tipo de artefacto preparado. Consulta la
[guía y variantes](operations/radian-emission.md).


La [matriz de fuentes](event-reference-map.md) permite localizar la sección, página,
ejemplos y pruebas de cada evento; los [modelos](models.md), [catálogos](catalogs.md)
y [errores](errors.md) documentan los contratos sin duplicar esta tabla de métodos.
