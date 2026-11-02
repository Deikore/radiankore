# Revisión de conformidad XML de eventos

Revisión realizada el 1 de noviembre de 2026 sobre los emisores 030–051.
Incluye el XML firmado que producen `DianClient` y `AsyncDianClient`, sus modelos
y los casos de prueba sintéticos. Las correcciones corresponden a la versión
0.7.1 del changelog; no se han enviado eventos a DIAN durante esta revisión.

La estructura comprobada es `ApplicationResponse`. No se generan facturas ni
se evalúa aquí un contenedor `AttachedDocument`. El alcance no es una
certificación de aceptación por DIAN ni de vigencia normativa posterior a las
fuentes conservadas.

## Fuentes y método

Se utilizaron los originales inventariados en las
[referencias técnicas](../technical-references.md):

| Fuente | Cobertura | Integridad verificada |
| --- | --- | --- |
| Anexo FE 1.9, 753 páginas, y caja FE edición 2026 | 030–034: §§6.5.4–6.5.5, 8.5–8.6, 11.5, 13.3.1 y 13.3.12 | PDF SHA-256 `1b4022ac112232cd525a455432b2bdfc977d2edcf14c1c7aa26f8ba93fe47ded`; 13 archivos del inventario FE coincidentes |
| Anexo RADIAN 1.1, 482 páginas | 035–051: §§7.2, 9.2, 9.3, 12 y 14 | PDF SHA-256 `f7e75b3fdbe93ae3167918f27fde2cbd370a5cffc175b14481793f9c38e7c9cc`; 138 archivos del inventario de la caja coincidentes |
| XSD UBL 2.1, XSD DIAN, Schematron, genericodes y ejemplos originales | Estructura, catálogos y contraste de variantes | Originales conservados sin modificación |

Las páginas de este informe son físicas. Se leyeron las convenciones RADIAN
§6: opcionales se validan cuando se informan y el anexo prevalece sobre las
ejemplificaciones. Las tablas de rechazo se distinguen de las notificaciones.
Las tablas anchas críticas de AAH04 y AAF12/AAF19 se comprobaron también mediante
renderizado de sus páginas.

La verificación combina XSD del documento, comprobaciones independientes de
perfil y verificación criptográfica sobre los bytes serializados. Los literales
de las pruebas se transcriben de AAH04; no se obtienen del builder ni de las
etiquetas de consulta. Las pruebas de mutación demuestran que detectan cambios
de literal, cardinalidad y pares de extensión que el XSD UBL permite.

## Matriz por evento y variante

Las rutas de la tabla son relativas a `ApplicationResponse`. `DR` abrevia
`cac:DocumentResponse`, `Ref` su `cac:DocumentReference` y `CT` la ruta
`ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/CustomTagGeneral`.
Los elementos bajo CT usan el namespace de ApplicationResponse, incluso sin
prefijo visible. Los demás prefijos conservan los namespaces UBL, DIAN y XAdES.
La [matriz de fuentes](../event-reference-map.md) enlaza los originales y
ejemplos de cada fila.

