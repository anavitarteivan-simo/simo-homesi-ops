---
description: Update the owning docs after work on a live system
---
Review what changed in this session (tool calls, deploys, workflow edits, git diff).

For each change to a live system:
1. Find the doc that owns that truth using `docs/INDEX.md`.
2. Update it in place with the date (YYYY-MM-DD), the environment, and the Ids involved.
   Mark each claim [Verified], [Likely] or [Unverified].
3. If a fact now contradicts another doc, fix the non-owner to link to the owner instead of
   restating it.
4. If you hit a new trap, append it as the next numbered gotcha in the system's reference doc.

Then show me the diff of the docs and propose one commit message. Do not commit until I confirm.
$ARGUMENTS
