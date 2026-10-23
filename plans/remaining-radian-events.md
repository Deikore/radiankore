# Plan de los eventos RADIAN restantes

Fecha: 23 de octubre de 2026. Estado: implementado en el árbol de trabajo.
Las guías de las cuatro familias y sus discrepancias están enlazadas desde
[`docs/operations/radian-emission.md`](../docs/operations/radian-emission.md).

La revisión de §9.2.3.11 confirmó que AAI05a de 049 es rechazo: se exige la suma
de cedentes, aunque AAF19 sea notificación. §7.2.5.19 AAF12 define una sola
participación de pago, por lo que 051 expone `payer`, sin una colección artificial.
Los nombres de archivo y atributos de adjuntos siguen los literales de rechazo
del perfil. Estas precisiones sustituyen las propuestas preliminares respectivas.

## Alcance y resultado esperado

Completar la emisión de los siete eventos pendientes del catálogo RADIAN 1.1:
035, 041, 042, 048, 049, 050 y 051. Son **14 operaciones** y hay **16 XML de
ejemplo** en la caja de herramientas. Con este alcance quedarán cubiertos los
eventos de participante 030–051. Los códigos 02/04 son respuestas generadas por
DIAN y no forman parte de los emisores del consumidor.

La revisión sigue `radian-anexo` para estructuras y reglas, y
`python-library-architect` para API, composición, compatibilidad y distribución.
Las fuentes son las copias versionadas del repositorio; el alcance corresponde
a RADIAN 1.1, sin afirmar vigencia frente a versiones posteriores.

| Evento | Operaciones / significado | Ejemplos | Orden |
| --- | --- | ---: | ---: |
| 035 Aval | 035; cobertura total, monto específico y varios avalados | 3 | 1 |
| 049 Transferencia de derechos económicos | 491 parcial con responsabilidad; 492 total con responsabilidad; 493 parcial sin responsabilidad; 494 total sin responsabilidad | 4 | 2 |
| 050 Notificación al deudor | 050 | 1 | 2 |
| 051 Pago de transferencia de derechos económicos | 511 parcial; 512 total | 2 | 2 |
| 041 Limitación a la circulación | 411 embargo; 412 mandamiento de pago | 2 | 3 |
| 042 Terminación de limitación | 421 sentencia; 422 terminación anticipada | 2 | 3 |
| 048 Protesto | 481 falta de aceptación; 482 falta de pago | 2 | 4 |

El orden prioriza la reutilización de la emisión financiera existente y después
introduce adjuntos y actas. No implica emitir los eventos automáticamente en ese
orden ni construir una máquina de estados del negocio.

## API y límites de módulos

Mantener el contrato común:

```python
prepared = client.prepare_radian_event(event=event, software=software)
# El consumidor puede inspeccionar o persistir los bytes antes del envío.
result = client.send_radian_event(prepared)
```

Ampliar `RadianEvent` con siete entradas específicas y conservar
`PreparedRadianEvent` y `SendEventResult | None`. El código se deriva del modelo
y la operación; el consumidor no suministra ambos. No añadir métodos públicos
por evento, dependencias, clases base ni registros de plugins.

| Módulo propuesto en `models/events/` | Entradas públicas propuestas |
| --- | --- |
| `guarantees.py` | `GuaranteeEvent`, `GuaranteeCommitment`, `GuaranteeBeneficiary` |
| `economic_rights.py` | `EconomicRightsTransferEvent`, `EconomicRightsNotificationEvent`, `EconomicRightsPaymentEvent`, `EconomicRightsTransferTerms` |
| `restrictions.py` | `CirculationRestrictionEvent`, `CirculationRestrictionTerminationEvent` |
| `protests.py` | `ProtestEvent`, `ProtestAct`, `ProtestNotary` |
| `attachments.py` | `RadianPdfAttachment` |

Todas las entradas serán dataclasses `frozen=True`, `slots=True`, `kw_only=True`,
con validación de dominio y sin XML, red ni lectura de archivos. Los nombres
propuestos se fijarán con sus ejemplos de uso antes de escribir los builders.

Reutilizar `RadianEventHeader`, `RadianParty`, ambas referencias tipadas,
`RadianParticipation`, normalización colombiana y validadores puros. No convertir
modelos de factura, mandato o endoso en un modelo con muchos campos opcionales.
El notario del acta tendrá un componente propio: su perfil pide nombre,
apellidos y cargo, sin exigir la identificación que requiere `RadianPerson`.

