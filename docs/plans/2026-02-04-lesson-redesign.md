# Lesson Redesign: 11-Lesson Structure

> **Date:** 2026-02-04
> **Status:** Design approved
> **Context:** Incorporates research from claude-md-templates repo, community best practices (Boris Cherny, HumanLayer, Anthropic), and Feb 2026 addendum from new-lesson-plan.md.

---

## Overview

Restructure the course from 9 lessons to 11 lessons. Front-load mental model and core loop before introducing tools. Add dedicated CLAUDE.md and Read/Edit/Verify lessons. Remove Custom Commands, Code Search, Code Review, and standalone Debugging lessons.

### What Changed

| Action | Details |
|--------|---------|
| **Added** | Lesson 2 (CLAUDE.md) and Lesson 3 (Read/Edit/Verify) |
| **Removed** | Custom Commands, Code Search Workflow, Code Review Workflow, Debugging (standalone) |
| **Kept** | MCP Servers, Plugins, Hooks, Worktrees |
| **Reordered** | Mental model first, then core loop, then tools |

---

## Final Lesson Lineup

| # | Lesson | Module | Status |
|---|--------|--------|--------|
| 1 | Context is Everything | Mental Model | Rework |
| 2 | CLAUDE.md - Project's Memory | Mental Model | **New** |
| 3 | Read → Edit → Verify | Core Loop | **New** |
| 4 | Plan Mode | Planning | Exists (was L2) |
| 5 | Spec-Driven Development | Planning | Exists (was L3) |
| 6 | Sub-Agents | Building Blocks | Exists (was L4) |
| 7 | Skills | Building Blocks | Exists (was L5) |
| 8 | MCP Servers | Extensions | Exists (was L6) |
| 9 | Plugins | Extensions | Exists (was L7) |
| 10 | Hooks | Safety | Exists (was L8) |
| 11 | Worktrees | Safety (Capstone) | Exists (was L9) |

---

## Lesson Details

### Lesson 1: Context is Everything

**Module:** Mental Model
**Objective:** Understand that context quality determines output quality

**Exercise:**

1. **Tell Claude something false:** "Important: This project uses PostgreSQL, not SQLite. The files might say SQLite but we migrated to PostgreSQL."
2. **Have Claude read the actual code:** "Read database.py and explain how the database works." (clearly uses SQLite)
3. **Ask the question:** "What database does this project use?" — Watch Claude get confused, hedge, or say the wrong thing.
4. **Run `/context`** — See how much of the context window is used. Ground the concept in real numbers.
5. **Learn Document & Clear** — The practical escape hatch:
   - "Dump your current progress to progress.md"
   - `/clear`
   - "Read progress.md and continue from where we left off"

**Key Takeaway:** Context isn't just about size — contradictory information leads to unreliable outputs. Quality > quantity.

**Verification:**
- Minimum 2 user messages
- Message exists

**Video Script (~60s):**
> "Every time you talk to Claude, it has a context window — a fixed amount of information it can hold. Everything you say, every file it reads, goes into that window. When it fills up, earlier information gets pushed out or ignored.
>
> But here's what most people miss: it's not just about size. It's about quality. If you give Claude contradictory information — say, telling it your project uses PostgreSQL when the code clearly uses SQLite — it gets confused. It might hedge, say the wrong thing, or confidently give you a wrong answer.
>
> In this lesson, you'll see this firsthand. You'll give Claude false information, then have it read the actual code, and watch what happens when you ask a simple question. Then you'll learn the Document and Clear workflow — how to dump progress, clear your context, and start fresh. It's the most useful context management trick you'll learn.
>
> The takeaway: context is finite and quality matters. Everything we teach from here builds on this idea."

---

### Lesson 2: CLAUDE.md - Your Project's Memory

**Module:** Mental Model
**Objective:** Create persistent project context that survives sessions

**Exercise:**

1. **Notice the problem:** Ask Claude how to run tests. It doesn't know. Ask it to explain the project — it has to read every file.
2. **Create CLAUDE.md** with:
   - Project description (1-2 sentences)
   - Stack (Python + SQLite)
   - Key commands (`python main.py`, `pytest -v`)
   - Conventions (type hints, no docstrings unless complex)
