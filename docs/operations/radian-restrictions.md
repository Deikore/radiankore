# Limitación 041 y terminación 042

Usa los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).
Autoridad y funcionario son identidades suministradas por el consumidor; en los
ejemplos se reutilizan participantes sintéticos, sin afirmar facultades reales.

```python
from dataclasses import replace

from radiankore.catalogs import RadianOperationType
from radiankore.models.events import (
    CirculationRestrictionEvent,
    CirculationRestrictionTerminationEvent,
    RadianEventReference,
    RadianPdfAttachment,
)

evidence = RadianPdfAttachment(
    filename="Mandamiento de pago emitido por un Juez PDF",
    content_bytes=b"%PDF-1.7\nActo sintetico de ejemplo.\n%%EOF",
)
event = CirculationRestrictionEvent(
    header=header,
    operation_type=RadianOperationType.RESTRICTION_ATTACHMENT,
    reference=invoice,
    authorities=(holder,),
    officials=(debtor,),
    attachment=evidence,
    measure_value=Decimal("100000.00"),
)
payment_order = replace(
    event,
    operation_type=RadianOperationType.RESTRICTION_PAYMENT_ORDER,
)
```

| Operación | Miembro | Referencia |
| --- | --- | --- |
| 411 | `RESTRICTION_ATTACHMENT` | Factura CUFE/01; embargo |
| 412 | `RESTRICTION_PAYMENT_ORDER` | Factura CUFE/01; mandamiento de pago |
| 421 | `RESTRICTION_TERMINATION_JUDGMENT` | Limitación CUDE/96; sentencia |
| 422 | `RESTRICTION_TERMINATION_EARLY` | Limitación CUDE/96; terminación anticipada |

Para terminar una limitación registrada:

```python
event = CirculationRestrictionTerminationEvent(
    header=header,
    operation_type=RadianOperationType.RESTRICTION_TERMINATION_JUDGMENT,
    reference=RadianEventReference(
        document_number="LIMITACION-EJEMPLO-1",
        uuid="d" * 96,
    ),
    authorities=(holder,),
    officials=(debtor,),
    attachment=evidence,
    debt_value=Decimal("100000.00"),
    restriction_value=Decimal("50000.00"),
)
early_termination = replace(
    event,
    operation_type=RadianOperationType.RESTRICTION_TERMINATION_EARLY,
)
```

| Entrada | Correspondencia | Requisito |
| --- | --- | --- |
| `authorities` | `SenderParty/PartyTaxScheme` | Tupla no vacía de autoridades con NIT; AAF04 |
| `officials` | `DocumentReference/IssuerParty/PartyTaxScheme` | Tupla no vacía; identidad y nombre explícitos; AAH24 |
| `attachment` | `DocumentReference/Attachment/EmbeddedDocumentBinaryObject` | PDF obligatorio; AAN01–07 |
| `measure_value` de 041 | `InformacionMedidaCautelar/MontoMedidaCautelar` | Decimal no negativo, hasta 20 caracteres |
| Importes de 042 | `InformacionMedidaCautelar/ValorDeuda`, `ValorLimitación` | Ambos explícitos, no negativos, hasta 20 caracteres |

La referencia 041 no emite vencimiento, aunque esté presente en el componente de
factura. La referencia de 042 identifica el evento que termina. El receptor DIAN
es fijo; orden y duplicados de autoridades y funcionarios se preservan.
No se impone igualdad entre deuda, limitación y factura sin regla expresa.

`RadianPdfAttachment` recibe bytes inmutables con cabecera PDF, ocultos en `repr`;
no abre rutas. Esa comprobación no certifica autenticidad ni integridad jurídica
del acto. El nombre debe ser el literal de AAN07 mostrado en el ejemplo. El builder
genera base64 una vez y usa los literales del perfil: `format="Archivo. PDF"`,
`mimeCode="PDF"`, `encodingCode="base64, UTF-8"`, `characterSetCode="UTF-8"`.
No sustituye `PDF` por `application/pdf`, ni copia adjuntos vacíos de las muestras.
El límite de 500.000 bytes se aplica al XML después de codificar y firmar.

El listado de negocio admite autoridad sin NIT; generación y rechazo AAF04
lo requieren. Este perfil exige NIT real y documenta esa diferencia; no fabrica
identificadores. Los datos del funcionario usan la identificación que corresponda
y solo requieren DV para NIT.

Fuentes: §§7.2.1.7–8, 7.2.4.6–7, 7.2.5.9–10, 9.2.3.6–7 y 9.2.10–11;
las cuatro ejemplificaciones de 041/042.
