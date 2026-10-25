# Consultar, interpretar y descargar

## Seleccionar la pregunta

| Pregunta funcional | Método Python / operación SOAP | Contrato detallado |
| --- | --- | --- |
| ¿Fue validado el documento? | `get_status(track_id)` / GetStatus | [Estado](../operations/status.md) |
| ¿Qué eventos están asociados a la factura? | `get_invoice_events(cufe)` / GetStatusEvent | [Eventos](../operations/events.md) |
| ¿Qué participantes, montos, tenedor y estados devuelve DIAN? | `get_document_info(uuid)` / GetDocumentInfo | [Información](../operations/document-info.md) |
| ¿Qué notas se referencian? | `get_reference_notes(track_id)` / GetReferenceNotes | [Notas](../operations/reference-notes.md) |
| ¿Puedo obtener los bytes del documento? | `get_xml_by_document_key(document_key)` / GetXmlByDocumentKey | [XML](../operations/xml-document.md) |
| ¿Qué rangos de numeración tiene el software? | `get_numbering_range(...)` / GetNumberingRange | [Numeración](../operations/numbering-range.md) |
| ¿Qué nombre/correo devuelve DIAN para el adquirente? | `get_acquirer(...)` / GetAcquirer | [Adquirente](../operations/acquirer.md) |
| ¿Qué directorio de correos está disponible? | `get_exchange_emails()` / GetExchangeEmails | [Correos](../operations/exchange-emails.md) |

## Un recorrido de consulta en Python

Las funciones no se ejecutan al importar este bloque. Reciben un cliente ya
configurado: reutiliza su certificado y selecciona explícitamente el ambiente.
`inspect_invoice` devuelve los modelos originales para que su presentación no
pierda campos. No deduce quién es tenedor a partir del último evento de una lista.

```python
from pathlib import Path

from radiankore import DianClient
from radiankore.catalogs import IdentificationType
from radiankore.models.responses import (
    AcquirerResult,
    DocumentInfoResult,
    DocumentStatusResult,
    ExchangeEmailsResult,
    InvoiceEventsResult,
    NumberingRangeResult,
    ReferenceNotesResult,
)


def inspect_invoice(
    client: DianClient, cufe: str
) -> tuple[
    DocumentStatusResult | None,
    InvoiceEventsResult,
    DocumentInfoResult | None,
    ReferenceNotesResult | None,
]:
    status = client.get_status(cufe)
    events = client.get_invoice_events(cufe)
    information = client.get_document_info(cufe)
    notes = client.get_reference_notes(cufe)
    return status, events, information, notes


def save_document(client: DianClient, document_key: str, destination: Path) -> bool:
    result = client.get_xml_by_document_key(document_key)
    if result is None or result.document_xml is None:
        return False
    destination.write_bytes(result.document_xml)
    return True


def inspect_directory(
    client: DianClient,
    account_code: str,
    account_code_t: str,
    software_code: str,
    identification_number: str,
) -> tuple[
    NumberingRangeResult | None, AcquirerResult | None, ExchangeEmailsResult | None
]:
    numbering = client.get_numbering_range(
        account_code=account_code,
        account_code_t=account_code_t,
        software_code=software_code,
    )
    acquirer = client.get_acquirer(
        identification_type=IdentificationType.NIT,
        identification_number=identification_number,
    )
    emails = client.get_exchange_emails()
    return numbering, acquirer, emails
```

`save_document` escribe bytes exactos, incluso `b""`; `False` significa ausencia
binaria, no diagnóstico de negocio. Seleccione el destino desde su aplicación, nunca
utilice directamente un nombre o ruta recibido del servidor. Compruebe también
`status_code` y `message` si necesita distinguir rechazo, ausencia y éxito.
Para una nota o un evento usa su clave conocida y el mismo método de descarga;
no todos los resultados proporcionan una clave ni garantizan disponibilidad del XML.
No sustituyas una referencia de la factura por una supuesta clave de la nota.