En `_soap/events/`, añadir builders por estas cuatro familias y extender el
dispatcher privado. Reutilizar cabecera, CUDE, QR, `DianExtensions`, participantes,
extensiones Name/Value, firma UBL, ZIP y transporte actuales. Compartir la
serialización de adjuntos y las comprobaciones de pago compatibles con 045,
sin cambiar las restricciones observables de 045 ni sus modelos públicos.

Extender `RadianOperationType` con los 14 valores y sus etiquetas oficiales.
Reutilizar `CurrencyCode`, `PaymentMeans`, `PaymentRestriction`, `FactorType`,
identificaciones, organizaciones y tributos. Añadir únicamente
`AcceptanceFailureType` (1 parcial, 2 total), según §14.2.20 y
`Falta de aceptacion.gc`; no reutilizar la clase de endoso por coincidencia de códigos.
Actualizar exports, unión de entradas, dispatcher y admisión de códigos de
`PreparedRadianEvent` conjuntamente.

## Etapa 0: fijar la matriz de requisitos

Antes de cada builder, registrar campo, XPath, cardinalidad, formato, regla de
rechazo/notificación y ejemplo que lo demuestra. Contrastar generación,
validación, genericodes y esquemas; anotar discrepancias fuera de los originales.
Las condiciones sobre historial, facultades, titularidad y roles autorizados
siguen a cargo del consumidor y DIAN.

Cerrar específicamente la opcionalidad del vencimiento y los datos tributarios
por perfil, los límites de longitud por importe y la serialización de adjuntos.
No imponer al conjunto de eventos los campos obligatorios de una sola familia.
Conservar notas, orden de participantes, duplicados y precisión `Decimal`.

## Etapa 1: aval 035

- Modelar valor de la factura, avalistas y sus compromisos, moneda y avalados
  opcionales. Destinatario DIAN y referencia a factura con CUFE/tipo 01.
- Emitir `InformacionAvalar/ValorFEVavala`; los compromisos van en
  `SenderParty/PartyLegalEntity/CorporateStockAmount` y los avalados en
  `DocumentResponse/IssuerParty/PartyLegalEntity`.
- Conservar la semántica explícita de AAF19: compromiso `Decimal("0.00")`
  significa responder por la totalidad. La ausencia de `IssuerParty` garantiza
  a todas las partes; no serializar identidades vacías como las muestras.
- `GuaranteeCommitment` permite el tamaño propio de AAF19 (hasta 25 caracteres),
  sin ampliar globalmente los 20 de `RadianParticipation`. El importe de cada
  avalado se modela opcional para uno y se exige cuando hay varios, conforme
  AAH32. Sus importes conservan el límite del perfil.
- AAF19 en validación trata la diferencia de sumas como notificación; no
  rechazar cobertura total cero por compararla con el valor de la factura.
  Exigir las declaraciones que correspondan y documentar su contenido esperado.
- Entregar ejemplos sintéticos de las tres variantes y varias participaciones.

## Etapa 2: derechos económicos 049, 050 y 051

**049.** Entrada con cedentes, cesionarios, deudores y términos propios:
valor transferido, precio, factor de descuento y medio de pago. Preservar
participaciones y moneda, los cuatro tipos de operación y la referencia CUFE/01.
Emitir `InformacionTransferenciaDerechos` con los literales ordenados
`ValorTransferenciaDerechos`, `PrecioPagarseFEV`, `FactordeDescuento` y `MedioPago`.
Reutilizar primitivas financieras; no reutilizar el literal `TasaDescuento`
del endoso ni heredar sus reglas de sumas: AAF19/AAG20 de 049 son notificaciones.
Precio y factor serán explícitos, sin deducirlos de fórmulas ambiguas.

**050.** Generador cedente, receptor deudor y referencia a factura CUFE/01.
Emitir `NotificacionPagoDeudor/ValorFEV-TV`. El modelo y la guía deben explicar
qué importe representa este literal contrastando negocio, generación y
validación; no cambiar el nombre XML por el de otro evento. No sustituir al
deudor por DIAN ni referenciar el CUDE de 049 en lugar del CUFE de la factura.

