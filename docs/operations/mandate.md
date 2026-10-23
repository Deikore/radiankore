# Mandato RADIAN (043)

`prepare_radian_event()` construye, firma y comprime un ApplicationResponse en
memoria, sin red ni escritura de archivos. `send_radian_event(prepared)` envía
exactamente ese ZIP mediante `SendEventUpdateStatus`, autenticado por SOAP.
Esta guía describe el mandato 043; las demás familias usan la misma API común.
No genera facturas ni realiza reintentos automáticos.

## Ejemplo de preparación y envío

Datos ficticios: sustituye identidades, CUFE, declaración, software y soportes por
los de tu operación. La declaración debe corresponder a las partes y al contrato;
la librería no redacta ni verifica declaraciones jurídicas.

```python
from datetime import date, time
from pathlib import Path

from radiankore import DianClient, Environment
from radiankore.catalogs import (
    IdentificationType,
    MandateChannel,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandatorType,
)
from radiankore.models.events import (
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateParty,
    MandatePerson,
    MandateScope,
    MandateValidityPeriod,
    RadianSoftware,
)

representative = MandatePerson(
    identification_number="100000001",
    identification_type=IdentificationType.CITIZENSHIP_CARD,
    first_name="Persona",
    family_name="De Ejemplo",
    job_title="Representante Legal",
)
mandator = MandateParty(
    name="Mandante de ejemplo",
    tax_number="900000001",
    verification_digit="1",
    identification_type=IdentificationType.NIT,
    role=MandatorType.INVOICE_ISSUER,
    representative=representative,
)
mandatee = MandateParty(
    name="Mandatario de ejemplo",
    tax_number="900000002",
    verification_digit="2",
    identification_type=IdentificationType.NIT,
    role=MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM,
    representative=representative,
)
event = MandateEvent(
    operation_type=MandateOperationType.LIMITED_LIMITED_TIME,
    nature=MandateNature.SPECIAL,
    reference_type=MandateReferenceType.ONE,
    event_number="MANDATO-1",
    issue_date=date(2026, 10, 22),
    issue_time=time(10, 30),
    notes=(
        "Declaración de ejemplo: confiero las facultades descritas en el contrato "
        "sintético. Este texto de demostración no constituye un mandato real.",
    ),
    sender_party=mandator,
    mandatee_party=mandatee,
    effective_date=date(2026, 10, 22),
    document_references=(
        MandateDocumentReference(document_number="FE1", uuid="a" * 96),
    ),
    validity_period=MandateValidityPeriod(
        start_date=date(2026, 10, 22),
        end_date=date(2026, 12, 31),
    ),
    scope=MandateScope(
        powers=(
            (
                MandatePower.WITH_REPRESENTATION,
                MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM,
            ),
            (MandatePower.MANDATE, MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM),
        )
    ),
    attached_contract=MandateAttachedDocument(
        document_id="CONTRATO-1",
        embedded_bytes=Path("contrato.pdf").read_bytes(),
    ),
    acceptance=True,
)
software = RadianSoftware(
    software_id="00000000-0000-4000-8000-000000000001",
    pin="pin-de-ejemplo",
    provider_tax_number="900000002",
    provider_verification_digit="2",
    signer_role="thirdparty",
)
client = DianClient(
    "certificado.pfx",
    password="password-de-ejemplo",
    environment=Environment.HABILITATION,
)
prepared = client.prepare_radian_event(event=event, software=software)
print(prepared.cude)
# Puedes inspeccionar o guardar prepared.xml_bytes y prepared.zip_bytes.
result = client.send_radian_event(prepared)  # Este paso sí contacta DIAN.
if result is not None:
    print(result.is_valid, result.status_code, result.messages)
```

## Variantes y restricciones

- Operaciones 431/432: alcance documental general, una facultad ALL17 con su canal.
  Operaciones 433/434: MR91 seguido por facultades R01–R22. Consulta los
  [catálogos](../catalogs.md). El canal PT no está permitido para R01–R05.
- Tiempo limitado (431/433): ambas fechas son obligatorias y fin ≥ inicio.
  Tiempo ilimitado (432/434): omite ambas fechas con `MandateValidityPeriod()`.