3. **Learn the attention budget:** Claude's system prompt already has ~50 instructions. Models reliably follow 150-200 total. Every line in CLAUDE.md competes for attention. Sweet spot: 40-60 lines.
4. **Start a new session** — Claude immediately knows the project without reading every file.

**Key Takeaway:** CLAUDE.md is the highest-leverage file in your project. Keep it lean, keep it accurate.

**Key Concepts from Research:**
- Only add rules Claude can't figure out by reading code
- "Don't X" must include "Do Y instead"
- Progressive disclosure: point to docs when needed, don't embed everything
- The self-improvement loop: when Claude makes a mistake, have it update CLAUDE.md

**Verification:**
- `CLAUDE.md` file exists
- Contains `pytest` or `test`

**Video Script (~60s):**
> "Every time you start a Claude Code session, Claude has zero memory of your project. It doesn't know how to run tests, what your stack is, or your conventions. CLAUDE.md fixes this. It's a file that gets loaded automatically at the start of every session — think of it as your project's memory.
>
> But here's the catch: Claude's system prompt already contains around 50 instructions. Models can reliably follow about 150 to 200 total. So every line you add to CLAUDE.md competes for attention. If you dump 200 lines in there, Claude starts ignoring all of them uniformly.
>
> The sweet spot is 40 to 60 lines. Project description, stack, how to run and test, your conventions, and common gotchas. That's it. If Claude can figure something out by reading your code, don't put it in CLAUDE.md.
>
> In this lesson, you'll create one from scratch and see the difference immediately."

---

### Lesson 3: Read → Edit → Verify

**Module:** Core Loop
**Objective:** Experience Claude's core workflow and teach it to verify its own work

**Exercise:**

1. **Find the bug:** `add_expense()` allows negative amounts — no validation.
2. **Ask Claude to fix it.** Watch the core loop: Claude reads `models.py`, makes a surgical edit (adds `if amount <= 0: raise ValueError`), and reports it's done.
3. **Make Claude prove it:** Tell Claude: "Now run pytest -v and confirm your fix works." Watch Claude run tests, see results, and fix any issues it missed.
4. **Codify verification in CLAUDE.md:** Add rules so Claude always checks its own work:
   ```markdown
   ## Verification
   After any code change, run in this order:
   1. `pytest -v` — fix failing tests
   2. All tests must pass before considering a task complete
   ```

**Key Takeaway:** Claude reads before editing. You verify after. But the real unlock: give Claude a way to verify its own work — it 2-3x's quality (Boris Cherny).

**Verification:**
- `models.py` contains amount validation (`amount <= 0` or `ValueError`)
- `CLAUDE.md` contains verification rules (`pytest` or `test`)

**Video Script (~60s):**
> "Claude's core loop is three steps: read the code, edit it surgically, then verify the change works. In this lesson, you'll see that in action by fixing a real bug — the add_expense function accepts negative amounts.
>
> But here's what most people miss: after Claude makes the fix, you need to tell it to prove it works. Say 'run pytest and confirm your fix works.' Claude will run the tests, see the results, and if anything's broken, fix it without you lifting a finger.
>
> This is the single highest-leverage habit from the Claude Code team: give Claude a way to verify its own work. It 2-3x's the quality of the output.
>
> Then you'll take it one step further — add verification rules to your CLAUDE.md so Claude always checks its own work going forward. Every session, automatically."

---

### Lesson 4: Plan Mode

**Module:** Planning
**Objective:** Use Shift+Tab plan mode for multi-file features

**Exercise:**

1. **Toggle plan mode** (Shift+Tab twice)
2. **Describe the feature:** "Add a reports module with monthly summaries, category breakdowns, and top expenses"
3. **Review Claude's plan** — Does it cover the right files? The right approach?
4. **Push back** on parts that don't look right
5. **Approve and implement** — Claude builds `generate_monthly_report()`, `get_category_breakdown()`, `get_top_expenses()`, `save_report()`

