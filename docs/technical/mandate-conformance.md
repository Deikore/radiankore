# Conformidad de mandatos 043 y 044

Esta revisión se limita a RADIAN 1.1 conservado en el repositorio. Los originales
no se modifican. La numeración siguiente permite revisar cada fila de generación;
se contrasta con §9.2.12/13 y los catálogos, no con los ejemplos como autoridad.
La cobertura de código y el XSD no prueban por sí solos la conformidad semántica.

## Decisiones y responsables

| Reglas / fuente | Decisión implementada | Verificación |
| --- | --- | --- |
| §6.5 | El anexo prevalece sobre los ejemplos; reglas específicas sobre tablas generales | Regresiones independientes y ejemplos originales intactos |
| AAD01–10, AAD12 | Perfil, ambiente, fecha colombiana, número y naturaleza explícitos | Matriz XML firmada, ambos ambientes |
| AAD11b/c, p.190 | Declaración estructurada; representante explícito del mandatario; ciudad para persona jurídica; contrato verbal o escrito | Texto completo independiente, alternativas y errores de modelo |
| Note[2], p.190 | El SDK compone representación breve primero y declaración larga después; observaciones adicionales al final | No se acepta sustituir declaraciones por notas manuales |
| AAF22–30, AAH69–77, AAF40–48 | Representantes completos; cargo, nacionalidad y departamento obligatorios en los modelos de mandato | Obligatoriedad local más estricta que las notificaciones; otros eventos conservan sus contratos |
| §7.2.1.4.1.16, AAH94–ABH26 | Notario separado: NIT/DV, nombres, cargo y número de notaría; sin NationalityID adicional en su bloque XML | Soportes de GENERAL, fecha de escritura y dos PDF recuperables |
| AAH06/09 frente a 14.2.6 | ALL: ID=1, sin UUID ni DocumentTypeCode; ONE/MULTIPLE: factura 01 y CUFE | Matriz de cardinalidades, XSD y CUDE; constantes de hash 1 y 01 para ALL |
| AAH58–60, ABH29 | Fechas solo en 431/433; códigos 1/2 y literales exactos de vigencia | Todos los bloques y variantes |
| AAH85–89, ABH13–17 | Literales de rechazo PDF/base64, PDF prevalecen sobre las tablas de generación contradictorias | Atributos y bytes de soportes |
| AAL01–15 | Descripción fija General/Limitado; facultades por catálogo, MR91 primero, PT prohibido en R01–05, máximo 600 caracteres | Agrupación por alcance y referencias repetidas; aceptación `ACEPTA` |
| §7.2.5.12 y tabla14.1.2 | Emisor derivado: mandante en 441/443, mandatario en 442; referencia de mandato tipo96 | Matriz de terminación, CUDE y firma |
| p.217 frente a p.43; matriz U88/U89 | Constancia obligatoria en renuncia 442; ratificación opcional solo en revocación 441 | Hechos explícitos, sin afirmar ausencia de actos por defecto |
| §7.2.1.4.3.8 | Fecha efectiva obligatoria en declaración, expresada en nota; no inventar Response/EffectiveDate | Pruebas de fecha nativa y texto |
| §11–12, ZA01, §8.7 | Firma XAdES y SOAP verificadas sobre serialización; XML máximo 500000 bytes y ZIP original | MockTransport, envío sync/async y controles existentes de recursos |

## Inventario de filas de generación

Cada identificador se contextualiza por evento: un mismo ID puede tener condiciones
u obligatoriedad diferentes. Las cardinalidades y tamaños se consultan en la fila
original señalada. La columna de encabezado es una transcripción abreviada para
localizar el campo, no una sustitución de sus observaciones multilínea.

