# Emitir eventos de factura 030–034

Contexto funcional: [030](../functional/events/030.md); [031](../functional/events/031.md); [032](../functional/events/032.md); [033](../functional/events/033.md); [034](../functional/events/034.md).

Esta guía describe la implementación y sus validaciones técnicas.

Para preparar y enviar con `AsyncDianClient`, consulte el
[ejemplo completo de acuse 030 con await](../guides/async.md).
Los modelos de esta guía se comparten entre ambos clientes.

`prepare_radian_event(*, event, software)` valida los datos, calcula CUDE,
firma un ApplicationResponse UBL 2.1 y crea el ZIP en memoria. No contacta DIAN
ni lee archivos después de cargar el certificado. `send_radian_event(prepared)`
envía el ZIP original una vez mediante `SendEventUpdateStatus` y devuelve
`SendEventResult | None`.

## Datos y diferencias entre eventos

| Código | Declaración | Generador → destinatario | Campos específicos |
| --- | --- | --- | --- |
| `030` | Acuse de recibo de la factura | Adquirente → facturador | `issuer_person` obligatorio |
| `031` | Reclamo | Adquirente → facturador | `claim_reason` obligatorio |
| `032` | Recibo de bienes o servicios | Adquirente → facturador | `issuer_person` obligatorio |
| `033` | Aceptación expresa | Adquirente → facturador | Sin persona receptora ni motivo |
| `034` | Aceptación tácita | Facturador → DIAN | `notes` con declaración juramentada |

Para 030–033, `receiver_party` identifica al facturador. Para 034 se omite: el
builder genera DIAN, NIT `800197268`, DV `4`, organización jurídica `1`.
`sender_party` identifica al titular del evento mediante NIT. El proveedor de
software, el firmante y la persona que recibió los bienes son datos independientes.
Los roles y autorizaciones efectivos se validan en DIAN.

`issuer_person` exige identificación, nombres y apellidos; cargo y departamento
son opcionales. Solo se admite para 030/032. `claim_reason` solo se admite en 031.
Todas las entradas usan dataclasses inmutables, con slots y argumentos por nombre.

## Ejemplos de los cinco eventos

Los datos siguientes son ficticios y no corresponden a participantes habilitados.
Los ejemplos comparten participantes y referencia para mostrar qué cambia por evento.

```python
from datetime import datetime, timedelta, timezone

from radiankore import DianClient, Environment
from radiankore.catalogs import (
    EventType,
    IdentificationType,
    InvoiceClaimReason,
    OrganizationType,
    PartyTaxScheme,
)
from radiankore.models.events import (
    InvoiceEventDocumentReference,
    InvoiceEventParty,
    InvoiceEventPerson,
    InvoiceResponseEvent,
    RadianSoftware,
)

buyer = InvoiceEventParty(
    name="Adquirente sintético",
    tax_number="900000001",
    identification_type=IdentificationType.NIT,
    verification_digit="1",
    organization_type=OrganizationType.LEGAL_PERSON,
    tax_scheme=PartyTaxScheme.VAT,
)
seller = InvoiceEventParty(
    name="Facturador sintético",
    tax_number="900000002",
    identification_type=IdentificationType.NIT,
    verification_digit="2",
    organization_type=OrganizationType.NATURAL_PERSON,
    tax_scheme=PartyTaxScheme.NOT_APPLICABLE,
)
person = InvoiceEventPerson(
    identification_number="100000003",
    identification_type=IdentificationType.CITIZENSHIP_CARD,
    first_name="Persona",
    family_name="Sintética",
    job_title="Recepción",
    organization_department="Compras",
)
reference = InvoiceEventDocumentReference(
    document_number="FE-PRUEBA-1",
    uuid="a" * 96,
)
stamp = datetime.now(timezone(timedelta(hours=-5)))

acknowledgement = InvoiceResponseEvent(
    code=EventType.INVOICE_ACKNOWLEDGEMENT,
    event_number="ACUSE-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    sender_party=buyer,
    receiver_party=seller,
    document_reference=reference,
    issuer_person=person,
)
claim = InvoiceResponseEvent(
    code=EventType.INVOICE_CLAIM,
    event_number="RECLAMO-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    sender_party=buyer,
    receiver_party=seller,
    document_reference=reference,
    claim_reason=InvoiceClaimReason.GOODS_PARTIALLY_DELIVERED,
)
receipt = InvoiceResponseEvent(
    code=EventType.GOODS_OR_SERVICES_RECEIPT,
    event_number="RECIBO-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    sender_party=buyer,
    receiver_party=seller,
    document_reference=reference,
    issuer_person=person,
)
express = InvoiceResponseEvent(
    code=EventType.EXPRESS_ACCEPTANCE,
    event_number="EXPRESA-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    sender_party=buyer,
    receiver_party=seller,
    document_reference=reference,
)
tacit = InvoiceResponseEvent(
    code=EventType.TACIT_ACCEPTANCE,
    event_number="TACITA-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    sender_party=seller,
    document_reference=reference,
    notes=(
        "Declaración sintética para demostrar la API; sustituir por el juramento "
        "aplicable del anexo FE 1.9 antes de una emisión real.",
    ),
)
software = RadianSoftware(
    software_id="00000000-0000-4000-8000-000000000001",
    pin="pin-sintético",
    provider_tax_number="900000002",
    provider_verification_digit="2",
    signer_role="thirdparty",
)
client = DianClient(
    "certificado.pfx",
    password="contraseña-de-ejemplo",
    environment=Environment.HABILITATION,
)
prepared = client.prepare_radian_event(
    event=acknowledgement,
    software=software,
)
print(prepared.code, prepared.cude)
# Inspecciona prepared.xml_bytes y prepared.zip_bytes antes de enviar.
result = client.send_radian_event(prepared)  # Este paso contacta DIAN.
if result is not None:
    print(result.is_valid, result.status_code, result.messages)
```

