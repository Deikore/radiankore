# Emitir eventos RADIAN

`prepare_radian_event(*, event, software)` prepara todos los eventos 030–051
mediante modelos específicos. Devuelve `PreparedRadianEvent`, con código, número,
CUDE, ambiente y bytes originales del XML firmado y ZIP. `send_radian_event(prepared)`
envía ese ZIP una vez mediante `SendEventUpdateStatus` y devuelve
`SendEventResult | None`.

La preparación no realiza I/O después de cargar el certificado. Cada envío posee
y cierra su conexión. No hay reintentos ni cambios automáticos de ambiente. Los
rechazos de negocio siguen siendo datos de respuesta; los fallos técnicos conservan
las excepciones existentes. Los eventos 030–034 exigen que la fecha de emisión
coincida con la fecha de firma en Colombia; esa restricción no se aplica a
035–051. El mandato conserva su perfil específico de firma.

## Modelos y variantes

| Evento | Modelo de entrada | Operaciones |
| --- | --- | --- |
| 030–034 | `InvoiceResponseEvent` | Código indicado en el modelo; [guía](invoice-emission.md) |
| 043 | `MandateEvent` | 431–434; [guía](mandate.md) |
| 035 | `GuaranteeEvent` | 035, fija |
| 041 | `CirculationRestrictionEvent` | 411, 412 |
| 042 | `CirculationRestrictionTerminationEvent` | 421, 422 |
| 048 | `ProtestEvent` | 481, 482 |
| 049 | `EconomicRightsTransferEvent` | 491, 492, 493, 494 |
| 050 | `EconomicRightsNotificationEvent` | 050, fija |
| 051 | `EconomicRightsPaymentEvent` | 511, 512 |
| 044 | `MandateTerminationEvent` | 441, 442, 443 |
| 036 | `RadianRegistrationEvent` | 361, 362, 363, 364 |
| 045 | `InvoicePaymentEvent` | 451, 452 |
| 046 | `PaymentReportEvent` | 046, fija |
| 037, 038, 039, 047 | `EndorsementEvent` | 371, 372, 038, 039, 047 |
| 040 | `EndorsementCancellationEvent` | 401, 402, 403 |

`RadianEvent` es la unión pública de estos quince modelos. Todos se importan desde
`radiankore.models.events`, son inmutables, tienen slots y se construyen por nombre.
`InvoiceResponseEvent` recibe el código 030–034; las demás familias lo derivan
del modelo y de `operation_type`, con código fijo 043 para `MandateEvent`.
Todas las familias usan `prepare_radian_event` y `send_radian_event`.

## Preparación común para los ejemplos

Los siguientes participantes, referencias, DV, software y declaraciones son
sintéticos. No representan documentos reales ni participantes autorizados. Copia
este bloque antes del ejemplo de la familia elegida y sustituye los datos para
una integración real. Los antecedentes y la exactitud de las declaraciones son
responsabilidad del consumidor.

```python
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from radiankore import DianClient, Environment
from radiankore.catalogs import IdentificationType, OrganizationType
from radiankore.models.events import (
    RadianEventHeader,
    RadianInvoiceReference,
    RadianParty,
    RadianPerson,
    RadianSoftware,
)

stamp = datetime.now(timezone(timedelta(hours=-5)))
header = RadianEventHeader(
    event_number="RADIAN-EJEMPLO-1",
    issue_date=stamp.date(),
    issue_time=stamp.timetz(),
    notes=("Declaración sintética; no constituye un acto mercantil real.",),
)
holder = RadianParty(
    name="Tenedor sintético",
    tax_number="900000001",
    identification_type=IdentificationType.NIT,
    verification_digit="1",
    organization_type=OrganizationType.LEGAL_PERSON,
)
buyer = RadianParty(
    name="Comprador sintético",
    tax_number="900000002",
    identification_type=IdentificationType.NIT,
    verification_digit="2",
    organization_type=OrganizationType.NATURAL_PERSON,
)
debtor = RadianParty(
    name="Deudor sintético",
    tax_number="900000003",
    identification_type=IdentificationType.NIT,
    verification_digit="3",
    organization_type=OrganizationType.LEGAL_PERSON,
)
representative = RadianPerson(
    identification_number="100000004",
    identification_type=IdentificationType.CITIZENSHIP_CARD,
    first_name="Persona",
    family_name="Sintética",
)
invoice = RadianInvoiceReference(
    document_number="FE-EJEMPLO-1",
    uuid="a" * 96,
    due_date=stamp.date() + timedelta(days=90),
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
```