| Evento | Regla | Página | Encabezado de la fila |
| --- | --- | ---: | --- |
| 043 | AAA01 | 188 | Registro de–Eventos - ApplicationResponse (raíz) G 1.0 /ApplicationResponse |
| 043 | AAD01 | 188 | cbc UBLVersionID E A 7-8 1..1 1.0 |
| 043 | AAD02 | 188 | cbc CustomizationID Versión del Formato E A 3-4 1..1 1.0 |
| 043 | AAD12 | 188 | cbc @schemeID Referencia a la naturaleza de los mandatos A N 1 ID 1..1 1.0 |
| 043 | AAD03 | 188 | cbc ProfileID Versión del Formato E A 8 1..1 literal “DIAN 2.1: ApplicationResponse de 1.0 |
| 043 | AAD04 | 188 | cbc E N 1 1..1 1.0 |
| 043 | AAD05 | 188 | cbc ID Numero del evento E A 1-50 1..1 1.0 /ApplicationResponse/cbc:ID |
| 043 | AAD06 | 189 | cbc UUID E A 96 1..1 correctamente calculado como se 1.0 |
| 043 | AAD07 | 189 | cbc @schemeID A N 1 UUID 1..1 1.0 //cbc:UUID/@schemeID |
| 043 | AAD08 | 189 | cbc @schemeName A A 12 UUID 1..1 1.0 |
| 043 | AAD09 | 189 | cbc IssueDate E F 10 1..1 1.0 |
| 043 | AAD10 | 189 | cbc IssueTime Hora de registro del evento E H 14 1..1 1.0 |
| 043 | AAF01 | 191 | cac SenderParty Grupo de información del generador del evento G 1..1 (Emisores/Facturadores y/o Legítimos 1.0 |
| 043 | AAF02 | 191 | cac PartyTaxScheme Grupo de información del generador del evento G SenderParty 1..1 1.0 |
| 043 | AAF03 | 191 | cbc Nombre o Razón Social del generador del evento E A 5-450 PartyTaxScheme 1..1 1.0 |
| 043 | AAF04 | 191 | cbc CompanyID NIT del generador el evento E N 3-13 1..1 1.0 |
| 043 | AAF05 | 191 | A N 3 CompanyID 1..1 Debe ser informado el literal “195” 1.0 |
| 043 | AAF06 | 191 | A N 54 CompanyID 1..1 (Dirección de Impuestos y Aduanas 1.0 mpanyID/@schemeAgencyNa |
| 043 | AAF07 | 191 | @schemeID DV del NIT del generador del evento A N 1 CompanyID 1..1 (@schemeName=31), el DV del NIT debe 1.0 |
| 043 | AAF08 | 191 | @schemeName A N 2 CompanyID 1..1 1.0 |
| 043 | AAF20 | 191 | Tipo de identificador de organización A N 1 CompanyID 1..1 1.0 |
| 043 | AAF09 | 191 | cac TaxScheme Grupo de detalles tributarios G PartyTaxScheme 1..1 1.0 |
| 043 | AAF10 | 192 | cbc ID Identificador del tributo E N 3-10 TaxScheme 0..1 1.0 |
| 043 | AAF11 | 192 | cbc Name Nombre del tributo E A 3-10 TaxScheme 0..1 1.0 |
| 043 | AAF22 | 192 | cac Person E A SenderParty 1..N 1.0 |
| 043 | AAF23 | 192 | cbc ID Número de identificación E N 3-14 Person 1..1 1.0 |
| 043 | AAF24 | 192 | @schemeID A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 derParty/cac:Person/cbc:ID/@ |
| 043 | AAF25 | 192 | @schemeName E A 1-100 ID 1..1 1.0 derParty/cac:Person/cbc:ID/@ |
| 043 | AAF26 | 192 | cbc FirstName E A 1-100 Person 1..1 1.0 derParty/cac:Person/cbc:First |
| 043 | AAF27 | 193 | cbc FamilyName E A 1-100 Person 1..1 1.0 derParty/cac:Person/cbc:Fami |
| 043 | AAF28 | 193 | cbc JobTitle E A 1-100 Person 1..1 1.0 derParty/cac:Person/cbc:JobTi |
| 043 | AAF29 | 193 | cbc NationalityID E A 1-100 Person 0..1 1.0 derParty/cac:Person/cbc:Nati |
| 043 | AAF30 | 193 | cbc E A 1-200 Person 0..1 1.0 derParty/cac:Person/cbc:Orga |
| 043 | AAF31 | 193 | cac Grupo de información del mantante G SenderParty 1..1 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF32 | 193 | cbc ID Número de identificación del mandante E N 3-13 1..1 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF33 | 193 | @schemeID DV del NIT del mandante A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF34 | 193 | @schemeName Tipo de identificador del tipo de documento del mandante E A 1-100 ID 1..1 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF35 | 194 | cbc Description Descripción del tipo de mandante E A 31 1..1 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF36 | 194 | cac AgentParty Grupo para informar el tipo del mandante G 1..1 1.0 derParty/cac:PowerOfAttorne |
| 043 | AAF37 | 194 | cac G 1..1 1.0 |
| 043 | AAF38 | 194 | cac ID Tipo de mandante E A 11 1..1 1.0 |
| 043 | AAG01 | 194 | cac ReceiverParty Nombre o Razón Social del receptor del evento G 1..1 Corresponde a la información de la DIAN 1.0 |
| 043 | AAG02 | 194 | cac PartyTaxScheme G ReceiverParty 1..N 1.0 ../cac:PartyTaxScheme |
| 043 | AAG03 | 194 | cbc Nombre o Razón Social del receptor del evento E A 5-450 PartyTaxScheme 1..1 1.0 |
| 043 | AAG04 | 194 | cbc CompanyID Id del receptor del evento E N 3-13 PartyTaxScheme 1..1 1.0 |
| 043 | AAG05 | 194 | A N 3 CompanyID 1..1 Debe ser informado el literal “195” 1.0 |
| 043 | AAG06 | 194 | A N 54 CompanyID 1..1 (Dirección de Impuestos y Aduanas 1.0 mpanyID/@schemeAgencyNa |
| 043 | AAG07 | 194 | @schemeID DV del NIT del receptor del evento A N 1 CompanyID 1..1 1.0 |
| 043 | AAG08 | 195 | @schemeName A N 2 CompanyID 1..1 atributo @schemeID. 1.0 |
| 043 | AAG23 | 195 | Tipo de identificador de organización del receptor del evento A N 1 CompanyID Se debe informar el literal “1” 1.0 ompanyID/@schemeVersionI |
| 043 | AAG09 | 195 | cac TaxScheme Grupo de detalles tributarios G PartyTaxScheme 1..1 1.0 |
| 043 | AAG10 | 195 | cbc ID Identificador del tributo E N 2 TaxScheme 0..1 Se debe informar “01” 1.0 |
| 043 | AAG11 | 195 | cbc Name Nombre del tributo E A 3 TaxScheme 0..1 Se debe informar “IVA” 1.0 |
| 043 | AAH01 | 195 | cac Grupo de información del evento a ser registrado. G 1..N 1.0 |
| 043 | AAH02 | 195 | cac Response Descripción del evento registrado G 1..1 1.0 cumentResponse/cac:Respon |
| 043 | AAH03 | 195 | cbc ResponseCode Código del evento registrado E N 3 Response 1..1 columna “Código” del numeral 14.2.1. 1.0 cumentResponse/cac:Respon |
| 043 | AAH10 | 195 | cbc @listID Referencia a documentos electronicos A N 1 ID 1..1 1.0 cumentResponse/cac:Respon |
| 043 | AAH04 | 196 | cbc Description Descripción del evento registrado E A 15-100 Response 1..1 1.0 cumentResponse/cac:Respon |
| 043 | AAH34 | 196 | cbc EffectiveDate Fecha desde cuando puede actuar el Mandatario E F 10 Response 1..1 cumentResponse/cac:Respon |
| 043 | AAH05 | 196 | cac referenciado el evento registrado G 1..20 referencia a documentos electrónicos 1.0 cumentResponse/cac:Docum |
| 043 | AAH06 | 196 | cbc ID Prefijo y Número del documento referenciado E A 50 1..1 1.0 cumentResponse/cac:Docum |
| 043 | AAH07 | 196 | cbc UUID CUFE ó CUDE del documento referenciado E A 96 1..1 1.0 umentResponse/cac:Docume |
| 043 | AAH08 | 196 | @schemeName Identificador del esquema de identificación A A 11 UUID 1..1 1.0 |
| 043 | AAH09 | 197 | cbc Identificador del tipo de documento de referencia A N 2 1..1 de venta tipo “01” 1.0 |
| 043 | AAH58 | 197 | cac ValidityPeriod Grupo de información para informar el tiempo del mandato G 1..1 1.0 |
| 043 | AAH92 | 197 | cbc StartDate Fecha de inicio del mandato E F 10 ValidityPeriod 0..1 1.0 |
| 043 | AAH59 | 197 | cbc EndDate Fecha de fin del mandato E H 10 ValidityPeriod 0..1 1.0 |
| 043 | ABH29 | 197 | cbc DescriptionCode Tiempo del mandato E H 10 ValidityPeriod 1..1 de la columna “Código” del numeral 1.0 |
| 043 | AAH60 | 198 | cbc Description Descripción del mandato E A 1-500 ValidityPeriod 1..1 1.0 |
| 043 | AAH11 | 198 | cac IssuerParty Grupo de informacion del Mandatario G 1..1 Corresponde al mandatario 1.0 cumentResponse/cac:IssuerP |
| 043 | AAH61 | 198 | Grupo de información del Mandatario G 1..1 1.0 cumentResponse/cac:IssuerP |
| 043 | AAH62 | 198 | cbc ID Número de identificación del Mandatario E N 3-13 1..1 registrado y habilitado en la plataforma 1.0 |
| 043 | AAH63 | 198 | @schemeID DV del NIT del mandatario A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 |
| 043 | AAH64 | 199 | @schemeName Tipo de identificador del tipo de documento del mandatario E A 1-100 ID 1..1 1.0 |
| 043 | AAH65 | 199 | cbc Description Descripción del Tipo de mandatario E A 31 1..1 columna “descripción” del numeral 1.0 |
| 043 | AAH66 | 199 | cac AgentParty Grupo para informar el tipo del mandatario G 1..1 |
| 043 | AAH67 | 199 | cac G AgentParty 1..1 arty/cac:PowerOfAttorney/ca |
| 043 | AAH68 | 199 | cac ID Tipo de mandatario E A 11 1..1 arty/cac:PowerOfAttorney/ca |
| 043 | AAH69 | 200 | cac Person G A AgentParty 1..N El grupo se debe repetir si se informa más 1.0 |
| 043 | AAH70 | 200 | cbc ID E N 3-15 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH71 | 200 | @schemeID A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH72 | 200 | @schemeName E A 1-100 ID 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH73 | 200 | cbc FirstName E A 1-100 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH74 | 201 | cbc FamilyName E A 1-100 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH75 | 201 | cbc JobTitle E A 1-100 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH76 | 201 | cbc NationalityID E A 1-100 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH77 | 201 | cbc E A 1-200 Person 1..1 1.0 arty/cac:PowerOfAttorney/ca |
| 043 | AAH78 | 201 | cac LineResponse Grupo de información del Mandato G 0..1 informar este grupo y embeber el 1.0 cumentResponse/cac:LineRes |
| 043 | AAH79 | 201 | cac LineReference G LineResponse 1..1 |
| 043 | AAH80 | 202 | cbc LineID E N 1 LineReference 1..1 Debe ser informado el literal “1” 1.0 |
| 043 | AAH81 | 202 | cac G LineReference 1..1 1.0 |
| 043 | AAH82 | 202 | cbc ID E 1..1 1.0 |
| 043 | AAH93 | 202 | cbc E 1..1 ponse/cac:LineReference/cac: |
| 043 | AAH83 | 202 | cac Attachment Grupo de información del contrato Mandato G 1..1 1.0 ponse/cac:LineReference/cac: |
| 043 | AAH84 | 202 | cbc mentBinaryObje Contrato del mandatos entre las partes E 1..1 (Mandante y Mandatario) el cual debe ser 1.0 |
| 043 | AAH85 | 203 | @format A 12 1..1 1.0 |
| 043 | AAH86 | 203 | @mimeCode A 3 1..1 Debe ir informado elliteral “PDF” 1.0 DocumentReference/cac:Atta |
| 043 | AAH87 | 203 | @encodingCode A 13 1..1 1.0 DocumentReference/cac:Atta |
| 043 | AAH88 | 203 | A 5 1..1 Debe ir informado el literal “UTF-8” 1.0 ce[1]/cac:DocumentReferenc |
| 043 | AAH89 | 204 | @filename A 49 1..1 1.0 |
| 043 | AAH94 | 204 | cac IssuerParty Grupo de informacion del notario G 1..1 Corresponde al Notario 1.0 |
| 043 | AAH95 | 204 | cac Person Grupo de información del notario G A AgentParty 1..N 1.0 |
| 043 | AAH96 | 204 | cbc ID Número de identificación del notario E N 3-15 Person 1..1 1.0 neReference/DocumentRefer |
| 043 | AAH97 | 204 | @schemeID DV del NIT del notario A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 neReference/DocumentRefer |
| 043 | AAH98 | 205 | @schemeName Tipo del documento de identificación del notario E A 1-100 ID 1..1 1.0 neReference/DocumentRefer |
| 043 | AAH99 | 205 | cbc FirstName Nombres del notario E A 1-100 Person 1..1 1.0 neReference/DocumentRefer |
| 043 | ABH01 | 205 | cbc FamilyName Apellidos del notario E A 1-100 Person 1..1 1.0 neReference/DocumentRefer |
| 043 | ABH02 | 205 | cbc JobTitle Cargo del notario E A 1-100 Person 1..1 1.0 neReference/DocumentRefer |
| 043 | ABH03 | 205 | cbc Area, sección o departamento del notario E A 1-200 Person 1..1 1.0 neReference/DocumentRefer |
| 043 | AAH90 | 205 | cac Response G 1..1 1.0 cumentResponse/cac:LineRes |
| 043 | AAH91 | 206 | cbc Description E 1..1 documento corresponde al contrato de 1.0 |
| 043 | ABH04 | 206 | cbc EffectiveDate Fecha de la escritura pública E F 10 Response 1..1 entResponse/LineResponse/R |
| 043 | ABH05 | 206 | cac LineResponse Grupo de información de la nota de vigencia G 0..1 informar este grupo y embeber el 1.0 cumentResponse/cac:LineRes |
| 043 | ABH06 | 206 | cac LineReference G LineResponse 1..1 |
| 043 | ABH07 | 206 | cbc LineID E N 1 LineReference 1..1 Debe ser informado el literal “2” 1.0 |
| 043 | ABH08 | 206 | cac G LineReference 1..1 1.0 |
| 043 | ABH09 | 206 | cbc ID E 1..1 1.0 ponse[2]/cac:LineReference[2 |
| 043 | ABH10 | 207 | cbc E 1..1 ponse[2]/cac:LineReference[2 |
| 043 | ABH11 | 207 | cac Attachment Grupo de información de la nota de vigencia G 1..1 1.0 ponse[2]/cac:LineReference[2 |
| 043 | ABH12 | 207 | cbc mentBinaryObje Nota de vigencia E 1..1 1.0 |
| 043 | ABH13 | 207 | @format A 12 1..1 1.0 ]/cac:DocumentReference[2]/ |
| 043 | ABH14 | 207 | @mimeCode A 3 1..1 Debe ir informado el literal “PDF” 1.0 ]/cac:DocumentReference[2]/ |
| 043 | ABH15 | 208 | @encodingCode A 13 1..1 1.0 ]/cac:DocumentReference[2]/ |
| 043 | ABH16 | 208 | A 5 1..1 Debe ir informado el literal “UTF-8” 1.0 ]/cac:DocumentReference[2]/ |
| 043 | ABH17 | 208 | @filename A 49 1..1 1.0 ]/cac:DocumentReference[2]/ |
| 043 | ABH18 | 208 | cac IssuerParty Grupo de informacion del Notario G 1..1 Corresponde al Notario 1.0 |
| 043 | ABH19 | 208 | cac Person Grupo de información para el notario G A AgentParty 1..N 1.0 ]/LineReference[2]/Document |
| 043 | ABH20 | 209 | cbc ID Número de identificación del notario E N 3-15 Person 1..1 1.0 ]/LineReference[2]/Document |
| 043 | ABH21 | 209 | @schemeID DV del NIT del notario A N 2 ID 1..1 @schemeName=31), el DV del NIT debe 1.0 ]/LineReference[2]/Document |
| 043 | ABH22 | 209 | @schemeName Tipo del documento de identificación del notario E A 1-100 ID 1..1 1.0 ]/LineReference[2]/Document |
| 043 | ABH23 | 209 | cbc FirstName Nombres del notario E A 1-100 Person 1..1 1.0 ]/LineReference[2]/Document |
| 043 | ABH24 | 209 | cbc FamilyName Apellidos del notario E A 1-100 Person 1..1 1.0 ]/LineReference[2]/Document |
| 043 | ABH25 | 210 | cbc JobTitle Cargo del notario E A 1-100 Person 1..1 1.0 ]/LineReference[2]/Document |
| 043 | ABH26 | 210 | cbc Area, sección o departamento del notario E A 1-200 Person 1..1 1.0 |
| 043 | ABH27 | 210 | cac Response G 1..1 1.0 cumentResponse/cac:LineRes |
| 043 | ABH28 | 210 | cbc Description E 1..1 documento corresponde a la nota de 1.0 |
| 043 | AAL01 | 211 | cac G 1..N * Para los códigos de operación (433 y 1.0 |
| 043 | AAL15 | 211 | cac Response G 1..1 1.0 umentResponse[2]/cac:Respo |
| 043 | AAL02 | 212 | cbc ResponseCode Código de la facultad E N 3-600 Response 1..1 documento limitado, para poder reportar 1.0 cumentResponse[2]/cac:Resp |
| 043 | AAL03 | 212 | cbc Description Descripción del mandato E A 15-100 Response 1..1 1.0 cumentResponse[2]/cac:Resp |
| 043 | AAL04 | 213 | cac G 1..N 1.0 cumentResponse[2]/cac:Docu |
| 043 | AAL05 | 213 | cbc ID Prefijo y número del documento electrónico a referenciar E A 1..1 1.0 cumentResponse[2]/cac:Docu |
| 043 | AAL07 | 213 | cbc UUID CUFE ó CUDE del documento referenciado E A 96 1..1 1.0 cumentResponse[2]/cac:Docu |
| 043 | AAL08 | 213 | @schemeName Identificador del esquema de identificación A A 11 UUID 1..1 1.0 |
| 043 | AAL09 | 213 | cac LineResponse Grupo de información de Aceptación del Mandato G 1..1 cumentResponse[2]/cac:Line |
| 043 | AAL10 | 213 | cac LineReference Grupo de información de Aceptación del Mandato G LineResponse 1..1 |
| 043 | AAL11 | 213 | cbc LineID Identificador de la linea E N 1 LineReference 1..1 Sebe ser informado el literal “1” |
| 043 | AAL12 | 213 | cac Response Grupo de información de Aceptación del Mandato G LineResponse 1..1 Rechazo: No fue informado el grupo cumentResponse[2]/cac:Line |
| 043 | AAL13 | 214 | cbc ResponseCode Aceptación del mandatario E A 6 Response 1..1 Se debe informar el literal “ACEPTA” |
| 043 | AAL14 | 214 | cbc Description E A 48 Response 1..1 |
| 044 | AAA01 | 215 | Registro de–Eventos - ApplicationResponse (raíz) G 1.0 /ApplicationResponse |
| 044 | AAD01 | 215 | cbc UBLVersionID E A 7-8 1..1 1.0 |
| 044 | AAD02 | 215 | cbc CustomizationID Tipo de operación E A 3-4 1..1 1.0 |
| 044 | AAD03 | 216 | cbc ProfileID Versión del Formato E A 8 1..1 literal “DIAN 2.1: ApplicationResponse de la 1.0 |
| 044 | AAD04 | 216 | cbc E N 1 1..1 1.0 |
| 044 | AAD05 | 216 | cbc ID Numero del evento E A 1-50 1..1 que ser generada de forma consecutiva. 1.0 /ApplicationResponse/cbc:ID |
| 044 | AAD06 | 216 | cbc UUID E A 96 1..1 correctamente calculado como se 1.0 /ApplicationResponse/cbc:UUID |
| 044 | AAD07 | 216 | cbc @schemeID A N UUID 1..1 1.0 //cbc:UUID/@schemeID |
| 044 | AAD08 | 216 | cbc @schemeName A A 12 UUID 1..1 1.0 |
| 044 | AAD09 | 217 | cbc IssueDate E F 10 1..1 1.0 |
| 044 | AAD10 | 217 | cbc IssueTime Hora de registro del evento E H 14 1..1 1.0 |
| 044 | AAD11 | 217 | cbc Note Notas E A 0-5000 1..N 1.0 /ApplicationResponse /cbc:Note |
| 044 | AAF01 | 218 | cac SenderParty Grupo de información del generador del evento G 1..1 Corresponde al Mandante o Mandatario 1.0 |
| 044 | AAF02 | 218 | cac PartyTaxScheme Grupo de información del generador del evento G SenderParty 1..1 1.0 |
| 044 | AAF03 | 218 | cbc Nombre o Razón Social del generador del evento E A 5-450 PartyTaxScheme 1..1 1.0 |
| 044 | AAF04 | 218 | cbc CompanyID NIT del generador del evento E N 3-13 1..1 1.0 |
| 044 | AAF05 | 218 | A N CompanyID 1..1 Debe ser informado el literal “195” 1.0 |
| 044 | AAF06 | 218 | A N CompanyID 1..1 (Dirección de Impuestos y Aduanas 1.0 |
| 044 | AAF07 | 218 | @schemeID DV del NIT del generador del evento A N CompanyID 1..1 (@schemeName=31), el DV del NIT debe 1.0 |
| 044 | AAF08 | 218 | @schemeName A N CompanyID 1..1 1.0 |
| 044 | AAF20 | 218 | A N 1 CompanyID 1..1 1.0 |
| 044 | AAF09 | 218 | cac TaxScheme Grupo de detalles tributarios G PartyTaxScheme 1..1 1.0 |
| 044 | AAF10 | 219 | cbc ID Identificador del tributo E N 3-10 TaxScheme 0..1 1.0 |
| 044 | AAF11 | 219 | cbc Name Nombre del tributo E A 3-10 TaxScheme 0..1 1.0 |
| 044 | AAF40 | 219 | cac Person G A SenderParty 1..N El grupo se debe repetir si se informa más 1.0 |
| 044 | AAF41 | 219 | cbc ID E N 3-15 Person 1..1 1.0 |
| 044 | AAF42 | 219 | @schemeID A N 2 ID 1..1 (@schemeName=31), el DV del NIT debe 1.0 |
| 044 | AAF43 | 219 | @schemeName E A 1-100 ID 1..1 1.0 |
| 044 | AAF44 | 219 | cbc FirstName E A 1-100 Person 1..1 1.0 |
| 044 | AAF45 | 220 | cbc FamilyName E A 1-100 Person 1..1 1.0 |
| 044 | AAF46 | 220 | cbc JobTitle E A 1-100 Person 1..1 1.0 |
| 044 | AAF47 | 220 | cbc NationalityID E A 1-100 Person 1..1 1.0 |
| 044 | AAF48 | 220 | cbc E A 1-200 Person 1..1 1.0 arty/Person/OrganizationDepar |
| 044 | AAG01 | 220 | cac ReceiverParty Nombre o Razón Social del receptor del evento G 1..1 Corresponde a información de la DIAN 1.0 |
| 044 | AAG02 | 220 | cac PartyTaxScheme G ReceiverParty 1..1 1.0 ../cac:PartyTaxScheme |
| 044 | AAG03 | 220 | cbc Nombre o Razón Social del receptor del evento E A 5-450 PartyTaxScheme 1..1 1.0 |
| 044 | AAG04 | 220 | cbc CompanyID Número de identificación del receptor del evento E N 3-13 PartyTaxScheme 1..1 Debe ser informado el literal “800197268” 1.0 |
| 044 | AAG05 | 220 | A N 3 CompanyID 1..1 Debe ser informado el literal “195” 1.0 |
| 044 | AAG06 | 220 | A N 54 CompanyID 1..1 (Dirección de Impuestos y Aduanas 1.0 |
| 044 | AAG07 | 220 | @schemeID DV del NIT del receptor del evento A N 1 CompanyID 1..1 1.0 |
| 044 | AAG08 | 221 | @schemeName A N 2 CompanyID 1..1 @schemeID. 1.0 |
| 044 | AAG23 | 221 | Tipo de identificador de organización del receptor del evento A N 1 CompanyID 1..1 “código” del numeral 14.2.14 1.0 |
| 044 | AAG09 | 221 | cac TaxScheme Grupo de detalles tributarios G PartyTaxScheme 1..1 1.0 |
| 044 | AAG10 | 221 | cbc ID Identificador del tributo E N 2 TaxScheme 0..1 Se debe informar “01” 1.0 |
| 044 | AAG11 | 221 | cbc Name Nombre del tributo E A 3 TaxScheme 0..1 Se debe informar “IVA” 1.0 |
| 044 | AAH01 | 221 | cac Grupo de información del evento a ser registrado G 1..1 1.0 |
| 044 | AAH02 | 221 | cac Response Descripción del evento registrado G 1..1 1.0 |
| 044 | AAH03 | 221 | cbc ResponseCode Código del evento registrado E N 3 Response 1..1 columna “Código” del numeral 14.2.1. Debe 1.0 mentResponse/cac:Response/c |
| 044 | AAH04 | 221 | cbc Description Descripción del evento registrado E A 15-100 Response 1..1 1.0 mentResponse/cac:Response/c |
| 044 | AAH05 | 222 | cac G 1..1 1.0 mentResponse/cac:DocumentR |
| 044 | AAH06 | 222 | cbc ID Prefijo y Número del documento referenciado E A 50 0..1 1.0 |
| 044 | AAH07 | 222 | cbc UUID CUFE o CUDE del documento referenciado E A 96 0..1 1.0 |
| 044 | AAH08 | 222 | cbc @schemeName Identificador del esquema de identificación A A 11 UUID 1..1 1.0 |
| 044 | AAH09 | 222 | cbc Identificador del tipo de documento de referencia E N 2 1..1 1.0 |

## Límite de las comprobaciones locales

DIAN verifica inscripción/habilitación de participantes y software, existencia y
pertenencia de CUFE/CUDE, número consecutivo no repetido, validez jurídica y vigencia
del mandato, actos pendientes, firma del titular autorizado y ausencia de pago total
que restrinja el evento. El SDK no declara esas condiciones como comprobadas por
construir XML, verificar criptografía o reconocer un código. No hace consultas ni
transmisiones implícitas al preparar.

Los NIT/DV se validan sin corregirlos. Algoritmo: módulo 11 con pesos primos,
Orden Administrativa DIAN 4 de 1989, apartado «Cálculo del Dígito de Verificación».
Las longitudes siguen las restricciones de cada contexto y no se rellenan datos.
