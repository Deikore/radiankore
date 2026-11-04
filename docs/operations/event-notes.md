# Notas y declaraciones de los eventos

La API de notas tipadas está disponible desde **0.7.2** y sustituye el contrato
de notas de 0.7.1. Las declaraciones estructuradas de 043/044 descritas aquí
se incorporan en **0.7.4**. Las clases actuales se amplían; no se requiere
construir XML ni importar fragmentos para emitir un evento.

## Declaraciones estructuradas de mandato

Los eventos 043 y 044 requieren `MandateDeclaration` y
`MandateTerminationDeclaration`, respectivamente. El SDK compone sus notas y
su orden; no se aportan declaraciones manuales mediante EventNote.
`additional_notes` acepta únicamente observaciones ADDITIONAL y conserva
repeticiones. En 044, `header.notes` debe estar vacío. La tabla de propósitos
siguiente describe el resultado generado para estos dos eventos; para las demás
familias se conserva la entrada de notas tipadas.

## Contrato y orden

`EventNote(kind: EventNoteKind, text: str)` recibe un propósito y el texto original.
Se importa desde `radiankore.models.events`; `EventNoteKind`, desde
`radiankore.catalogs`. Los eventos 030–034 reciben
`notes: tuple[EventNote, ...]` directamente y las
demás familias utilizan `RadianEventHeader.notes`, excepto 043/044: estos generan
`event.notes` desde declaraciones estructuradas; 044 exige `header.notes=()`.
Las cadenas, listas, propósitos ajenos al evento, textos vacíos y excesos se
rechazan antes de construir o firmar. FE admite 10.000 caracteres por nota;
RADIAN admite 5.000. No se recorta, completa, ordena ni deduplica el texto.

La representación ocupa la primera nota cuando es aplicable. La declaración
específica que el anexo sitúa en `Note[2]` va inmediatamente después. Sin
representación, la declaración aplicable comienza en la primera nota, sin
inventar una nota vacía. En 044, sin representación, la manifestación de
terminación precede a la constancia/ratificación; con representación, esta última
ocupa la segunda nota y la manifestación de terminación queda después.
Las notas adicionales pueden repetirse y no satisfacen declaraciones obligatorias.

El tipo acredita el **propósito declarado por el consumidor**, no la verdad del
texto. No se comprueban mediante búsqueda de palabras las redacciones equivalentes
permitidas para garantía, procuración o ausencia de responsabilidad. La nota de
protesto sí exige el literal `Con protesto`; la representación exige la frase fija
y dos nombres no vacíos. El consumidor completa identidades, capacidades, documentos,
fechas y circunstancias reales. No envía las instrucciones editoriales del anexo.

## Inventario completo de propósitos

La tabla describe condiciones, no una instrucción para incluir todas las notas.
`ADDITIONAL` admite texto adicional en todos los perfiles. La representación es
condicional a una actuación por mandato y se declara con
`MANDATE_REPRESENTATION`. En 043 se genera siempre primero, seguida de la
declaración particular
obligatoria. En 044 se genera cuando se aporta `declaration.representation`.

