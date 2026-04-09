# README Redesign

**Date**: 2026-04-08
**Status**: Approved

## Goal

Rewrite the README so developers discovering the repo on GitHub can quickly understand what the course teaches and decide if it's worth trying.

## Audience

Primary: developers who find the repo on GitHub. Secondary: contributors who want to hack on it.

## Decisions

1. **Primary audience**: GitHub visitors wanting to understand + try it
2. **Run method**: `npx claude-code-game` as primary, clone for contributors
3. **Curriculum detail**: Titles + descriptions + "what you'll learn" for each lesson
4. **Screenshot**: Placeholder image reference (capture later)
5. **Contributor info**: Short section with dev commands, link to CLAUDE.md for details

## Structure

1. **Hero** — One-line description, screenshot placeholder, `npx` quick start
2. **Curriculum table** — All 12 lessons with title + what you'll learn
3. **How It Works** — Two sentences + ASCII diagram
4. **Contributing** — Dev commands only, link to CLAUDE.md
5. **License** — MIT
