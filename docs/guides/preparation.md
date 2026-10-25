# Preparar una integración

## Antes de configurar

Identifique el acto y las facultades en la [documentación funcional](../functional/index.md).
La configuración del cliente selecciona destinos y credenciales; no registra
participantes ni habilita software en DIAN. Antes de una prueba real deben existir
los recursos autorizados para el ambiente correspondiente.

## Instalación y compatibilidad

Para consumir la versión documentada: `python -m pip install radiankore==0.5.0`.
Para contribuir al repositorio: `uv sync --locked`. No son procedimientos
intercambiables: el segundo utiliza el checkout y su lockfile. Consulte
[instalación](../installation.md) para las bibliotecas nativas de `lxml`/`xmlsec`.

Se requiere Python >=3.13. CI contempla 3.13–3.15; esto no garantiza que toda
combinación de sistema, arquitectura y bibliotecas nativas disponga de wheel.
Compruebe importación y firma en la imagen final de su aplicación. Mezclar versiones
incompatibles de libxml2 entre lxml y xmlsec puede impedir importar o firmar.

## Configuración de la aplicación

Los nombres siguientes son una propuesta para su aplicación: el SDK no lee
variables de entorno automáticamente ni carga un archivo `.env`.

| Variable propuesta | Contenido | Tratamiento |
| --- | --- | --- |
| `DIAN_CERTIFICATE_PATH` | Ruta del PFX/P12 | Archivo restringido y fuera de Git |
| `DIAN_CERTIFICATE_PASSWORD` | Contraseña del contenedor, opcional | Secreto, distinto del PIN |
| `DIAN_ENVIRONMENT` | `habilitation` o `production` | Selección explícita, sin fallback |
| `DIAN_SOFTWARE_ID` | Identificador de software autorizado | Configuración por ambiente |
| `DIAN_SOFTWARE_PIN` | PIN del software | Secreto usado en CUDE y código de seguridad |

NIT es una identidad tributaria; DV es su dígito de verificación. No reemplazan
software ID, PIN o contraseña. No incluyas secretos en errores, trazas, notebooks,
argumentos de consola ni ejemplos publicados. Proteja también XML y respuestas,
que pueden contener datos comerciales y personales.

## Primera consulta

Este bloque realiza una consulta **solo cuando llamas la función**. Requiere un
certificado propio y una clave de documento conocida del ambiente indicado.
No lo ejecutes contra producción como prueba de instalación.

```python
from pathlib import Path

from radiankore import DianClient, Environment
from radiankore.models.responses import DocumentStatusResult


def check_document(
    certificate_path: Path,
    password: str | bytes | None,
    track_id: str,
) -> DocumentStatusResult | None:
    client = DianClient(
        certificate_path,
        password=password,
        environment=Environment.HABILITATION,
        timeout=30.0,
    )
    return client.get_status(track_id)
```

El constructor lee el archivo y carga certificado y clave una vez, sin abrir HTTP.
Cada operación abre y cierra sus conexiones. No es necesario usar `with client`.
El timeout se aplica a conexión, lectura, escritura y pool; no es un plazo total.
La API es síncrona: en un servidor asíncrono ejecuta el trabajo bloqueante mediante
el mecanismo de workers de su framework y limita concurrencia desde su aplicación.

## Primera preparación sin transmisión

Seleccione una familia en [emisión](../operations/radian-emission.md), copia sus datos
comunes y construye una sola variante. Llama `prepare_radian_event` y conserva
`xml_bytes`, `zip_bytes`, CUDE, número y ambiente del resultado. Esta fase no contacta
DIAN después de cargar el PFX. No llames `send_radian_event` hasta comprobar las
facultades, antecedentes, numeración y destino.

`DigitalCertificate.from_pfx` comprueba contenedor, clave privada y correspondencia
con el certificado. Puede cargar una clave no RSA, pero la firma requiere RSA.
No comprueba vigencia, cadena de confianza, CRL/OCSP, revocación ni autorización DIAN.
Planifica renovación y respaldo seguro; nunca envíes el PFX ni su contraseña en SOAP.
La clave privada permanece en memoria mientras exista el objeto; evita volcados de
memoria y procesos compartidos sin aislamiento apropiado.
