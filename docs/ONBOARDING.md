# Onboarding — lógica de negocio y operación

Guía para quien asume la operación técnica que llevaba Melquiades Rodriguez. Resume **qué hace
cada pieza y por qué**; el detalle vive en los documentos enlazados (rutas relativas a `docs/`).
Fuentes: los documentos del repo, principalmente `handover/HANDOVER_2026-09-04.md` (escaneo en
vivo del 4 de septiembre de 2026) y `salesforce/ORG_REFERENCE.md`. Todo lo que diga "hoy" se
refiere a esa fecha; verifica en vivo antes de actuar.

---

## 1. El negocio en una página

**Homesí** es la división latina de **Supreme Lending** (razón social *Everett Financial, Inc.
dba Supreme Lending*), un originador de préstamos hipotecarios en EE. UU. **Simo Solutions
Group** es la empresa que opera el back-office, el CRM y las integraciones. En los sistemas
aparecen también dominios heredados de **City Lending** (`citylendinginc.com`), la etapa
anterior de la operación.

El negocio tiene cuatro líneas, y cada una vive en un *record type* distinto de Lead y
Opportunity en Salesforce:

| Línea | Record type | Qué es |
|---|---|---|
| **B2C — préstamos** | `Borrower` | El núcleo. Un prestatario pide una hipoteca; el préstamo se procesa en **Encompass** (el LOS, *Loan Origination System*) y Salesforce refleja su avance. |
| **B2B — socios referidores** | `Realtor`, `Broker` | Agentes inmobiliarios y brokers que refieren prestatarios. Se gestionan como relaciones comerciales. |
| **Recruitment** | `Loan_Officer` | Captación de Loan Officers de otras empresas para que se unan a Supreme. |
| **SiMo BPO** | `SiMo_BPO` | Servicio de BPO que Simo ofrece a realtors y LOs; pipeline separado, con su propio workspace de Customer.io. |

La regla que ordena todo: **Encompass es la fuente de verdad del préstamo** (fechas de hitos,
tasas, montos, equipo asignado) y **Salesforce es la fuente de verdad de la relación y del
trabajo** (quién debe hacer qué, seguimiento, comunicación, KPIs). Casi toda la automatización
de Salesforce reacciona a datos que escribe Encompass.

---

## 2. Mapa de sistemas

```
Encompass (LOS)
   │  push REST directo + export Excel nocturno → S3 → Lambda processFile
   ▼
SALESFORCE PROD  (org HomeSi, 00DKb000000OvoRMAS)  ◄── el centro de todo
   ├──► Customer.io   campañas de email; lee Leads/Opps cada 30 min, escribe Tasks de engagement y opt-outs
   ├──► n8n Cloud     digests diarios a agentes + motor Borrower Follow-Up (desplegado, no activo)
   ├──► Make.com      enriquecimiento de Leads Realtor con Claude (campos AI_*)
   ├──► BigQuery      espejo diario de 10 objetos → apps SimoOS y Lovable
   ├──► AWS           backend del portal LeadView, sync Encompass, API de calidad de datos
   └──► 360 SMS, Zoom, RingCentral, Kixie (paquetes / conexiones de telefonía y webinars)

Microsoft 365: itsupportaccount@simosolutionsgroup.com (remitente de alertas y digests)
               docs@homesi.co (buzón de prestatarios del sistema FUR)
```

Qué corre de verdad, sin intervención humana, y toca datos del negocio (handover, Parte 1):
Salesforce; dos digests de n8n; una integración de Make; los syncs de Customer.io; el sync
Encompass→Salesforce y el portal en AWS; y el espejo de BigQuery. **La producción real es más
pequeña de lo que sugiere la documentación.**

---

## 3. Salesforce

### 3.1 Datos básicos

- Prod: alias `prod`, org `00DKb000000OvoRMAS`, `ruby-ruby-7485.my.salesforce.com`, Enterprise.
- Sandbox: alias `homesi-staging` (`00DEm000008XXK7MAO`). **Se refresca desde prod y contiene
  emails y teléfonos reales de prestatarios**: cualquier envío construido contra staging necesita
  un modo de prueba. Staging y prod tienen diferencias de metadata en ambos sentidos.
