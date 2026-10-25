# Consultar notas referenciadas

`GetReferenceNotes` devuelve notas tipadas, el estado de la consulta y los campos
binarios originales del contrato `DianResponse`. Utilice el certificado y ambiente del
mismo cliente:

```python
from radiankore import DianClient
from radiankore.catalogs import DocumentType
from radiankore.models.responses import ReferenceNotesResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
)
notes: ReferenceNotesResult | None = client.get_reference_notes("TRACK-ID-DE-EJEMPLO")
if notes is not None:
    print(notes.is_valid, notes.status_code, notes.status_description)
    print(notes.status_message, notes.messages)
    print(notes.document_key, notes.file_name)
    for note in notes.notes:
        print(note.code, note.description, note.date, note.time)
        if note.code is DocumentType.CREDIT_NOTE:
            print("Nota crédito")
        for reference in note.references:
            print(reference.id, reference.uuid)
        for line in note.line_responses:
            for response in line.responses:
                print(line.line_id, response.code, response.description)
    if notes.xml_base64_bytes is not None:
        print("Bytes de XmlBase64Bytes:", len(notes.xml_base64_bytes))
    if notes.xml_bytes is not None:
        print("Bytes de XmlBytes:", len(notes.xml_bytes))
```

`track_id` debe ser texto no vacío tras recortar espacios exteriores. Se envía como
`trackId`, sin imponer formato UUID ni hexadecimal. Un resultado ausente o nulo
produce `None`; uno presente y vacío produce `ReferenceNotesResult()`.

El modelo es una dataclass inmutable, con slots y argumentos por nombre, exportada
desde `radiankore.models.responses` y definida en `models/responses/reference_notes.py`.
`is_valid` es `bool | None`; los campos de estado, `document_key` y `file_name` son
`str | None`. Los textos escalares ausentes, nulos o vacíos valen `None`. Los estados
de negocio se conservan sin convertirlos automáticamente en excepciones.
`IsValid` ausente vale `None`; nulo o con un valor distinto de `true`, `false`, `1`
o `0` genera `DianResponseError`.

`messages` representa `ErrorMessage/string` como `tuple[str | None, ...]`: conserva
orden, repeticiones, elementos nulos y cadenas vacías; recorta espacios exteriores.
Un contenedor ausente, nulo o vacío produce `()`.

`xml_base64_bytes` y `xml_bytes` son `bytes | None`, decodificados respectivamente
de `XmlBase64Bytes` y `XmlBytes`. Ambos admiten espacios XML en Base64; un contenido
inválido genera `DianResponseError`, conservando la causa. Un elemento ausente o
nulo produce `None`; uno presente y vacío produce `b""`. Son independientes, no se
sustituyen entre sí y se excluyen de `repr`.

`notes` es una tupla de `ReferenceNote` obtenida automáticamente del UBL
`ApplicationResponse` contenido en `XmlBase64Bytes`, conforme a la muestra DIAN
observada. Puede contener varias notas: cada `DocumentResponse` produce una.
Se conserva el orden XML y las repeticiones, sin ordenar por `reference_id`.
El parseo se realiza también cuando `is_valid=False`, sin inferir el significado de
esa combinación con `status_code`.

Los modelos públicos adicionales se importan desde `radiankore.models.responses`:

- `ReferenceNote`: `reference_id`, `code`, `description`, `date`, `time`,
  `references`, `issuer`, `recipient` y `line_responses`.
- `NoteDocumentReference`: `id` obligatorio y `uuid` opcional. Todas las referencias
  se conservan; los identificadores no provienen del contenedor ni de `document_key`.
- `NoteLineResponse`: `line_id` obligatorio y tupla `responses`.
- `NoteResponse`: `reference_id`, `code`, `description`, `date` y `time` de una
  respuesta por línea. Cada línea conserva todas sus respuestas.

`ReferenceNote.code` tiene tipo `DocumentType | None`. Solo admite
`DocumentType.CREDIT_NOTE` (`91`) y `DocumentType.DEBIT_NOTE` (`92`). Campos
ausentes, nulos o vacíos producen `None`; el parser recorta espacios exteriores.
Códigos desconocidos, no canónicos como `091`, o de otros documentos generan
`DianResponseError` con `ValueError` como causa. `.value` devuelve el código de
texto y `.label` su etiqueta. Al construir una nota directamente, pasa el enum:
cadenas u otros tipos generan `TypeError`, y miembros de `DocumentType` distintos
de crédito/débito generan `ValueError`.

`reference_id` y `NoteResponse.code` siguen siendo `str | None`. Los códigos de
las respuestas por línea representan motivos independientes, como `2`, y admiten
valores no catalogados. No utilizan `DocumentType` ni `EventType`.
`description` une textos no vacíos con saltos de línea; si faltan, vale `""`.
Los participantes usan `EventParty`, con identificación, dígito y tipo de documento.
No se reutiliza `DocumentNote`, que pertenece al contrato de `GetDocumentInfo`.

Las fechas efectivas aceptan `YYYY-MM-DD` y son `datetime.date | None`; las horas
son `datetime.time | None` normalizadas a Colombia, UTC−05:00, ajustando la fecha
si cambia el día. Horas sin zona se interpretan como colombianas. Campos ausentes
o vacíos valen `None`; no se sustituyen por las fechas del contenedor. Estas reglas
se aplican tanto a la nota principal como a cada respuesta por línea.

Un payload ausente, nulo o vacío deja `notes=()`, conservando sus bytes originales.
Un `ApplicationResponse` sin `DocumentResponse` también produce `()`.
Un payload no vacío debe ser XML válido con raíz UBL `ApplicationResponse`; el
parser rechaza DTD, raíces incorrectas, fechas inválidas y estructuras sin los
campos obligatorios mediante `DianResponseError`. Cada nota requiere un `Response`
y al menos un `DocumentReference` con `ID` no vacío. Cada `LineResponse` requiere
`LineReference/LineID` y al menos un `Response`. El parser no realiza validación
integral XSD ni verifica la firma de la respuesta.

`XmlBytes` se mantiene independiente y no se interpreta como XML ni se usa como
fallback. No se descomprime ningún payload. El WSDL describe la respuesta exterior;
el contenido de notas se apoya en la muestra observada y los XSD UBL locales.
Consulte el [contrato SOAP local](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/wsdl/README.md#getreferencenotes).
