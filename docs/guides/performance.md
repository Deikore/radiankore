# Rendimiento y ciclo de vida del cliente

Disponible desde radiankore 0.6.1. La API es síncrona y no administra colas,
trabajadores, permisos de plataforma ni selección de certificados.

## Construcción desde memoria

`DianClient.from_pfx(data, *, password=None, environment=Environment.PRODUCTION,
timeout=30.0, reuse_connections=False)` carga un PKCS#12 desde bytes.
`DianClient.from_certificate(certificate, *, environment=Environment.PRODUCTION,
timeout=30.0, reuse_connections=False)` utiliza un `DigitalCertificate` ya cargado.
Ambas devuelven un cliente y no abren conexiones de red durante la construcción.

```python
from radiankore import DianClient, DigitalCertificate


# Valores suministrados por la aplicación desde su almacenamiento seguro.
def consultar(pfx_bytes: bytes, password: str | None, cufe: str):
    with DianClient.from_pfx(
        pfx_bytes, password=password, reuse_connections=True
    ) as client:
        return client.get_invoice_events(cufe)


def consultar_con_material(certificate: DigitalCertificate, cufe: str):
    with DianClient.from_certificate(certificate, reuse_connections=True) as client:
        return client.get_document_info(cufe)
```

Los ejemplos son funciones de integración: el consumidor proporciona los datos.
La librería no conserva el contenedor PKCS#12 ni la contraseña. Sí conserva el
material criptográfico decodificado durante la vida del cliente. Cargarlo no
comprueba confianza, revocación, vigencia ni autorización ante DIAN; la aplicación
debe aplicar las políticas que correspondan antes de utilizarlo.

## Reutilizar conexiones

El constructor por ruta también admite `reuse_connections=True`. El valor
predeterminado sigue siendo `False`: cada operación cierra su cliente HTTP.
Con `True`, las operaciones reutilizan un cliente HTTP de SOAP y otro de
descargas, creados de forma diferida y separados. Las cookies se eliminan entre
operaciones; la autenticación SOAP se firma de nuevo para cada solicitud.

Use `with` o llame a `close()` al finalizar. El cierre es idempotente. Las
operaciones de red y la preparación de eventos rechazan un cliente cerrado con
`RuntimeError`. Cerrar recursos HTTP no garantiza el borrado físico de todos los
objetos criptográficos: Python y las bibliotecas nativas administran su memoria.

HTTPX puede reutilizar conexiones TCP cuando el servidor las mantiene abiertas,
lo que evita parte del establecimiento repetido de conexiones. Esto no garantiza
una reducción concreta de latencia ante DIAN. Consulte la
[documentación de clientes HTTPX](https://www.python-httpx.org/advanced/clients/).
El timeout sigue aplicando por fase HTTP; no es un plazo total de la operación.
TLS, errores SOAP y bytes originales conservan sus contratos anteriores.
No existen reintentos automáticos ni cambios de ambiente implícitos.

## Procesos y concurrencia

Cree un cliente dentro de cada proceso, después de `fork`. No comparta clientes
ni conexiones entre procesos. Esta versión no garantiza llamadas concurrentes
sobre una misma instancia: utilice una llamada a la vez por cliente y proceso.
Varios procesos pueden cargar independientemente el mismo certificado.

Mantenerlo cifrado en una base de datos es compatible con este modelo. La
aplicación descifra en memoria y controla vencimiento, rotación, permisos, tiempo
de retención y cierre de recursos. No incluya claves, contraseñas ni XML reales
en registros o pruebas.

## Medición y firma

El transporte puede medirse contra un servidor HTTP local; `MockTransport`
comprueba contratos, pero no demuestra reutilización de conexiones TCP.
Las pruebas incluyen ambas verificaciones. Los resultados locales no representan
los tiempos de DIAN ni los límites que pueda aplicar ese servicio.

La firma mantiene una clave xmlsec y un contexto nuevos por operación. No se ha
introducido una caché de claves nativas: su posible ahorro exige medir el coste
y verificar propiedad y aislamiento antes de modificar ambos perfiles de firma.
No se reutilizan documentos firmados, identificadores ni contextos mutables.

## Migración desde 0.5.0

El constructor por ruta y el cierre por operación siguen funcionando. Para
adoptar reutilización, agregue el argumento y establezca el cierre explícito.
Si los datos ya están en memoria, sustituya la ruta por una de las fábricas.
No cambian las respuestas, los modelos ni las firmas de las operaciones SOAP.

Para repetir el ensayo local desde el checkout:

```bash
uv run python scripts/benchmark_clients.py --counts 1 4 8 12 16 --requests-per-process 10
```

El JSON incluye procesos, latencias, conexiones, carga PKCS#12, preparación de
claves xmlsec, CPU y memoria por proceso. Incluye el coste de arranque de procesos
en el tiempo total; usa HTTP local sin TLS y no sustituye una medición de DIAN.

### Ensayo local de referencia

El ensayo con certificado sintético y ocho solicitudes por proceso produjo:

| Procesos | Conexiones sin reutilización | Conexiones con reutilización |
|---|---:|---:|
| 1 | 8 | 1 |
| 4 | 32 | 4 |
| 8 | 64 | 8 |
| 12 | 96 | 12 |
| 16 | 128 | 16 |

Los resultados completos se conservan en
[JSON del ensayo](../benchmarks/client-reuse.json). El escenario sin reutilización
reconstruye también el cliente por solicitud, como hacía el adaptador anterior;
por tanto, sus latencias combinan carga PKCS#12 y transporte. La preparación de
la clave xmlsec tuvo medianas inferiores a un milisegundo en este ensayo.
No se incorporó caché nativa: no se verificó un modelo seguro de propiedad y
reutilización que cumpla las condiciones de adopción. La memoria criptográfica
adicional y los riesgos de concurrencia requieren una evaluación independiente.
