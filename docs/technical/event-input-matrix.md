# Matriz completa de entradas de eventos

Esta referencia describe la API de **0.7.2**, que amplía los modelos de 0.7.1.
Cada campo constructor de las clases públicas de emisión tiene una correspondencia
abajo. Los nombres de grupo se interpretan dentro del contexto de la clase; un
componente repetido conserva todos sus elementos, en orden y con duplicados.
Los atributos fijos y valores derivados se detallan al final.

No se utiliza un diccionario de XML libre ni fragmentos etree en modelos públicos.
Los objetos se entregan a `prepare_radian_event(event=..., software=...)` en ambos
clientes; `send_radian_event` recibe el mismo `PreparedRadianEvent` y ZIP originales.
No se importan XML existentes ni se generan facturas o eventos DIAN 02/04.

## Perfiles, cardinalidades y fuentes

| Eventos / operaciones | Clase de entrada | Grupos y condiciones | Generación / rechazo RADIAN 1.1 salvo FE |
| --- | --- | --- | --- |
| 030–034 | InvoiceResponseEvent | Un DocumentResponse y referencia; persona en 030/032, motivo en 031; receptor DIAN en 034 | FE §§6.5.4–6.5.5.7 y 8.5.3–8.6.3 |
| 035 | GuaranteeEvent | Avalistas y compromisos; avalados opcionales y repetibles; cero significa cobertura total | §§7.2.5.3 y 9.2.4, pp.105–116/340–345 |
| 036 / 361–364 | RadianRegistrationEvent | Un bloque; comprador directo solo 362/364; condiciones de pago opcionales | §§7.2.5.4 y 9.2.5, pp.116–125/346–349 |
| 037 / 371–372 | EndorsementEvent | Completo/en blanco; identidades y participaciones; deudores; factor opcional en endosatario | §§7.2.5.5 y 9.2.6, pp.125–136/350–355 |
| 038–039 | EndorsementEvent | Completo/en blanco; negociación sin campos de venta; vencimiento/deudores opcionales | §§7.2.5.6–7 y 9.2.7–8, pp.136–160/356–368 |
| 040 / 401–403 | EndorsementCancellationEvent | Referencia CUDE/96; identidades tributarias adicionales del generador; revocatoria de procuración en 402 | §§7.2.5.8 y 9.2.9, pp.160–168/369–371 |
| 041 / 411–412 | CirculationRestrictionEvent | responses 1..N; references 1..N por respuesta; PDF y funcionarios propios por referencia | §§7.2.5.9 y 9.2.10; AAH01 p.173, AAH05 p.174 |
| 042 / 421–422 | CirculationRestrictionTerminationEvent | responses 1..N; exactamente una referencia CUDE/96 por respuesta y su evidencia | §§7.2.5.10 y 9.2.11; AAH01 p.182, AAH05 p.183 |
| 043 / 431–434 | MandateEvent | Variantes de poder, tiempo y referencias; representantes/notarios 1..N; bloques de facultades; aceptación y soportes | §§7.2.5.11 y 9.2.12, pp.186–214/381–393 |
| 044 / 441–443 | MandateTerminationEvent | Referencia al mandato, representantes 1..N, declaraciones por operación | §§7.2.5.12 y 9.2.13, pp.214–222/393–396 |
| 045 / 451–452 | InvoicePaymentEvent | Un pagador legal; identidades tributarias adicionales; importes y saldo; listID independiente de parcial/total | §§7.2.5.13 y 9.2.14, pp.222–231/397–401 |
| 046 | PaymentReportEvent | Generador con identidades adicionales; deudor, valor y vencimiento | §§7.2.5.14 y 9.2.15, pp.231–239/402–404 |
| 047 | EndorsementEvent | Completo posterior al vencimiento; venta, deudores y factor opcional; sin responsabilidad cuando se declare | §§7.2.5.15 y 9.2.16, pp.239–250/405–410 |
| 048 / 481–482 | ProtestEvent | responses 1..N; references 1..N y un acta por respuesta; aceptación solo en 481 | §§7.2.5.16 y 9.2.17; AAH01/05 p.257 y AAI78 p.258 |
| 049 / 491–494 | EconomicRightsTransferEvent | Cedentes/cesionarios, deudores, negociación, juramento y vencimiento | §§7.2.5.17 y 9.2.18, pp.261–272/416–421 |
| 050 | EconomicRightsNotificationEvent | Generador con identidades adicionales; referencia de factura y receptor deudor | §§7.2.5.18 y 9.2.19, pp.272–280/422–424 |
| 051 / 511–512 | EconomicRightsPaymentEvent | Un pagador legal; identidades tributarias adicionales; fecha y ecuación de saldo | §§7.2.5.19 y 9.2.20, pp.280–289/425–429 |