| Evento / operaciones | Generación y validación | Estructura y condiciones comprobadas |
| --- | --- | --- |
| 030 | FE §6.5.5.3, p. 291; §8.5.3 | Un DR, referencia de factura y `DR/IssuerParty/Person` obligatorio; sin LineResponse; descripción AAH04 |
| 031 | FE §6.5.5.4, p. 293; §8.6 | Motivo 01–04 en `ResponseCode/@listID` y `@name`, tabla 13.3.12; sin persona receptora |
| 032 | FE §6.5.5.5, p. 295; §8.6.1 | Persona obligatoria; literal de rechazo `Recibo del bien y/o prestación del servicio` |
| 033 | FE §6.5.5.6, p. 298; §8.6.2 | Un DR, sin persona ni motivo; literal `Aceptación expresa` |
| 034 | FE §6.5.5.7, p. 299; §8.6.3 | DIAN como receptor; declaración en Note; referencia de factura y ausencia de persona/motivo |
| 035 | RADIAN §7.2.5.3, p. 105; §9.2.4 | CT/InformacionAvalar; avalistas e importes ordenados; avalados opcionales en DR/IssuerParty; no vencimiento |
| 036 / 361–364 | §7.2.5.4, p. 116; §9.2.5 | CT/ConstanciadePagos; vencimiento obligatorio; comprador directo solo para 362/364 |
| 037 / 371–372 | §7.2.5.5, p. 125; §9.2.6 | CT/InformacionNegociacion con cuatro pares; endoso completo/en blanco; deudores en Ref/IssuerParty; literal AAH04 corregido |
| 038 | §7.2.5.6, p. 136; §9.2.7 | Completo/en blanco; extensión con ValorTotalEndoso, sin campos vacíos de venta; literal AAH04 corregido |
| 039 | §7.2.5.7, p. 149; §9.2.8 | Completo/en blanco; extensión con ValorTotalEndoso; literal AAH04 corregido |
| 040 / 401–403 | §7.2.5.8, p. 160; §9.2.9 | Ref identifica el endoso: CUDE-SHA384 y tipo 96; declaraciones explícitas; sin extensión financiera |
| 041 / 411–412 | §7.2.5.9, p. 168; §9.2.10 | CT/InformacionMedidaCautelar, MontoMedidaCautelar; Ref de factura, PDF y funcionarios; sin vencimiento |
| 042 / 421–422 | §7.2.5.10, p. 177; §9.2.11 | ValorDeuda y ValorLimitación; Ref del evento de limitación, tipo 96; PDF y funcionarios |
| 043 / 431–434 | §7.2.5.11, p. 186; §9.2.12 | Mandato general/especial, referencias ONE/MULTIPLE/ALL y alcance general/limitado; bloques de facultades, aceptación y soportes; organización/tributo del mandante explícitos |
| 044 / 441–443 | §7.2.5.12, p. 214; §9.2.13 | DIAN como receptor, representantes del emisor; Ref al mandato por CUDE y tipo 96 |
| 045 / 451–452 | §7.2.5.13, p. 222; §9.2.14 | CT/InformacionPagos; un PartyLegalEntity de pago, EffectiveDate y vencimiento; pago/saldo coherentes; restricción independiente de parcial/total |
| 046 | §7.2.5.14, p. 231; §9.2.15 | CT/InformacionParaelPago; destinatario deudor; referencia y vencimiento; sin crear un registro de pago |
| 047 | §7.2.5.15, p. 239; §9.2.16 | Endoso completo posterior al vencimiento; cuatro pares de negociación; deudores; listID=1 |
| 048 / 481–482 | §7.2.5.16, p. 250; §9.2.17 | CT/InformacionProtesto; acta en DR/LineResponse/LineReference/DocumentReference; aceptación solo en 481; fecha del acta y notarios separados de la factura |
| 049 / 491–494 | §7.2.5.17, p. 261; §9.2.18 | CT/InformacionTransferenciaDerechos; cedentes, cesionarios y deudores; participaciones positivas y suma de cedentes por AAI05a |
| 050 | §7.2.5.18, p. 272; §9.2.19 | CT/NotificacionPagoDeudor; referencia a la factura, no al CUDE de transferencia; vencimiento y destinatario deudor |
| 051 / 511–512 | §7.2.5.19, p. 280; §9.2.20 | CT/InformacionPagoTransferencia; un pago del deudor; EffectiveDate, vencimiento y ecuación de saldo |

Se comprueban ambos ambientes. Las cuatro operaciones de mandato se cruzan con
las dos naturalezas y los tres modos de referencia. Las variantes sin muestra
403 y 443 se sustentan en las tablas de operación y el genericode, sin inventar
una ejemplificación oficial.

## Elementos comunes y reglas de corrección

| Elemento / XPath | Regla y decisión | Evidencia |
| --- | --- | --- |
| Raíz y secuencia de cabecera | Namespace AR; UBLExtensions antes de UBLVersionID, CustomizationID, ProfileID, ProfileExecutionID, ID, UUID, IssueDate e IssueTime; notas antes de participantes | XSD UBL y comprobación `assert_profile` |
| ProfileID | FE usa `de Factura`; RADIAN usa `de la Factura`; no se unifican perfiles por compartir primitives | FE AAD03 y tablas RADIAN |
| UUID | SHA-384 de 96 caracteres; schemeName=CUDE-SHA384 y schemeID coherente con ProfileExecutionID | Vectores oficiales y recomposición desde XPath en pruebas de XML |
| DianExtensions | Un grupo con InvoiceSource, SoftwareProvider, SoftwareSecurityCode, AuthorizationProvider y QRCode, en orden | RADIAN §7.2.4.1 y controles de perfil |
| SoftwareSecurityCode | SHA384(software ID + PIN + número del evento) | §12.2 y recomputación independiente |
| Extensiones particulares | Un grupo CT por perfil, secuencia exacta Name/Value y nombres de §§7.2.4.3–13 | Controles de perfil y mutaciones que pasan el XSD |
| Partes FE | Nombre 1–450 e identificación 3–13; organización explícita | FE AAF03/AAF04 y AAG03/AAG04, pp. 284–285 |
| Partes RADIAN | Nombre informado 5–450 e identificación 3–13; sin identidad ficticia en endosante en blanco | Tablas AAF03/AAF04 y AAG03/AAG04; RadianParty |
| Proveedor de software | NIT 3–15 y DV de un dígito; ambiente fijo | AAB19/AAB22; RadianSoftware |
| Fechas | Date/time nativos, conversión conjunta a Colombia y segundos; ValidationDate de respuestas conserva su contrato independiente | Pruebas de medianoche y zonas horarias |
| Firma | Árbol final, referencias al documento, KeyInfo y SignedProperties; verificación sobre bytes serializados y fallo al alterar un dato | XAdES-EPES y pruebas criptográficas independientes |
| Envío | ZIP original; ambiente idéntico; una transmisión por llamada explícita, sin reconstrucción ni reintento | MockTransport, firmas SOAP y comparación de contentFile decodificado |

