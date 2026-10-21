# Errores y certificado

- `TypeError`: campos de enum incorrectos en los modelos o tipos de argumentos
  incorrectos en los métodos de consulta.
- `ValueError`: ambiente, timeout, CUFE, UUID, track ID, clave de documento o número de identificación vacío inválidos.
- `OSError` y subclases: fallo al leer el PFX.
- `DigitalCertificateError`: PFX inválido, contraseña incorrecta o material incompleto.
- `DianSignatureError`: clave no RSA o fallo al firmar el sobre.
- `DianTransportError`: fallo de red o HTTP sin SOAP Fault; expone `status_code`.
- `DianSoapFaultError`: fallo SOAP, incluso con HTTP 500; expone `code` y `reason`.
- `DianResponseError`: SOAP, Base64 o UBL malformados, o códigos de identificación
  o evento desconocidos, o fechas y otros valores tipados inválidos de las respuestas.

Las cuatro excepciones de operación heredan de `DianError` y se exportan desde
`radiankore`. Las causas de errores técnicos se conservan cuando corresponde.

`DigitalCertificate.from_file()` y `from_pfx()` permiten cargar certificados directamente.
La carga comprueba correspondencia entre clave y certificado, pero no valida
vigencia, confianza, revocación ni aceptación por DIAN. La firma SOAP usa RSA-SHA256
sobre `wsa:To`. HTTP se envía al endpoint `.svc`; el destino firmado en `wsa:To`
incluye `?WSDL`. No se descarga WSDL.
La firma del sobre no equivale a firmar un documento UBL ni la respuesta recibida.
