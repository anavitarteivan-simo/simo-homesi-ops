**Borrower Follow-Up System**

Agent & LOA User Guide

Simo Solutions Group  /  Homesí

*How an automated follow-up works from Lead to Opportunity — end to end.*

Screens shown are from the Sandbox (staging) environment.

**Version 11 — 20 August 2026.  Same content as v10, now illustrated: new screenshots for the request-box confirmation, the per-document off-switch on a Lead (Chase With Borrower), a follow-up escalated for missing wording, and an escalation work item. Screens are from the Sandbox (staging) environment, captured with administrator access.**

# Contents

# 1. What this system does

The Borrower Follow-Up system automatically chases borrowers for you. Instead of you remembering to email a borrower for their documents, ask if they are still interested, or nudge them for a meeting, you tell it once what is needed and the system sends the reminders on a schedule, in the borrower’s language, and reacts as soon as the borrower responds.

When the borrower replies — with a document, a question, or a "please call me" — the system reads the reply, files any documents onto the record, and, when a human is needed, hands the borrower off to you with a task, a flag on the record, and a Chatter mention. You never lose a reply, and you are only pulled in when the borrower actually needs a person.

It runs on both Leads and Opportunities, and carries the follow-up across automatically when a Lead converts. The one thing that differs is how you START a chase: on a Lead you type a plain-language request (Section 3); on an Opportunity you tick a checkbox on the document condition and the system translates it for the borrower (Section 4).

## The two things you will see

There are only two records you need to recognize. Keeping them straight makes everything else easy:

- **Borrower Follow-Up (the "follow-up" or "FUR").** This is the automation’s mission — "chase this borrower for X." It runs quietly in the background and holds the status, the schedule, and the history. The system owns it; you rarely edit it directly.

- **Work Item (your to-do).** This is what lands on your plate when a human is needed — an "AI Follow-Up" task on the Opportunity or Lead, shown in your Work Items list. You own these; you work them and mark them done.

**In one line:  **The Follow-Up is the robot’s job; the Work Item is the task the robot hands you when it needs help. Each Work Item links back to the Follow-Up that created it.

## The three kinds of chase

Every follow-up is one of three kinds. The kind decides the message wording and the reminder schedule, and the system works it out from what you asked for:

- **Document Collection** — chasing paperwork (ID, bank statements, pay stubs, letters of explanation). The email lists the specific outstanding items and updates itself as they arrive. Started from a Lead request naming documents, or by ticking Chase With Borrower on an Opportunity condition.

- **Interest Check** — "are you still moving forward?" Used when a borrower has gone quiet and you need to know if they are still in the market. Shorter, softer, invites a one-word reply.

- **Appointment** — getting a call or meeting booked. Asks the borrower for a good time and nudges twice if they do not answer.

**One kind per follow-up:  **A borrower can have more than one running at once (e.g. a document chase AND an interest check) — they are separate conversations on separate schedules, which is why one note should contain one kind of ask.

# 2. Key terms

- **AI Follow-Up Request (the "request box").** The free-text box on a LEAD where you type what you want chased. This is the Sales-Agent starting point. (On an Opportunity you start a chase differently — see Section 4.)

- **Borrower Follow-Up (FUR).** The follow-up "mission" the system creates from your request. Viewable on the Borrower Follow-Ups tab.

- **Chase With Borrower.** The checkbox on a work item / document condition that tells the system to start asking the borrower for that item. Ticking it starts a follow-up (or joins the one already running); unticking it stops that one item. It behaves the same way on an Opportunity and on a Lead.

- **Cadence.** The fixed schedule of reminder messages (e.g. day 0, +2, +5). Different types of chase use different cadences.

- **Work Item.** A to-do record (the "AI Follow-Up" task) the system creates for you when a borrower needs a human.

- **Needs Agent.** A checkbox the system ticks on the Opportunity or Lead when that record needs your attention.

- **Escalated.** A follow-up’s status when the automation has paused and handed the borrower to a human.

# 3. Starting a follow-up from a Lead

