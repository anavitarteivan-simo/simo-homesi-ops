*LOA1 **&** LOA2 Follow-Up Task Playbook*

**LOA1 ****&**** LOA2**

**Follow-Up Task Playbook**

*A step-by-step guide for working First Touch tasks in Salesforce*

Simo Solutions Group / Homesi

Version 1.0 — May 2026

# 1. What This Playbook Covers

This guide walks you, the LOA1 or LOA2 assigned to an Opportunity, through the full lifecycle of a First Touch task — from the moment the task lands in your queue, to reaching the Borrower, to posting the mandatory Chatter comment on the Opportunity that auto-completes the task.

Read it once end-to-end so you understand what the system is doing for you automatically. After that, use the Quick Reference and Troubleshooting sections as your day-to-day cheat sheet.

## Who this is for

- Anyone assigned to an Opportunity as LOA1 or LOA2.

- LOAs covering for a teammate (you'll get the same tasks they would).

- Managers who want to understand what their LOAs are working from.

Note: Processor Jr and other follow-up roles use a separate workflow and are NOT covered in this playbook.

## Quick overview of the workflow

- An Opportunity is assigned to you *(either automatically from Encompass or manually by the LOA Team Lead)*.

- Salesforce creates a "First Touch" task for you on that Opportunity.

- You reach out to the Borrower.

- You log the contact by posting a Chatter comment on the Opportunity *(not on the task — on the Opportunity record itself)*. The Chatter post is **mandatory** and must be made by you, the task owner.

- Salesforce automatically marks your First Touch task as Completed the moment your Chatter post lands.

- Coverage exception: **if you are covering for another LOA who is out, you cannot trigger their auto-completion (because you are not the task owner). In that case, manually mark the task Completed instead.**

# 2. How Tasks Get Assigned to You

There are two ways you can end up with a First Touch task. The end result is the same task on the same Opportunity — only the trigger differs.

## Path A — Automatic assignment from Encompass (the LOS)

When a loan is created or updated in Encompass and pushed to Salesforce, the integration writes your name into the LOA or LOA 2 text field on the Opportunity. Salesforce then looks up your User record by name, populates the matching LOA1 or LOA2 lookup field, and creates your First Touch task — all without anyone touching the record in Salesforce.

| **Heads up** If your name in Salesforce doesn't exactly match how it's spelled in Encompass, the lookup fails and the task won't be created. If you suspect a name mismatch (you know you should have a task and you don't), see the Troubleshooting section. |
| --- |

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture an Opportunity record showing the LOA and LOA 2 fields populated from Encompass* |
| --- |

## Path B — Manual assignment from the Opportunity

The LOA Team Lead can also assign you directly from the Opportunity:

- Open the Opportunity record.

- Click into the LOA1 or LOA2 lookup field.

- Search for and select your name.

- Save the record.

The task is created the moment the record is saved.

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture the Opportunity record with the LOA1 / LOA2 lookup field being edited* |
| --- |

# 3. Anatomy of a First Touch Task

Every task you receive follows the same naming convention and lives in the same place.

## Task subject

The subject tells you immediately which role you've been assigned and which loan it belongs to:

| **Your role** | **Task subject** |
| --- | --- |
| LOA1 | First Touch - LOA1 - <Opportunity Name> |
| LOA2 | First Touch - LOA2 - <Opportunity Name> |

## Where the task lives

- **On the Opportunity record **— under the Activity timeline / Open Tasks section.

- **On your home page **— in the "Today's Tasks" or "My Tasks" component.

- **In the Salesforce report **(Tasks and Events folder) called **First Touch and Follow Ups - Open**. This is the recommended way to pull your daily list — it shows every open First Touch task assigned to you in one place.

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture the **"**First Touch and Follow Ups - Open**"** report showing the user**'**s open First Touch tasks* |
| --- |

## Due date

New First Touch tasks open with a near-term due date. The task stays open with that due date until either (a) you post a Chatter comment on the Opportunity, which auto-completes the task, or (b) you manually mark it Completed yourself. There is no recurring follow-up cycle on a First Touch task — once it's done, it's done.