**Key Takeaway:** For complex features, plan first. Review before implementing. Most experienced users start every significant task in Plan Mode.

**Verification:**
- `generate_monthly_report()` not raising NotImplementedError
- `get_category_breakdown()` implemented

**Video Script (~60s):**
> "When you ask Claude to build something complex — say a reports module that touches multiple files — you don't want it to just start coding. You want a plan first.
>
> Press Shift+Tab twice to enter Plan Mode. Claude will research your codebase, draft a plan, and show you exactly what it intends to do before writing a single line of code.
>
> Review the plan. Push back on parts you don't like. Once you approve, Claude implements it step by step. If something goes wrong, you can rewind to the plan.
>
> Most experienced Claude Code users start every significant task in Plan Mode. It's not a special mode — it's the default way of working. Think of it as the difference between building with blueprints versus winging it."

---

### Lesson 5: Spec-Driven Development

**Module:** Planning
**Objective:** Write specifications before code for complex or ambiguous features

**Exercise:**

1. **Create `specs/recurring-expenses.md`** with:
   - Problem statement: Why do we need recurring expenses?
   - Requirements: What must it do? (frequencies, storage, triggering)
   - Non-requirements: What it won't do (explicit scope boundary)
   - Implementation approach: How should it work?
2. **Hand the spec to Claude:** "Implement this following the spec exactly."
3. **Compare result to spec** — Did Claude follow it?

**Key Takeaway:** Plan Mode is a conversation. A spec is a document. Use Plan Mode for medium tasks, specs for complex or ambiguous ones. Better specs = better code.

**Verification:**
- `specs/*.md` exists
- Contains problem/requirements/implementation sections

**Video Script (~60s):**
> "Plan Mode is great for features you mostly understand. But what about features that are ambiguous? Where you're not sure what the requirements are, or there are multiple valid approaches?
>
> That's where spec-driven development comes in. Before any code, you write a short document: what's the problem, what are the requirements, what are the non-requirements, and how should it work.
>
> In this lesson, you'll write a spec for recurring expenses — monthly bills like rent and subscriptions. The spec forces you to answer questions upfront: What frequencies do we support? How do we store them? What happens when a recurring expense triggers?
>
> Once the spec is solid, you hand it to Claude and say 'implement this.' The output is dramatically better because Claude isn't guessing at requirements — it's following a clear contract.
>
> Think of it this way: Plan Mode is a conversation. A spec is a document. Use Plan Mode for medium tasks, specs for complex or ambiguous ones."

---

### Lesson 6: Sub-Agents for Context Isolation

**Module:** Building Blocks
**Objective:** Use sub-agents to keep your main context clean

**Exercise:**

1. **Run `/context`** — note starting context usage
2. **Spawn a sub-agent:** "Use a sub-agent to analyze reports.py and summarize how it generates reports. I just want a summary, not all the details in my context."
3. **Get the summary** — Clean, concise, in your main session
4. **Run `/context` again** — Main session barely moved

**Key Takeaway:** Sub-agents solve the context problem from Lesson 1. Your main session is your desk. Sub-agents are researchers you send to the library.

**Verification:**
- Message exists (sub-agent returned summary)
- Task tool called (sub-agent was spawned)

**Video Script (~60s):**
> "Remember Lesson 1 — context is finite, and filling it with noise leads to worse results. Sub-agents are how you solve that.
>
> A sub-agent is a separate Claude session with its own fresh context window. You tell Claude to spawn one for a research task — 'use a sub-agent to analyze reports.py and summarize how it works.' The sub-agent reads all the files, does the heavy lifting, and sends back a clean summary.
>
> Your main session gets the answer without any of the noise. Run /context before and after — your main context barely moved.
>
> This is context isolation. Use sub-agents for research, exploration, one-off analysis — anything where you need information but don't want to pollute your working context.
>
> The mental model: your main session is your desk. Sub-agents are researchers you send to the library. They come back with a summary, not the entire library."

---

### Lesson 7: Skills (Auto-Activating Commands)

**Module:** Building Blocks
**Objective:** Create skills that activate automatically based on context

**Exercise:**