Everything begins with you typing a request in plain English (or Spanish) on the Lead. You do not fill out fields or pick document types — you just describe what you need, the way you would tell a teammate.

**Prerequisite:  **The Lead must have a Phone number before it can be saved. If the Phone field is blank, Salesforce will block the save with a "We hit a snag — Phone" message. Add a phone first, then continue.

## 3.1  Create a request

- Open the Lead.

- Click the AI Follow Up Request tab (next to Details).

- Click into the AI Follow-Up Request box (the pencil).

*The AI Follow Up Request tab on a Lead — the empty request box.*

- Type what you want chased, in plain language — one kind of ask per note. Example: "Please collect the borrower’s driver’s license and their two most recent bank statements."

*A plain-language request for documents. You do not need to pick document types or fill in fields — just name what you need.*

- Click Save.

*The saved request. From here the system takes over automatically.*

**Tip:  **Write it the way you would say it out loud — the system works out what kind of chase it is and which documents you named. Keep ONE kind of ask per note: a note is read as a single request, so if you mix "collect these documents" and "book a call" in one note, only one of them starts. Save the note, then type the second ask separately.

## 3.2  Add to a request later (asking for one more thing)

**Expect an empty box.  **Once the system has read your request it CLEARS the box and writes a confirmation into the AI Follow-Up Status field ("AI follow-up started FUR-…"). That is normal — it means it was picked up. You will not see your original wording there afterward.

*After the system picks up a request the box is EMPTY — that is the confirmation, not a loss.*

So to ask for something else later, you do not edit old text — you type the new ask into the (now empty) box. The system attaches it to the follow-up already running for that borrower.

- Open the Lead → AI Follow Up Request tab.

- Click the pencil on the AI Follow-Up Request box (it will be empty).

- Type only the NEW request — for example: "Also need a copy of their most recent pay stub."

- Click Save. On the next run it is added to the same follow-up, so the borrower gets one consolidated ask instead of a second separate thread.

### When it joins the existing follow-up — and when it does not

- **Same kind of request → joins.** Another document request is added to the document follow-up already running for that borrower.

- **Different kind of request → its own follow-up.** Asking for an appointment, or an interest check, starts a separate follow-up — on purpose, because it is a different conversation with its own schedule.

**If you catch it quickly:  **The system checks for new requests every few minutes. If you go back into the box before it has been picked up (the box still shows your text), you can freely edit or rewrite it — it is all read as one request.

## 3.3  Cancelling: two different situations

**Important:  **Clearing the request box does NOT cancel a follow-up. The box is only an inbox for new requests — emptying it does not tell the system to stop anything. Which action you need depends on whether the request has already been picked up.

### A) You just typed it and changed your mind (not picked up yet)

If the box still shows your text, the system has not read it yet. Clearing the text means it will never be read, so no follow-up is created.

- Open the Lead → AI Follow Up Request tab → pencil on the box.

*Your text is still in the box — it has not been picked up yet, so it can still be pulled back.*

- Delete the text so the box is empty.

- Click Save. Nothing further happens — no follow-up is created.

### B) The follow-up is already running (box already empty)

Once the system has read the request, the box is empty and a follow-up exists. At that point clearing the box achieves nothing — you have to stop the follow-up itself:

- Open the Borrower Follow-Ups tab and click the follow-up (or reach it from the record).

- Set Status to Cancelled and save. That is all — Next Touch At is cleared for you automatically, so no further message can go out.

*Stopping a running follow-up: set Status to Cancelled on the follow-up record. Next Touch At clears itself.*

**It also stops by itself when:  **the borrower replies "stop" or "not interested" (opt-out), all requested documents are in, or the cadence runs out and it is handed to a human. You do not need to intervene in those cases.

## 3.4  What happens after you save

Within a few minutes the system reads your request and creates a Borrower Follow-Up (a "mission"). It works out the type (documents, interest check, or appointment) and the specific items from your wording, then begins sending the borrower reminders on the schedule for that type. You do not have to do anything else unless the borrower needs a person.

### How you know it worked

- **The request box goes empty** — the system took it.