# 4. Your Daily Workflow — Step by Step

This is the routine you will run every day on each open First Touch task assigned to you.

## Step 1 — Find your tasks for the day

- Open Salesforce.

- Navigate to the Reports tab.

- Open the report **First Touch and Follow Ups - Open** (in the *Tasks and Events* folder).

- Sort by Due Date, ascending. Work the oldest dates first.

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture the **"**First Touch and Follow Ups - Open**"** report opened, sorted by Due Date* |
| --- |

## Step 2 — Open the task and review context

- Click the task subject to open it.

- Click the linked Opportunity name (in the Related To field) to open the loan record in a new tab.

- Review key fields on the Opportunity: *Current Milestone, Loan Officer, Branch, Borrower contact info, and any notes in the Description.*

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture an open First Touch task showing Subject, Related To, and Due Date* |
| --- |

## Step 3 — Reach out to the Borrower

LOA1 and LOA2 First Touch tasks are exclusively for Borrower contact. Make the call, send the email, or text the borrower — whatever you'd normally do for first-touch outreach. You are not expected to chase title, agents, appraisers, or other third parties from this task.

## Step 4 — Post a Chatter on the Opportunity (mandatory)

Once you've made contact, you MUST log it by posting a Chatter comment on the Opportunity. This is not optional — it is the standard way to close out a First Touch task and is what triggers Salesforce to auto-complete the task. Posting on the Opportunity also leaves an audit trail of what you did, visible to the LO, your manager, and anyone else with access.

- Open the **Opportunity** record (not the task — this is the key difference).

- Click in the Chatter / Post box at the top of the Opportunity feed.

- Write a short note describing the contact: who you reached, by what method, what they said, what's outstanding.

- Click Share. The post must be made by **you, the task owner** — a Chatter post by anyone else (the LO, a manager, the other LOA) will NOT complete your task.

**Example: ***"**Spoke with borrower at 10:32 AM. Confirmed receipt of welcome packet. Borrower will upload pay stubs by EOD tomorrow.**"*

Within seconds, Salesforce automatically marks your First Touch task as Completed.

| **[ SCREENSHOT PLACEHOLDER ]** — *Capture the Chatter post box at the top of an Opportunity record with an example post being typed* |
| --- |

| **Important — who can trigger the auto-completion** The Chatter-on-Opportunity auto-completion ONLY fires when the post is made by the User who owns the task. If the LO, your LOA Team Lead, or your fellow LOA posts a Chatter on the Opp, your task stays open. Only YOUR Chatter post completes YOUR task. |
| --- |

## Step 5 — Coverage exception: manually mark the task Completed

The ONE situation where you skip the Chatter post is when you are covering for another LOA who is out of office. Because the auto-completion is gated on the task owner being the one who posts, a Chatter posted by you (the cover person) would not close the absent LOA's task — Salesforce would leave it open and dangling.

In coverage scenarios:

- Do the outreach to the Borrower yourself.

- Open the absent LOA's task (it's still owned by them) and **manually set Status to Completed**. Save.

- Add a brief note in the task's Comments field describing what you did, so the absent LOA has context when they return.

This is the only path that bypasses the Chatter requirement. In every other situation, you, the task owner, post the Chatter on the Opportunity.

# 5. What the System Does for You Automatically

You don't need to memorize all of this, but it helps to know what's happening behind the scenes so you can recognize unusual behavior.

## Duplicate prevention

Two different flows can both try to create a First Touch task for the same role on the same Opportunity — one when Encompass pushes data, and one when the LOA Team Lead picks you manually in the UI. Without protection, you'd sometimes end up with two identical tasks.

As of May 2026, both flows now check for an existing open task for you (same Opportunity, same owner, same subject prefix) before creating a new one. If one already exists, the system skips creating a duplicate. You should not see two identical First Touch tasks on the same Opportunity. If you do, see Troubleshooting.

## Chatter-driven auto-completion

