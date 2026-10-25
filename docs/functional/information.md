# Información que se puede consultar

La consulta permite conocer información registrada y obtener documentos disponibles.
No modifica por sí misma la situación comercial de la factura. Para interpretar
el resultado deben distinguirse la pregunta realizada, el documento consultado y
la fecha de la consulta.

## Estado de validación

Permite conocer el resultado informado por DIAN para un documento. Deben revisarse
el estado, la descripción y los mensajes, sin confundir una validación con la
aceptación del adquirente. La ausencia de un resultado no acredita éxito ni pago.

## Eventos asociados a una factura

Permite identificar las actuaciones relacionadas con la factura y revisar sus
códigos, descripciones, fechas, participantes y referencias disponibles. Cada
actuación se interpreta mediante su [página de evento](events/index.md).

Una relación de eventos no debe tratarse como una declaración automática del
legítimo tenedor. Es necesario revisar modalidades, referencias, cancelaciones,
limitaciones y los demás antecedentes que correspondan.

## Información del documento

Puede reunir emisor, receptor, numeración, tenedor informado, valores, impuestos,
estados, eventos, notas, referencias y observaciones de validación. Debe conservarse
la relación entre esos datos y el documento al que pertenecen, especialmente si
la consulta devuelve varios documentos.

| Dato | Pregunta funcional que ayuda a resolver |
| --- | --- |
| Emisor y receptor | ¿Quiénes intervienen en la operación facturada? |
| Número y fecha | ¿Qué documento se está examinando? |
| Tenedor informado | ¿Qué posición reporta la consulta en ese momento? |
| Valores e impuestos | ¿Qué montos informa el documento? |
| Estados y validaciones | ¿Qué situaciones y observaciones registra la respuesta? |
| Referencias y eventos | ¿Qué documentos y actuaciones están relacionados? |

Los campos ausentes deben presentarse como información no disponible, sin
atribuirles un valor cero, una identidad o una fecha que no hayan sido informados.
El valor de la factura, el precio de negociación, el pago y el saldo son conceptos
diferentes y no deben agruparse bajo una sola etiqueta de monto.

## Notas relacionadas

Las notas crédito y débito son documentos diferentes de los eventos de recepción,
aceptación o circulación. La consulta de notas permite examinar sus referencias,
fechas, motivos y demás información disponible. Debe comprobarse qué documento
referencia cada nota; una referencia puede identificar la factura antecedente.

La existencia de una nota no debe interpretarse como cancelación de un endoso o
terminación de un mandato. Antes de emitir notas deben considerarse las condiciones
relacionadas con la aceptación, descritas en [033](events/033.md) y [034](events/034.md).

## Documentos originales

Cuando se dispone de una clave y el documento está disponible, se puede obtener
su archivo original. Deben distinguirse factura, evento, nota y respuesta de
validación. La falta de un archivo no permite sustituirlo por otro documento
relacionado ni concluir que el acto comercial no ocurrió.

Los archivos pueden contener información comercial y personal; su consulta y
conservación deben respetar las facultades y el acceso que correspondan.

## Rangos de numeración

Permiten consultar la información de numeración autorizada que devuelva DIAN,
como resolución, prefijo, límites y vigencia. La consulta no otorga una nueva
autorización ni asigna por sí sola el siguiente número de factura.

## Datos del adquirente

Permiten consultar el nombre y correo que se informen para una identificación.
La consulta no sustituye la verificación de representación, capacidad, mandato o
legitimación de esa persona para realizar un evento.

## Directorio de correos

Permite consultar los correos registrados disponibles para el intercambio de
documentos. La presencia de un correo no demuestra que una factura haya sido
entregada o aceptada, ni atribuye al destinatario facultades sobre ella.

## Caso práctico

Distribuciones del Norte revisa FE-100. Comprueba el resultado de validación,
consulta los eventos, contrasta participantes y valores y examina las notas y
los documentos disponibles. Conserva la fecha de revisión. Si un dato no está
disponible o los antecedentes no permiten establecer la tenencia, deja esa
situación pendiente de comprobación en lugar de completar la información por
suposición.

Fuentes: contratos del servicio de consulta publicados por DIAN y materiales
versionados de Factura Electrónica y RADIAN. El alcance y las referencias de
negocio se describen en [Fuentes y alcance](sources.md).