- Dos apps: **HOMESÍ-B2C** y **HOMESÍ-B2B**.
- 88 usuarios activos, 78/78 licencias Salesforce usadas (quedan 5 licencias de Integration).
- Volumen: 2,68 M Tasks (la mayoría escritas por Customer.io), 183 K Leads, 37 K Opportunities,
  42 K Contacts, 169 K mensajes SMS.

### 3.2 Objetos que tienes que conocer

| Objeto | Para qué |
|---|---|
| `Lead` | Prospecto de cualquier línea (record type define cuál). |
| `Opportunity` | En `Borrower` **es el préstamo**. En Realtor/Broker/LO es la relación comercial o el proceso de reclutamiento. |
| `Contact` | Personas; los realtors referidores son Contacts (`Referred_By__c`, `Buyers_Agent__c`, `Listing_Agent__c` apuntan a Contact). |
| `Loan_Officer__c` | Catálogo de Loan Officers (348). En la Opp se usa `Loan_Officers__c`; `Loan_Officer__c` está deprecado. |
| `Mortgage_Condition__c` — etiqueta **"Work Item"** | La unidad de trabajo operativo: condiciones del préstamo, tareas de hitos LOA2, First Touch. OWD privado. |
| `NPPM__c` | Realtors con rol especial en el programa de referidos (`Realtor-NPPM`, `Realtor-BD`). Los documentos no definen la sigla. |
| `Follow_Up_Request__c` (FUR), `Outbound_Message__c`, `Inbound_Message__c` | Sistema Borrower Follow-Up (§4). |
| `Notification_Settings__c` | Custom setting con el interruptor `Test_Mode__c` de las notificaciones de hitos. |
| `Task` | Actividades. Mezcla tareas humanas y millones de registros de engagement de email. |

### 3.3 Ciclo de vida del Lead

1. **Entrada.** Formularios web, Facebook/redes, imports masivos (Data Import Wizard, ver
   `salesforce/LEAD_IMPORT.md`), Customer.io, recruitment. Al crearse, flows asignan **branch**
   por defecto (`branch_default_when_Lead_create`, versión 39: la regla más editada del org),
   Loan Officer por defecto, importancia (`Lead_Importance__c`) y campaña.
2. **Calidad de datos.** `LeadDataQualityTrigger` encola un Queueable por Lead que llama a una
   API en AWS. **Más de 50 Leads por transacción es fatal**: en cargas masivas se usa el permission
   set `Bypass_Lead_Automation`.
3. **Trabajo comercial.** Estados New → Working → … Crear una Task o cambiar notas mueve el
   estado; descartar exige motivo (`Reason_for_Discarded`). Hay validaciones de campos mínimos
   para calificar cada record type (`Check_Fields_For_Qualified_*`).
4. **Referidos.** Si un realtor refiere, `Referred_By__c` apunta a su Contact; flows calculan
   `Strategy__c`, la fecha de referido, y si la cadena llega a un NPPM (§3.8).
5. **Conversión.** Al convertir, flows copian datos y posts de Chatter a la Opportunity, sincronizan
   SiMo BPO y reapuntan los FUR del Lead a la nueva Opp.

Enriquecimiento con IA: cuando se marca `Lead.AI_Trigger__c` en un Lead Realtor, Salesforce
llama un webhook de Make, que consulta a Claude y escribe ~28 campos `AI_*` de perfil (§6).

### 3.4 Ciclo de vida del préstamo (Opportunity `Borrower`)

**Encompass empuja los datos.** El endpoint Apex `OpportunityUpdater`
(`/services/apexrest/OpportunityUpdate/*`) recibe el préstamo y encuentra la Opp por este orden:
LoanId → número de préstamo → branch + email/teléfono. Filtra valores basura de Encompass (emails
tipo `na@…`, teléfonos de relleno) y protege transferencias de branch. El otro camino es el export
Excel nocturno que procesa una Lambda en AWS.

**La etapa se calcula, no se escribe a mano.** El flow `Update_current_Milestone_Loan_status_Opp`
(before-save, el corazón del motor) deriva `StageName` a partir de `Closed_Loan__c`,
`Loan_Status__c`, `Application_Date__c` y `Current_Milestone__c` en cada guardado. Otro flow
deriva `Current_Status__c` de la etapa:

| Stage | Current Status |
|---|---|
| Qualification | Pre-Qualified/Doc Requested |
| Proposal | Pre-Approved |
| Negotiation | Ratified |
| Needs Analysis | un valor On-Hold |
| Closed Won / Closed Lost | vacío |

