# Borrower Follow-Up — Email Template Brief for Marketing & Compliance

**Prepared 20 August 2026 · Simo Solutions Group / Homesí**
Source of truth: n8n workflow `WF-2 Cadence Engine` (`nG8hwck9RsoJZiQb`), copy extracted verbatim from the live staging build. Nothing in this document is estimated.

---

## 1. Scope — this is 20 emails, not one template

Every borrower email comes from one engine. There are **four cadences**; each has several timed steps, and **every step exists in English and Spanish**.

| Cadence | Sending steps | Bodies (EN+ES) | Launching? |
|---|---|---|---|
| **Docs Standard** — chasing documents | 4 (day 0, +2, +5, +9) | 8 | Yes |
| **Interest Standard** — "are you still moving forward?" | 3 (day 0, +3, +7) | 6 | Yes |
| **Appointment** — booking a call | 3 (day 0, +2, +5) | 6 | Yes |
| **Reactivation** — cold re-engagement | 3 (day 0, +4, +10) | 6 | **No — Phase 2** |

**At launch marketing needs to produce 20 bodies + 20 subject lines.** Reactivation adds 6 more later, and should be designed separately: it is cold outreach and is planned to send from a *different* mailbox so it cannot damage the sending reputation of live-loan mail.

Each cadence ends with a silent "exhaust" step that sends nothing — it hands the borrower to a human (Docs, Appointment) or closes the follow-up (Interest, Reactivation). **No email is needed for those.**

---

## 2. Hard constraints — things marketing cannot change

These are load-bearing. Changing any of them breaks the system, not just the design.

1. **The subject line must keep its tracking token at the very end**, in square brackets:
   `Still need a few documents [FUR-AMRZABF0P0]`
   This token is how borrower replies are matched back to the right loan. If it is removed, moved, or wrapped in different punctuation, replies stop being routed and documents get lost. Marketing owns the words before the bracket; the bracket itself is untouchable.
2. **The document list is generated per borrower and cannot be written in advance.** Each bullet is written by AI from the actual underwriting condition on that loan, in the borrower's language. Marketing designs the *container* — the lead-in line and the list styling — not the contents.
3. **Only one merge field exists today: the borrower's first name.** There is no loan number, no loan officer name, no branch, no due date available in the template. If marketing wants any of those, that is an engineering request.
4. **HTML only.** There is currently no plain-text alternative version. Some corporate mail clients and accessibility tools will show a blank or garbled message. Adding a plain-text part is an engineering task worth requesting.
5. **Emails are sent from the mailbox the system is connected to** — there is no separate "from" address. See §4.1.

---

## 3. What every email is made of today

```
┌─────────────────────────────────────────────┐
│ [1] Intro paragraph  — greeting + the ask   │  ← marketing rewrites (20 versions)
│                                              │
│ [2] "Here is what we still need:"           │  ← marketing rewrites (2 versions)
│     • document 1                             │  ← generated per borrower, do not touch
│     • document 2                             │
│                                              │
│ [3] Footer — brand, NMLS, opt-out           │  ← marketing + COMPLIANCE (2 versions)
└─────────────────────────────────────────────┘
```

There is **no header, no logo, no button, no signature, no physical address**. Every email is a single grey-text paragraph on white. That is the whole design brief: this needs to look like it came from a licensed lender.

The list lead-in line, current copy:

| | Current |
|---|---|
| EN | `Here is what we still need:` |
| ES | `Esto es lo que aun necesitamos:` |

---

## 4. Compliance problems that must be fixed before a single borrower email goes out

These were found by reading the live code. **Items 4.1–4.4 cannot be fixed by marketing alone.**

### 4.1 The sender address does not match the brand — needs IT
Mail is signed "Homesi" but physically sends from **`itsupportaccount@simosolutionsgroup.com`**. To a borrower — and to spam filters — a lending email signed by one brand and sent from an unrelated IT account looks like phishing. The intended address is **`docs@homesi.co`**, which is not yet live and needs SPF/DKIM/DMARC set up. **Marketing's branding work is wasted if this isn't done first.**

### 4.2 The NMLS number has never been filled in — needs compliance
The footer literally renders:

> Homesi · NMLS #—.

