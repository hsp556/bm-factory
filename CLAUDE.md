# BM Factory Suite (building S3 Capitaline first)

This is a suite of benchmarking agents:
- a hosted **Command Centre** (AWS Mumbai) with voice input, an orchestrator, approvals and hosted analysis agents,
- one **station** per licensed database PC, all on a shared Station Core.

**Current focus: the S3 Capitaline station.** It takes a `CAP-` job, runs the Capitaline desktop TP Screener search (G0–G3, then the financial and company-report pulls), files every export with evidence on SharePoint `BM Backup/Capitaline/<RunID>/` and moves the job to `_jobs/enable`. **Stations make no accept/reject comparability decisions.**

Read first: `docs/ARCHITECTURE.md` (spec and decisions), `docs/PLAN.md` (what is next, and where), `docs/BUILD.md` (setup, agent team, rules). Sources of truth for the procedure: `SKILL (9).md` (§3D screen map), `BM-Chats (2).md` (job flow), `docs/source/Cap-SOP.txt` (full SOP). Where these disagree, ask. Do not pick one silently.

## Architecture (hybrid)
Orchestrator (Python, resumable state machine) → Planner (Claude API, schema-validated strategy.json) → Capitaline driver (pywinauto; Claude computer use only as the rescue fallback) → Collector (pandas: rename, sha256, union, reconcile) → Uploader (Microsoft Graph) → Teams notifier and heartbeat.
Playwright is NOT used for Capitaline, which is a Windows app. It is only for web databases or sites in other stations.

## Gotchas (keep the reasons)
- **UI automation needs an interactive, logged-in, unlocked desktop.** Never run the bot as a Windows service (session 0 has no GUI). Start it from Task Scheduler at logon, with auto-login and no screen lock.
- Display must be 1920×1080 at 100% scaling, or recorded coordinates and vision fallbacks drift.
- Licence: one Capitaline window, human pace, no parallel sessions, no direct reads of Capitaline data files. The licence position was confirmed by the user on 2026-11-14 (ARCHITECTURE D7).
- System 3 is reached through Iperius Remote during development. Don't touch its mouse or keyboard while a script is driving Capitaline.
- Never type or store Capitaline credentials. Sign-in is done by a human. The bot pauses with a resume code.
- Raw dumps in `02-Raw-Dumps` are never modified. All transformations go in Workings.

## Coding principles (Karpathy)
1. **Think before coding.** State assumptions. If there are several interpretations, list them. Ask when unclear.
2. **Simplicity first.** Write the minimum code for the task, with no speculative features or single-use abstractions.
3. **Surgical changes.** Every changed line traces to the task. Match the existing style. Clean up only your own leftovers.
4. **Goal-driven.** Every task has a check you can run (`[step] → verify: [check]`). Loop until it passes.

## How we build: skills in `.claude/skills/`
| When | Use |
|---|---|
| Have a spec or phase goal, before any code | `writing-plans` → plan saved in `docs/plans/` |
| Executing a plan | `subagent-driven-development` (default) or `executing-plans` (small or tightly coupled work) |
| Writing any code | `test-driven-development`: failing test first |
| Any bug or unexpected behaviour | `systematic-debugging` (for UI waits, see `condition-based-waiting.md`; never use fixed sleeps) |
| Before saying "done" | `verification-before-completion`: show the command output |
| Review | `requesting-code-review` / `receiving-code-review` |
| Branch finished | `finishing-a-development-branch` |

**Per-task review panel** (each reviewer in a fresh context, run in parallel after the implementer reports DONE):
1. SDD task reviewer (spec + code quality), from `subagent-driven-development/task-reviewer-prompt.md`
2. `tp-sop-reviewer` agent: SOP conformance
3. `security-licence-reviewer` agent: when the diff touches credentials, Graph, job intake, Claude calls, logging or the Capitaline driver

A task is complete only when all applicable reviewers pass, or every open finding is parked with a ruling in the ledger. Implementers never review their own work and never spawn reviewers.

## Overrides to the vendored skills
- SDD's "continuous execution, never pause" applies **within one plan only**. Always stop for a human at:
  - the end of each phase,
  - before any step that drives the **live** Capitaline seat or writes to a **production** SharePoint folder,
  - pushes and merges.
- Development and test runs write only to the SharePoint **test** folder.
- Commit only when the user approves. Never use `git add -A`; stage files explicitly.

## Commands
(fill in as they are created: setup, test, run-dry, run-live)