Los hitos del préstamo (`Current_Milestone__c`): Started → Processing → Submittal → Initial
Decision → Resubmittal → Clear To Close → Closing.

**Reglas de protección de etapas** (nacieron de un incidente el 2026-05-15, cuando una
actualización masiva reabrió 569 préstamos cerrados):

- **Closed Won solo lo pone la automatización**, cuando el préstamo fondea (`Closed_Loan__c = true`).
  Un usuario no puede marcarlo.
- **Un préstamo fondeado no puede pasar a Closed Lost.**
- Un usuario sí puede cerrar como Closed Lost (con `Reason_for_loss__c`), y se queda así.
- **Una Opp cerrada nunca se recalcula.** Los flows del motor excluyen Closed Won/Lost en sus
  criterios de entrada.
- Cambiar etapa o Current Status exige número de préstamo (`Loan__c`), salvo en etapas iniciales.

**KPI principal: Closing On Time.** Dashboard `01ZQg00000MH3EXMA1`. Un préstamo cerró "On Time"
si `Disbursement_Date__c <= Org_Est_Closing_Date__c` (la fecha estimada original, que nunca se
actualiza). La consulta canónica de "préstamos cerrados" está en `salesforce/ORG_REFERENCE.md`:
Borrower + `Closed_Loan__c` + `Lender__c LIKE '%Eve%'` + no archivado. `Stat_Closing_Risk__c` es
el pronóstico para el pipeline activo (On Track / Delayed / Out of Scope).

### 3.5 Roles del equipo de un préstamo

| Rol | Qué hace | Campo en la Opp |
|---|---|---|
| **Loan Officer (LO)** | Dueño comercial del préstamo | `Loan_Officers__c` |
| **LOA1** | Loan Officer Assistant: primer contacto con el prestatario, antes de ratificar | `LOA1__c` (lookup) / `LOA__c` (texto de Encompass) |
| **LOA2** | Loan Officer Assistant: lleva el préstamo hito por hito hasta el cierre | `LOA2__c` / `LOA_2__c` |
| **Processor Jr** | Seguimiento de documentos | `Processor_Jr__c` / `Processor_Jr_Text__c` |
| **Loan Processor** | Procesamiento; solo se guarda su email | `Loan_Processor_Email__c` |
| **Account Executive** | Dueño de la Opp según reglas de Apex | `OwnerId` (`OpportunityAccountExecutiveOwner`) |
| LOA Team Leads | Supervisan y asignan manualmente | grupo `LOA_Team_Leads` |

**Asignación.** Encompass escribe el **nombre** del LOA en un campo de texto; el flow
`LOA_Assignment_First_Touch` busca el User con ese nombre y llena el lookup. Si el nombre no
coincide exactamente, no se asigna nada, sin error. También se puede asignar a mano desde la
Opp. Al asignar se crea un **Work Item "First Touch"** (una vez por préstamo). Apex
(`OpportunityCoOwnerSharing`) comparte la Opp con cada persona del equipo, porque el modelo de
compartición es privado.

**Owner inactivo.** Todo flow que asigna dueño tiene respaldo: LOA2 → LOA1 → dueño de la Opp,
porque asignar a un usuario inactivo rompe el guardado.

### 3.6 Hitos del LOA2: notificaciones y Work Items

Es el grupo más grande de automatización (22 flows). Cada vez que Encompass escribe una fecha de
hito en la Opp:

1. Se envía un **email de notificación** al LO, LOA2 y Loan Processor (más dos direcciones fijas:
   Pier Laino y Alejandra Murillo), desde `sfintegrations@supremelending.com`, la única dirección
   que Mimecast deja salir.
2. Si hay LOA2 asignado, se crea un **Work Item** con la siguiente acción y su fecha límite.
3. Cuando llega el hito siguiente, otro flow **cierra** el Work Item anterior.

Ejemplos: `Application_Date__c` → "Issue Disclosures"; `LE_Sent_Date__c` → seguimiento de
disclosures; `Disclosures_Signed_Date__c` → ordenar avalúo y enviar a procesamiento;
`Lock_Date__c` → revisión de cambio de circunstancias (COC); fechas de título + seguro + lock →
pedir ICD; `Clear_to_Close_Date__c` → cierre. Tabla completa en
`salesforce/AUTOMATION_INVENTORY.md` §2.1.

