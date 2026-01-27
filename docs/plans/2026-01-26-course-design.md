# Claude Code Course - Design Document

**Goal:** Transform the Claude Code Game into a paid, comprehensive course with video lessons + interactive exercises.

**Format:** Watch → Do (video lesson, then hands-on exercise in sandbox)

**Duration:** ~2.5 hours across 12 lessons

---

## Curriculum

### Module 1: Mental Model

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 1 | Context is Everything | LLMs as pure functions, context quality curve, tool architecture | Ask Claude "what does this todo app do?" |
| 2 | Your First Bug Fix | Watch Claude read → edit → verify workflow | Tell Claude to fix the bug and verify it works |

### Module 2: Context Control

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 3 | CLAUDE.md | High-leverage context, what belongs, what doesn't | Create a CLAUDE.md file for the project |
| 4 | Monitor & Manage | /context command, context warnings, when to start fresh | Fill context, run /compact |

### Module 3: Planning & Specs

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 5 | Spec-Driven Development | Write the spec first, Claude implements to spec | Write a spec for "add due dates", have Claude implement |
| 6 | Planning Mode | Think → plan → execute, checkpoints, iteration | Use plan mode to add priority levels (high/medium/low) |

### Module 4: Real Workflows

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 7 | Testing & Debugging | Write tests, debug errors, TDD with Claude | Have Claude write tests, then fix any failures |
| 8 | Git Integration | Commits, PRs, /rewind, checkpoints | Make a change, commit, /rewind, try different approach |

### Module 5: Power Features

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 9 | Skills | Markdown + scripts, dynamic loading, when to use | Create a /lint skill that runs the linter |
| 10 | MCP Servers | When to use MCP vs skills, token cost tradeoffs | Add a file search MCP and use it |

### Module 6: Scale

| # | Lesson | Video Focus | Exercise |
|---|--------|-------------|----------|
| 11 | Parallel Work | Git worktrees, sub-agents, context isolation | Create a worktree, implement a feature in isolation |
| 12 | Hooks & Safety | Guard rails, automation, full workflow demo | Add a pre-commit hook that blocks dangerous commands |

---

## Lesson Structure

Each lesson consists of:

```
levels/
  01-context-is-everything/
    lesson.yaml          # metadata, video URL, exercise config
    exercise/            # sandbox files for this lesson
      todo.py
      test_todo.py
      README.md
```

### lesson.yaml Schema

```yaml
id: "context-is-everything"
number: 1
module: "Mental Model"
title: "Context is Everything"

video:
  url: "https://vimeo.com/xxx"    # external hosted video
  duration_seconds: 240

exercise:
  intro: |
    Now try it yourself. You have a simple todo app in front of you.
    Ask Claude to explain what it does.

  objective: "Have a conversation with Claude about the codebase"

  verification:
    - type: message_exists         # assistant responded

  hints:
    - after_minutes: 2
      text: "Try asking Claude 'what does this todo app do?'"

  success: |
    Great! You just had your first conversation with Claude Code.
    Notice how Claude read the files to understand the code before responding.
```

---

## Verification Types

Backend verifies completion by parsing `messages.jsonl`:

| Type | Description | Example Use |
|------|-------------|-------------|
| `message_exists` | Any assistant message exists | Lesson 1: first conversation |
| `tool_called` | Specific tool was used | Check if Read, Edit, Bash called |
| `file_exists` | File exists in sandbox | CLAUDE.md created |
| `file_contains` | File contains pattern | Bug fix applied |
| `command_output` | Command returns expected result | Tests pass |
| `commit_exists` | Git commit was made | Git integration lesson |

---

## UI Flow

### Start Screen
- Course title and description
- "Start Course" or "Continue" button
- Progress indicator (X of 12 lessons complete)

### Lesson Screen (Video Phase)
```
┌─────────────────────────────────────────────────────────┐
│  Module 1: Mental Model                                 │
│  Lesson 1: Context is Everything                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    ┌─────────────┐                      │
│                    │             │                      │
│                    │   VIDEO     │                      │
│                    │   PLAYER    │                      │
│                    │             │                      │
│                    └─────────────┘                      │
│                                                         │
│                  [ Start Exercise → ]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Lesson Screen (Exercise Phase)
```
┌──────────────────┬──────────────────────────────────────┐
│                  │                                      │
│  Lesson 1        │                                      │
│  Context is      │         TERMINAL                     │
│  Everything      │         (xterm.js)                   │
│                  │                                      │
│  ────────────    │                                      │
│                  │                                      │
│  Objective:      │                                      │
│  Ask Claude to   │                                      │
│  explain the     │                                      │
│  todo app        │                                      │
│                  │                                      │
│  ────────────    │                                      │
│                  │                                      │
│  /hint - help    │                                      │
│  /skip - skip    │                                      │
│                  │                                      │
│  ────────────    │                                      │
│  [ Rewatch Video ]                                      │
│                  │                                      │
└──────────────────┴──────────────────────────────────────┘
```

### Level Complete
- Success message
- "Next Lesson" button
- Option to replay exercise

---

## Progressive Todo App

All lessons use the same todo app, progressively enhanced:

| After Lesson | Todo App State |
|--------------|----------------|
| 1-2 | Bug fixed (text vs title) |
| 3 | Has CLAUDE.md |
| 5 | Has due dates feature |
| 6 | Has priority levels |
| 7 | Has test coverage |
| 8 | Has git history |
| 9 | Has /lint skill |
| 10 | Uses MCP for search |
| 11 | Has parallel feature branch |
| 12 | Has safety hooks |

Each lesson resets to expected state, but shows progress.

---

## Video Production Notes

Each video should:
- Be 3-5 minutes max
- Show real Claude Code terminal
- Highlight the "why" not just "how"
- End with clear transition to exercise

Can be chopped into segments later for step-through format.

---

## Technical Changes Required

### Backend
- [ ] Add `video` field to lesson schema
- [ ] Add lesson progress tracking per user
- [ ] Add new verification types (commit_exists, command_output)
- [ ] Persist sandbox state between lessons (or reset to checkpoint)

### Frontend
- [ ] Add video player component (use react-player or similar)
- [ ] Add Watch → Exercise phase transition
- [ ] Add course progress UI
- [ ] Add "Rewatch Video" button during exercise

### Content
- [ ] Record 12 videos
- [ ] Create exercise files for each lesson
- [ ] Write lesson.yaml for each lesson
- [ ] Create progressive todo app checkpoints

---

*Design created 2026-01-26*