| Eventos / operaciones | `EventNoteKind` | Condición y contenido |
| --- | --- | --- |
| 030–051 | `MANDATE_REPRESENTATION` | Cuando se actúa como mandatario: nombre del mandatario, frase fija y nombre del mandante. Una sola pareja; primera nota. En 043 se genera siempre; en 044 se aporta opcionalmente como hecho estructurado. |
| 037–040/047 | `ACTING_CAPACITY` | Cuando corresponde otra calidad de actuación: declarar la calidad y a quién representa; no sustituye una representación por mandato. |
| 034 directo | `TACIT_ACCEPTANCE_DIRECT` | Obligatoria sin mandatario: recibo 032 y CUDE; adquirente y NIT; plazo y ausencia de aceptación/reclamo bajo juramento. |
| 034 por mandatario | `TACIT_ACCEPTANCE_LEGAL_MANDATE` | Alternativa para mandante jurídico: mandatario e identificación, mandante y NIT, adquirente y NIT, hechos y juramento. Requiere además representación. |
| 034 por mandatario | `TACIT_ACCEPTANCE_NATURAL_MANDATE` | Alternativa para comerciante natural: mandatario e identificación; comerciante con identificación y NIT; adquirente, hechos y juramento. Requiere representación. |
| 035 | `GUARANTEE_NATURAL_PERSON` | Declaración del avalista natural con identificación, avalados, CUFE y cobertura; precisar importe si es parcial. |
| 035 | `GUARANTEE_LEGAL_PERSON` | Declaración del representante, sociedad/NIT, capacidad acreditada, avalados, CUFE y cobertura; importe si es parcial. |
| 036 / 361–364 | `SPECIAL_PAYMENT_TERMS` | Opcional, como máximo una: condiciones especiales pactadas para el pago. Su ausencia es notificación AAD11d, no rechazo local. |
| 037 / 372 | `WITHOUT_RECOURSE` | Obligatoria: «sin mi responsabilidad» u otra equivalente. Incompatible con 371. |
| 047 | `WITHOUT_RECOURSE` | Cuando se declara esa condición; el código 047 no la determina por sí solo. |
| 038 | `GUARANTEE_ENDORSEMENT` | Obligatoria: «en garantía», «en prenda» u otra equivalente. |
| 039 | `COLLECTION_ENDORSEMENT` | Obligatoria: «en procuración», «al cobro» u otra equivalente. |
| 040 / 402 | `COLLECTION_REVOCATION` | Obligatoria al cancelar procuración: manifestación de revocatoria contenida en el endoso. 401/403 no exigen esta nota. |
| 043 | `MANDATE_NATURAL_PERSON` | Una alternativa para mandatario natural: identificación, representado, contrato, facultades y duración. |
| 043 | `MANDATE_LEGAL_PERSON` | Una alternativa para mandatario jurídico: representante e identificación, sociedad, acreditación de representación, mandante, contrato, facultades y duración. |
| 044 / 441–443 | `MANDATE_TERMINATION` | Manifestación generada desde la referencia, partes y fecha efectiva; sin `Response/EffectiveDate`. |
| 044 / 441 | `MANDATE_RATIFICATION` | Opcional: ratificación de los actos realizados por el mandatario. |
| 044 / 442 | `MANDATE_NO_PENDING_ACTS` | Obligatoria: constancia de que no queda pendiente ejecutar ningún acto del mandato terminado. |
| 048 / 481–482 | `PROTEST` | Obligatoria: literal `Con protesto`. |
| 049 / 491–494 | `ECONOMIC_RIGHTS_TRANSFER` | Obligatoria: juramento sobre contrato de cesión, identidades de cedente/cesionario y cumplimiento de sus términos. |
| Todos | `ADDITIONAL` | Opcional y repetible; conserva caracteres, orden y duplicados. |

034 exige exactamente una alternativa de juramento. 043 exige la declaración
correspondiente a `mandatee_party.organization_type`. 035 admite declaraciones de
varios avalistas, incluidos casos mixtos. Las alternativas de juramento/mandato, las condiciones especiales de pago y la
representación no se duplican. Las cláusulas y observaciones repetibles conservan
todas sus ocurrencias. Ratificación y constancia no son intercambiables.
La tabla distingue las notas opcionales de las obligatorias; no se exige una nota
adicional genérica en 401/403 ni en los perfiles sin declaración específica.

## Construcción mediante clases

Ejemplo íntegramente ficticio de representación, cláusulas, condiciones de pago y
notas adicionales. Las alternativas se utilizan en eventos distintos.