Después de construir `event` con una de las guías:

```python
prepared = client.prepare_radian_event(event=event, software=software)
print(prepared.code, prepared.cude)
# Inspecciona o guarda prepared.xml_bytes y prepared.zip_bytes.
result = client.send_radian_event(prepared)  # Este paso contacta DIAN.
if result is not None:
    print(result.is_valid, result.status_code, result.messages)
```

No emitas automáticamente las variantes sobre una misma factura: son operaciones
de negocio diferentes. El consumidor aporta numeración única, documentos previos,
roles, vigencia, autorización y declaraciones de representación.

```{toctree}
:maxdepth: 1

radian-termination
radian-registration
radian-payments
radian-endorsements
radian-guarantees
radian-economic-rights
radian-restrictions
radian-protests
```

## Validaciones, precisión y bytes

- Una referencia de factura contiene CUFE, tipo fijo `01` y vencimiento cuando el
  perfil lo requiere. Una referencia de evento contiene CUDE y tipo fijo `96`.
  No se sustituyen unas por otras.
- Las cabeceras aceptan fechas/horas nativas y notas en tuplas, hasta 5.000 caracteres
  por nota. Se normalizan fecha y hora conjuntamente a UTC−05:00, con segundos
  enteros; las horas sin zona se interpretan en Colombia.
- Los valores financieros deben ser `Decimal` finitos. Se rechazan `float`, NaN,
  infinito, negativos y valores que no caben en el campo; no hay redondeos ni
  conversión a notación exponencial. Los cálculos locales de saldo y sumas usan
  precisión propia, independiente del contexto Decimal del consumidor.
- Se preservan orden y repeticiones de notas y participantes. Las identidades se
  serializan antes de sus participaciones legales, según el orden UBL.
- El CUDE general usa las primeras identidades de generador y receptor seleccionadas
  por los XPath del anexo. Los endosos en blanco usan §12.1.3: omiten la identidad
  del endosante e incluyen el identificador `2` de la clase de endoso.
- El QR referencia el CUFE de la factura o el CUDE del evento terminado/cancelado,
  con el host del ambiente seleccionado. No se genera representación gráfica.
- El XML firmado admite hasta 500.000 bytes. El ZIP contiene exactamente un
  `ar_<CUDE>.xml`; los bytes firmados no se reformatean. El artefacto solo puede
  enviarse con un cliente del mismo ambiente y con el método de su tipo.

La validación local cubre invariantes comprobables, no consulta antecedentes ni
calcula plazos hábiles. No transforma las notificaciones del anexo en rechazos.
La aceptación real debe comprobarse con participantes y software autorizados en
habilitación. Los [errores](../errors.md) y el [resultado](../models.md) conservan
los contratos existentes.

## Fuentes y discrepancias

RADIAN 1.1 §§7.2.1, 7.2.4–7.2.5, 9.2.3–9.2.20 y 12–14;
tablas, genericodes, XSD, Schematron y las 36 ejemplificaciones disponibles para
estas 16 clases de evento, incluidas las de extensión `.XML`.

Se preservan los originales y su inventario. Las muestras no son documentos
válidos de referencia: contienen CUDE ficticios, identificadores de longitud
incorrecta y otras inconsistencias. Las diferencias concretas figuran en cada guía.
La [procedencia](../technical-references.md) enlaza las fuentes versionadas.


El Schematron de la caja declara `queryBinding="xslt3"` e incluye una lista
`DIAN_UBL21-listacodigos_v2.0.sch` que no está distribuida. Algunas reglas comunes
también usan estructuras anteriores, como `SoftwareIDs`. No se presenta como una
validación integral ejecutable con lxml: las pruebas validan XSD, firma serializada,
catálogos y los XPath aplicables de las tablas, sin sustituir la validación DIAN.
Las guías nuevas registran las discrepancias de aval, adjuntos, AAI05a de 049,
roles de 051 y campos condicionales del protesto.