### Endosos y transferencias

Se corrigieron los literales `Endoso en propiedad`, `Endoso en garantía` y
`Endoso en procuración`, exigidos por AAH04 en pp. 354, 361 y 367. Las etiquetas
del catálogo de consultas permanecen independientes.

Las tablas de generación prohíben cero en las participaciones de endosantes y
endosatarios (pp. 131, 134, 143, 145, 155, 157, 245 y 248) y de cesionarios
(p. 270). Esto se comprueba por participante. Una diferencia de **sumas** de
endosatarios/cesionarios continúa siendo notificación AAG20: no se transforma
en excepción. AAI05a sí exige la suma de los cedentes o endosantes del perfil
de venta correspondiente.

El aval conserva su excepción: un compromiso cero significa cobertura total.
No se ha impuesto positividad global a `RadianParticipation` ni se ha eliminado
el cero de `GuaranteeCommitment`.

### Pago 045 y contrato público

AAF12, p. 227, declara `SenderParty/PartyLegalEntity` con cardinalidad `1..1`.
La API anterior admitía varios. `InvoicePaymentEvent` utiliza ahora
`payer: RadianParticipation`, igual que 051; `payers` se elimina. La
[guía de migración](../operations/radian-payments.md) contiene el ejemplo vigente.

Las comprobaciones compartidas son:

- AAF19: pago estrictamente positivo.
- AAF19b: pago no superior al valor actual.
- AAF19c: un pago total equivale al valor actual.
- AAK07: pago más saldo pendiente equivale al valor actual.
- Pago parcial: saldo positivo y menor que el valor actual; total: saldo cero.
- Fecha efectiva no posterior a la emisión normalizada a Colombia.

Se conserva la restricción `ResponseCode/@listID` como dato independiente de la
operación parcial/total. No se fusionan personas, infieren saldos ni redondean
importes. La aritmética usa un contexto Decimal local suficiente para los
tamaños admitidos, sin depender de la precisión del consumidor.

### Mandato 043

Se añadieron organización y tributo explícitos a `MandateParty`; los
predeterminados conservan persona jurídica e IVA. El mandante puede representarse
como persona natural, sin deducir esa condición de su documento. Los atributos
se emiten en PartyTaxScheme; el mandatario conserva PowerOfAttorney/AgentParty.

Se aplican AAD05 (ID 1–50), AAF03 (nombre 5–450), AD11 (nota hasta 5.000),
AAH06 (referencia hasta 50), identificaciones de parte 3–13, nombres personales
hasta 100 y departamento hasta 200. AAF23 permite hasta 14 caracteres para el
representante del mandante; AAH70 y ABH20 permiten hasta 15 para agente/notario.
No se rellenan referencias cortas a 50 posiciones: se preservan los números
reales, conforme a las convenciones y las ejemplificaciones.

## Discrepancias de fuentes y condiciones pendientes

