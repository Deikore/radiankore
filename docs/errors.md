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