DIAN documenta disponibilidad de numeración en producción. El SDK conserva el
ambiente elegido también para esa operación; no cambia automáticamente de destino.
Configura el cliente y las autorizaciones según el servicio que vaya a consultar.

## Leer las respuestas sin perder significado

Ejemplo **inventado**, expresado como resumen funcional y no como captura DIAN:

```text
HTTP de transporte: 200
GetStatus: IsValid=false, StatusCode="99", mensajes=("Regla sintética",)
GetDocumentInfo: StatusCode=200, documentos=[FE-DEMO-1, null]
FE-DEMO-1: tenedor declarado en respuesta, total=Decimal("120000.50")
GetStatusEvent: ReferenceID=[1, 2, 10], códigos=[030, 032, 033]
GetReferenceNotes: nota 91, referencias con ID y UUID propios
GetXmlByDocumentKey: Code=200, bytes XML originales
```

Aquí HTTP 200 no convierte `IsValid=false` en aceptación. Los códigos de
`GetStatus`, eventos y numeración conservan sus contratos de texto; los de
`GetDocumentInfo` y `GetXmlByDocumentKey` son `HTTPStatus | None`, aunque viajen
dentro de SOAP. Un HTTP 404 de transporte sigue siendo error, salvo la excepción
específica de `get_acquirer`: sin SOAP Fault devuelve `None`.

| Situación | Cómo interpretarla |
| --- | --- |
| Resultado ausente o `xsi:nil` | Generalmente `None`; eventos conserva `InvoiceEventsResult` con colección vacía |
| Resultado presente vacío | Modelo vacío según operación, no aceptación implícita |
| `is_valid=False` | Resultado de negocio; conserva mensajes y payloads |
| `messages` no vacío con `is_valid=True` | No conviertas toda advertencia en rechazo |
| Código catalogado desconocido | `DianResponseError`; conserva evidencia saneada y revisa compatibilidad |
| `documents` con varias entradas o `None` | Itera todas, comprueba nulos; no selecciona automáticamente una factura |
| Eventos ordenados por ReferenceID numérico | No equivale a orden jurídico ni a reconstrucción de tenencia |
| Notas repetidas | Se preservan, junto con orden XML y motivos por línea |

`DocumentInfo` contiene participantes, numeración, tenedor, totales, estados,
eventos, notas, referencias y validaciones. Los importes se convierten directamente
a `Decimal` sin `float`; las respuestas que proceden de `xs:double` pueden incluir
NaN/INF. Decida su presentación antes de hacer cálculos financieros.
Los estados de documento conservan claves enteras y texto; no existe en el SDK
un catálogo oficial inferido a partir de observaciones aisladas.

`compressed_document_info` es texto opaco: no se presupone gzip ni se usa como
fallback de `documents`. `XmlBase64Bytes` y `XmlBytes` se decodifican por separado
cuando existen, sin reinterpretar ni reformatear sus bytes.

Las fechas efectivas de eventos/notas se normalizan conjuntamente a Colombia
(UTC−05:00), con posible cambio de día; no se reemplazan por la fecha del
contenedor. `ValidationDate` de XML conserva fecha o timestamp y su zona original.
Las notas usan tipos 91/92, nunca `EventType`; los motivos de línea son otro contrato.

`get_exchange_emails` puede efectuar una segunda petición GET a una URL temporal
para descargar un ZIP con exactamente un CSV UTF-8. Ese GET no lleva la firma
SOAP. No hay redirecciones ni reintentos. No registres URL temporales o CSV completos.
Consulte su guía para columnas, errores y opcionalidad.

## Límite de confianza

El parser interpreta datos y rechaza estructuras inválidas según su contrato;
no verifica firmas de respuestas ni ejecuta validación integral XSD/Schematron.
Conservar bytes es necesario si su aplicación incorpora una verificación adicional.
Para distinguir fallos de red, SOAP, parsing y negocio usa
[operación y diagnóstico](operations.md).
