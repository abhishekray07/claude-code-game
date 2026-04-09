# Claude Code Game

An interactive course that teaches Claude Code through hands-on exercises. Run it locally — no Docker, no cloud sandboxes.

![Screenshot of Claude Code Game](docs/images/screenshot.png)
<!-- TODO: capture screenshot showing lesson panel + terminal side by side -->

## Quick Start

```bash
npx @opslane/claude-code-game
```

Opens a local terminal UI in your browser with guided lessons, a real Claude Code session, and automatic verification when you complete each exercise.

## What You'll Learn

You'll build a working expense tracker app from scratch with Claude Code — no coding experience needed. Along the way, you'll learn the professional dev workflow in 6 steps:

| Step | Topic | What You'll Learn |
|------|-------|-------------------|
| 1 | **Define & Plan** | Talk to Claude before coding — write requirements and a phased build plan with acceptance criteria |
| 2 | **Build** | Let Claude implement from the plan — watch it read files, write code, and iterate |
| 3 | **Verify** | Prove it works — have Claude write and run tests for your app |
| 4 | **CLAUDE.md** | Teach Claude about your project so it works effectively every session |
| 5 | **Review** | Ask Claude to review the code for bugs, edge cases, and improvements |
| 6 | **Ship** | Commit your work with a clear, descriptive message |

## How It Works

The game runs a local Express server that spawns a bash PTY per session. Your browser connects via WebSocket and renders a real terminal with xterm.js. Each lesson copies starter files into a workspace and verifies completion automatically.

```
Browser (xterm.js) <-> WebSocket <-> Express server <-> node-pty (local bash)
```

## Contributing

```bash
# Dev servers (run in separate terminals)
cd server && npm run dev        # Express + tsx watch
cd frontend && npm run dev      # Vite dev server

# Typecheck before committing
cd server && npx tsc --noEmit
cd frontend && npx tsc --noEmit
```

See [CLAUDE.md](./CLAUDE.md) for architecture details, lesson structure, and debugging tips.

## License

MIT