**051.** Modelar pagadores, fecha efectiva, valor actual, saldo, moneda y
restricción; receptor DIAN, referencia CUFE/01 y extensión
`InformacionPagoTransferencia`. Mantener independientes operaciones 511/512 y
`ResponseCode/@listID` 1/2 de `PaymentRestriction`.
Los importes pagados deben ser positivos y no superar el valor actual; para
pago total se exige la igualdad prevista por AAF19c. Aplicar el alcance de esas
reglas al participante o total que indique su XPath, sin confundirlos. La fecha
efectiva no supera la fecha de emisión colombiana. Contrastar saldos con las
reglas de la extensión y no redondear.

Documentar la diferencia de roles entre la lista de negocio de 051 y su tabla
§14.2.1/muestras; conservar identidad explícita y no inferirla del certificado.
Probar las cuatro combinaciones de tipo de pago y restricción.

## Etapa 3: limitación 041 y terminación 042

- Crear dos modelos: 041 exige referencia de factura CUFE/01; 042 exige
  referencia de la limitación CUDE/96. Ambos generan receptor DIAN.
- Modelar autoridades y funcionarios en tuplas ordenadas según las
  cardinalidades. El funcionario va en `DocumentReference/IssuerParty`.
- 041 emite `InformacionMedidaCautelar/MontoMedidaCautelar`; 042 emite los
  pares `ValorDeuda` y `ValorLimitación`, preservando el acento del literal.
- Modelar el acto en `RadianPdfAttachment(filename, content_bytes)` con bytes
  inmutables no vacíos, ocultos en `repr`, sin abrir rutas durante preparación.
  El builder codifica base64 una sola vez en `DocumentReference/Attachment`.
- Conservar los atributos literales del perfil DIAN, incluido `mimeCode="PDF"`,
  aunque difieran de MIME habitual. Resolver diferencias entre generación,
  validación y ejemplos de `format`, `encodingCode` y `characterSetCode` con
  pruebas explícitas; las muestras vacías no son adjuntos válidos.
- La descripción de negocio admite autoridad sin NIT, pero AAF04 de generación
  y rechazo lo exige. El perfil inicial exigirá NIT real según esas reglas,
  documentando la divergencia; nunca fabricar uno ni usar un NIT por defecto.
- No exigir que deuda y medida cautelar sean iguales ni inferir proporcionalidad
  a la factura sin una regla expresa. No añadir adjuntos al modelo de referencia
  común ni cambiar `MandateAttachedDocument`.

## Etapa 4: protesto 048

- Modelar generador, receptor, referencia de factura y vencimiento según su
  perfil, valores de protesto y acta con fecha, notaría, notarios y PDF.
- Para 481 exigir `AcceptanceFailureType` en `CustomizationID/@schemeID` y los
  importes `ValorAceptado` / `ValorPendiente`, con saldo igual a valor de factura
  menos aceptado. Distinguir falta parcial/total según §14.2.20.
- Para 482 no exigir ni copiar automáticamente el atributo y valores de falta
  de aceptación: generación los condiciona a 481, aunque su muestra los incluye.
  Resolver la discrepancia de AAD13 de validación en la matriz de esta familia.
- Emitir `InformacionProtesto` y el acta en
  `DocumentResponse/LineResponse/LineReference/DocumentReference`, con `LineID=1`,
  número de notaría, descripción, adjunto e información del notario. La fecha
  del acta pertenece al `LineResponse/Response/EffectiveDate`, no al pago.
- Reutilizar los bytes y el encoder de adjuntos de 041/042 con atributos propios
  del acta. No recalcular plazos legales ni validar autenticidad del acto.

## Verificación y criterios de aceptación

1. Contratos públicos: imports explícitos, dataclasses inmutables, operaciones
   válidas por familia, tipos de referencia, ausencia de I/O al preparar y
   errores comprensibles. Mantener los contratos de 030–034, 036–040 y 043–047.
2. Cubrir las 14 operaciones en habilitación y producción; las 16 muestras
   sirven para comparar estructura, no para reutilizar identidades o firmas.
   Añadir límites y datos sintéticos para variantes no demostradas por ellas.
3. Verificar XML con XSD disponible y reglas Schematron aplicables, atributos,
   namespace de extensiones, orden UBL, CUDE calculado independientemente,
   SoftwareSecurityCode y QR de la referencia correcta. Verificar la firma
   de los bytes serializados y el ZIP exacto de un solo XML.
