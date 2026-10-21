# Consultar los eventos de una factura

```python
from radiankore import DianClient, Environment
from radiankore.models.responses import InvoiceEventsResult

client = DianClient(
    certificate_path="/ruta/segura/certificado.pfx",
    password="password-de-ejemplo",
    environment=Environment.HABILITATION,
    timeout=30.0,
)
result: InvoiceEventsResult = client.get_invoice_events("CUFE-DE-LA-FACTURA")
print(result.status_code, result.status_description)
for event in result.events:
    print(event.id, event.code, event.description, event.uuid, event.date, event.time)
    if event.issuer is not None:
        print(
            event.issuer.tax_number,
            event.issuer.verification_digit,
            event.issuer.identification_type,
        )
```

## Conexiones automáticas

Cada consulta abre y cierra sus conexiones HTTP internamente, incluso si ocurre
un error. La gestión de conexiones es automática.

Puedes reutilizar el cliente para consultar otras facturas sin volver a cargar
el certificado:

```python
other_result = client.get_invoice_events("OTRO-CUFE")
print(other_result.status_code, other_result.status_description)
```

Las conexiones no se reutilizan entre consultas: cada operación establece una
conexión nueva. Este comportamiento simplifica la gestión de recursos a cambio
del coste de conexión en cada consulta.

## Configuración

La ruta admite `str` o `os.PathLike[str]`. El PFX se carga una sola vez al construir
el cliente, mediante `DigitalCertificate.from_file()`. La contraseña admite `str`
(UTF-8), `bytes` o `None` para un contenedor sin cifrar. El cliente conserva solo el
material decodificado: `client.certificate` no vuelve a leer el archivo.

El constructor no crea clientes HTTP ni realiza conexiones. El timeout debe ser
positivo y finito y se aplica a conexión, lectura, escritura y espera del pool;
no es un plazo total.
No hay reintentos automáticos ni seguimiento de redirecciones.