1. **Create a code-explainer skill** in `.claude/skills/`
2. **Define when it activates** — on code explanation requests
3. **Test it** — Ask Claude to explain a function, see the skill activate

**Key Takeaway:** CLAUDE.md loads every session. Skills load on demand. Use CLAUDE.md for things that always matter. Skills for workflow-specific instructions.

**Verification:**
- `.claude/skills/*/SKILL.md` glob exists

**Video Script (~60s):**
> "Skills are markdown files that Claude loads automatically when it thinks they're relevant. They live in .claude/skills/ and contain instructions for specific workflows.
>
> Think of them as standing instructions. Instead of telling Claude 'remember to run the linter after editing Python files' every time, you write a skill that says exactly that. Claude reads it when it's relevant, ignores it when it's not.
>
> In this lesson, you'll create a code-explainer skill that activates when someone asks Claude to explain code. It'll define how Claude should structure explanations — what to include, what level of detail, what format.
>
> Skills are different from CLAUDE.md. CLAUDE.md loads every session. Skills load on demand. Use CLAUDE.md for things that always matter. Use skills for workflow-specific instructions that only apply sometimes."

---

### Lesson 8: MCP Servers

**Module:** Extensions
**Objective:** Install MCP servers to give Claude new abilities

**Exercise:**

1. **Install context7 MCP server:** `claude mcp add context7 -- npx -y @upstash/context7-mcp@latest`
2. **Use it:** Ask Claude to fetch current FastAPI documentation using the MCP tool
3. **See the result** — Claude now has access to up-to-date library docs it wouldn't have from training data alone

**Key Takeaway:** MCP servers extend Claude's capabilities beyond your local files. Training data has a cutoff — MCP gives Claude access to current information.

**Verification:**
- Message exists

**Video Script (~60s):**
> "So far, Claude can read your files, run commands, and search your codebase. But what if you need it to fetch documentation, query a database, or call an API? That's what MCP servers do.
>
> MCP — Model Context Protocol — is a standard for giving Claude new tools. You install an MCP server, and Claude can use it like any other tool. No code changes, no complex setup.
>
> In this lesson, you'll install context7, an MCP server that gives Claude access to up-to-date library documentation. One command: claude mcp add context7 — and suddenly Claude can look up the latest FastAPI docs, React docs, whatever you need.
>
> The power here is that Claude's training data has a cutoff date. MCP servers give it access to current information. Think of them as plugins that extend what Claude can do beyond reading your local files."

---

### Lesson 9: Plugins

**Module:** Extensions
**Objective:** Install bundled skill collections from the plugin marketplace

**Exercise:**

1. **Connect to marketplace:** `/plugin marketplace add obra/superpowers-marketplace`
2. **Install plugin:** `/plugin install superpowers@superpowers-marketplace`
3. **Test it:** Use the `/brainstorm` skill from the installed plugin

**Key Takeaway:** Plugins are collections of skills packaged by the community. Install what works, customize from there.

**Verification:**
- Message exists

**Video Script (~60s):**
> "In Lesson 7 you created a single skill by hand. Plugins are collections of skills that someone else has built and packaged for you.
>
> Think of the difference between writing a script yourself versus installing a library. Same idea. A plugin might include skills for brainstorming, code review, debugging, deployment — an entire workflow toolkit.
>
> In this lesson, you'll install the superpowers plugin from the marketplace. One command connects you to the marketplace, another installs the plugin. Then you'll test it with the /brainstorm skill — a structured creative thinking workflow.
>
> The plugin ecosystem is how the Claude Code community shares workflows. Instead of every team building their own skills from scratch, you install what works and customize from there."

---

### Lesson 10: Safety Hooks

**Module:** Safety
**Objective:** Create pre/post-command hooks for safety guardrails

**Exercise:**

1. **Create `.claude/hooks/block-dangerous.sh`** — blocks `rm -rf` commands
2. **Register in `.claude/settings.json`** — wire the hook to pre-command events
3. **Test it** — Try a dangerous command, see it get blocked

**Key Takeaway:** Claude can run any command on your machine. Hooks let you set the boundaries — what's allowed, what needs confirmation, and what's never okay.

