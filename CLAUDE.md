# CLAUDE.md - Project Instructions for Claude Code

## Agent Usage

- Prefer using parallel team agents (Task tool) for multi-area exploration and independent subtasks
- Use direct tools (Grep, Read, Glob) for targeted single-file lookups or when you already know the exact file/location
- When a task touches 3+ unrelated areas of the codebase, spawn parallel explore agents rather than searching sequentially
- Do not use agents for tasks with sequential dependencies — do those directly or in sequence
