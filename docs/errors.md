# Errores y certificado

- `TypeError`: campos de enum incorrectos en los modelos o tipos de argumentos
  incorrectos en los métodos de consulta. Cadenas en `ReferenceNote.code` también
  generan `TypeError`; otros miembros de `DocumentType` generan `ValueError`.
- `ValueError`: ambiente, timeout, CUFE, UUID, track ID, clave de documento o número de identificación vacío inválidos.
- Los NIT vacíos o con caracteres distintos de dígitos ASCII en
  `get_numbering_range` generan `ValueError` antes de contactar DIAN.
- `OSError` y subclases: fallo al leer el PFX.
- `DigitalCertificateError`: PFX inválido, contraseña incorrecta o material incompleto.
- `DianSignatureError`: clave no RSA o fallo al firmar el sobre.
- `DianTransportError`: fallo de red o HTTP sin SOAP Fault; expone `status_code`.
  También cubre la descarga del ZIP de `GetExchangeEmails`, sin resultado parcial.
- `DianSoapFaultError`: fallo SOAP, incluso con HTTP 500; expone `code` y `reason`.
- `DianResponseError`: SOAP, Base64 o UBL malformados,
  URL o UTF-8 inválidos de `GetExchangeEmails`, ZIP corrupto o sin un único CSV,
  códigos de tipo de documento, motivo de nota, identificación o evento desconocidos,
  códigos distintos de crédito/débito en `ReferenceNote.code`,
  fechas o límites `xs:long` inválidos en `GetNumberingRange`,
  códigos HTTP inválidos en `GetDocumentInfo` o
  `GetXmlByDocumentKey`, o fechas y otros valores tipados inválidos de las respuestas.

Las cuatro excepciones de operación heredan de `DianError` y se exportan desde
`radiankore`. Las causas de errores técnicos se conservan cuando corresponde.
En `get_acquirer`, HTTP 404 sin SOAP Fault devuelve `None`; los demás métodos
mantienen `DianTransportError` para ese estado HTTP.

`DigitalCertificate.from_file()` y `from_pfx()` permiten cargar certificados directamente.
La carga comprueba correspondencia entre clave y certificado, pero no valida
vigencia, confianza, revocación ni aceptación por DIAN. La firma SOAP usa RSA-SHA256
sobre `wsa:To`. HTTP se envía al endpoint `.svc`; el destino firmado en `wsa:To`
incluye `?WSDL`. No se descarga WSDL.
El GET de `GetExchangeEmails` usa la URL recibida, sin firma ni certificado SOAP.
La firma del sobre no equivale a firmar un documento UBL ni la respuesta recibida.

## Preparación y envío del mandato 043

Para preparar el mandato, pasa `MandateEvent` y `RadianSoftware` a
`prepare_radian_event()`. Los modelos
validan operación, facultades, referencias, aceptación, fechas y soportes antes
de firmar. Los errores de composición son `TypeError` o `ValueError`.
`send_radian_event()` exige `PreparedRadianEvent` del mismo ambiente; no
reconstruye el XML ni reintenta el envío. Los fallos de firma conservan
`DianSignatureError`; los de red, SOAP y respuesta conservan sus excepciones
públicas. Un rechazo de negocio devuelve `SendEventResult`, sin convertirlo en
excepción. La [guía de mandato](operations/mandate.md) documenta las condiciones.

## Preparación y envío de eventos 030–034

Se conservan las excepciones de firma, transporte, SOAP y respuesta del mandato.
Las entradas rechazan tipos incorrectos con `TypeError` y valores incompatibles
con `ValueError`: código distinto de 030–034, CUFE inválido, motivo fuera de 031,
persona fuera de 030/032 o notas ausentes en 034. No se valida el contenido jurídico
de las declaraciones. La preparación exige fecha de emisión y de firma iguales
en Colombia, XML firmado de hasta 500.000 bytes y un software válido.
Enviar con otro ambiente o con una entrada que no sea `PreparedRadianEvent`
genera error local antes de abrir conexiones. Un rechazo de negocio sigue siendo `SendEventResult`.


## Preparación y envío RADIAN

`prepare_radian_event()` acepta los quince modelos de su unión pública y
`RadianSoftware`. Las composiciones incorrectas generan `TypeError` o `ValueError`
antes del envío: operación ajena a la familia, declaración requerida ausente,
comprador directo incompatible, importe no finito, saldo incoherente, vencimiento
ausente o modalidad de endoso incompatible. No se impone una fórmula de descuento
contradictoria ni se convierten notificaciones en rechazos locales. La suma de
cedentes de 049 sí se exige por el rechazo AAI05a de su extensión, aunque AAF19
la trate como notificación. 051 exige un pagador, importe positivo y saldo
aritmético; 035 conserva cero como cobertura total. Adjuntos de 041/042/048
requieren bytes PDF y el nombre literal de su perfil. El tamaño del XML firmado
incluye base64 y no se corrige truncando el soporte.

`send_radian_event()` exige `PreparedRadianEvent` del mismo ambiente para todas
las familias 030–051. Se reutilizan excepciones de
firma, transporte, SOAP y parsing. No hay reintentos. Un rechazo de DIAN se devuelve
como `SendEventResult`; un resultado ausente/nil es `None`. La emisión real requiere
antecedentes y participantes autorizados que no se consultan automáticamente.

## API asíncrona

`DianTransportError.retry_after: float | None` conserva una pausa HTTP expresada
en segundos cuando la respuesta contiene un Retry-After válido. Es información
para el consumidor, no un reintento automático. El cliente async también aplica
esa pausa a nuevas solicitudes del mismo servicio.

Un plazo total vencido produce `DianTransportError` con `TimeoutError` como causa;
`CancelledError` se propaga. Una emisión interrumpida puede tener resultado
desconocido: no la reenvíe automáticamente. Consulte
[timeouts, cierre y cancelación](guides/async.md).