- **AI Follow-Up Status shows a confirmation** such as "AI follow-up started FUR-MRZABGFY0."

*The AI Follow Up Request tab after the system has picked up a request: the request box is empty and AI Follow-Up Status carries the confirmation, naming the follow-up it created.*

- **The follow-up appears** on the Borrower Follow-Ups tab (and in the Follow-Up Requests list on the record).

**Note on the Status field:  **AI Follow-Up Status is written by the system but may not be placed on your Lead page yet — if you do not see it, ask your admin to add it. The empty box plus the new follow-up on the tab are the signals you can always see, and any problem is also posted to you as a Chatter @mention on the record.

**If the box still has your text after several minutes:  **The system could not act on it and has asked YOU for more detail — you get a High-priority work item ("AI Follow-Up - Needs detail") in your Work Items list, plus "NEEDS DETAIL" in AI Follow-Up Status and a Chatter @mention on the record. The usual cause is asking for documents without naming any (e.g. just "get docs"), which it deliberately will not guess at. Edit the box to name the documents and save; editing the text is what makes it try again.

## 3.5  Stop asking for one document (without stopping the follow-up)

Once your request has been picked up, each document being chased is a work item on the Lead, carrying the same Chase With Borrower checkbox used on an Opportunity. So you can drop a single item without cancelling anything: open the Lead, find the document in the Work Items card, and untick Chase With Borrower. It comes off the borrower’s list at the next reminder and everything else carries on.

*The Work Items card on a Lead. Every document being chased is a row here, with its due date — including Spanish wording where the borrower is Spanish-speaking.*

*Open a document row to reach the off-switch. Under Borrower Chase (Automation): Chase With Borrower is the tick that starts and stops the asking, Borrower Doc Ask is the plain-language wording the borrower actually receives, and Follow-Up Request links back to the chase it belongs to. Untick Chase With Borrower to drop this one document and leave the rest running.*

**If you untick every item:  **the system sees nothing left to chase, sends no further email, and closes the follow-up as Completed with the Outcome "Chase Cancelled" — so reports never mistake it for documents that were actually received. Marking the documents Completed instead closes it as "All Docs Received."

# 4. Starting a follow-up from an Opportunity

On a loan (Opportunity) you do not type a free-text request. The documents you need are already on the file as work items / conditions — so you simply tell the system which ones to chase, and it turns the underwriting wording into something the borrower can understand.

## 4.1  Ask the borrower for a document

- Open the Opportunity and find the document condition in the Work Items card (or the work item record).

- Tick the Chase With Borrower checkbox on that condition. Repeat for each item you want chased.

- That is it. Within a few minutes the system creates one Borrower Follow-Up for the loan and starts asking.

*A document condition after ticking Chase With Borrower: the internal wording stays in Condition Name, and Borrower Doc Ask holds the plain-language version the borrower receives. Note the Follow-Up Request link.*

**What the AI does here:  **It rewrites the internal condition into plain borrower language and strips the jargon. It also refuses to send anything a borrower cannot action — an internal-only check is left unworded. Rather than stalling silently, it raises a High-priority work item asking you for wording, and the follow-up escalates instead of closing (Section 4.5).

### Real examples from the system

- **Condition: **"{A-0012} Assets - Provide two (2) most recent consecutive months bank statements, all pages, including any large deposit LOE."

- **Borrower sees: **"Please provide your 2 most recent consecutive bank statements (all pages). If any large deposits appear, include a brief letter explaining where that money came from."

- **Condition: **"{C-0025} Credit - Provide signed LOE addressing all credit inquiries within the last 120 days per AUS."

- **Borrower sees: **"Please provide a signed letter explaining the reason for each credit inquiry shown on your credit report from the last 120 days."

## 4.2  Add another document later

Tick Chase With Borrower on the additional condition. It joins the follow-up already running on that loan, so the borrower gets one consolidated list — not a second email thread.

## 4.3  Stop asking for one document

Untick Chase With Borrower on that condition. It drops off the borrower’s list at the next reminder and the chase continues for everything else. No other step is needed — you do not have to edit or cancel the follow-up.

