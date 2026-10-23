# Aval 035

Parte de los [datos comunes](radian-emission.md#preparación-común-para-los-ejemplos).
Las tres variantes tienen operación y código fijos `035`.

```python
from dataclasses import replace

from radiankore.models.events import (
    GuaranteeBeneficiary,
    GuaranteeCommitment,
    GuaranteeEvent,
)

# Cobertura total; la ausencia de avalados cubre a todas las partes del título.
event = GuaranteeEvent(
    header=header,
    reference=invoice,
    title_value=Decimal("100000.00"),
    guarantors=(GuaranteeCommitment(party=holder, amount=Decimal("0.00")),),
)
```

Para un monto específico, construye la alternativa:

```python
event = replace(
    event,
    guarantors=(GuaranteeCommitment(party=holder, amount=Decimal("30000.00")),),
)
```

Para varios avalados con valores individuales:

```python
event = replace(
    event,
    guarantors=(GuaranteeCommitment(party=holder, amount=Decimal("100000.00")),),
    beneficiaries=(
        GuaranteeBeneficiary(party=buyer, amount=Decimal("50000.00")),
        GuaranteeBeneficiary(party=debtor, amount=Decimal("50000.00")),
    ),
)
```

Prepara y envía mediante la [API común](radian-emission.md). Las variantes son
actos diferentes: no deben enviarse juntas automáticamente.

| Entrada | XPath relativo a `ApplicationResponse` | Cardinalidad / regla |
| --- | --- | --- |
| `guarantors` | `SenderParty/PartyTaxScheme` y `SenderParty/PartyLegalEntity` | Tupla no vacía; identidad y participación emparejadas por orden |
| `GuaranteeCommitment.amount` | `SenderParty/PartyLegalEntity/CorporateStockAmount` | Decimal no negativo, hasta 25 caracteres; `0.00` indica cobertura total (AAF19) |
| `title_value` | Extensión `InformacionAvalar/Value`, nombre `ValorFEVavala` | Obligatorio, positivo, hasta 20 caracteres (AAY06) |
| `beneficiaries` | `DocumentResponse/IssuerParty/PartyLegalEntity` | Grupo opcional; omitirlo garantiza a todas las partes (AAH11) |
| `GuaranteeBeneficiary.amount` | `IssuerParty/PartyLegalEntity/CorporateStockAmount` | Obligatorio si hay varios avalados (AAH32), opcional para uno |
| `reference` | `DocumentResponse/DocumentReference` | Factura CUFE/01; no emite vencimiento |
| `header.notes` | `Note` | Declaraciones explícitas del aval y representación |

La moneda se toma de `event.currency`, COP de forma predeterminada. El receptor
DIAN se genera internamente. Se preservan orden y duplicados de avalistas y
avalados, sin sumar participaciones para inferir cobertura total. La diferencia
de sumas de AAF19 es notificación; no se convierte en rechazo local.

Las dos primeras muestras oficiales incluyen avalados con identidad vacía;
la librería omite el grupo opcional en ese caso. No inventa identificadores ni
reproduce grupos incompletos. Las declaraciones jurídicas se aportan en notas;
su contenido y la facultad del firmante pertenecen al consumidor.

Fuentes RADIAN 1.1: §7.2.1.3, §7.2.4.3, §7.2.5.3, §9.2.3.3 y §9.2.4;
las tres ejemplificaciones de `035-Aval`.