Las fechas de final de una tabla pueden compartir página con la tabla siguiente.
En 041/042/048 la propiedad `reference` consulta la primera referencia, seleccionada
por los XPath CUDE/QR del anexo; no elimina las demás ni es un argumento constructor.
Los valores financieros de la extensión son globales del documento, como en el
anexo; no se duplican ni se calculan valores por referencia no prescritos.

## Campos Python y correspondencias XML

Las tablas siguientes cubren todos los argumentos constructor de las clases de
emisión. La [referencia de modelos](../models.md) describe fechas, Decimal y tipos;
las [notas tipadas](../operations/event-notes.md) describen todas las alternativas,
condiciones, posiciones y excepciones normativas. La representación del propósito
es exclusivamente de dominio: `EventNote.kind` nunca se emite como atributo XML.

### CirculationRestrictionEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `authorities` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] |
| `responses` | `tuple[radiankore.models.events.restrictions.CirculationRestrictionResponse, ...]` | cac:DocumentResponse[] |
| `measure_value` | `<class 'decimal.Decimal'>` | InformacionMedidaCautelar / MontoMedidaCautelar |

### CirculationRestrictionResponse

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `references` | `tuple[radiankore.models.events.restrictions.RestrictionDocumentReference, ...]` | cac:DocumentReference[] |

### CirculationRestrictionTerminationEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `authorities` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] |
| `responses` | `tuple[radiankore.models.events.restrictions.CirculationRestrictionTerminationResponse, ...]` | cac:DocumentResponse[] |
| `debt_value` | `<class 'decimal.Decimal'>` | InformacionMedidaCautelar / ValorDeuda |
| `restriction_value` | `<class 'decimal.Decimal'>` | InformacionMedidaCautelar / ValorLimitación |

### CirculationRestrictionTerminationResponse

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `reference` | `<class 'radiankore.models.events.restrictions.RestrictionDocumentReference'>` | cac:DocumentReference (componente tipado) |

### EconomicRightsNotificationEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `sender_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:SenderParty |
| `receiver_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:ReceiverParty |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `current_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorActualTituloValor o ValorFEV-TV (050) |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### EconomicRightsPaymentEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `payer` | `<class 'radiankore.models.events.radian_common.RadianParticipation'>` | cac:SenderParty/cac:PartyLegalEntity (único) |
| `restriction` | `<enum 'PaymentRestriction'>` | cac:Response/cbc:ResponseCode/@listID |
| `effective_date` | `<class 'datetime.date'>` | cac:Response/cbc:EffectiveDate (contexto del componente) |
| `current_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorActualTituloValor o ValorFEV-TV (050) |
| `remaining_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorPendienteTituloValor |
| `currency` | `<enum 'CurrencyCode'>` | cbc:CorporateStockAmount/@currencyID y valores de extensión |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### EconomicRightsTransferEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `transferors` | `tuple[radiankore.models.events.radian_common.RadianParticipation, ...]` | cac:SenderParty: identidades y participaciones |
| `transferees` | `tuple[radiankore.models.events.radian_common.RadianParticipation, ...]` | cac:ReceiverParty: identidades y participaciones |
| `debtors` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme[] |
| `terms` | `<class 'radiankore.models.events.economic_rights.EconomicRightsTransferTerms'>` | InformacionTransferenciaDerechos / EconomicRightsTransferTerms |

### EconomicRightsTransferTerms

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `transferred_value` | `<class 'decimal.Decimal'>` | ValorTransferenciaDerechos |
| `price` | `<class 'decimal.Decimal'>` | PrecioPagarseFEV |
| `discount_factor` | `<class 'decimal.Decimal'>` | FactordeDescuento |
| `payment_means` | `<enum 'PaymentMeans'>` | MedioPago |
| `currency` | `<enum 'CurrencyCode'>` | cbc:CorporateStockAmount/@currencyID y valores de extensión |

### EndorsementCancellationEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `sender_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:SenderParty |
| `receiver_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:ReceiverParty |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianEventReference'>` | cac:DocumentReference (componente tipado) |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### EndorsementEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `form` | `<enum 'EndorsementForm'>` | cac:Response/cbc:ResponseCode/@listID (completo/en blanco) |
| `endorsers` | `tuple[radiankore.models.events.radian_common.RadianParticipation, ...]` | cac:SenderParty: identidades y participaciones |
| `endorsees` | `tuple[radiankore.models.events.radian_common.RadianParticipation, ...]` | cac:ReceiverParty: identidades y participaciones |
| `negotiation` | `<class 'radiankore.models.events.endorsements.NegotiationTerms'>` | InformacionNegociacion / NegotiationTerms |
| `debtors` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme[] |

### EventNote

ApplicationResponse/Note / AAD11 y variantes

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `kind` | `<enum 'EventNoteKind'>` | propósito de dominio: selecciona condición/posición; no es atributo XML |
| `text` | `<class 'str'>` | cbc:Note/text() |

