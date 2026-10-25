# Terminación del mandato 044

Contexto funcional: [044](../functional/events/044.md).

Esta guía describe la implementación y sus validaciones técnicas.

Utilice los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).

```python
from radiankore.catalogs import RadianOperationType
from radiankore.models.events import MandateTerminationEvent, RadianEventReference

event = MandateTerminationEvent(
    header=header,
    operation_type=RadianOperationType.MANDATE_REVOCATION,
    sender_party=holder,
    representatives=(representative,),
    reference=RadianEventReference(
        document_number="MANDATO-EJEMPLO-1",
        uuid="b" * 96,
    ),
)
```

| Operación | Miembro | Generador |
| --- | --- | --- |
| 441 | `MANDATE_REVOCATION` | Mandante |
| 442 | `MANDATE_RESIGNATION` | Mandatario |
| 443 | `MANDATE_REJECTION` | Rechazo del mandante, según tabla 14.1.2 |

El destinatario DIAN se genera internamente. La referencia identifica al mandato
original por su número y CUDE, con `CUDE-SHA384` y tipo `96`. No se referencia
directamente la factura ni se reconstruye el mandato. Los representantes forman
una tupla no vacía y conservan su orden; nombres, apellidos e identificación son
obligatorios. Cargo, nacionalidad y departamento permanecen opcionales conforme
a sus reglas de notificación.

`header.notes` debe contener las declaraciones aplicables. El consumidor aporta
la manifestación de terminación, su fecha efectiva, las constancias de actos
pendientes y la ratificación cuando correspondan; el modelo comprueba presencia,
no contenido jurídico. El perfil no añade un `Response/EffectiveDate` inexistente
en su tabla de generación. Las notas de representación también son explícitas.

La tabla 14.1.2 admite 443, aunque la caja solo ejemplifica revocatoria y renuncia.
Se utiliza la estructura común 044 y se prueban las tres operaciones con datos
ficticios, sin inventar una extensión nueva para 443. El literal de descripción
se conserva como `Terminacion del Mandato`, conforme al rechazo AAH04.

Fuentes: requisitos §7.2.1.4.3, estructura §7.2.5.12, reglas §9.2.13 y tabla
14.1.2. La verificación de que el generador corresponde al mandato registrado
y la aceptación de la terminación pertenecen a DIAN.
