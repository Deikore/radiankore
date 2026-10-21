# Ambientes

| Selección | Endpoint |
| --- | --- |
| `Environment.PRODUCTION` o `"production"` (predeterminado) | `https://vpfe.dian.gov.co/WcfDianCustomerServices.svc` |
| `Environment.HABILITATION` o `"habilitation"` | `https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc` |

Otros valores, incluido `None`, generan `ValueError`. `client.environment` expone
el ambiente seleccionado. Nunca se cambia de ambiente automáticamente.