## 4.4  Stop asking for everything

Untick every condition. The system notices there is nothing left to chase, sends no further email, and closes the follow-up as Completed with the Outcome "Chase Cancelled" (so reports do not mistake it for documents actually received). Marking the conditions Completed instead closes it as "All Docs Received".

**Either way:  **no wasted messages and no leftover open follow-up — the checkbox is the only control you need.

## 4.5  When the system cannot word a request

Occasionally a condition cannot be turned into something a borrower can act on — it is an internal underwriting check, or the wording is too ambiguous to guess at. The system will not email a vague request, and it will not quietly pretend the item was collected either. It raises a High-priority work item asking you for wording, and escalates the follow-up instead of closing it.

*A follow-up escalated because a ticked condition had no borrower wording. Status is Escalated, Next Touch At is blank so nothing further is sent, and Escalation Reason tells you exactly what to do: write the request in Borrower Doc Ask, or untick Chase With Borrower.*

**Your two options:  **reword the item in Borrower Doc Ask so the borrower receives something they can act on, or untick Chase With Borrower if it was never a borrower-facing item to begin with. Either way the chase continues normally for every other document on the loan.

# 5. What the automation does for you

Once a follow-up exists, the system runs it on a fixed, sensible schedule so borrowers are nudged without being spammed:

- It sends the borrower a first message, then follows up on a set schedule (roughly a couple of days later, then a few days after that) — each message a little more direct.

- Each message **lists the specific items still outstanding** — the actual documents you asked for, not a generic nudge — and is written in the borrower’s language (English or Spanish) based on the request.

- It only sends during business hours (currently 9am–7pm Eastern) and never on Sundays.

- It never messages a borrower who has opted out — on either a Lead or an Opportunity.

- Every borrower reply resets the clock — the next reminder is pushed out a couple of business days, so the robot never emails right after the borrower has already answered. If they ask a question or ask to stop, the reminders stop entirely.

- If the borrower never responds the follow-up eventually runs out, and what happens then depends on the kind of chase. A document chase or an appointment request is handed to you as a work item. An interest check simply closes itself as "No Response" with no task — deliberately, so a quiet borrower on a soft ask does not manufacture work for you. Either way nothing sits chasing forever.

# 6. Seeing your follow-ups

You can see every follow-up in one place, and you can see a specific borrower’s follow-ups on their record.

## 6.1  The Borrower Follow-Ups tab

Open the **Borrower Follow-Ups** tab (use the App Launcher — the grid icon top-left — and search "Borrower Follow-Up" if you don’t see the tab). Three ready-made list views:

- **Open FURs** — everything currently in motion.

- **Escalated – Needs Human** — the follow-ups waiting on a person. This is your queue.

- **All FURs** — the complete list.

*The Borrower Follow-Ups tab, Open FURs list — status, type, cadence, next touch, requesting agent, and the linked Opportunity or Lead.*

Switch the view (the dropdown next to the title) to "Escalated – Needs Human" to see only the follow-ups waiting on a person:

*The Escalated – Needs Human view: your queue of borrowers who need a human response.*

## 6.2  Anatomy of a follow-up record

Open any follow-up to see its full state. The fields worth knowing:

- **Status** — where the follow-up is (Active, Awaiting Reply, Docs Partial, Escalated, Completed, Opted Out, Dead, Cancelled).

- **Type ****&**** Cadence** — what is being chased and on which schedule.

- **Next Touch At / Last Inbound At** — when the next reminder is due and when the borrower last replied.

- **Escalation Reason** — if escalated, the borrower’s own words (kept in their language).

- **Related lists** — Work Items (both the documents being chased and any escalation task), Outbound Messages (every email sent), and Files (documents the borrower sent). There is no separate "Requested Documents" list any more: a requested document IS a work item, which is why you can edit it, renote it, or switch it off exactly like any other task.

*A Borrower Follow-Up record. Note the Escalation Reason captured in the borrower’s own language.*

# 7. When the borrower replies

Borrower replies come back to the shared documents inbox, and the system handles them automatically:

- **They send a document** — the file is saved onto the record (Files) and the follow-up moves to "Docs Partial." The document is filed even when the same email also needs a person.

- **They say they will send it / acknowledge** — the follow-up is snoozed a couple of business days and keeps running.

- **They ask a question or want a call** — the follow-up is escalated to you (see below).

- **They say "stop" / "not interested"** — the follow-up is closed and no more messages go out.

- **They do two things at once** — one reply can attach a pay stub AND ask a question. Both are handled: the document is filed and the question is escalated to you. You will not lose the question just because a file came with it.

Every matched reply adds a dated line to the follow-up’s AI Summary — the intent, a one-line summary in the borrower’s language, and a note when documents arrived or were promised. That field keeps the most recent entries (about 4,000 characters), so on a very long thread the oldest lines eventually roll off. Escalation Reason holds the specific question the borrower asked rather than their whole email, so you can see what is being asked at a glance; their full message is on the work item’s Latest Note and in its Notes History.

*A work item created by the system. Latest Note carries the reason, and the linked Follow-Up Request shows which automated chase it came from.*

# 8. Escalations — when the borrower needs you

When a borrower asks something the automation should not answer, or asks for a person, the follow-up is handed to you in four ways at once. This works identically on a Lead and on an Opportunity — only the record it lands on differs:

- **A Work Item is created** on the Opportunity (or Lead) — an "AI Follow-Up" task, High priority, due the next business day, owned by the requesting agent, carrying the borrower’s question in the Latest Note and a link back to the follow-up.

- **The record is flagged** — the Needs Agent checkbox is ticked on the Opportunity or Lead.

- **You are @mentioned in Chatter** on the record, so you get a notification.

- **The follow-up itself pauses** — its Status becomes Escalated, Escalation Reason is filled with what the borrower asked, and Next Touch At is cleared, so no further automated email can go out while it sits with you.

Nothing further is needed from the automation’s side — it will not keep chasing while you are handling the borrower. Every escalated reply is also logged centrally, so the team can spot questions that keep recurring and answer them earlier in the wording.

### Where you see it on the record

*An Opportunity: the Work Items card (your tasks) and the Follow-Up Requests related list on the right.*

*The Chatter @mentions the system posts on the record when a borrower needs a person — one per escalation, with the reason.*

### Working the task

Open the Work Item to see what the borrower said and what is needed. The Latest Note holds the borrower’s own words; the Notes History keeps every entry, newest first.

*An AI Follow-Up Work Item — High priority, the borrower’s message in Latest Note, full history newest-first, linked to the Opportunity.*

- Reach out to the borrower however you normally would.

- Add a note on the Work Item as you go (it is kept in the history).

- When you are done, just mark the Work Item complete. That single action restarts the follow-up (next reminder one business day out), clears the Needs Agent flag, and advances the chase one step so the borrower is not re-sent the message they already had — you do not have to touch the follow-up record at all.

*An escalation work item. Priority High, due the next business day, the borrower’s question in Latest Note, the timestamped history below it, and the Opportunity it belongs to on the right. Marking this complete is what restarts the follow-up.*

**Good to know:  **If the same borrower sends another message before you finish, the system updates the same Work Item with the newest note rather than piling up duplicates — so you always have one live task per follow-up.

### When completing the work item does NOT resume the follow-up

Resuming is deliberately conditional. If the borrower opted out, or the follow-up was closed as Dead or Cancelled while you were working the escalation, completing your work item does not restart it — someone who asked to stop is never put back into an automated sequence. Your work item still closes normally.

**One other exception:  **the "AI Follow-Up - Needs detail" item. That one exists precisely because no follow-up was ever created, so completing it starts nothing. Edit the request box to name what you need — editing the text is what starts the follow-up (Section 3.4).

# 9. Lead → Opportunity: nothing is lost on conversion

When a Lead converts to an Opportunity, the follow-up does not start over and nothing falls through the cracks. Automatically, at the moment of conversion:

- Every open follow-up on the Lead is re-pointed to the new Opportunity.

- Every open Work Item on the Lead is moved to the new Opportunity.