An em-dash where the number should be, in both languages. **Compliance must supply the exact required wording.** Note that Homesí is a marketing brand, not the licensed entity — the licensed lender is *Everett Financial, Inc. dba Supreme Lending*. Confirm whether the footer must name the licensed entity, its NMLS ID, a state-license line, and the Equal Housing Lender logo or text.

### 4.3 The footer promises an unsubscribe link that does not exist — needs engineering
Current EN footer:

> You are receiving this about your loan inquiry. Reply STOP to opt out of texts; use the unsubscribe link to stop emails.

There is **no link in the email at all**. Promising an opt-out mechanism and not providing one is the single biggest exposure here. Two things are needed: a real unsubscribe mechanism (engineering), and footer copy that describes what actually exists (marketing + compliance). Until the link exists, the sentence must not claim it.

### 4.4 "Reply STOP to opt out of texts" appears on email-only sends
No SMS is built yet. Every borrower currently receives an instruction about a channel they are not being contacted on. Remove it from the email footer, and keep it for the SMS templates in Phase 2.

### 4.5 Brand is written "Homesi", not "Homesí"
The accent is missing throughout, and there is no "powered by Supreme Lending" attribution anywhere.

### 4.6 The Spanish copy has no accents or tildes — and it shows
The hardcoded Spanish templates were written without accents (`prestamo`, `aun`, `Sigue interesado en avanzar?` with no opening `¿`). But the AI-generated document lines in the *same email* are fully accented and idiomatic (`Por favor, envíe el recibo de servicio público más reciente…`). So one message contains two different registers of Spanish. For the Latino division this is the most visible quality problem in the whole set. **All Spanish copy must be properly accented, with opening `¿` and `¡`.**

### 4.7 No-name fallback in Spanish reads "Hola there,"
When the borrower's first name is unavailable, the system falls back to the English word *there* in both languages. Marketing should supply a proper Spanish fallback greeting (e.g. `Hola,`), and an English one that doesn't read as a mail-merge failure.

---

## 5. Current copy — rewrite in place

Verbatim from the live system. `[NAME]` marks where the first name is inserted.

### Docs Standard — chasing documents

| Step | | Subject | Body |
|---|---|---|---|
| Day 0 | EN | Documents needed for your loan | Hi [NAME], to keep your loan moving we still need the documents below. Please reply to this email with photos or PDFs attached. |
| | ES | Documentos necesarios para su prestamo | Hola [NAME], para avanzar con su prestamo necesitamos los siguientes documentos. Responda a este correo con fotos o PDFs adjuntos. |
| Day +2 | EN | Quick reminder on your documents | Hi [NAME], a quick nudge - we still need the items below. Reply here or text us a photo. |
| | ES | Recordatorio sobre sus documentos | Hola [NAME], un recordatorio - aun necesitamos lo siguiente. Responda aqui o envienos una foto. |
| Day +5 | EN | Still need a few documents | Hi [NAME], here is your updated checklist. Reply with the remaining items when you can. |
| | ES | Aun faltan algunos documentos | Hola [NAME], aqui esta su lista actualizada. Responda con lo que falta cuando pueda. |
| Day +9 | EN | Action needed to keep your loan on track | Hi [NAME], we need the documents below to avoid a hold on your file. Please send them as soon as you can. |
| | ES | Accion necesaria para su prestamo | Hola [NAME], necesitamos los documentos de abajo para evitar una pausa en su expediente. Envielos lo antes posible. |

> ⚠️ "text us a photo" on the day +2 email refers to SMS, which is not built. Remove or defer.
> ⚠️ Tone escalates to "avoid a hold on your file" by day +9. Compliance should confirm that is an acceptable statement.

### Interest Standard — still moving forward?

| Step | | Subject | Body |
|---|---|---|---|
| Day 0 | EN | Are you still looking to move forward? | Hi [NAME], are you still looking to buy? Reply 1 = yes, 2 = need more time, 3 = no longer interested. |
| | ES | Sigue interesado en avanzar? | Hola [NAME], sigue buscando comprar? Responda 1 = si, 2 = necesito mas tiempo, 3 = ya no interesado. |
| Day +3 | EN | Checking in on your home loan | Hi [NAME], just checking in - are you still interested in moving forward? |
| | ES | Seguimiento sobre su prestamo | Hola [NAME], solo confirmando - sigue interesado en avanzar? |
| Day +7 | EN | Last check-in on your home loan | Hi [NAME], last check-in - reply anytime and we will pick up where we left off. |
| | ES | Ultimo seguimiento | Hola [NAME], ultimo mensaje - responda cuando guste y retomamos. |