Para preparar otro evento, proporcione `claim`, `receipt`, `express` o `tacit` en
`event`. Estos ejemplos son alternativas; no se envían todos sobre una
misma factura. Reclamo y aceptación son declaraciones incompatibles.

## Declaraciones explícitas y representación

El consumidor aporta los textos de `notes`; la librería conserva caracteres,
orden y repeticiones. En 034 se exige al menos una nota no vacía. Se comprueba su
presencia, no la veracidad de los hechos ni el contenido jurídico del juramento.
Cada nota admite hasta 10.000 caracteres.

Las plantillas oficiales completas están en FE 1.9 §6.5.5.7, páginas 301–302:

| Plantilla | Datos que debe completar el consumidor |
| --- | --- |
| Persona natural o jurídica sin mandatario | Número y CUDE del recibo 032, razón social y NIT del adquirente; declaración sobre el plazo transcurrido y ausencia de aceptación/reclamo |
| Mandatario de persona jurídica | Nombre e identificación del mandatario, razón social y NIT del mandante y adquirente; juramento correspondiente |
| Mandatario de persona natural comerciante | Identificación y NIT del comerciante, identificación del mandatario y adquirente; juramento correspondiente |

Copie la plantilla aplicable del
[anexo oficial FE 1.9](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf#page=301)
y completa todos sus campos. No envíes las tres alternativas ni las instrucciones
editoriales incluidas en las ejemplificaciones. En cualquier evento generado por
mandatario, incluye también la nota de representación de §6.5.4, AAD11, con los
nombres reales del mandatario y mandante. La librería no deduce representación
del rol `thirdparty` del firmante.

## Hashes, firma y envío

- CUDE: SHA384 de número, fecha/hora colombiana, identificación del generador,
  identificación del destinatario real, código del evento, número/tipo de factura
  referenciada y PIN, en ese orden. Se valida el vector publicado en §11.5.1.
- SoftwareSecurityCode: SHA384 de software ID + PIN + número del evento.
- QR: URL del ambiente seleccionado con el **CUFE de la factura**, distinto del
  CUDE del nuevo evento. El mandato 043 conserva su perfil y QR actuales.
- `IssueDate`/`IssueTime`: normalización conjunta a UTC−05:00 y segundos enteros.
  Horas sin zona se interpretan en Colombia. La fecha resultante debe coincidir
  con la fecha real de firma en Colombia (AAD09e); no se cambia la fecha de firma
  para aceptar eventos históricos.
- Firma XAdES-EPES y SOAP con el certificado cargado, sin volver a leerlo ni
  descargar certificados. El XML firmado no se reformatea.
- XML firmado de hasta 500.000 bytes; ZIP con un único `ar_<CUDE>.xml`.
  El envío exige un cliente del mismo ambiente, conserva los bytes y cierra
  la conexión. No hay reintentos ni cambio automático de ambiente.

La referencia acepta `DocumentType` de factura `01`–`04` y CUFE hexadecimal de
96 caracteres. El tipo debe coincidir con el documento original. No se generan
facturas ni se reconstruyen sus CUFE.

DIAN valida documentos existentes, autorización, antecedentes y plazos hábiles.
La librería no consulta esos antecedentes automáticamente ni calcula un calendario
de días hábiles. Las respuestas de rechazo se conservan como `SendEventResult`;
los fallos técnicos mantienen las [excepciones existentes](../errors.md).

## Discrepancias de las referencias

| Dato | Criterio de implementación |
| --- | --- |
| `ProfileID` | Literal de AAD03: `DIAN 2.1: ApplicationResponse de Factura Electrónica de Venta`; algunas muestras añaden «la» |
| Descripción de 032 | Literal de rechazo AAH04, §8.6.1: `Recibo del bien y/o prestación del servicio`; la tabla de generación y el catálogo de consulta difieren |
| Reclamo 031 | Códigos y significados de tabla FE 13.3.12, coincidentes con la muestra FE 2026 para `02`; el genericode y la muestra RADIAN antigua difieren para `02`/`03` |
| Persona 030/032 | Obligatoria por reglas de rechazo; cargo/departamento opcionales, cuya ausencia produce notificación |
| Notas 034 | Plantillas vigentes del anexo FE; no se reproducen instrucciones ni múltiples alternativas de las muestras antiguas |

Las fuentes originales se preservan con procedencia y SHA-256 en el
[inventario FE 1.9](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/invoicing/1.9/README.md).
Las pruebas usan datos ficticios, XSD y verificación criptográfica independiente.
Estas comprobaciones locales no acreditan aceptación en DIAN; queda pendiente
validar con participantes y software autorizados en habilitación.