When you (the task owner) post a Chatter comment on the Opportunity that owns your First Touch task, an automated flow runs in the background and marks the task as Completed. The Chatter post must be on the Opportunity record — not on the task, not on the borrower's Contact — and it must be posted by you, the task owner. Posts by anyone else do not complete your task.

## Assignment Date stamping

When you (or the LOS integration) are assigned to an Opportunity as LOA1 or LOA2, the system also stamps a date on the Opportunity itself (LOA1 Assignment Date / LOA2 Assignment Date). Managers use this to track how long you've been on a file.

# 6. Troubleshooting & FAQ

## "I expected a First Touch task but didn't get one"

Most common causes, in order of likelihood:

- **Name mismatch between Encompass and Salesforce. **If the LOS wrote a name into the LOA or LOA 2 text field that doesn't exactly match your Salesforce User Name, the system can't resolve you and won't create a task. Check the Opportunity record — does the text field show your name correctly?

- **You****'****re not actually assigned. **Open the Opportunity and verify that your name appears in the LOA1 or LOA2 lookup field.

- **Task already exists. **The duplicate-prevention guard suppresses a second task if you already have one open for that Opportunity. Check My Tasks for an existing one.

If none of these explains it, contact IT Support.

## "There are two First Touch tasks for the same Opportunity assigned to me"

This should not happen after the May 2026 duplicate-prevention fix. If it does, close one of them (it doesn't matter which — they're identical) and report it to IT Support so we can investigate.

## "I posted a Chatter on the Opportunity but my task didn't auto-complete"

Most common causes:

- **You posted on the wrong place. **The post must be on the Opportunity record — not on the task itself, not on the borrower's Contact, not on the Account. If you posted on the task, the auto-completion won't fire.

- **Someone else made the post. **The auto-completion only fires when YOU (the task owner) make the Chatter post. A post by the LO, the LOA Team Lead, your fellow LOA, or anyone else does not count.

- **Brief delay. **The automation runs within seconds, but occasionally Salesforce has a short delay. Refresh after 30–60 seconds; the task should be Completed.

If none of the above applies and the post you made is correct, contact IT Support.

## "I'm covering for another LOA who's out — how do I handle their First Touch tasks?"

See Step 5 — Coverage exception. The short version: do the outreach yourself, then open the absent LOA's task and manually set Status to Completed. You cannot use the Chatter-on-Opportunity auto-completion path because the automation requires the task owner (the absent LOA) to be the one who posts. Add a quick note in the task's Comments field so the absent LOA has context when they return.

# 7. Quick Reference Card

Cut this section out and keep it next to your monitor.

## Daily workflow at a glance

- Open Salesforce → Reports → **First Touch and Follow Ups - Open** (Tasks and Events folder) → sort by Due Date ascending.

- Open oldest task → click the linked Opportunity in a new tab.

- Call / email / text the Borrower.

- **Post a Chatter on the Opportunity **(as the task owner) describing the contact. This is mandatory.

- Salesforce auto-completes your task. Move on to the next one.

- **Coverage exception only: **if you are covering for an absent LOA, skip the Chatter and manually set the task Status to Completed.

## Do / Don't

| **Do** | **Don****'****t** |
| --- | --- |
| Post your Chatter on the OPPORTUNITY record. | Don't post on the task — the auto-completion only fires from a post on the Opportunity. |
| Make sure YOU (the task owner) are the one posting the Chatter. | Don't expect the LO's, LOA Team Lead's, or someone else's Chatter to close your task — only yours will. |
| Manually mark Completed ONLY when covering for an absent LOA. | Don't skip the Chatter on your own tasks — it's mandatory and creates the audit trail. |
| Close tasks when work is done. | Don't leave finished work as Open — it skews everyone's reporting. |

## Need help?

For anything that doesn't match what's in this guide — missing tasks, duplicate tasks, name mismatches, broken automation — contact IT Support at itsupportaccount@simosolutionsgroup.com with the Opportunity Name and a brief description of what you expected versus what happened.

Simo Solutions Group  —  Page  of