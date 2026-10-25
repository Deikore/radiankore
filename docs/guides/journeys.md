# Ejemplos de integración por proceso

Esta página permite localizar los ejemplos técnicos de cada proceso. Las
condiciones de negocio se explican en [Procesos y casos prácticos](../functional/processes.md).

| Objetivo técnico | Ejemplo canónico | Resultado que debe comprobar |
| --- | --- | --- |
| Consultar factura, eventos, información y notas | [Funciones de consulta](queries.md) | Modelos de respuesta, datos ausentes y bytes descargados |
| Preparar recepción, reclamo o aceptación | [Eventos 030–034](../operations/invoice-emission.md) | Artefacto del único evento elegido y resultado de envío |
| Preparar mandato y terminación | [043](../operations/mandate.md) y [044](../operations/radian-termination.md) | Referencias, soportes, modalidad y CUDE |
| Registrar, endosar e informar pagos | [036](../operations/radian-registration.md), [endosos](../operations/radian-endorsements.md) y [045/046](../operations/radian-payments.md) | Modelo de la variante, importes y respuesta |
| Preparar aval, limitación o protesto | [035](../operations/radian-guarantees.md), [041/042](../operations/radian-restrictions.md) y [048](../operations/radian-protests.md) | Participantes, adjuntos y tamaño del XML firmado |
| Preparar derechos económicos | [049–051](../operations/radian-economic-rights.md) | Participaciones, valores y saldo de la operación seleccionada |

## Ejecución de los ejemplos

1. Configure Python y las dependencias de [instalación](../installation.md).
2. Prepare un certificado propio y seleccione el ambiente explícitamente.
3. Para las familias RADIAN, ejecute el bloque de datos comunes de
   [emisión](../operations/radian-emission.md) antes del ejemplo elegido.
4. Construya una sola variante y llame a la preparación local.
5. Revise y conserve el artefacto antes de autorizar el envío explícito.
6. Compruebe el resultado o gestione la excepción según la [referencia de errores](../errors.md).

El ejemplo de mandato requiere un archivo de soporte en la ruta indicada.
Los ejemplos que llaman a envío realizan una petición real si no se sustituye el
transporte. Las pruebas documentales utilizan certificados sintéticos y transporte
simulado. Importar las funciones de consulta o preparación no inicia un envío.

## Preparar sin enviar desde una aplicación

Este bloque es reutilizable con cualquiera de los modelos de los seis recorridos.
No realiza una transmisión ni asigna numeración. La aplicación debe guardar el
resultado antes de autorizar `send_radian_event`.

```python
from radiankore import DianClient
from radiankore.models.events import PreparedRadianEvent, RadianEvent, RadianSoftware


def prepare_for_review(
    client: DianClient, event: RadianEvent, software: RadianSoftware
) -> PreparedRadianEvent:
    return client.prepare_radian_event(event=event, software=software)
```

Para los estados de aplicación, concurrencia y resultado incierto consulte
[operación](operations.md). Los ejemplos de familia que llaman `send_radian_event`
realizan red si se ejecutan con un cliente real: la suite sustituye ese transporte.