### GuaranteeBeneficiary

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | PartyLegalEntity del avalado |
| `amount` | `decimal.Decimal \| None` | cbc:CorporateStockAmount (obligatorio para varios avalados) |

### GuaranteeCommitment

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | PartyTaxScheme y PartyLegalEntity del avalista |
| `amount` | `<class 'decimal.Decimal'>` | cbc:CorporateStockAmount (0.00 significa total) |

### GuaranteeEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `title_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorFEV-TV o ValorFEVavala |
| `guarantors` | `tuple[radiankore.models.events.guarantees.GuaranteeCommitment, ...]` | cac:SenderParty: identidades y participaciones |
| `beneficiaries` | `tuple[radiankore.models.events.guarantees.GuaranteeBeneficiary, ...]` | cac:DocumentResponse/cac:IssuerParty/cac:PartyLegalEntity[] |
| `currency` | `<enum 'CurrencyCode'>` | cbc:CorporateStockAmount/@currencyID y valores de extensión |

### InvoiceEventDocumentReference

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `document_number` | `<class 'str'>` | cbc:ID |
| `uuid` | `<class 'str'>` | cbc:UUID |
| `document_type` | `<enum 'DocumentType'>` | cbc:DocumentTypeCode |

### InvoiceEventParty

PartyTaxScheme / FE AAF02–11 y AAG02–11

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `name` | `<class 'str'>` | cbc:RegistrationName |
| `tax_number` | `<class 'str'>` | cbc:CompanyID |
| `identification_type` | `<enum 'IdentificationType'>` | cbc:CompanyID/@schemeName |
| `organization_type` | `<enum 'OrganizationType'>` | cbc:CompanyID/@schemeVersionID |
| `verification_digit` | `str \| None` | cbc:CompanyID/@schemeID |
| `tax_scheme` | `radiankore.catalogs.parties.PartyTaxScheme \| radiankore.models.events.tax_details.RadianTaxDetails` | cac:TaxScheme (RadianTaxDetails o par de catálogo) |

### InvoiceEventPerson

IssuerParty/Person / FE 030 y 032

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `identification_number` | `<class 'str'>` | cbc:ID |
| `identification_type` | `<enum 'IdentificationType'>` | cbc:ID/@schemeName |
| `first_name` | `<class 'str'>` | cbc:FirstName |
| `family_name` | `<class 'str'>` | cbc:FamilyName |
| `verification_digit` | `str \| None` | cbc:ID/@schemeID |
| `job_title` | `str \| None` | cbc:JobTitle |
| `organization_department` | `str \| None` | cbc:OrganizationDepartment |

### InvoicePaymentEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `payer` | `<class 'radiankore.models.events.radian_common.RadianParticipation'>` | cac:SenderParty/cac:PartyLegalEntity (único) |
| `restriction` | `<enum 'PaymentRestriction'>` | cac:Response/cbc:ResponseCode/@listID |
| `effective_date` | `<class 'datetime.date'>` | cac:Response/cbc:EffectiveDate (contexto del componente) |
| `current_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorActualTituloValor o ValorFEV-TV (050) |
| `remaining_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorPendienteTituloValor |
| `currency` | `<enum 'CurrencyCode'>` | cbc:CorporateStockAmount/@currencyID y valores de extensión |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### InvoiceResponseEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `code` | `<enum 'EventType'>` | cac:DocumentResponse/cac:Response/cbc:ResponseCode |
| `event_number` | `<class 'str'>` | cbc:ID |
| `issue_date` | `<class 'datetime.date'>` | cbc:IssueDate |
| `issue_time` | `<class 'datetime.time'>` | cbc:IssueTime |
| `sender_party` | `<class 'radiankore.models.events.invoice.InvoiceEventParty'>` | cac:SenderParty |
| `document_reference` | `<class 'radiankore.models.events.invoice.InvoiceEventDocumentReference'>` | cac:DocumentResponse/cac:DocumentReference |
| `receiver_party` | `radiankore.models.events.invoice.InvoiceEventParty \| None` | cac:ReceiverParty |
| `issuer_person` | `radiankore.models.events.invoice.InvoiceEventPerson \| None` | cac:DocumentResponse/cac:IssuerParty/cac:Person (030/032) |
| `claim_reason` | `radiankore.catalogs.invoice_events.InvoiceClaimReason \| None` | cac:Response/cbc:ResponseCode/@listID y @name (031) |
| `notes` | `tuple[radiankore.models.events.notes.EventNote, ...]` | cbc:Note[] / EventNote |

### MandateAttachedDocument

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `document_id` | `<class 'str'>` | cac:LineReference/cac:DocumentReference/cbc:ID |
| `embedded_bytes` | `<class 'bytes'>` | cbc:EmbeddedDocumentBinaryObject/text() codificado Base64 |
| `issuers` | `tuple[radiankore.models.events.mandate.MandateNotary, ...]` | cac:LineReference/cac:DocumentReference/cac:IssuerParty/cac:Person[] |
| `effective_date` | `datetime.date \| None` | cac:LineResponse/cac:Response/cbc:EffectiveDate (contrato) |