- Any documents the borrower already sent stay attached and follow along.

In practice: a Sales Agent can start a follow-up on a Lead, and when the loan becomes an Opportunity the LOA inherits the live follow-up and the same to-do list — same thread, same history, no re-typing.

**What changes for you:  **After conversion you will find the follow-up and Work Items on the Opportunity (not the Lead). The Borrower Follow-Ups tab shows the Opportunity in the "Opportunity" column once converted.

# 10. Quick reference — what you can do

## On a Lead

- **Create a follow-up:** type a request in the AI Follow Up Request box and Save (Section 3.1).

- **Read follow-up status:** the Borrower Follow-Ups tab, or the Follow-Up Requests related list / Work Items card on the Lead.

- **Add another ask later:** type the new ask into the (now empty) request box and Save — it joins the running follow-up (Section 3.2).

- **Pull back a request you just typed:** clear the box before it is picked up (Section 3.3A). To stop a follow-up that is already running, set its Status to Cancelled (Section 3.3B).

- **Answer a "needs detail" ask:** If a request was too vague you get an "AI Follow-Up - Needs detail" work item. Edit the request box to name the documents and save — the item closes itself once the follow-up starts.

- **Work an escalation:** Leads escalate exactly like Opportunities — you get an "AI Follow-Up" work item on the Lead, the Needs Agent box ticked, and a Chatter @mention. Open it, act, add a note, mark it complete (Section 8).

- **Create a manual task:** use the Work Items card ("Create your lead tasks here") for your own to-dos, separate from the automation.

- **Stop asking for one document:** untick Chase With Borrower on that document’s work item on the Lead — the rest of the chase continues (Section 3.5).

- **Cancel the whole follow-up:** set the follow-up’s Status to Cancelled (Section 3.3B).

## On an Opportunity

- **Read follow-up status:** the Follow-Up Requests related list and the Work Items card on the Opportunity.

- **Work an escalation:** open the AI Follow-Up Work Item, act, add a note, mark complete (Section 8).

- **See the flag:** the Needs Agent checkbox shows the Opportunity needs attention.

- **Documents:** anything the borrower sent appears in the Files area of the Opportunity / follow-up.

- **Stop asking for one document:** untick Chase With Borrower on that condition — everything else keeps being chased (Section 4.3). Untick them all and the follow-up closes itself as "Chase Cancelled" (Section 4.4).

- **Resume after an escalation:** mark the AI Follow-Up work item complete. That is the whole action — the follow-up restarts one business day later (Section 8).

# 11. Troubleshooting & FAQ

### I saved the request box but got a "We hit a snag — Phone" error.

The Lead needs a Phone number before it can be saved. Add a phone, then save the request again.

### My request box went blank — did I lose it?

No. An empty box means the system read your request and started the follow-up. Check AI Follow-Up Status for the confirmation, and the Borrower Follow-Ups tab for the new follow-up. Your original wording is kept on the follow-up record (Request Text).

### I typed a request and the box still has my text after several minutes.

The system could not act on it and has asked you for more detail. The usual cause: you asked for documents without naming any — "please get the docs" gives it nothing specific to chase, so it deliberately refuses to guess rather than send the borrower a vague request.

You get three signals, strongest first:

- **A work item** called "AI Follow-Up - Needs detail" appears in your Work Items list — High priority, due the next business day, with the reason in Latest Note.

- **AI Follow-Up Status** on the record reads "NEEDS DETAIL: name the documents to collect".

- **A Chatter @mention** on the record explaining what is missing.

To fix it: edit the box to name the documents (e.g. "driver’s license and last two bank statements") and save. Editing the text is what tells the system to try again — there is no button to press. Once it starts, the work item closes itself.

**Your text is safe:  **A request the system cannot act on is left exactly as you typed it, and nothing is sent to the borrower. It will not keep re-reading the same wording either — it waits for you to change it, so it costs nothing to leave it sitting there while you find out what underwriting needs.

### I asked for one more document and a second follow-up appeared.

