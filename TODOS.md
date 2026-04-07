# TODOS

## v1 — Killer Lesson

### Handle ~/expense-tracker/ already existing on save
When the user clicks "Save my code," the backend copies the workspace to ~/expense-tracker/. If that directory already exists (user ran the lesson before), the copy could silently overwrite previous work. Fix: check if dir exists, append `-2`, `-3`, etc. Or warn in UI.
- **Why:** Prevents data loss for repeat users
- **Blocked by:** Save-workspace endpoint implementation

### Test CLAUDE.md steering prompt
Run the killer lesson 5 times end-to-end. Check if Claude consistently builds a single HTML file vs scaffolding React/Next.js. If steering fails >1/5 times, strengthen the CLAUDE.md prompt wording. The fallback glob catches HTML files elsewhere, but the UX is confusing if Claude builds in src/pages/.
- **Why:** Biggest verification risk — if index.html doesn't exist, Phase 3 fails and users get stuck
- **Blocked by:** Killer lesson YAML + workspace setup implementation

### Write Show HN post draft
Draft the Show HN post before shipping. Headline: "Zero to working app. You + Claude Code. 20 minutes." Body needs: what this is, why it's different, link to repo. Use /show-hn or /hn-writing skills.
- **Why:** HN posts with strong descriptions get more traction. Writing after shipping is always worse.
- **Blocked by:** v1 implementation complete

## v1.1 — After Signal

### Choose-your-own-app (3 options)
Let users pick: Budget Tracker, Todo List, or Personal Website. Requires 3 CLAUDE.md templates and verification rule adjustments per app type.

### Share button on completion
Copy-to-clipboard message: "I just built a working app in 20 minutes with Claude Code! [link]"

### Completion confetti + screenshot
Confetti animation on Phase 5 completion. Screenshot capture for social sharing.
