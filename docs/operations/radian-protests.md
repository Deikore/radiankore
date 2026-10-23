# Protesto 048

Usa los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).
El receptor es el adquirente/deudor y la referencia es factura CUFE/01 con
vencimiento obligatorio. El acta usa su fecha propia y datos notariales.

```python
from dataclasses import replace

from radiankore.catalogs import AcceptanceFailureType, RadianOperationType
from radiankore.models.events import (
    ProtestAct,
    ProtestEvent,
    ProtestNotary,
    RadianPdfAttachment,
)

act = ProtestAct(
    notary_number="5",
    effective_date=stamp.date(),
    notaries=(
        ProtestNotary(
            first_name="Persona",
            family_name="Sintética",
            job_title="Notario",
        ),
    ),
    attachment=RadianPdfAttachment(
        filename="Acta de protesto, PDF",
        content_bytes=b"%PDF-1.7\nActa sintetica de ejemplo.\n%%EOF",
    ),
)
event = ProtestEvent(
    header=header,
    operation_type=RadianOperationType.PROTEST_NON_ACCEPTANCE,
    sender_party=holder,
    receiver_party=debtor,
    reference=replace(invoice, due_date=stamp.date() - timedelta(days=1)),
    title_value=Decimal("100000.00"),
    act=act,
    acceptance_failure=AcceptanceFailureType.PARTIAL,
    accepted_value=Decimal("40000.00"),
    pending_value=Decimal("60000.00"),
)
```

Falta total de aceptación mantiene operación 481 y cambia su identificador:

```python
total_non_acceptance = replace(
    event,
    acceptance_failure=AcceptanceFailureType.TOTAL,
    accepted_value=Decimal("0.00"),
    pending_value=Decimal("100000.00"),
)
```

El protesto por falta de pago usa operación 482 y omite datos de aceptación:

```python
non_payment = replace(
    event,
    operation_type=RadianOperationType.PROTEST_NON_PAYMENT,
    acceptance_failure=None,
    accepted_value=None,
    pending_value=None,
)
```

| Entrada | Correspondencia | Regla |
| --- | --- | --- |
| Operación 481/482 | `CustomizationID` | `PROTEST_NON_ACCEPTANCE` / `PROTEST_NON_PAYMENT` |
| `acceptance_failure` | `CustomizationID/@schemeID` | Obligatorio para 481; `PARTIAL=1`, `TOTAL=2` |
| `title_value` | `InformacionProtesto/ValorFEV-TV` | Positivo, hasta 20 caracteres |
| `accepted_value`, `pending_value` | `InformacionProtesto/ValorAceptado`, `ValorPendiente` | Solo 481; suma igual a valor del título, sin redondeo |
| `act.notary_number` | `LineResponse/LineReference/DocumentReference/ID` | Número de notaría, texto de dígitos |
| `act.notaries` | `LineReference/DocumentReference/IssuerParty/Person` | Tupla no vacía, nombres, apellidos y cargo obligatorios |
| `act.attachment` | `LineReference/DocumentReference/Attachment` | PDF obligatorio |
| `act.effective_date` | `LineResponse/Response/EffectiveDate` | Fecha nativa del acta, independiente de fecha de emisión |

El acta se incorpora dentro de `DocumentResponse/LineResponse`, con `LineID=1`,
`DocumentDescription="Acta de Protesto"` y la descripción de respuesta requerida.
No se inventa identificación del notario: ese perfil no la solicita. Los notarios
conservan orden y repeticiones. No se calculan plazos hábiles ni se certifica el acta.

El nombre del PDF es fijo `Acta de protesto, PDF` por AAI89. El adjunto conserva
sus bytes y genera `format="Archivo. PDF"`, `mimeCode="PDF"`,
`encodingCode="base 64, UTF-8"` y `characterSetCode="UTF-8"`, siguiendo AAI85–89.
El espacio de `base 64` es propio del perfil, diferente de 041/042.

La generación condiciona `schemeID` y los importes de aceptación a 481;
la tabla de validación los presenta sin esa condición y la muestra 482 incluye
atributo y valores vacíos. Se aplica la condición explícita de generación:
482 omite estos campos, no emite números vacíos ni inventa una falta de aceptación.
Esta interpretación se prueba y debe confirmarse en habilitación.

Para falta total de aceptación se exige valor aceptado cero; para parcial es
positivo. El pendiente siempre es positivo y ambos suman el título con precisión
propia, independiente del contexto Decimal del consumidor.

Fuentes: §§7.2.1.9, 7.2.4.10, 7.2.5.16, 9.2.3.10, 9.2.17 y tabla 14.2.20;
`Falta de aceptacion.gc` y las dos ejemplificaciones de `048-Protesto`.
