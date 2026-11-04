# Terminación del mandato 044

Contexto funcional: [044](../functional/events/044.md).

Esta página describe el contrato de **0.7.4**, con declaraciones estructuradas
y emisor derivado de la operación. Copie la [base común](mandate/participants.md#base-común),
después uno de los ocho casos y finalmente la
[preparación](mandate.md#ejemplo-de-preparación-y-envío). Todos usan habilitación
explícita. No necesitan un evento de constitución ejecutado previamente.

| Operación | Miembro | Emisor derivado | Declaración condicional |
| --- | --- | --- | --- |
| 441 | `MANDATE_REVOCATION` | Mandante y sus representantes | Ratificación opcional con `ratify_acts=True` |
| 442 | `MANDATE_RESIGNATION` | Mandatario y sus representantes | Siempre `no_pending_acts=True` explícito |
| 443 | `MANDATE_REJECTION` | Mandante y sus representantes | Sin ratificación ni constancia de actos pendientes |

`reference` identifica el mandato original por número y CUDE (`CUDE-SHA384`, tipo
`96`), no la factura. No se reconstruye ni consulta el mandato. La fecha efectiva
se toma de `declaration.effective_date` y se expresa en la nota de terminación;
no hay `Response/EffectiveDate`. DIAN se genera como receptor.

`header.notes` debe estar vacío. `event.notes` es de solo lectura y compone las
notas. La representación es opcional y debe identificar las dos partes originales;
no modifica el emisor derivado. Los nombres de la representación no son nombres
de representantes personales. Los representantes del emisor conservan su orden.
Las observaciones `additional_notes` van al final, incluidas las repetidas.

## Orden de las notas

R = representación; T = manifestación de terminación; A = ratificación;
P = constancia de ausencia de actos pendientes. El número indica posición XML,
sin insertar notas vacías. Las observaciones adicionales siguen estas notas.

| Caso | Emisor / representante de la base | Orden |
| --- | --- | --- |
| T441-SIN-SIN | Mandante / Ana Ejemplo | 1 T |
| T441-SIN-CON | Mandante / Ana Ejemplo | 1 T, 2 A |
| T441-CON-SIN | Mandante / Ana Ejemplo | 1 R, 2 T |
| T441-CON-CON | Mandante / Ana Ejemplo | 1 R, 2 A, 3 T |
| T442-SIN | Mandatario / Luis Sintético | 1 T, 2 P |
| T442-CON | Mandatario / Luis Sintético | 1 R, 2 P, 3 T |
| T443-SIN | Mandante / Ana Ejemplo | 1 T |
| T443-CON | Mandante / Ana Ejemplo | 1 R, 2 T |

Los siguientes XML son **fragmentos del documento**, no XML para transmitir.
Muestran operación, identidad y personas del emisor, referencia original y todas
las notas en orden. Cada `cbc:Note` procede de `declaration` y de las partes y
referencia del evento; véase [notas y migración](mandate/notes.md).
Las decisiones ante discrepancias (incluido 443 y el literal `Terminacion del
Mandato`) se explican en la [matriz de conformidad](../technical/mandate-conformance.md).

## T441-SIN-SIN

| Condición | Valor |
| --- | --- |
| Operación / emisor | 441 / Mandante |
| Representación / ratificación | Sin representación / sin ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T441-SIN-SIN",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REVOCATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>441</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Manifiesto la revocación del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

## T441-SIN-CON

| Condición | Valor |
| --- | --- |
| Operación / emisor | 441 / Mandante |
| Representación / ratificación | Sin representación / con ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T441-SIN-CON",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REVOCATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        ratify_acts=True,
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>441</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Manifiesto la revocación del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Ratifico los actos realizados por el mandatario en virtud del mandato identificado.</cbc:Note>
```

## T441-CON-SIN

| Condición | Valor |
| --- | --- |
| Operación / emisor | 441 / Mandante |
| Representación / ratificación | Con representación / sin ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T441-CON-SIN",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REVOCATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        representation=MandateRepresentation(
            mandatee_name=mandatee_legal.name,
            mandator_name=mandator.name,
        ),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>441</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Mandatario Sintético SAS OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Manifiesto la revocación del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

## T441-CON-CON

| Condición | Valor |
| --- | --- |
| Operación / emisor | 441 / Mandante |
| Representación / ratificación | Con representación / con ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T441-CON-CON",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REVOCATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        ratify_acts=True,
        representation=MandateRepresentation(
            mandatee_name=mandatee_legal.name,
            mandator_name=mandator.name,
        ),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>441</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Mandatario Sintético SAS OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Ratifico los actos realizados por el mandatario en virtud del mandato identificado.</cbc:Note>
```

<!-- xml-path: cbc:Note[3] -->

```xml
<cbc:Note>Manifiesto la revocación del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

## T442-SIN

| Condición | Valor |
| --- | --- |
| Operación / emisor | 442 / Mandatario |
| Representación / ratificación | Sin representación / sin ratificación |
| Actos pendientes | Constancia explícita no_pending_acts=True |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T442-SIN",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_RESIGNATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        no_pending_acts=True,
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>442</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandatario Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="1" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000002</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000002</cbc:ID>
    <cbc:FirstName>Luis</cbc:FirstName>
    <cbc:FamilyName>Sintético</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Mandatos</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Manifiesto la renuncia del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Dejo constancia de que no se encuentra pendiente de ejecución ningún acto en virtud del mandato que se termina.</cbc:Note>
```

## T442-CON

| Condición | Valor |
| --- | --- |
| Operación / emisor | 442 / Mandatario |
| Representación / ratificación | Con representación / sin ratificación |
| Actos pendientes | Constancia explícita no_pending_acts=True |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T442-CON",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_RESIGNATION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        no_pending_acts=True,
        representation=MandateRepresentation(
            mandatee_name=mandatee_legal.name,
            mandator_name=mandator.name,
        ),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>442</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandatario Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="1" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000002</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000002</cbc:ID>
    <cbc:FirstName>Luis</cbc:FirstName>
    <cbc:FamilyName>Sintético</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Mandatos</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Mandatario Sintético SAS OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Dejo constancia de que no se encuentra pendiente de ejecución ningún acto en virtud del mandato que se termina.</cbc:Note>
```

<!-- xml-path: cbc:Note[3] -->

```xml
<cbc:Note>Manifiesto la renuncia del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

## T443-SIN

| Condición | Valor |
| --- | --- |
| Operación / emisor | 443 / Mandante |
| Representación / ratificación | Sin representación / sin ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T443-SIN",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REJECTION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>443</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Manifiesto rechazo del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```

## T443-CON

| Condición | Valor |
| --- | --- |
| Operación / emisor | 443 / Mandante |
| Representación / ratificación | Con representación / sin ratificación |
| Actos pendientes | no_pending_acts=None (predeterminado) |
| Mandato / fecha efectiva | MANDATO-ORIGINAL-1, CUDE ficticio de 96 caracteres `c` / 24-10-2026 |

Copie una base común nueva antes de este caso.

```python
event = MandateTerminationEvent(
    header=RadianEventHeader(
        event_number="T443-CON",
        issue_date=date(2026, 10, 23),
        issue_time=time(11, 0),
        notes=(),
    ),
    operation_type=RadianOperationType.MANDATE_REJECTION,
    mandator_party=mandator,
    mandatee_party=mandatee_legal,
    reference=original_mandate,
    declaration=MandateTerminationDeclaration(
        effective_date=date(2026, 10, 24),
        representation=MandateRepresentation(
            mandatee_name=mandatee_legal.name,
            mandator_name=mandator.name,
        ),
    ),
)
```

<!-- xml-path: cbc:CustomizationID -->

```xml
<cbc:CustomizationID>443</cbc:CustomizationID>
```

<!-- xml-path: cac:SenderParty -->

```xml
<cac:SenderParty>
  <cac:PartyTaxScheme>
    <cbc:RegistrationName>Mandante Sintético SAS</cbc:RegistrationName>
    <cbc:CompanyID schemeName="31" schemeID="2" schemeAgencyID="195" schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)" schemeVersionID="1">900000001</cbc:CompanyID>
    <cac:TaxScheme>
      <cbc:ID>01</cbc:ID>
      <cbc:Name>IVA</cbc:Name>
    </cac:TaxScheme>
  </cac:PartyTaxScheme>
  <cac:Person>
    <cbc:ID schemeName="13">100000001</cbc:ID>
    <cbc:FirstName>Ana</cbc:FirstName>
    <cbc:FamilyName>Ejemplo</cbc:FamilyName>
    <cbc:JobTitle>Representante Legal</cbc:JobTitle>
    <cbc:NationalityID>CO</cbc:NationalityID>
    <cbc:OrganizationDepartment>Legal</cbc:OrganizationDepartment>
  </cac:Person>
</cac:SenderParty>
```

<!-- xml-path: cac:DocumentResponse -->

```xml
<cac:DocumentResponse>
  <cac:Response>
    <cbc:ResponseCode>044</cbc:ResponseCode>
    <cbc:Description>Terminacion del Mandato</cbc:Description>
  </cac:Response>
  <cac:DocumentReference>
    <cbc:ID>MANDATO-ORIGINAL-1</cbc:ID>
    <cbc:UUID schemeName="CUDE-SHA384">cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc</cbc:UUID>
    <cbc:DocumentTypeCode>96</cbc:DocumentTypeCode>
  </cac:DocumentReference>
</cac:DocumentResponse>
```

<!-- xml-path: cbc:Note[1] -->

```xml
<cbc:Note>Mandatario Sintético SAS OBRANDO EN NOMBRE Y REPRESENTACION DE Mandante Sintético SAS</cbc:Note>
```

<!-- xml-path: cbc:Note[2] -->

```xml
<cbc:Note>Manifiesto rechazo del mandato MANDATO-ORIGINAL-1, CUDE cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc, conferido por Mandante Sintético SAS a Mandatario Sintético SAS, con efectos a partir de 2026-10-24.</cbc:Note>
```