> The "Reply 1 / 2 / 3" pattern is an SMS convention and reads oddly in email. Worth reconsidering for the email version.

### Appointment — booking a call

| Step | | Subject | Body |
|---|---|---|---|
| Day 0 | EN | Let us find a time to talk | Hi [NAME], would you like to set up a quick call? Reply with a good time. |
| | ES | Busquemos un momento para hablar | Hola [NAME], desea programar una llamada? Responda con un buen horario. |
| Day +2 | EN | Following up on scheduling a call | Hi [NAME], following up - reply with a time that works and we will confirm. |
| | ES | Seguimiento para agendar | Hola [NAME], responda con un horario y lo confirmamos. |
| Day +5 | EN | Last call to schedule | Hi [NAME], last note on this - reply anytime to set up a call. |
| | ES | Ultimo aviso para agendar | Hola [NAME], responda cuando guste para agendar una llamada. |

### Reactivation — Phase 2, design later

| Step | | Subject | Body |
|---|---|---|---|
| Day 0 | EN | Still thinking about a home loan? | Hi [NAME], you looked into a home loan with us - still interested? Reply and we will help. |
| | ES | Aun piensa en un prestamo? | Hola [NAME], usted consulto por un prestamo - sigue interesado? Responda y le ayudamos. |
| Day +4 | EN | Checking back in | Hi [NAME], checking back - reply 1 = yes, 2 = maybe later, 3 = no thanks. |
| | ES | Volviendo a saludar | Hola [NAME], responda 1 = si, 2 = quizas luego, 3 = no gracias. |
| Day +10 | EN | One last note | Hi [NAME], one last note - we are here whenever you are ready. |
| | ES | Un ultimo mensaje | Hola [NAME], estamos aqui cuando este listo. |

> Reactivation is cold outreach to people who are not active borrowers. It carries different consent obligations than live-loan mail and should get its own compliance review.

---

## 6. A real example of what a borrower receives today

Subject: `Still need a few documents [FUR-AMRZABF0P0]`

> Hi Melquiades, here is your updated checklist. Reply with the remaining items when you can.
>
> Here is what we still need:
> - Please share your last 3 months of personal bank statements. Include ALL pages — even blank ones.
> - Please write a brief letter explaining any recent credit inquiries (when you applied for new credit) that appeared on your credit report in the last 90 days. Sign and date the letter.
> - Please share your 2 most recent pay stubs, covering at least 30 days of pay.
>
> <small>Homesi · NMLS #—. You are receiving this about your loan inquiry. Reply STOP to opt out of texts; use the unsubscribe link to stop emails.</small>

The document bullets are the strong part of this email and are already good — they are AI-rewritten from underwriting jargon into plain language. Everything around them needs work.

---

## 7. What to ask each group for

**Marketing**
- 20 subject lines + 20 body paragraphs (10 steps × EN/ES), properly accented Spanish
- The email shell: logo/header, typography, and a footer block
- Spanish and English fallback greetings for when no first name is available
- Keep the `[FUR-XXXXX]` token at the end of every subject

**Compliance**
- Exact required footer wording: licensed entity name, NMLS ID, any state-license line, Equal Housing Lender requirements
- Sign-off on the day +9 "avoid a hold on your file" escalation
- Separate review for the Reactivation cold-outreach set

**IT / engineering (us)**
- Stand up `docs@homesi.co` with SPF/DKIM/DMARC and repoint the sender
- Build a real unsubscribe mechanism before the footer can reference one
- Add a plain-text alternative part
- Add any extra merge fields marketing asks for (loan officer name, branch, etc.)

---

## 8. When these send — for context

Emails only go out **09:00–19:00 Eastern, Monday to Saturday, never Sunday**. A borrower who has opted out is never emailed. A borrower who replies resets their own clock — the next reminder moves out two business days, so nobody receives a reminder right after they have answered. If a borrower asks a question, the automated sequence stops entirely and a human takes over.

Note for compliance: quiet hours are currently evaluated in **Eastern time for every borrower**, not in the borrower's own timezone. A 9:00 AM Eastern send reaches a California borrower at 6:00 AM.