- `ONE`: una referencia; `MULTIPLE`: entre 2 y 20; `ALL`: tupla vacía explícita.
  Las referencias concretas son facturas `01` y requieren número y CUFE hexadecimal
  de 96 caracteres. ALL produce ID `1`, sin UUID ni DocumentTypeCode en XML.
- Para facultades por factura en 433/434, pasa `scope=MandateScope(...)` en cada
  `MandateDocumentReference`. Si se omite, se usa el alcance común del evento.
  Alcances iguales comparten un bloque DocumentResponse; cada grupo conserva
  el orden de sus referencias. El bloque principal conserva todas las referencias
  en el orden suministrado, incluidas repeticiones.
- Tanto SPECIAL como GENERAL requieren el contrato PDF. GENERAL requiere además
  `attached_validity_note`. En ambos soportes indica `issuer=MandatePerson(...)`
  con identidad, nombre y `organization_department` (número de notaría).
  En el contrato indica `effective_date=date(...)` con la fecha de escritura pública.
  SPECIAL no incluye nota notarial de vigencia.
- La aceptación debe ser explícitamente `True`; solo se emite `ACEPTA`.
  El receptor DIAN y las descripciones fijas se generan internamente.

## Hashes, firma y bytes

SoftwareSecurityCode es SHA384(software ID + PIN + número de evento).
El CUDE usa número de evento, fecha/hora de emisión, identificación del mandante,
NIT DIAN, `043`, número de la primera referencia, `01` y PIN (§12.1.1).
Para ALL, la referencia de hash es `1` y el tipo `01` (§12.1.4), aunque este último
se omite del XML. Fecha y hora se normalizan juntas a UTC−05:00, con precisión de
segundos; horas sin zona se interpretan en Colombia. El QR se deriva del CUDE
y del ambiente. No se produce representación gráfica.

La firma XAdES-EPES usa xmlsec, RSA-SHA256, SHA256, C14N inclusiva y referencias al
documento, KeyInfo y SignedProperties. Incluye el certificado y la cadena disponible
en el PFX; no descarga certificados. La firma SOAP conserva su perfil separado.
El XML firmado no se reformatea. El ZIP contiene un único `ar_<CUDE>.xml`, sin rutas.
El límite local es 500.000 bytes para el XML firmado (500 KB decimales, ZA01).

Producción sigue siendo el ambiente predeterminado. Un artefacto de habilitación
no se puede enviar con un cliente de producción, ni a la inversa. El PIN, los PDFs
y los binarios preparados no aparecen en `repr`. Consulta los
[modelos de respuesta](../models.md) y [errores](../errors.md).

## Criterios frente a discrepancias del anexo

Se usan los XSD para estructura, reglas de rechazo para restricciones y tablas /
genericodes para códigos. Los 25 ejemplos de mandato ayudan a contrastar formas,
pero contienen inconsistencias y no se toman como firmas válidas de referencia.

- Las reglas de rechazo §9.2.12 y ejemplos utilizan `format="PDF"`, `mimeCode="PDF"`,
  `encodingCode="base64, PDF"`, `characterSetCode="base64, PDF"`; se adoptan frente a
  la tabla estructural que indica UTF-8 / Archivo. PDF.
- Tabla 14.2.8 y genericode fijan `M-SN-e`, frente a `M-SNE` en ejemplos.
- La regla DC56 permite `thirdparty` o `supplier`; se adopta frente a la grafía
  «third party» de §11.12. La política incluye URL, descripción y hash del anexo.
- El vector publicado de CUDE usa `030`; las emisiones reales de mandato usan `043`.

Fuentes: RADIAN 1.1 §§7.2.1, 7.2.5.11, 8.7, 9.2.12, 9.3, 11–12, 14.2 y
WSDL `SendEventUpdateStatus`; copias inventariadas en las
[referencias técnicas](../technical-references.md).
La validación local y las firmas verificadas no acreditan aceptación de negocio:
queda pendiente probar con software y participantes autorizados en habilitación.
