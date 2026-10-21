# Catálogos DIAN

`radiankore.catalogs` exporta `IdentificationType` y `EventType`, enums `StrEnum`
con códigos de texto en `.value` y etiquetas en español en `.label`. Puedes
iterarlos para mostrar las opciones disponibles:

```python
from radiankore.catalogs import EventType, IdentificationType
from radiankore.models.responses import EventParty, InvoiceEvent

for option in IdentificationType:
    print(option.value, option.label)

party = EventParty(identification_type=IdentificationType.NIT)
if party.identification_type is not None:
    print(party.identification_type.value, party.identification_type.label)

event = InvoiceEvent(
    id="EVENT-1",
    code=EventType.EXPRESS_ACCEPTANCE,
    description="Synthetic XML description",
)
if event.code is EventType.EXPRESS_ACCEPTANCE:
    print(event.code.value, event.code.label)
```

`identification_type` tiene tipo `IdentificationType | None` y `code` tiene tipo
`EventType | None`. Ambos campos contienen directamente miembros del enum o
`None` si faltan o están vacíos en el XML. Al construir las dataclasses, pasa el
enum correspondiente o `None`; una cadena u otro tipo genera `TypeError`.

El parser quita espacios exteriores y utiliza los constructores estrictos de los
enums. Un código desconocido genera `DianResponseError`; no se devuelve como texto
ni se sustituye por `None`. El valor original de cada código conocido está en
`.value`, incluidos sus ceros iniciales. La etiqueta del catálogo es independiente
de `event.description`, que conserva las descripciones del XML. Los miembros
`StrEnum` se serializan como códigos de texto mediante `json.dumps()`.

Para resolver códigos fuera del parser, `IdentificationType.from_code()` y
`EventType.from_code()` son utilidades opcionales: devuelven el enum o `None` ante
valores ausentes, vacíos o desconocidos. No normalizan códigos: `"30"` y `" 030 "`
no se convierten en `"030"`. Los constructores directos, como
`IdentificationType("31")`, generan `ValueError` ante códigos desconocidos.

El catálogo de identificación incluye los 11 códigos de `TipoIdFiscal-2.1.gc`
y el código `48` (PPT) de la guía de integración de `GetAcquirer`.
El de eventos combina `02`, `04` y `030`–`051` de las fuentes documentadas en el
[índice de referencias](https://github.com/Deikore/radiankore/blob/HEAD/docs/references/dian/README.md#catálogos-de-códigos).
Son catálogos de referencia versionados, sin descargas ni lectura de documentos
durante la ejecución. No se presume que incluyan futuros códigos de DIAN.
La etiqueta `NUIP` no incluye la llamada de nota del anexo: el código `91` está
reservado allí para el adquiriente. Estos catálogos no validan roles ni números
de identificación.