4. Probar montos cero especiales del aval, precisión Decimal con contexto reducido,
   tuplas múltiples, saldos, fechas y cambio de día por zona horaria. Probar
   bytes de PDF recuperados del XML y el límite de 500.000 bytes después de
   base64 y firma; no comprimir o truncar documentos automáticamente.
5. Enviar mediante MockTransport: ZIP intacto, ambiente, cierre de conexiones,
   respuesta vacía, rechazos y fallos técnicos. Sin llamadas a DIAN ni reintentos.
6. Ejecutar Ruff, formato, mypy, suite completa, Sphinx con warnings como errores,
   build y pruebas del wheel aislado; conservar CI Python 3.13–3.15. No confundir
   esta verificación local con aceptación real en habilitación DIAN.
7. Documentar guías por familia y ejemplos ejecutables de cada operación,
   discrepancias, campos exigidos y roles; actualizar README, API, modelos,
   catálogos, errores, changelog y smoke tests de distribución.

Cada etapa entrega modelos, builders, integración, pruebas y ejemplos de uso
verificados. El cierre requiere los siete códigos disponibles en la API común,
sin regresiones ni nuevas dependencias. La validación con software y participantes
autorizados en habilitación será una actividad posterior explícita.

## Fuentes revisadas y trazabilidad

Anexo local: `docs/references/dian/radian/1.1/anexo-tecnico.pdf`.
Caja: `docs/references/dian/radian/toolbox/`.

| Familia | Negocio | Extensiones | Generación | Validación |
| --- | --- | --- | --- | --- |
| 035 | §7.2.1.3, p. 40 | §7.2.4.3, p. 80 | §7.2.5.3, pp. 105–115 | §9.2.4, pp. 340–345 |
| 041/042 | §§7.2.1.7–8, pp. 45–46 | §§7.2.4.6–7, pp. 86–89 | §§7.2.5.9–10, pp. 168–185 | §§9.2.10–11, pp. 372–380 |
| 048 | §7.2.1.9, p. 47 | §7.2.4.10, pp. 92–93 | §7.2.5.16, pp. 250–260 | §9.2.17, pp. 411–415 |
| 049/050/051 | §§7.2.1.10–12, pp. 47–50 | §§7.2.4.11–13, pp. 93–99 | §§7.2.5.17–19, pp. 261–289 | §§9.2.18–20, pp. 416–429 |

Completar el contraste de las extensiones de validación (§9.2.3) y la matriz
sujeto–evento–rol al fijar cada contrato. Tipos de operación: §14.1.2,
pp. 468–469 y `TiposOperaciónRADIAN-2.1.gc`; aceptación: §14.2.20, p. 482 y
`Falta de aceptacion.gc`; pagos: §14.2.9 y `TipoPago.gc`. CUDE general:
§12.1.1; QR: §12.3. Usar los XSD/Schematron de la caja según su cobertura real.

Se inspeccionaron las 16 ejemplificaciones de las carpetas 035, 041, 042 y
048–051, incluyendo operaciones, atributos y estructura de participantes,
extensiones, referencias y actas. Se preservarán los originales y sus inventarios.

## Verificación de la implementación

- Python local 3.13: 1.909 pruebas completas, con cobertura del 99 %; Ruff,
  formato y mypy estrictos sin errores. La matriz de CI conserva 3.13–3.15.
- Las 14 operaciones nuevas se preparan en ambos ambientes y los siete códigos
  se envían mediante MockTransport, sin contactar a DIAN.
- Los ejemplos nuevos generan 17 XML con XSD y firmas verificadas, incluidas
  las variantes de aval y falta de aceptación. También se ejecutaron desde el wheel.
- Sphinx compila con advertencias como errores. Wheel/sdist construidos,
  imports de CI y `py.typed` comprobados en instalación aislada: 1.879 pruebas
  pasan y 30 se omiten por referencias excluidas de las distribuciones.
- Inventario SHA-256 de la caja RADIAN intacto. Las limitaciones del Schematron
  distribuido se documentan en la guía común; no se afirma ejecución integral.
- Pendiente externa: aceptación con participantes y software autorizados en
  habilitación DIAN, especialmente las discrepancias documentadas del anexo.
