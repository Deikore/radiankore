# Mandato RADIAN (043)

Contexto funcional: [043](../functional/events/043.md).

Esta guía describe el contrato de **0.7.4**, incluidas las declaraciones
estructuradas y su migración desde 0.7.3.
El SDK genera los textos con los hechos suministrados; el integrador responde
por su veracidad y DIAN evalúa la aceptación de negocio.

## Dimensiones independientes

| Dimensión | Campo | Elección |
| --- | --- | --- |
| Operación | `operation_type` | 431: facultades generales y tiempo limitado; 432: generales y tiempo ilimitado; 433: facultades particulares y tiempo limitado; 434: particulares y tiempo ilimitado |
| Naturaleza del poder | `nature` | `SPECIAL` (`schemeID=1`) o `GENERAL` (`schemeID=2`); determina soportes notariales, independientemente de la operación |
| Facturas | `reference_type` | `ONE`: una; `MULTIPLE`: 2–20; `ALL`: tupla vacía explícita |
| Tipo de persona del mandatario | `mandatee_party.organization_type` | `NATURAL_PERSON` o `LEGAL_PERSON`; selecciona la declaración y la condición de ciudad |

El nombre «General» de 431/432 se refiere al alcance de facultades `ALL17`,
no al poder `GENERAL` ni a la cardinalidad `ALL`. Por eso hay doce combinaciones
por operación: dos naturalezas × tres referencias × dos tipos de persona.
431/432 contienen exactamente `ALL17` con su canal; 433/434 contienen `MR91`
seguido de facultades particulares R01–R22. `PT` no se admite para R01–R05.

## Participantes y catálogo de ejemplos

Comience por [participantes, recursos y base común](mandate/participants.md).
Cada caso tiene identificador estable, condiciones, construcción completa de
`MandateEvent` y fragmentos del XML producido en habilitación.
Todos usan contrato escrito y canal SNE; las alternativas están en recetas.

```{toctree}
:maxdepth: 1

mandate/participants
mandate/notes
mandate/431
mandate/432
mandate/433
mandate/434
mandate/recipes
```

- [431: 12 casos con facultades generales y duración limitada](mandate/431.md).
- [432: 12 casos con facultades generales y duración ilimitada](mandate/432.md).
- [433: 12 casos con facultades particulares y duración limitada](mandate/433.md).
- [434: 12 casos con facultades particulares y duración ilimitada](mandate/434.md).
- [044: ocho casos de revocación, renuncia y rechazo](radian-termination.md).
- [Recetas: contrato verbal, roles, canales, facultades y multiplicidad](mandate/recipes.md).
- [Notas generadas, migración y errores](mandate/notes.md).

## Ejemplo de preparación y envío

Copie primero la [base común](mandate/participants.md#base-común) y **un solo
caso** de 043 o 044 que defina `event`. Después ejecute este bloque. Sustituya el
PFX y su contraseña ficticios por material propio de habilitación.
La carga del PFX ocurre una vez; la preparación construye, firma y comprime en
memoria, sin red ni escritura de archivos.

```python
with DianClient(
    "certificado.pfx",
    password="password-ficticio",
    environment=Environment.HABILITATION,
) as client:
    prepared = client.prepare_radian_event(event=event, software=software)

print(prepared.cude)
# Inspect prepared.xml_bytes and prepared.zip_bytes before transmission.
```

La transmisión es un paso explícito posterior y **sí contacta DIAN**.
Copie este segundo bloque solo cuando haya revisado el artefacto. Debe usar el
mismo ambiente y el ZIP original, sin reformatear el XML firmado.

```python
with DianClient(
    "certificado.pfx",
    password="password-ficticio",
    environment=Environment.HABILITATION,
) as client:
    result = client.send_radian_event(prepared)

if result is not None:
    print(result.is_valid, result.status_code, result.messages)
```

El cierre del primer cliente permite separar revisión y transmisión. Si se
integran ambos pasos en un mismo contexto, el certificado se carga una sola vez
para todo el flujo. El cliente síncrono cierra las conexiones por operación salvo
pooling opcional y el contexto libera sus recursos. Los estados de negocio no
se convierten en excepciones; también puede recibirse `None`. No hay reintentos
ni fallback de ambientes. Producción es el predeterminado cuando no se indica
ambiente; aquí se elige habilitación explícitamente. Para el cliente asíncrono,
consulte el [patrón de emisión async](../guides/async.md).

## Variantes y restricciones

Las [páginas de casos](mandate/431.md) y las [recetas](mandate/recipes.md)
detallan las variantes. Los modelos son inmutables y usan tuplas: conservan
orden y repeticiones de representantes, referencias, notarios y notas adicionales.
La aceptación de 043 debe ser explícitamente `True` y produce `ACEPTA`.

El número de evento admite 1–50 caracteres; las notas RADIAN hasta 5.000 por nota;
el número de factura hasta 50 y el CUFE exactamente 96 caracteres hexadecimales.
`ONE` y `MULTIPLE` referencian facturas `01`. `ALL` genera `ID=1`, sin UUID ni
DocumentTypeCode. Las fechas del período son obligatorias en 431/433 y se omiten
en 432/434. Consulte las validaciones de identidad y soportes en
[participantes](mandate/participants.md) y los [errores](mandate/notes.md#errores-habituales).

## Hashes, firma y bytes

SoftwareSecurityCode es SHA384(software ID + PIN + número de evento).
El CUDE 043 usa número de evento, fecha/hora de emisión, identificación del
mandante, NIT DIAN, `043`, primera referencia, tipo `01` y PIN.
Para ALL se calculan los hashes con referencia `1` y tipo `01`, aunque este
último se omite del XML. El QR depende del CUDE y ambiente; no se produce
representación gráfica.

La firma XAdES-EPES utiliza RSA-SHA256, SHA256 y C14N inclusiva, con referencias
al documento, KeyInfo y SignedProperties. Incluye el certificado y la cadena
presentes en el PFX, sin descargar certificados. SOAP tiene su perfil de firma
separado. El XML firmado no se reformatea. El ZIP contiene un único
`ar_<CUDE>.xml`, sin rutas. El XML firmado tiene un límite local de 500.000 bytes.
El PIN, los PDF y los binarios preparados no aparecen en `repr`.

## Criterios frente a discrepancias del anexo

La [matriz de conformidad 043/044](../technical/mandate-conformance.md) recoge las
fuentes RADIAN 1.1, discrepancias y decisiones actuales; no repita alternativas
editoriales de los ejemplos originales en sus declaraciones. Los fragmentos
publicados son partes del documento, **no XML listo para transmitir**: omiten la
raíz, extensiones y firma, y usan prefijos del documento completo. La validación
XSD y las firmas locales no acreditan aceptación de negocio ni una prueba remota
con participantes autorizados.

## Migración a declaraciones estructuradas

El contrato actual exige `declaration=MandateDeclaration(...)` en 043 y
`MandateTerminationDeclaration(...)` en 044. `event.notes` es de solo lectura.
Retire las declaraciones manuales y traslade solo observaciones a
`additional_notes`; en 044 deje `header.notes=()`. Consulte la
[migración detallada](mandate/notes.md#migración) y la
[matriz de entradas XML](../technical/event-input-matrix.md).