### MandateDocumentReference

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `document_number` | `<class 'str'>` | cbc:ID |
| `uuid` | `<class 'str'>` | cbc:UUID |
| `document_type` | `<enum 'DocumentType'>` | cbc:DocumentTypeCode (01, derivado) |
| `scope` | `radiankore.models.events.mandate.MandateScope \| None` | selecciona DocumentResponse adicional por facultades |

### MandateEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `operation_type` | `<enum 'MandateOperationType'>` | cbc:CustomizationID |
| `nature` | `<enum 'MandateNature'>` | cbc:CustomizationID/@schemeID |
| `reference_type` | `<enum 'MandateReferenceType'>` | cac:Response/cbc:ResponseCode/@listID |
| `event_number` | `<class 'str'>` | cbc:ID |
| `issue_date` | `<class 'datetime.date'>` | cbc:IssueDate |
| `issue_time` | `<class 'datetime.time'>` | cbc:IssueTime |
| `declaration` | `<class 'radiankore.models.events.mandate.MandateDeclaration'>` | cbc:Note: declaraciones generadas |
| `sender_party` | `<class 'radiankore.models.events.mandate.MandateParty'>` | cac:SenderParty |
| `mandatee_party` | `<class 'radiankore.models.events.mandate.MandateParty'>` | cac:DocumentResponse/cac:IssuerParty/cac:PowerOfAttorney |
| `effective_date` | `<class 'datetime.date'>` | cac:Response/cbc:EffectiveDate (contexto del componente) |
| `document_references` | `tuple[radiankore.models.events.mandate.MandateDocumentReference, ...]` | cac:DocumentReference[] en bloque principal y bloques de facultades |
| `validity_period` | `<class 'radiankore.models.events.mandate.MandateValidityPeriod'>` | cac:DocumentReference/cac:ValidityPeriod |
| `scope` | `<class 'radiankore.models.events.mandate.MandateScope'>` | cac:DocumentResponse[] de facultades |
| `attached_contract` | `<class 'radiankore.models.events.mandate.MandateAttachedDocument'>` | cac:LineResponse con LineID=1 |
| `acceptance` | `<class 'bool'>` | cac:LineResponse/cac:Response/cbc:ResponseCode=ACEPTA |
| `attached_validity_note` | `radiankore.models.events.mandate.MandateAttachedDocument \| None` | cac:LineResponse con LineID=2 (poder general) |
| `additional_notes` | `tuple[radiankore.models.events.notes.EventNote, ...]` | cbc:Note adicionales después de declaraciones |

### MandateParty

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `name` | `<class 'str'>` | cbc:RegistrationName del mandante; el nombre del mandatario interviene en la declaración generada |
| `tax_number` | `<class 'str'>` | cac:PowerOfAttorney/cbc:ID y CompanyID del mandante |
| `identification_type` | `<enum 'IdentificationType'>` | ID/CompanyID/@schemeName |
| `role` | `radiankore.catalogs.mandates.MandatorType \| radiankore.catalogs.mandates.MandateeType` | cac:PowerOfAttorney/cac:AgentParty/cac:PartyIdentification/cbc:ID y Description derivada |
| `representatives` | `tuple[radiankore.models.events.mandate.MandatePerson, ...]` | cac:SenderParty/cac:Person[] o cac:PowerOfAttorney/cac:AgentParty/cac:Person[] |
| `verification_digit` | `str \| None` | ID/CompanyID/@schemeID |
| `organization_type` | `<enum 'OrganizationType'>` | CompanyID/@schemeVersionID del mandante; selecciona declaración del mandatario |
| `tax_scheme` | `radiankore.catalogs.parties.PartyTaxScheme \| radiankore.models.events.tax_details.RadianTaxDetails` | cac:PartyTaxScheme/cac:TaxScheme del mandante |

### MandatePerson

Person del mandante, agente o notario / AAF22–30, AAH69–77, AAH95–ABH27

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `identification_number` | `<class 'str'>` | cbc:ID |
| `identification_type` | `<enum 'IdentificationType'>` | cbc:ID/@schemeName |
| `first_name` | `<class 'str'>` | cbc:FirstName |
| `family_name` | `<class 'str'>` | cbc:FamilyName |
| `nationality_id` | `<class 'str'>` | cbc:NationalityID |
| `organization_department` | `<class 'str'>` | cbc:OrganizationDepartment |
| `job_title` | `<class 'str'>` | cbc:JobTitle |
| `verification_digit` | `str \| None` | cbc:ID/@schemeID |

### MandateRepresentation