Detalles importantes:

- **Solo aplica a préstamos alimentados por Encompass** (`Loan__c` lleno y lender Everett); en el
  resto nunca se escriben esas fechas.
- `Notification_Settings__c.Test_Mode__c` desvía todos los emails a un destinatario de prueba
  (hoy `m.rodriguez@…`, hay que cambiarlo). `LOA2_FHA_Docs_Email_to_Nila` **no** respeta ese modo.
- Todo `Send_Email` en un flow after-save necesita `faultConnector`: si el envío falla sin él, se
  revierte el guardado de la Opp.
- En un rate lock salen dos emails por diseño (Rate Locked + COC Review); el usuario lo aceptó.

### 3.7 Tareas, Work Items y SLA

- **Work Items** (`Mortgage_Condition__c`) tienen tres record types: `Mortgage_Condition`
  (condiciones del préstamo), `LOA2_Milestone_Task` y `Task` (tareas sueltas, también en Leads).
  Se ven en los LWC `mortgageChecklist` y `myWorkItems`. Al cerrar la Opp se cierran sus Work
  Items; al ratificar se completan los de LOA1.
- **SLA.** `SLA_Follow_Ups` califica Tasks según `Touch_Type__c`: *First Touch* 24 h hábiles,
  *Follow Up* 48 h. Escribe `SLA__c` y `SLA_Missed_By__c`. Tres flows programados recalculan el
  envejecimiento a las 9:00, 13:00 y 17:00.
- **Hueco conocido:** como el First Touch de LOA1 y LOA2 migró de Task a Work Item, ya no tiene
  SLA. Está diseñado un "SLA v2" sobre Work Items, sin construir.
- `playbooks/LOA_PLAYBOOK.md` (mayo 2026) describe el First Touch como Task que se completa con un
  post de Chatter; eso cambió en julio. Úsalo para entender el proceso humano, no el técnico.
- Un digest de n8n envía cada día hábil a las 9:00 a cada dueño sus Work Items vencidos.

### 3.8 Referidos, NPPM y Strategy

`Strategy__c` clasifica el origen comercial del préstamo (por ejemplo `NPPM` o `B2B Strategy`).
`Set_NPPM_From_Referral_Chain` recorre la cadena de referidos **solo por Ids**:

- **Directo (1 salto):** el realtor que refirió *es* un NPPM → `Referred_By_NPPM__c = Yes`.
- **Downline (2 saltos):** el realtor que refirió fue referido a su vez por un NPPM.
- Si faltan enlaces, el flow **no toca** los campos, en vez de escribir un "No" falso.

Lección del diseño: dos flows before-save en el mismo objeto no tienen orden garantizado, así
que el mismo flow escribe NPPM y Strategy juntos.

### 3.9 Reglas transversales del org

- Casi todas las validaciones respetan `Bypass_Validation_Rules__c` y excluyen al usuario de
  integración `sfintegrations@citylendinginc.com`.
- **Usuarios clave:**
  - **It Support** (`005Kb00000B1HzJIAV`) es una cuenta de rol, no personal. Se queda activa;
    solo cambia su email. **Nunca la desactives ni revoques sus sesiones**: de ella cuelgan los
    tokens OAuth de n8n, 360 SMS, Kixie, RingCentral, probablemente Customer.io, y 35 dashboards.
  - **sf integrations** (`005Qg00000C9srvIAB`) es el usuario de integraciones: Make, el batch
    nocturno y el remitente de emails.
- El batch nocturno de `sf integrations` reescribe campos de texto de LOA desde Encompass y
  vuelve a disparar los flows de asignación, así que todo flow tiene guardas anti-duplicado.
- Las 5 trampas de orden de ejecución están en `salesforce/AUTOMATION_INVENTORY.md` §6. La que
  causó 2 días de caída: en criterios de entrada de un flow, usar `RecordTypeId` con el Id, nunca
  `RecordType.DeveloperName` (`salesforce/PROD_OUTAGE_RCA_2DAY.md`).

---

## 4. Borrower Follow-Up (FUR): el proyecto grande de 2026

**Qué hace.** Persigue por email a los prestatarios para que envíen documentos o respondan.
Clasifica las respuestas con Claude, sube adjuntos a Salesforce Files y escala las preguntas a
agentes como Work Items.