| Condición | Tratamiento | Estado |
| --- | --- | --- |
| El XSD DIAN enumera tipos de identificación en schemeID de coID2Type, rechazando el DV 4 de DIAN | Conservar el original y `schemeID=4`, exigido por AAB34; prueba específica reproduce la incompatibilidad | Contradicción documentada; no se cambia el XML para satisfacer ese XSD |
| El XSD UBL permite contenido de extensiones con processContents=lax | Complementar con controles de namespaces, orden, grupos y valores de perfil; mutaciones demuestran el límite del XSD | Comprobado |
| Schematron xslt3 incluye una lista v2.0 ausente y reglas antiguas como SoftwareIDs | No presentarlo como validador integral ejecutado; comprobar los XPath aplicables de las tablas | Recurso incompleto; sin descarga ni modificación de originales |
| AAI07b y las fórmulas de tasa/factor difieren de los importes de los ejemplos | Conservar precio, tasa/factor y medio explícitos; no inventar una fórmula de cálculo | Aceptación financiera pendiente de evidencia DIAN |
| Alcances múltiples de mandato y tamaños incompatibles con literales/tablas | Conservar facultades y sus descripciones completas, orden y repeticiones; no truncar textos derivados para satisfacer una celda contradictoria | Interpretación explícita; sin garantía de aceptación remota |
| Metadatos PDF de mandato frente a tablas estructurales | Usar literales de rechazo de §9.2.12; 041/042/048 conservan sus propios literales | Comprobado en tests de bytes y atributos |
| Perfil FE frente a muestras RADIAN antiguas para 030–034 | Prevalecen AAD03, AAH04 y tablas FE 1.9; motivos de tabla 13.3.12 | Comprobado; muestras intactas |
| Vigencia, facultades, antecedentes, plazos hábiles, existencia de CUFE/CUDE y veracidad de declaraciones | Datos y comprobaciones del consumidor y validación DIAN; no se consultan ni se certifican localmente | Dependencia externa |

## Pruebas y operación asíncrona

Los módulos `test_event_conformance`, `test_event_constraints`,
`test_invoice_event_xml`, `test_mandate_xml`, `test_radian_xml` y
`test_remaining_radian_xml` cubren los perfiles y las correcciones. Las pruebas
de envío comprueban firmas, bytes originales, errores y cierre de conexiones.
Los mismos controles de perfil se aplican a los eventos preparados con await.
Las pruebas que necesitan originales se ejecutan en el checkout con
`--require-references`; las comprobaciones de perfil siguen ejecutándose al
probar el wheel instalado, aunque sus originales se excluyen de la distribución.

Validación de la revisión XML inicial en Python 3.13.16: 2.616 pruebas aprobadas
con cobertura en
el checkout y 2.616 con el wheel importado desde un entorno aislado. Ruff,
formato, mypy, Sphinx con avisos tratados como errores y construcción de wheel y
sdist terminaron correctamente. Las distribuciones conservan `py.typed` y
excluyen las referencias originales. La matriz de CI 3.13–3.15 se conserva;
este informe no atribuye una ejecución local a 3.14 ni 3.15.

El procesamiento de certificados, XML, firma y ZIP permanece fuera del event
loop. La construcción y la compresión ya no mantienen el bloqueo del
certificado; la firma UBL y el acceso nativo siguen protegidos. Para 030–034,
el reloj real se lee después de esperar el bloqueo para evitar firmar con la
fecha previa a un cambio de día colombiano.

`test_async_event_resources` demuestra que otra solicitud puede firmarse mientras
se construye o comprime un evento, que las firmas UBL no se solapan, que el
cierre drena trabajos físicos cancelados y envíos activos, y que cancelar un
cuerpo HTTP cierra el stream sin retransmitir. Se conserva la incertidumbre de
un envío interrumpido; una segunda llamada sigue siendo una decisión explícita.

La aceptación en habilitación con software y participantes autorizados sigue
pendiente. No existe una prueba local que convierta esa dependencia externa en
una garantía de aceptación de todos los eventos.

## Ampliación 0.7.2 de entradas completas

La [matriz de entradas XML](event-input-matrix.md) amplía la auditoría inicial.
Se corrigen las restricciones artificiales de cardinalidad: 041/042/048 admiten
varios DocumentResponse; 041/048 varias referencias por bloque; 043 varios
representantes y notarios por soporte. Se prueban hijos tributarios opcionales,
identidades adicionales y notas tipadas por propósito; no basta una nota no vacía
para satisfacer cualquier declaración. CompanyLegalFormCode queda limitado a
endosatarios 037/047, únicos perfiles que lo incluyen en sus tablas de generación.

Los casos repetidos usan el primer XPath de referencia/identidad para CUDE/QR,
sin concatenar claves ni alterar sus fórmulas. Los importes globales de las
extensiones permanecen globales; no se inventan reglas de reparto por referencia.
Las [notas](../operations/event-notes.md) documentan las alternativas de 034/035/043,
las cláusulas obligatorias de 038/039/048/049 y las notas opcionales de 036/044.