AAD11 de representación; en 043 se genera siempre antes de su declaración particular;
en 044 se aporta opcionalmente en `declaration.representation`.

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `mandatee_name` | `<class 'str'>` | cbc:Note: nombre anterior a la frase fija |
| `mandator_name` | `<class 'str'>` | cbc:Note: nombre posterior a la frase fija |

### MandateScope

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `powers` | `tuple[tuple[radiankore.catalogs.mandates.MandatePower, radiankore.catalogs.mandates.MandateChannel], ...]` | cac:Response/cbc:ResponseCode; Description derivada de catálogo |

### MandateTerminationEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `mandator_party` | `<class 'radiankore.models.events.mandate.MandateParty'>` | SenderParty en 441/443 y notas de terminación |
| `mandatee_party` | `<class 'radiankore.models.events.mandate.MandateParty'>` | SenderParty en 442 y notas de terminación |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianEventReference'>` | cac:DocumentReference (componente tipado) |
| `declaration` | `<class 'radiankore.models.events.mandate_termination.MandateTerminationDeclaration'>` | cbc:Note: declaraciones generadas |
| `additional_notes` | `tuple[radiankore.models.events.notes.EventNote, ...]` | cbc:Note adicionales después de declaraciones |

### MandateValidityPeriod

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `start_date` | `datetime.date \| None` | cbc:StartDate |
| `end_date` | `datetime.date \| None` | cbc:EndDate |

### NegotiationTerms

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `total_value` | `<class 'decimal.Decimal'>` | ValorTotalEndoso |
| `price` | `decimal.Decimal \| None` | PrecioPagarseFEV (037/047) |
| `discount_rate` | `decimal.Decimal \| None` | TasaDescuento (037/047) |
| `payment_means` | `radiankore.catalogs.radian.PaymentMeans \| None` | MedioPago (037/047) |
| `currency` | `<enum 'CurrencyCode'>` | cbc:CorporateStockAmount/@currencyID y valores de extensión |

### PaymentReportEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `sender_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:SenderParty |
| `receiver_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:ReceiverParty |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `title_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorFEV-TV o ValorFEVavala |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### ProtestAct

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `notary_number` | `<class 'str'>` | cac:LineReference/cac:DocumentReference/cbc:ID |
| `effective_date` | `<class 'datetime.date'>` | cac:LineResponse/cac:Response/cbc:EffectiveDate |
| `notaries` | `tuple[radiankore.models.events.protests.ProtestNotary, ...]` | cac:LineReference/cac:DocumentReference/cac:IssuerParty/cac:Person[] |
| `attachment` | `<class 'radiankore.models.events.attachments.RadianPdfAttachment'>` | cac:Attachment / RadianPdfAttachment |

### ProtestDocumentResponse

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `references` | `tuple[radiankore.models.events.radian_common.RadianInvoiceReference, ...]` | cac:DocumentReference[] |
| `act` | `<class 'radiankore.models.events.protests.ProtestAct'>` | cac:LineResponse / ProtestAct |

### ProtestEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `sender_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:SenderParty |
| `receiver_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:ReceiverParty |
| `responses` | `tuple[radiankore.models.events.protests.ProtestDocumentResponse, ...]` | cac:DocumentResponse[] |
| `title_value` | `<class 'decimal.Decimal'>` | extensión propia / ValorFEV-TV o ValorFEVavala |
| `acceptance_failure` | `radiankore.catalogs.radian.AcceptanceFailureType \| None` | cbc:CustomizationID/@schemeID (solo 481) |
| `accepted_value` | `decimal.Decimal \| None` | InformacionProtesto / ValorAceptado (solo 481) |
| `pending_value` | `decimal.Decimal \| None` | InformacionProtesto / ValorPendiente (solo 481) |
| `additional_sender_parties` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:SenderParty/cac:PartyTaxScheme[] después de la primera identidad |

### ProtestNotary

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `first_name` | `<class 'str'>` | cbc:FirstName |
| `family_name` | `<class 'str'>` | cbc:FamilyName |
| `job_title` | `<class 'str'>` | cbc:JobTitle |

### RadianEventHeader

ApplicationResponse / AAD05, AAD09–11

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `event_number` | `<class 'str'>` | cbc:ID |
| `issue_date` | `<class 'datetime.date'>` | cbc:IssueDate |
| `issue_time` | `<class 'datetime.time'>` | cbc:IssueTime |
| `notes` | `tuple[radiankore.models.events.notes.EventNote, ...]` | cbc:Note[] / EventNote |

### RadianEventReference

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `document_number` | `<class 'str'>` | cbc:ID |
| `uuid` | `<class 'str'>` | cbc:UUID |

### RadianInvoiceReference

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `document_number` | `<class 'str'>` | cbc:ID |
| `uuid` | `<class 'str'>` | cbc:UUID |
| `due_date` | `datetime.date \| None` | cac:ValidityPeriod/cbc:EndDate |

### RadianParticipation

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `amount` | `<class 'decimal.Decimal'>` | cbc:CorporateStockAmount |
| `party` | `radiankore.models.events.radian_common.RadianParty \| None` | identidad en PartyTaxScheme y PartyLegalEntity; ausente en endosante en blanco |
| `factor_type` | `radiankore.catalogs.radian.FactorType \| None` | cbc:CompanyLegalFormCode (solo endosatarios 037/047) |

### RadianParty

PartyTaxScheme / AAF02–11, AAG02–11, AAH22–44

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `tax_number` | `<class 'str'>` | cbc:CompanyID |
| `identification_type` | `<enum 'IdentificationType'>` | cbc:CompanyID/@schemeName |
| `organization_type` | `<enum 'OrganizationType'>` | cbc:CompanyID/@schemeVersionID |
| `name` | `str \| None` | cbc:RegistrationName |
| `verification_digit` | `str \| None` | cbc:CompanyID/@schemeID |
| `tax_scheme` | `radiankore.catalogs.parties.PartyTaxScheme \| radiankore.models.events.tax_details.RadianTaxDetails` | cac:TaxScheme (RadianTaxDetails o par de catálogo) |

### RadianPdfAttachment

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `filename` | `<class 'str'>` | cbc:EmbeddedDocumentBinaryObject/@filename |
| `content_bytes` | `<class 'bytes'>` | cbc:EmbeddedDocumentBinaryObject/text() codificado Base64 |

### RadianPerson

Person / 044 AAF40–48

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `identification_number` | `<class 'str'>` | cbc:ID |
| `identification_type` | `<enum 'IdentificationType'>` | cbc:ID/@schemeName |
| `first_name` | `<class 'str'>` | cbc:FirstName |
| `family_name` | `<class 'str'>` | cbc:FamilyName |
| `verification_digit` | `str \| None` | cbc:ID/@schemeID |
| `job_title` | `str \| None` | cbc:JobTitle |
| `nationality_id` | `str \| None` | cbc:NationalityID |
| `organization_department` | `str \| None` | cbc:OrganizationDepartment |

### RadianRegistrationEvent

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `header` | `<class 'radiankore.models.events.radian_common.RadianEventHeader'>` | cabecera ApplicationResponse / RadianEventHeader |
| `operation_type` | `<enum 'RadianOperationType'>` | cbc:CustomizationID |
| `sender_party` | `<class 'radiankore.models.events.radian_common.RadianParty'>` | cac:SenderParty |
| `reference` | `<class 'radiankore.models.events.radian_common.RadianInvoiceReference'>` | cac:DocumentReference (componente tipado) |
| `payment_state` | `<class 'radiankore.models.events.registration.RegistrationPaymentState'>` | ConstanciadePagos / RegistrationPaymentState |
| `direct_buyer` | `radiankore.models.events.radian_common.RadianParty \| None` | cac:DocumentResponse/cac:IssuerParty/cac:PartyLegalEntity |

### RadianSoftware

DianExtensions y firma / AAB19–28, DC56

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `software_id` | `<class 'str'>` | sts:SoftwareProvider/sts:SoftwareID |
| `pin` | `<class 'str'>` | solo entrada de hash CUDE y SoftwareSecurityCode; no se serializa |
| `provider_tax_number` | `<class 'str'>` | sts:SoftwareProvider/sts:ProviderID |
| `provider_verification_digit` | `<class 'str'>` | sts:ProviderID/@schemeID |
| `signer_role` | `typing.Literal['supplier', 'thirdparty']` | xades:SignerRole/xades:ClaimedRoles/xades:ClaimedRole |

### RadianTaxDetails

TaxScheme / AAF09–11 y equivalentes por participante

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `code` | `radiankore.catalogs.parties.PartyTaxScheme \| None` | cbc:ID (opcional) |
| `name` | `str \| None` | cbc:Name (opcional) |

### RegistrationPaymentState

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `invoice_value` | `<class 'decimal.Decimal'>` | ValorFEV-TV |
| `paid_value` | `<class 'decimal.Decimal'>` | ValorPagado |
| `remaining_value` | `<class 'decimal.Decimal'>` | NuevoValorTV |

### RestrictionDocumentReference

Perfil de su familia; véase la tabla de eventos

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `reference` | `radiankore.models.events.radian_common.RadianInvoiceReference \| radiankore.models.events.radian_common.RadianEventReference` | cac:DocumentReference (componente tipado) |
| `officials` | `tuple[radiankore.models.events.radian_common.RadianParty, ...]` | cac:IssuerParty/cac:PartyTaxScheme[] |
| `attachment` | `<class 'radiankore.models.events.attachments.RadianPdfAttachment'>` | cac:Attachment / RadianPdfAttachment |

## Atributos fijos y valores calculados

Estos datos también pertenecen a la estructura del XML; no necesitan fragmentos
aportados por la aplicación. Un literal obligatorio no se expone como texto libre.

| Elementos / atributos | Procedencia | Evidencia |
| --- | --- | --- |
| ApplicationResponse; namespaces AR, CAC, CBC, EXT, STS, DS y XAdES | Perfiles DIAN/UBL; secuencia de grupos fijada por XSD | `test_event_conformance`, firmas y pruebas XSD |
| UBLVersionID, ProfileID | Literales del perfil; FE usa «de Factura» y RADIAN «de la Factura» | AAD01/AAD03; oráculo independiente por código |
| ProfileExecutionID, UUID/@schemeID | `Environment`, coherente con el destino | Ambos ambientes en pruebas de preparación/envío |
| UUID, UUID/@schemeName | CUDE y literal CUDE-SHA384; perfil general, en blanco o mandato | Vectores oficiales, recomposición desde XML |
| CustomizationID y @schemeID de 043/048 | Operación, naturaleza del poder o falta de aceptación | Modelos y variantes completas |
| DianExtensions/InvoiceSource/IdentificationCode y @listAgencyID/@listAgencyName/@listSchemeURI | CO, 6, agencia y URI de lista prescritos | AAB04–09; `test_event_conformance` |
| SoftwareProvider/ProviderID y SoftwareID | `RadianSoftware`; atributos de identificación y agencia DIAN | AAB19–25; firma y pruebas de CUDE/código de seguridad |
| ProviderID/@schemeName/@schemeID/@schemeAgencyID/@schemeAgencyName; SoftwareID/@schemeAgencyID/@schemeAgencyName | NIT, DV y literales de agencia | Componentes comunes y pruebas de atributos |
| SoftwareSecurityCode, @schemeAgencyID/@schemeAgencyName | SHA384(software ID + PIN + número), agencia fija | AAB26–28; recomposición independiente |
| AuthorizationProvider/AuthorizationProviderID y atributos | DIAN 800197268, DV 4, identificación 31 y agencia fija | AAB30–34; oráculo de extensión |
| QRCode | Host del ambiente y clave de la primera referencia; en 043 CUDE propio | Pruebas de ambos ambientes |
| SenderParty/ReceiverParty/PartyTaxScheme/CompanyID y PartyLegalEntity/CompanyID, atributos de agencia | Identidad, DV, organización y agencia 195 con su nombre literal | AAF/AAG; orden identidades antes de participaciones |
| TaxScheme | El grupo se conserva; ID y Name pueden omitirse independientemente cuando el perfil lo permite | `RadianTaxDetails`; ausencia/presencia y XSD |
| ReceiverParty de DIAN en los perfiles correspondientes | Identidad y nombre literales; no modificables por la aplicación | Pruebas por evento y ambiente |
| ResponseCode, Description y atributos de motivo/forma/restricción | Código de evento, descripción obligatoria y catálogos separados | Oráculo independiente por evento |
| DocumentReference/DocumentTypeCode, UUID/@schemeName | 01 para factura RADIAN, 96 para evento; FE admite 01–04; CUFE/CUDE diferenciados | Pruebas de referencias incorrectas y signos serializados |
| Mandato: referencias ALL | ID 1; sin UUID ni DocumentTypeCode (tabla 14.2.6); entradas de hash conservan sus constantes | Modalidades ONE/MULTIPLE/ALL y CUDE oficial |
| PowerOfAttorney/Description, AgentParty/PartyIdentification/ID | Rol explícito y descripción del catálogo; se omite schemeDataURI en los identificadores del rol del mandante y del mandatario | 043, tablas 14.2.5/8 y pruebas de variantes |
| Mandato: ValidityPeriod/DescriptionCode/Description | Tipo de tiempo derivado de operación y fechas | 431–434; fechas ausentes/presentes |
| Mandato: bloques de facultades ResponseCode/Description y referencias | `MandateScope.powers`, agrupación estable por alcance, sin deduplicar referencias | Alcances individuales/comunes y XSD |
| Mandato: aceptación y LineID | ACEPTA y descripción obligatoria; LineID 1; aceptación explícita True | AAL09–14; las alternativas rechazadas no se generan |
| Mandato: adjuntos LineID/DocumentDescription/Response/Description | Literales de contrato y vigencia; LineID 1/2 | AAH78–ABH27; PDF y varios emisores |
| PDF: format, mimeCode, encodingCode, characterSetCode, filename | Metadatos específicos de 043, 041/042 o 048, sin unificación arbitraria | Pruebas de bytes, atributos y límites del XML firmado |
| Protesto: LineID, DocumentDescription y Response/Description | 1, Acta de Protesto y descripción prescrita | AAI78–95; un acta por bloque y varios notarios |
| CustomTagGeneral y pares Name/Value | Nombre, orden y cantidad por evento; Decimal sin redondeo | AAY–AAZD, validaciones de extensiones y mutaciones |
| ds:Signature, SignedInfo, Reference, KeyInfo, Object y xades:SignedProperties | Certificado del cliente, clave RSA, política fija, rol explícito y reloj real; IDs nuevos | Verificación criptográfica independiente después de serializar |
| SigningTime, SigningCertificate, política, SignerRole y DataObjectFormat; digests y SignatureValue | Implementación XAdES-EPES, no datos XML arbitrarios | `test_mandate_xml`, `test_signing`, `test_async_events` |

La [guía de comunicación y firmas](../guides/communication-and-signatures.md)
detalla los algoritmos, referencias, URIs y atributos de ambos perfiles de firma.
La firma SOAP no es parte del modelo de datos del evento; se genera al enviar.

## Cobertura y migración

El inventario de campos constructor se conserva también en
`tests/fixtures/event_input_fields.json`; su prueba documental exige correspondencia
con todos los campos públicos y con las tablas anteriores. No se obtiene de los
builders para decidir las reglas del anexo. Las pruebas de XML y sus oráculos
independientes comprueban los valores y estructuras, no solo los nombres Python.

Los casos máximos se comprueban en `test_complete_event_inputs`: referencias y
bloques repetidos, PDF diferente por referencia, varios representantes y notarios,
identidades tributarias adicionales sin participaciones inventadas y las cuatro
combinaciones de presencia de los hijos tributarios. La suite existente conserva
las operaciones, variantes en blanco, naturalezas/tiempos/alcances de 043, catálogos,
precisión Decimal, límites, respuestas, firmas y transmisión original.

Cambios incompatibles adicionales a las notas:

- `MandateParty(representatives=(persona, ...))` sustituye `representative`.
- `MandateAttachedDocument(issuers=(notario, ...))` sustituye `issuer`; `()` significa
  ausencia cuando el perfil lo permite. En poder general cada soporte requiere
  emisores y datos de notaría completos.
- 041 recibe `responses=(CirculationRestrictionResponse(references=(
  RestrictionDocumentReference(reference=..., officials=(...), attachment=...),
  ...)), ...)`. 042 usa `CirculationRestrictionTerminationResponse(reference=...)`.
- 048 recibe `responses=(ProtestDocumentResponse(references=(factura, ...),
  act=acta), ...)`. No se entrega `act` ni `reference` al evento raíz.
- `additional_sender_parties=()` agrega identidades después de la principal en
  040/045/046/048/050/051. No inventa participaciones ni cambia el primer NIT
  seleccionado para el CUDE. Una lista, elemento inválido o generador sin NIT
  se rechaza antes de serializar.
- `factor_type` corresponde a endosatarios 037/047. Otros participantes/perfiles
  lo rechazan, en lugar de emitir CompanyLegalFormCode fuera de su tabla.

## Alcance de la evidencia

Las [discrepancias del anexo](xml-conformance.md) y las de
[declaraciones](../operations/event-notes.md#fuentes-y-discrepancias) se conservan
explícitas. Se siguen reglas de rechazo y condiciones específicas de generación;
los ejemplos y XSD laxos no se interpretan como autorización para campos distintos.
Los originales no se modifican. No se consulta DIAN durante tests ni preparación.
Habilitación de participantes, confianza/vigencia de certificados, antecedentes,
facultades, plazos y verdad de las declaraciones requieren evidencia externa.

### MandateDeclaration

Mandatos 043/044: datos estructurados y notas generadas

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `declarant` | `<class 'radiankore.models.events.mandate.MandatePerson'>` | selección explícita de Person del mandatario; Note[2] |
| `contract_form` | `<enum 'MandateContractForm'>` | cbc:Note[2]: verbal o escrito |
| `chamber_of_commerce_city` | `str \| None` | cbc:Note[2]: Cámara de Comercio |

### MandateNotary

Mandatos 043/044: datos estructurados y notas generadas

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `identification_number` | `<class 'str'>` | cbc:ID (NIT, schemeName=31) |
| `verification_digit` | `<class 'str'>` | cbc:ID/@schemeID |
| `first_name` | `<class 'str'>` | cbc:FirstName |
| `family_name` | `<class 'str'>` | cbc:FamilyName |
| `job_title` | `<class 'str'>` | cbc:JobTitle |
| `office_number` | `<class 'str'>` | cbc:OrganizationDepartment (número de notaría) |

### MandateTerminationDeclaration

Mandatos 043/044: datos estructurados y notas generadas

| Campo | Tipo | Correspondencia / condición |
| --- | --- | --- |
| `effective_date` | `<class 'datetime.date'>` | cbc:Note: fecha efectiva de terminación |
| `ratify_acts` | `<class 'bool'>` | cbc:Note[2]: ratificación en 441 |
| `no_pending_acts` | `bool \| None` | cbc:Note[2]: constancia en 442 |
| `representation` | `radiankore.models.events.notes.MandateRepresentation \| None` | cbc:Note[1]: representación explícita |