**Flujo.**
1. **Intake (WF-1).** Dos entradas:
   - *Path A:* un agente marca condiciones del préstamo con `Chase_With_Borrower__c`.
   - *Path B:* un agente escribe la petición en texto libre en el Lead (`AI_Followup_Request__c`).
   Claude redacta la petición en inglés y español, y se crea un `Follow_Up_Request__c` con sus documentos.
2. **Cadencia (WF-2).** Cada 15 minutos envía el siguiente toque según `fur_cadences`, respetando
   horas de silencio. Si se agota la cadencia, Docs y Appointment escalan a un agente; Interest
   Check se cierra sin respuesta.
3. **Respuestas (WF-4).** El Dispatcher lee `docs@homesi.co` cada minuto, filtra respuestas
   automáticas y llama al handler. El handler encuentra el FUR por token `[FUR-xxxxxx]` en el
   asunto, luego por email en la Opp y luego en el Lead. Una respuesta con documento y pregunta
   archiva el documento **y** escala la pregunta. Los opt-outs se propagan a Salesforce.
4. **Escalamiento.** Crea un Work Item, marca `Needs_Agent__c`, hace @mention en Chatter y pone
   el FUR en Escalated.
5. **Mantenimiento (WF-5).** Limpieza y digest diario.

**Principio de diseño:** Salesforce guarda todo el estado; n8n no guarda nada duradero. Si n8n
cae un día, se retoma donde el estado en Salesforce diga.

**Estado hoy: desplegado, no activo.** La metadata está en prod desde el 2026-08-21 y los
workflows apuntan a prod desde el 2026-08-24, pero WF-1, WF-2 y WF-5 nunca se publicaron, el
Dispatcher está apagado y `fur_settings.test_mode = true`. **No se procesa ningún email de
prestatario.** El motor de cadencia **nunca ha corrido solo** en su horario; todas las pruebas
fueron manuales.

**Qué falta para salir en vivo** (`borrower-followup/REMAINING_CUTOVER.md` §0):
- Plantillas reales con pie de cumplimiento; hoy imprimen `NMLS #—` literal y prometen un link de baja que no existe.
- Usuario de integración en vez del login personal.
- Cadena de buzón verificada; WF-2 todavía envía desde `itsupportaccount@`.
- Alcance del piloto: una branch, 2–3 agentes.
- FLS en 13 perfiles.
- 15 pruebas de humo.

El handover recomienda decidir en la semana 3: terminarlo o apagarlo limpiamente, no dejarlo a
medias.

---

## 5. n8n Cloud

`https://simosolutionsgroup.app.n8n.cloud`. 23 workflows; 9 son de un negocio paralelo de Jorge
Campodonico (JOGA / La Gemma). Hay que decidir si pertenecen a la instancia de la empresa.

**Lo único que corre en producción por sí solo:**

| Workflow | Cuándo | Qué hace |
|---|---|---|
| LOA Work Items – Daily Digest | días hábiles 9:00 ET | email a cada dueño con sus Work Items vencidos, con copia a team leads |
| Document Follow Up – Daily Digest | días hábiles 9:00 ET | email con Tasks "Document Follow Up" vencidas |
| Error Alert (shared) | ante error | avisa a `m.rodriguez@…`; hay que cambiar el destinatario |

Patrón canónico de digest: Schedule → consulta SOQL → Code (agrupa y arma HTML) → Outlook.
Las credenciales de Salesforce y Outlook son tokens OAuth del administrador saliente. Las reglas
de construcción (§2 de `n8n/ENGINE_REFERENCE.md`) costaron días aprenderlas; léelas antes de
editar.

---

## 6. Make.com

Plan Core, 10.000 operaciones al mes. Todo pertenece a la cuenta `itsupportaccount@`: **2FA
apagado, sin segundo admin.**

**Único proceso vivo, sano:** Lead Realtor con `AI_Trigger__c` → webhook `1909871` → escenario
*Realtor Worker* → Claude Sonnet → escribe ~28 campos `AI_*` en el Lead. Son ~11 operaciones por
Lead, sin fallos en las últimas 50 corridas.

**No reactivar:**
- *Homesi Copilot*: tiene la marca de agua fija en mayo y escribe `Needs_Agent__c`, que ahora
  pertenece al FUR.