```python
from radiankore.catalogs import EventNoteKind
from radiankore.models.events import EventNote, MandateRepresentation

representation = MandateRepresentation(
    mandatee_name="Gestor Sintético SAS",
    mandator_name="Comercial Sintética SAS",
).as_note()
clauses = {
    "038": EventNote(kind=EventNoteKind.GUARANTEE_ENDORSEMENT, text="en garantía"),
    "039": EventNote(kind=EventNoteKind.COLLECTION_ENDORSEMENT, text="al cobro"),
    "372": EventNote(
        kind=EventNoteKind.WITHOUT_RECOURSE, text="sin mi responsabilidad"
    ),
    "402": EventNote(
        kind=EventNoteKind.COLLECTION_REVOCATION,
        text="Revoco la procuración conferida por el endoso sintético ENDOSO-1.",
    ),
    "048": EventNote(kind=EventNoteKind.PROTEST, text="Con protesto"),
}
payment_terms = EventNote(
    kind=EventNoteKind.SPECIAL_PAYMENT_TERMS,
    text="Condición ficticia pactada: el pago se efectuará mediante transferencia.",
)
additional = EventNote(kind=EventNoteKind.ADDITIONAL, text="Observación sintética.")
guarantee_endorsement_notes = (representation, clauses["038"], additional, additional)
registration_notes = (representation, payment_terms)
```

Asigna la tupla a `header.notes` o al argumento `notes`, según el modelo.
Para 043/044 usa declaraciones estructuradas y `additional_notes`, conforme a
[notas de mandato y migración](mandate/notes.md). Una nota
juramentada o de aval debe contener la información indicada en la tabla. Las
plantillas completas para 034 están en FE 1.9 pp. 301–302; las de 035 en RADIAN
pp. 115–116 y las de 043 en p. 190. Debe elegirse y completar una alternativa
aplicable, no enviar juntas las alternativas editoriales de las muestras.

## Migración

Antes se utilizaba `notes=("texto",)`. Ahora usa
`notes=(EventNote(kind=EventNoteKind.ADDITIONAL, text="texto"),)` para una observación.
Para un juramento o cláusula utiliza su propósito específico. Clasificar todas
las cadenas como `ADDITIONAL` no conserva la validez de los eventos que exigen una
declaración. No hay una conversión automática basada en frases o en `thirdparty`.

`MandateRepresentation.as_note()` sustituye la redacción manual de la declaración
genérica. En las familias distintas de 043/044 se incluye explícitamente en la tupla;
043 la genera y 044 la recibe en `declaration.representation`. No mezcles dos declaraciones de representación del mismo evento.

## Fuentes y discrepancias

Fuentes primarias: [FE 1.9 §6.5.4, AAD11, p. 284 y §6.5.5.7, pp. 301–302](https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf#page=284),
y [RADIAN 1.1 §§7.2.5.3–19 y 9.2.4–20](https://www.dian.gov.co/normatividad/Normatividad/Anexo%2085%20-%20Resoluci%C3%B3n%20000085%20de%202022.pdf#page=109).

043: p. 190 indica `Note[2]`, cardinalidad `1..1` y dos alternativas; el control de
cambios elimina AAD11a, y AAD11b/c distinguen mandatario natural/jurídico. El
contrato actual del repositorio genera siempre una representación breve
como primera nota y la alternativa aplicable como segunda. Las observaciones
adicionales siguen después. La [guía de mandato](mandate/notes.md) muestra ambos
textos y su migración desde 0.7.3 a 0.7.4.
No se copian ambas alternativas de las ejemplificaciones.

044: negocio p. 43 atribuye la constancia a revocatoria, pero generación p. 217 y
la matriz oficial «Requisitos a los eventos», U88/U89, distinguen constancia en
renuncia y ratificación opcional en revocación. Se sigue esa estructura; la fecha
se aporta en la manifestación de terminación, no en un elemento no definido.
Las decisiones están probadas localmente; la aceptación remota no está acreditada.

La habilitación, aceptación, vigencia y facultades del mandato se verifican antes
de cada actuación (§7.2.1.4.2; LGC35/LGC36/LGC53/LGC59–61/LGC65/LGC88).
La representación no cambia al titular, software, certificado ni ambiente.
El SDK no obtiene ni certifica esos antecedentes. Véase la
[matriz completa de entradas XML](../technical/event-input-matrix.md).