**Verification:**
- `.claude/hooks/*.sh` glob exists
- `.claude/settings.json` contains "hooks"

**Video Script (~60s):**
> "Claude can run any command on your machine. That's powerful, but it means you need guardrails. Hooks are shell scripts that run before or after Claude executes commands.
>
> In this lesson, you'll create a safety hook that blocks dangerous commands like rm -rf. You write a small script, register it in .claude/settings.json, and now Claude physically cannot run that command — it gets blocked before execution.
>
> You can also create hooks that require confirmation for risky operations like force push, or hooks that automatically run linters after file edits.
>
> Think of hooks as your safety net. Claude is powerful, but you set the boundaries. The best teams use hooks to encode their operational rules — what's allowed, what needs confirmation, and what's never okay."

---

### Lesson 11: Git Worktrees (Capstone)

**Module:** Safety
**Objective:** Work on multiple features safely with git worktrees

**Exercise:**

1. **Create a worktree:** `git worktree add ../feature-branch feature/add-version`
2. **Start Claude in the worktree** — separate session, isolated workspace
3. **Implement feature:** Add `--version` flag to `main.py` printing "Expense Tracker v1.0"
4. **Commit and merge** back to main
5. **Clean up** the worktree

**Key Takeaway:** This is the complete professional workflow — isolated workspaces, safety hooks preventing mistakes, CLAUDE.md ensuring consistency, verification rules catching bugs.

**Verification:**
- Commit exists with pattern "version"

**Video Script (~60s):**
> "This is the capstone. Everything you've learned comes together here: context management, CLAUDE.md, planning, sub-agents, skills, MCP, plugins, and hooks. Now you add the final piece — parallel development.
>
> Git worktrees let you have multiple branches checked out simultaneously. Each worktree can have its own Claude session. You work on a feature in one worktree while main stays stable in another.
>
> In this lesson, you'll create a worktree for a feature branch, start Claude in it, add a version flag to the app, commit, merge back to main, and clean up. The full professional workflow.
>
> This is how teams ship with Claude Code — isolated workspaces, safety hooks preventing mistakes, CLAUDE.md ensuring consistency, and verification rules catching bugs before they merge. You've got the complete toolkit."

---

## Implementation Notes

### New Lessons to Build
1. **Lesson 2 (CLAUDE.md):** Create `levels/02-claude-md/` with lesson.yaml and exercise files. Exercise starts with NO CLAUDE.md — student creates one.
2. **Lesson 3 (Read/Edit/Verify):** Create `levels/03-read-edit-verify/` with lesson.yaml and exercise files. Exercise has the negative-amount bug in `models.py`.

### Existing Lessons to Renumber
| Current Dir | New Dir |
|---|---|
| `01-context-is-everything` | `01-context-is-everything` (rework content) |
| `02-planning-mode` | `04-planning-mode` |
| `03-spec-driven` | `05-spec-driven` |
| `04-sub-agents` | `06-sub-agents` |
| `05-skills` | `07-skills` |
| `06-mcp-servers` | `08-mcp-servers` |
| `07-plugins` | `09-plugins` |
| `08-hooks` | `10-hooks` |
| `09-worktrees` | `11-worktrees` |

### Exercise File Changes
- **Lesson 1:** Update lesson.yaml with conflicting info experiment, remove camelCase exercise
- **Lesson 2:** New exercise dir — same expense tracker but no CLAUDE.md
- **Lesson 3:** New exercise dir — expense tracker with negative-amount bug intact, CLAUDE.md from L2 present but without verification rules yet
- **Lessons 4-11:** Renumber in lesson.yaml, update `number` field and module names

### Verification Types Used
| Type | Lessons |
|------|---------|
| `message_exists` | 1, 6, 8, 9 |
| `file_exists` / `file_contains` | 2, 3, 5, 10 |
| `command_output` | 4 |
| `glob_exists` | 5, 7, 10 |
| `tool_called` | 6 |
| `commit_exists` | 11 |

### Video Scripts
All 11 video scripts written (~60 seconds each). Ready for recording.