- *LOA Digest* viejo: lo reemplazó n8n.
- El conector de webinars tiene 23 registros de GoToWebinar sin procesar desde julio.

La API key del webhook de SMS está en texto plano dentro de los blueprints de Homesi Copilot;
hay que rotarla.

---

## 7. Customer.io

| Workspace | Para qué | Datos de Salesforce |
|---|---|---|
| **164380** "Supreme Lending" | Campañas Homesí (~180 K perfiles) | Lead sync 503 y Opp sync 623, cada 30 min, **excluye** SiMo BPO |
| **224311** "Simo Solutions Group" | Base de realtors y LOs para SiMo BPO (~35 K) | syncs 2082/2083, **solo** SiMo BPO |
| 177825 "BIM" | Sin inventariar | — |

**Hacia Salesforce (write-back):** cada envío, apertura, clic, rebote o spam crea una Task en el
Lead u Opp, con dueño fijo "Team Marketing city". Por eso hay millones de Tasks. Un unsubscribe
marca `HasOptedOutOfEmail`; es cumplimiento normativo y no puede romperse.

No hay eventos personalizados: toda la segmentación usa atributos sincronizados desde Salesforce.
El token OAuth del sync pertenece a un usuario de Salesforce desconocido; hay que reautorizarlo
como `sf integrations` (handover, Parte 3, fila 2). Laura Betancourt arma segmentos y campañas.

---

## 8. AWS

Cuenta `443216489626`, us-east-1, ~600 USD al mes.

| Carga | Qué hace |
|---|---|
| `supreme-encompass-salesforce-prod` | Export Excel de Encompass → S3 → Lambda `processFile` → Salesforce. **El camino nocturno de datos del préstamo.** |
| `salesforce-lambda-bridge-prod` | Backend del portal **LeadView / Refer-by-Salesforce** (25 Lambdas, Cognito) |
| `salesforce-data-quality-api-prod` | La API de calidad de datos que llama el trigger de Leads |
| `createLoanEncompass` | Crear préstamo en Encompass desde Salesforce |
| S3 `loanrepository` | 2,44 TB de eFolders de préstamos; fuente de los binders FHA |

**Riesgo número uno del traspaso:** si los secretos en Secrets Manager de estas stacks contienen
un login personal, el sync con Encompass y el portal se caen el día que se cierre ese login.
Hay que leerlos primero.

Deuda de seguridad:
- La cuenta root tiene access key activa.
- 3 bases RDS públicas.
- El bucket `integrator-upload-documents` no tiene bloqueo de acceso público.
- El usuario `serverless` es administrador y lo usa un cliente desconocido.

---

## 9. BigQuery

Proyecto `mcp-connector-procedure`. El **Data Transfer Service** copia 10 objetos de Salesforce
cada día a las ~05:02 UTC al dataset `salesforce`. Encima hay vistas en `home_si`, `lending_marts`,
`b2b_marts` y otros datasets. Las consumen la app **SimoOS** (métricas), una app de **Lovable**
(deduplicación de leads) y el agente de analítica (`bigquery/AGENT_PROMPT.md`).

Todo pertenece a cuentas del dominio `simologic.com`. Si se elimina `itsupportaccount@simologic.com`,
el espejo se congela y las apps siguen mostrando datos viejos sin avisar.

`hr_centralizado` contiene datos personales sensibles de empleados (identificaciones, cuentas
bancarias) que deberían restringirse.

---

## 10. Herramientas de IA en uso

| Skill | Qué hace |
|---|---|
| **recruitment-copilot** | Cada día califica Leads Loan Officer. Revisa licencia, unidades en 14 meses, relación con agentes, ≥15 % agentes latinos y antigüedad en NMLS. Marca hasta 30 como *Ready to Call*. (`salesforce/RECRUITMENT_COPILOT.md`) |
| **salesforce-lead-import** | Prepara lotes de Leads (`NEW.csv` / `IN_QUESTION.csv`) para el Data Import Wizard. |
| **fha-lrs-binder** | Arma expedientes FHA post-endoso desde S3 con OCR de Textract. Maneja muchos datos personales. |

Además: el escore de probabilidad de nombre latino (`salesforce/LATINO_NAME_RUNBOOK.md`) y dos
diseños sin construir, SiMo BPO con captura por respuesta (`simo-bpo/DESIGN.md`) y el score de
engagement de email (`customerio/EMAIL_ENGAGEMENT_DESIGN.md`).

