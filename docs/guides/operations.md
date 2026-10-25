# Operar, persistir y diagnosticar

## Responsabilidades de la aplicación

radiankore es un SDK síncrono, sin base de datos, cola de trabajos, almacenamiento
de credenciales ni generación durable de consecutivos. Tu aplicación debe persistir
el acto de negocio y asignarle una numeración única antes de preparar el evento.
La siguiente máquina de estados es una **recomendación de integración**, no una
funcionalidad incorporada al paquete.

| Estado de aplicación | Evidencia mínima | Siguiente decisión |
| --- | --- | --- |
| Borrador | Datos, actor, facultades, referencias | Validar antecedentes y soportes |
| Preparado | Ambiente, número, CUDE, XML y ZIP exactos | Aprobar transmisión autorizada |
| En transmisión | Intento y fecha, correlación interna | Esperar resultado sin otro envío concurrente |
| Aceptado | Resultado de negocio que confirma aceptación | Consultar y conservar evidencia |
| Rechazado | Resultado y reglas/mensajes | Corregir el acto conforme al proceso |
| Resultado incierto | Timeout/desconexión tras posible envío | Conciliar antes de decidir reenvío |

Llamar dos veces `send_radian_event` puede realizar dos transmisiones. No existe
exactly-once, llave de idempotencia durable ni deduplicación en el SDK. Un timeout
no permite concluir si DIAN recibió el documento. No prepares otro CUDE ni reintentes
ciegamente para ocultar esa incertidumbre: conserve el artefacto original, consulte
con los identificadores conocidos y aplique su procedimiento de conciliación.

Controle concurrencia mediante una exclusión/transacción por acto de negocio en su
persistencia. Evite que dos workers consuman simultáneamente el mismo preparado.
La exclusión protege su aplicación, no crea una transacción distribuida con DIAN.
No cambie a producción cuando falle habilitación, ni a la inversa.

## Diagnóstico por capa

| Síntoma / excepción | Qué comprobar | Recuperación razonable |
| --- | --- | --- |
| `OSError` al construir cliente | Ruta, montaje, permisos de lectura | Corregir acceso al archivo sin imprimirlo |
| `DigitalCertificateError` | PKCS#12, contraseña, clave y certificado | Validar copia controlada; no registrar secretos |
| `TypeError` / `ValueError` | Enum, entrada, saldo, referencia, soporte, fecha y tamaño | Corregir composición antes de transmitir |
| `DianSignatureError` | Clave RSA, dependencias nativas y perfil de firma | Verificar entorno y firma local serializada |
| `DianTransportError` | DNS, TLS, conectividad, timeout y estado HTTP | En consultas decidir reintento desde la app; en envíos conciliar incertidumbre |
| `DianSoapFaultError` | `code`, `reason`, destino, Action, reloj y credenciales | Separar fallo SOAP de un rechazo de reglas del evento |
| `DianResponseError` | SOAP/Base64/UBL/ZIP/CSV, códigos o fechas no soportados | Conservar evidencia saneada; revisar contrato y compatibilidad |
| Resultado con `is_valid=False` | Reglas y mensajes de negocio | Resolver el antecedente o dato específico, sin tratarlo como caída de red |
| Resultado `None` | Resultado ausente/nil según operación | No asumir éxito ni volver a emitir automáticamente |

HTTP exitoso, ausencia de SOAP Fault, respuesta interpretable y aceptación de
negocio son cuatro condiciones distintas. Algunas respuestas expresan códigos
HTTP dentro del payload SOAP: no son el estado de transporte.
La [referencia de errores](../errors.md) detalla las excepciones y causas conservadas.

## Seguridad y observabilidad

Registra correlación propia, operación, ambiente, duración, CUDE/número cuando sea
pertinente y categoría de resultado. Evite PFX, contraseña, PIN, clave privada,
URL temporales, XML completo y payload comercial en logs ordinarios. Los `repr`
que omiten bytes no sustituyen una política de redacción: serializadores genéricos
pueden recuperar esos campos y las causas de errores pueden incorporar contexto.

Guarde los artefactos y respuestas en un repositorio protegido con control de
acceso, retención y respaldo. Proteja por separado las claves que cifran ese
repositorio. La librería no ofrece cifrado en reposo ni borra memoria de manera
certificada. Vigila vencimiento del certificado, deriva de reloj UTC y cambios
de contrato; distingue certificados de habilitación de configuración productiva.

## Rendimiento y despliegue

Reutilizar `DianClient` evita releer el PFX, pero no crea un pool HTTP persistente
entre operaciones. Presupuesta handshake, firma RSA, tamaño del soporte y varias
consultas independientes por pantalla. No ejecutes las ocho consultas si necesita
solo el estado. En un frontend, evita volver a consultar al expandir datos ya obtenidos;
una caché de aplicación debe tener antigüedad visible e invalidación explícita.

No ejecutes operaciones bloqueantes directamente en un event loop. Dimensiona
workers, límites de concurrencia y tiempos de espera desde su servicio. El SDK
no administra rate limits ni paraleliza consultas internamente. Prueba carga con
transporte simulado antes de ensayar tráfico autorizado en habilitación.

En contenedores instale bibliotecas nativas compatibles, ejecute como usuario
sin privilegios y monte el PFX como secreto de solo lectura. Compruebe importación
y preparación local en la imagen final; no utilice una llamada real a DIAN como healthcheck.

## Qué todavía no ofrece el SDK

El WSDL contiene además GetStatusZip, SendBillAsync, SendTestSetAsync, SendBillSync,
SendBillAttachmentAsync y SendNominaSync: **no tienen método público implementado**.
No se generan facturas, notas o nómina; consultar sus documentos no implica poder
emitirlos. Tampoco se implementan trámites de habilitación, consultas de revocación,
verificación de firmas de respuestas ni validación integral de antecedentes.
La superficie soportada son ocho consultas y preparación/envío de eventos 030–051.
