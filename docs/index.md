# radiankore

Librería Python de Deikore SAS para consultas directas a DIAN mediante SOAP y
certificados PFX/P12. La API es síncrona, admite Python >=3.13 y se distribuye bajo MIT.
Permite preparar y enviar eventos 030–051; no genera facturas.

## Primeros pasos

Instala el paquete, crea un `DianClient` y selecciona producción o habilitación.
El certificado se carga una vez y cada consulta gestiona sus conexiones.

```{toctree}
:maxdepth: 2
:caption: Primeros pasos

installation
environments
```

## Consultas disponibles

GetStatus devuelve el resultado de validación del documento; GetStatusEvent consulta
los eventos asociados a una factura. Las demás operaciones permiten consultar
rangos de numeración, adquirientes, el directorio de correos, información del documento, notas
referenciadas y el XML original.

```{toctree}
:maxdepth: 2
:caption: Operaciones

operations/numbering-range
operations/exchange-emails
operations/status
operations/events
operations/acquirer
operations/document-info
operations/reference-notes
operations/xml-document
operations/mandate
operations/invoice-emission
operations/radian-emission
```

```{toctree}
:maxdepth: 2
:caption: Referencia

api
models
catalogs
errors
technical-references
event-reference-map
```

```{toctree}
:maxdepth: 2
:caption: Contribuir

development
publishing
readthedocs
changelog
```