---

## 11. Qué corre y cuándo (hora del Este)

| Cuándo | Qué |
|---|---|
| Continuo | Encompass → `OpportunityUpdater`; Lead `AI_Trigger__c` → Make; write-back de Customer.io |
| Cada 30 min | Customer.io lee Leads y Opps de Salesforce |
| Noche | Apex programado `Update Delivery Status`; batch de `sf integrations` que reescribe campos de LOA |
| ~01:00 (05:02 UTC) | BigQuery copia Salesforce |
| 08:00 | Flow `Discarded_Lead_Follow_Up_Automation` |
| 09:00 días hábiles | Digests de n8n |
| 09:00 / 13:00 / 17:00 | Envejecimiento de SLA |
| 15:00 / 16:00 | Flows de revisión de aperturas de email |

---

## 12. Tus primeros 30 días, según el handover (Parte 4)

1. **Semana 1 — proteger lo que corre con identidades compartidas.**
   - Congelar It Support: no desactivarla ni revocar sesiones.
   - Cambiar su email y el `Test_Recipient__c`.
   - Leer los secretos de AWS.
   - Reautorizar Customer.io como `sf integrations`.
   - Cambiar los destinatarios de alertas en n8n y Make.
   - Confirmar el dueño de la transferencia de BigQuery.
2. **Semana 2 — deuda de seguridad.**
   - Rotar la key root de AWS.
   - Rastrear el usuario `serverless`.
   - Bloquear acceso público en S3.
   - Revisar la cuenta de proveedor **La Haus AI**, que tiene System Administrator en prod.
3. **Semana 3 — decidir el destino del FUR**: terminarlo o apagarlo limpio.
4. **Semana 4 — costos e higiene.**
   - Subir RDS MySQL a 8.4 (ahorra ~300 USD al mes).
   - Crear un presupuesto en AWS.
   - Borrar las reglas de EventBridge que apuntan a Lambdas inexistentes.

Personas útiles:
- **Camilo Delgado**: admin de Salesforce activo, el respaldo natural.
- **Laura Betancourt**: Customer.io.
- **Alejandra Murillo, Monica Fernandez, Carlos Alvarez, Igleth Mercado**: LOA team leads.
- **Nila Granadillo, Adriana Cervantes**: Production Support.

---

## 13. Glosario

| Término | Significado |
|---|---|
| LOS / Encompass | Sistema de originación de préstamos; fuente de verdad del préstamo |
| LO / LOA1 / LOA2 | Loan Officer / asistente de primer contacto / asistente de hitos hasta cierre |
| Ratified | Current Status de un préstamo en Negotiation (contrato aceptado) |
| LE / ICD / COC / CTC | Loan Estimate / Initial Closing Disclosure / Change of Circumstance / Clear to Close |
| Disbursement | Fondeo del préstamo = cierre real |
| Work Item | `Mortgage_Condition__c`, la unidad de trabajo operativo |
| FUR | Follow-Up Request, registro del sistema Borrower Follow-Up |
| First Touch | Primer contacto obligatorio del LOA con el prestatario |
| NPPM | Realtor con rol especial en el programa de referidos (sigla sin definir en los documentos) |
| Branch | Sucursal, código numérico (ej. `716`, `770`) |
| SiMo BPO | Línea de negocio de BPO de Simo; record type propio |

---

## 14. Ruta de lectura sugerida

1. Este documento.
2. `handover/HANDOVER_2026-09-04.md`, Partes 1–6: qué existe y qué depende de quién.
3. `salesforce/ORG_REFERENCE.md`: *Project context*, *Stage protection*, la sección de
   notificaciones de hitos y la lista de 30 gotchas.
4. `salesforce/AUTOMATION_INVENTORY.md` completo; es corto y da el mapa de los 209 flows.
5. `borrower-followup/DESIGN_SPEC.md` §0–3, solo si vas a retomar el FUR.
6. `n8n/ENGINE_REFERENCE.md` §0–2 antes de tocar cualquier workflow.
7. `customerio/OPERATING_CONTEXT.md` §1, §6 y §9.

Un ejercicio que ayuda: toma un préstamo real en staging y sigue sus campos de Encompass, su
etapa, su equipo asignado, sus Work Items y sus emails de hitos. Luego repite con un Lead Realtor.