A second document request joins the existing document follow-up. But a different kind of ask — an appointment, or an interest check — intentionally starts its own follow-up, because it is a separate conversation on its own schedule. Both are normal.

### I asked for the same document twice — will the borrower be asked twice?

No — it is deduplicated. A new ask is matched against the documents already outstanding on that follow-up and, instead of adding a second line, the existing one is updated. It matches across languages too, so an English request for "driver’s license" will not duplicate a Spanish "Licencia de conducir" already being chased. And if the new ask is bigger — three months of statements where two were outstanding — the larger ask wins, so the borrower is asked once, for three.

### The borrower replied but I did not get a task.

You only get a task when the borrower needs a person: a question, or a request for a call. "I’ll send it," or a document on its own, does not create one — the document is filed and the follow-up keeps running. A question buried in an email that also contains a document DOES create a task. Automatic replies (out-of-office, no-reply system mail) are screened out on purpose and never create tasks. If a genuine reply could not be matched to a follow-up, the team is emailed and any attachments on it are still saved, so nothing is lost.

### Do I get a task when a borrower’s out-of-office replies?

No. Out-of-office and other automatic replies are detected and skipped. They are logged for the team but never escalate, never move the follow-up, and never create work for you. It also means an auto-reply does not count as the borrower answering — the reminder schedule carries on unchanged.

### There are two follow-ups on one borrower — is that wrong?

Not necessarily. A borrower can have more than one follow-up at a time (for example, a document chase and an interest check). Each runs on its own.

### How do I stop the messages to a borrower?

To stop everything: open the follow-up and set Status to Cancelled (Section 3.3B) — Next Touch At clears itself, so that one change is enough. To stop asking for a single document, untick Chase With Borrower on that work item and leave the rest running (Sections 3.5 and 4.3). Clearing the request box will NOT stop a follow-up that is already running; the box is only an inbox for new requests. The system also stops on its own if the borrower opts out or says they are not interested.

### A borrower said "stop" — is that handled automatically?

Yes. The follow-up is closed as Opted Out, no further messages are sent, and the email opt-out box is ticked on their Lead or Opportunity so other Salesforce email respects it too. You do not have to do anything.

# Appendix A — Reminder schedule by type

Day 0 is when the follow-up starts. Each step is one email; the wording gets progressively more direct. If the borrower replies at any point the clock resets, and when the last step passes with no answer the follow-up is handed to a human (or closed) as shown in the last column.

## Document Collection ("Docs Standard")

- **Day 0** — "Documents needed for your loan" + the list of what is outstanding.

- **Day +2** — quick reminder, same list.

- **Day +5** — updated checklist ("here is what is still missing").

- **Day +9** — more direct: action needed to keep the loan on track.

- **Day +12 — end of cadence** — no more emails; handed to a human (Escalated).

## Interest Check ("Interest Standard")

- **Day 0** — "Are you still looking to move forward?" (reply 1 = yes, 2 = need more time, 3 = no longer interested).

- **Day +3** — checking in.

- **Day +7** — last check-in.

- **Day +10 — end of cadence** — closed as Dead / No Response.

## Appointment

- **Day 0** — "Let us find a time to talk" — asks for a good time.

- **Day +2** — following up on scheduling.

- **Day +5** — last call to schedule.

- **End of cadence** — handed to a human.

**Two things that always apply:  **emails only go out 9am–7pm Eastern and never on Sundays; and a borrower who opts out is never messaged again on either a Lead or an Opportunity. The exact day offsets are configuration — IT can change them without a redeploy, so check with your admin if the timing looks different.

# Appendix B — Follow-up statuses

- **Active** — newly created, about to start.

- **Awaiting Reply** — a reminder went out; waiting on the borrower.

- **Docs Partial** — the borrower has sent some documents.

- **Escalated** — paused and handed to a person (your queue).

- **Completed** — finished. Check the Outcome field for why: "All Docs Received" (the borrower delivered everything) or "Chase Cancelled" (the team stopped asking).

- **Opted Out** — the borrower asked to stop.

- **Dead** — no response / not interested; closed.

- **Cancelled** — stopped manually (see Section 3.3B).