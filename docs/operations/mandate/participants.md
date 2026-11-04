# Participantes y base común de 043 y 044

Copie **todo el bloque de base común** antes del caso elegido en
[431](431.md), [432](432.md), [433](433.md), [434](434.md) o
[terminación](../radian-termination.md). Cada caso parte de esta base nueva;
no ejecute los casos anteriores. Después utilice la
[preparación y el envío separados](../mandate.md#ejemplo-de-preparación-y-envío).

## Responsabilidades y ubicación XML

Las rutas son relativas a `ApplicationResponse`. Los prefijos `cac` y `cbc`
corresponden a los componentes agregados y básicos UBL 2.1.

| Participante / recurso | Responsabilidad y modelo | Campos obligatorios y validaciones | Ubicación XML en 043 |
| --- | --- | --- | --- |
| Mandante | Otorga el encargo; `MandateParty` con `MandatorType` | Nombre de 5–450 caracteres; identificación de 3–13, tipo, DV correcto si NIT; rol; `representatives` no vacío. Organización jurídica por defecto; no se infiere del NIT | `cac:SenderParty/cac:PartyTaxScheme` y `cac:PowerOfAttorney`; personas en `cac:SenderParty/cac:Person` |
| Mandatario | Recibe el encargo; `MandateParty` con `MandateeType` | Misma identidad y representantes; `organization_type` selecciona la declaración natural o jurídica. Aceptación explícita `True` en el evento | `cac:DocumentResponse[1]/cac:IssuerParty/cac:PowerOfAttorney`; personas en `cac:AgentParty/cac:Person` |
| Representantes | Identifican a quienes intervienen; `MandatePerson` | Número, tipo, nombres, apellidos, cargo, nacionalidad y departamento; DV correcto si NIT. Identificación hasta 14 en mandante, 15 en mandatario. Nombres, apellidos, cargo y nacionalidad hasta 100; departamento hasta 200 | `cac:Person/cbc:ID`, `FirstName`, `FamilyName`, `JobTitle`, `NationalityID`, `OrganizationDepartment`; cada persona conserva su posición, incluso repetida |
| Declarante | Atestigua los hechos; `MandateDeclaration.declarant` | Debe pertenecer a `mandatee_party.representatives`; selección explícita, sin elegir automáticamente el primero. `contract_form` obligatorio; ciudad de Cámara de Comercio obligatoria solo para mandatario jurídico | Su persona ya figura en el bloque de representantes; sus datos redactan `cbc:Note[2]`. Las demás personas no producen declaraciones adicionales |
| Notario | Expide soportes del poder general; `MandateNotary` independiente | NIT, DV válido, nombres, apellidos, cargo y `office_number`; no usa nacionalidad ni departamento empresarial. Ambos soportes generales exigen uno o más notarios | `cac:DocumentResponse[1]/cac:LineResponse/cac:LineReference/cac:DocumentReference/cac:IssuerParty/cac:Person`; `office_number` se escribe en `cbc:OrganizationDepartment` |
| Proveedor de software | Identifica el software; `RadianSoftware` | `software_id`, `pin`, `provider_tax_number`, `provider_verification_digit`; `signer_role` obligatorio, `thirdparty` o `supplier` | Extensión `sts:DianExtensions/sts:SoftwareProvider`; PIN interviene en hashes y no se publica como texto |
| Certificado / cliente | Material criptográfico de firma; `DianClient` | PFX y contraseña propios. Se carga una vez al construir el cliente; ambiente explícito en estos ejemplos. El contexto cierra recursos | Firma XAdES del documento y firma SOAP al enviar; no se convierte en declarante, notario ni parte |
| DIAN | Destinatario generado internamente | El consumidor no aporta una parte receptora; NIT `800197268`, DV `4` | `cac:ReceiverParty` |

En 044 el emisor se deriva de la operación: mandante en 441/443 y mandatario en
442. Sus representantes se escriben en `cac:SenderParty/cac:Person` en el orden
original. La referencia es al mandato, no a las facturas.

Los cuatro roles del mandante son `INVOICE_ISSUER` (Mandante-FE),
`LEGITIMATE_HOLDER` (Mandante-LT), `GUARANTOR` (Mandante-AV) y
`ACQUIRER_DEBTOR` (Mandante-AD). Los del mandatario son
`ELECTRONIC_NEGOTIATION_SYSTEM` (M-SN-e), `FACTOR` (M-Factor),
`TECHNOLOGY_PROVIDER` (M-PT) e `INVOICE_ISSUER` (M-FE).
El rol, la organización y el canal son datos independientes; véanse las
[recetas](recipes.md). El proveedor de software puede ser una entidad distinta
de cualquiera de estas partes y del notario.

## Soportes y fechas

| Dato | Campo | Función / ubicación |
| --- | --- | --- |
| Contrato | `attached_contract` | PDF obligatorio en SPECIAL y GENERAL, incluso si la declaración dice contrato verbal; primer `LineResponse` del bloque principal |
| Escritura pública | `attached_contract.effective_date` | Fecha nativa obligatoria solo en GENERAL; `LineResponse[1]/cac:Response/cbc:EffectiveDate`. SPECIAL omite fecha y notarios |
| Nota de vigencia | `attached_validity_note` | Segundo PDF obligatorio solo en GENERAL, con notario; acredita vigencia del poder. No es una `cbc:Note` ni el período de duración |
| Fecha efectiva de constitución | `MandateEvent.effective_date` | `DocumentResponse[1]/cac:Response/cbc:EffectiveDate`; no reemplaza la fecha de escritura |
| Período | `validity_period` | Inicio y fin nativos en 431/433, fin ≥ inicio; ambos ausentes en 432/434. En cada referencia principal, `cac:ValidityPeriod` |
| Fecha efectiva de terminación | `MandateTerminationDeclaration.effective_date` | En el texto de terminación 044; no genera `Response/EffectiveDate` |
| Emisión | `issue_date`, `issue_time` (en `header` para 044) | Fecha/hora de emisión normalizadas juntas a Colombia UTC−05:00; hora sin zona se interpreta en Colombia, precisión de segundos |

La validación de PDF comprueba bytes y cabecera `%PDF-`; no acredita firmas de
las partes, contenido jurídico ni vigencia real del soporte. Las rutas de abajo
son archivos ficticios que el integrador debe reemplazar. El código lee los PDF
**antes** de preparar; la preparación trabaja únicamente en memoria.

## Base común

Todos los nombres, números, CUFE/CUDE y credenciales son ficticios. Los NIT tienen
DV aritméticamente válido; ello no acredita registro ni habilitación. Disponga de
`contrato.pdf` y `vigencia.pdf` de ejemplo en el directorio de ejecución. Para un
poder especial solo se utiliza el contrato; la base carga ambos para permitir
copiar cualquiera de los casos generales sin pasos implícitos.

```python
from dataclasses import replace
from datetime import date, time
from pathlib import Path

from radiankore import DianClient, Environment
from radiankore.catalogs import (
    EventNoteKind,
    IdentificationType,
    MandateChannel,
    MandateContractForm,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandatorType,
    OrganizationType,
    RadianOperationType,
)
from radiankore.models.events import (
    EventNote,
    MandateAttachedDocument,
    MandateDeclaration,
    MandateDocumentReference,
    MandateEvent,
    MandateNotary,
    MandateParty,
    MandatePerson,
    MandateRepresentation,
    MandateScope,
    MandateTerminationDeclaration,
    MandateTerminationEvent,
    MandateValidityPeriod,
    RadianEventHeader,
    RadianEventReference,
    RadianSoftware,
)

mandator_representative = MandatePerson(
    identification_number="100000001",
    identification_type=IdentificationType.CITIZENSHIP_CARD,
    first_name="Ana",
    family_name="Ejemplo",
    job_title="Representante Legal",
    nationality_id="CO",
    organization_department="Legal",
)
mandatee_representative = MandatePerson(
    identification_number="100000002",
    identification_type=IdentificationType.CITIZENSHIP_CARD,
    first_name="Luis",
    family_name="Sintético",
    job_title="Representante Legal",
    nationality_id="CO",
    organization_department="Mandatos",
)
mandator = MandateParty(
    name="Mandante Sintético SAS",
    tax_number="900000001",
    verification_digit="2",
    identification_type=IdentificationType.NIT,
    role=MandatorType.INVOICE_ISSUER,
    representatives=(mandator_representative,),
)
mandatee_legal = MandateParty(
    name="Mandatario Sintético SAS",
    tax_number="900000002",
    verification_digit="1",
    identification_type=IdentificationType.NIT,
    role=MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM,
    organization_type=OrganizationType.LEGAL_PERSON,
    representatives=(mandatee_representative,),
)
natural_person = replace(mandatee_representative, job_title="Comerciante")
mandatee_natural = MandateParty(
    name="Luis Sintético",
    tax_number="900000003",
    verification_digit="7",
    identification_type=IdentificationType.NIT,
    role=MandateeType.FACTOR,
    organization_type=OrganizationType.NATURAL_PERSON,
    representatives=(natural_person,),
)
notary = MandateNotary(
    identification_number="900000004",
    verification_digit="4",
    first_name="Clara",
    family_name="Ficticia",
    job_title="Notaria",
    office_number="12",
)
contract_bytes = Path("contrato.pdf").read_bytes()
validity_bytes = Path("vigencia.pdf").read_bytes()
contract_special = MandateAttachedDocument(
    document_id="CONTRATO-ESPECIAL-1",
    embedded_bytes=contract_bytes,
)
contract_general = MandateAttachedDocument(
    document_id="ESCRITURA-1",
    embedded_bytes=contract_bytes,
    issuers=(notary,),
    effective_date=date(2026, 10, 20),
)
validity_note = MandateAttachedDocument(
    document_id="VIGENCIA-1",
    embedded_bytes=validity_bytes,
    issuers=(notary,),
)
invoice_one = MandateDocumentReference(document_number="FE1", uuid="a" * 96)
invoice_two = MandateDocumentReference(document_number="FE2", uuid="b" * 96)
original_mandate = RadianEventReference(
    document_number="MANDATO-ORIGINAL-1", uuid="c" * 96
)
software = RadianSoftware(
    software_id="00000000-0000-4000-8000-000000000001",
    pin="pin-ficticio",
    provider_tax_number="900000005",
    provider_verification_digit="1",
    signer_role="thirdparty",
)
```

El mandatario natural conserva su persona en `representatives`; no se elimina ese
bloque por ser natural. La base usa NIT para ambas organizaciones, con los datos
de identificación personal del representante separados. También se admite otra
identificación de parte conforme al modelo; no deduzca la organización de ella.
La ciudad de Cámara de Comercio se aporta en el caso jurídico, no en la base.

Para `AsyncDianClient`, reutilice los mismos modelos y software y siga el
[patrón async](../../guides/async.md); use `async with` o `aclose()`.
