# BM Factory: Master Plan

This file says what we do, in what order, on which machine, and how we know each step is done.
- Design and decisions: `docs/ARCHITECTURE.md`
- How we build (setup, agent team, rules): `docs/BUILD.md`
- Detailed task plans: `docs/plans/` (one per phase, written with the `writing-plans` skill when the phase starts)

**Status (2026-11-14):** Phase 0 steps 0.4 and 0.5 (build half) are done: Tasks 1-5 built, reviewed and final-reviewed; 384 tests pass, 1 live test skipped. Merged to `main` and pushed to the private GitHub repo (O4 decided). **Order set by the user:** System 3 comes first (setup 0.2, inspector run, supervised walk through the desktop app) so the real codes and screens are known; the Claude intake plan (`docs/plans/2026-11-14-phase-0b-claude-intake.md`) is written and plan-reviewed but waits until after that walk-through.

Machine key: 💻 dev PC · 🖥️ System 3 (via Iperius) · ☁️ AWS · 👤 a person

---

## Phase 0: Foundations
Detailed plan: `docs/plans/2026-11-14-phase-0-foundations.md`

| # | Step | Where | Who | Done when |
|---|---|---|---|---|
| 0.1 | Approve the first commit, and decide **O4** (private GitHub repo recommended) | 💻 | 👤 You | Repo exists. This folder is pushed on `main` |
| 0.2 | System 3 setup: Git, Python 3.12, Claude Code; Windows never sleeps, no lock screen, auto-login, 1920×1080 at 100%; clone the repo | 🖥️ | 👤 Aslam / you via Iperius | `git`, `python` and `claude --version` run on System 3 |
| 0.3 | **Iperius disconnect test:** start a 3-minute screenshot loop, disconnect Iperius, reconnect | 🖥️ | 👤 + Claude on System 3 | Screenshots taken while disconnected show the unlocked desktop |
| 0.4 | Build Tasks 1–4 (RunID, command parser, job/manifest, steps/screen map) | 💻 | Subagents | `pytest` all green; three reviewers pass each task |
| 0.5 | Build Task 5 (read-only UI inspector and coverage report) | 💻 → 🖥️ | Subagents | Unit tests green on 💻; live run on 🖥️ produces `docs/discovery/` |
| 0.6 | Run the inspector on the Capitaline main window and the TP Screener (Domain, Filters, Output tabs opened by hand) | 🖥️ | 👤 opens the screens, the inspector records | `docs/discovery/capitaline-feasibility.md` lists each target as green/amber/red |
| 0.7 | **Supervised learning run:** Claude on System 3 walks SKILL §3D for L1 on the golden job while a TP manager watches through Iperius | 🖥️ | Claude + 👤 TP manager | Screen map v1 PR with real labels; Save/Load Screener and Import Peerset results noted |
| 0.8 | Claude route: **decided, direct Anthropic API** (D9). Set `ANTHROPIC_API_KEY` as an environment variable on the dev PC and System 3 | — | 👤 You | Key set; never in chat or files |
| 0.9 | IT: Entra app registration with Graph `Sites.Selected` on the SharePoint **test** folder | — | 👤 IT | A test upload from System 3 works |
| 0.10 | Start recording ~40 voice commands (for the Phase 3 bake-off) | — | 👤 You | Stored in a restricted folder |
| **Gate** | 👤 Review the Phase 0 results and approve the move to Phase 1 | | | |

### Carried into Phase 1 from the Phase 0 reviews
Driver and uploader requirements the reviewers set; the Phase 1 plan must include each one.
- **Save path:** the driver owns the landing-folder template (not the YAML), confines the resolved path to the landing root, and verifies the file landed. One `raw_dump_name()` function serves both the step list and the manifest; `{field}` is `[A-Za-z0-9]` only.
- **Placeholders:** fixed allowlist, strict substitution (never `str.format`), fail on an unknown placeholder, re-check the text after filling.
- **Windows:** every window must belong to the single Capitaline process (executable + PID), plus a title allowlist. The Save As dialog must be owned by that process.
- **Screenshots:** capture the Capitaline window only, never the whole desktop. The engine takes one before every click and writes one evidence-log row per action.
- **Screen map:** `verified: false` blocks live runs; a learning-run rewrite resets it to false.
- **Uploader:** the test/production root allowlist for `Job.dest` is the first uploader task; SharePoint tenant allowlist from config.
- **Contracts tidy-up:** public `contracts/text.py`; reserved names in `Job.dest`; a "complete" manifest must list files; patterns in exported schemas before the PWA or TAIGA use them; models for `counts.json` and `run-record.json`; `command.json` must keep the raw text and which values were defaulted.
- **Free-text leniency (with the free-text reader):** thousands separators, `Mode: strategy only`, `Industry: 6201`, empty optional values, Indian-script joiner characters.

### Questions for you / the TP manager (working choice in brackets)
1. RunID format `CAP-FY2526-LIB-20261114-01` (D6). [in use]
2. Default FY switches on 1 April. [yes]
3. Tested party defaults to "service" when not stated. [yes]
4. Export file name with a sequence number, as Cap-SOP, or without, as SKILL §3D? [with]
5. Is there a Parse button on the desktop screener? [step included, unverified]
6. Domain: all companies (Cap-SOP) or ticked industries (SKILL §3D), per layer? [strategy supplies it]
7. Who names the export file: the watcher or the bot? [bot types the full name]
8. How is the screener CSV saved? [Save button then Save As, unverified]
9. Client short names are cut at 30 characters. [yes]
10. Region: decided 2026-11-14, not an input for Capitaline (India only; D10).
11. Track `SKILL (9).md` and `BM-Chats (2).md` in the private repo? [recommended]

## Phase 1: Station Core + S3 tracer (one layer, end to end)
Where: 💻 for the core, 🖥️ for the Capitaline adapter and live tests.
- **Builds:** job runner (started by hand), resumable step engine, evidence log + screenshots, Capitaline adapter for the 17 L1 steps, collector (rename, sha256), Graph upload to the SharePoint test folder, manifest writer.
- **Exit:** a real L1 run on System 3 produces the files, `_manifest.json` and `evidence-log.csv` in the SharePoint test folder. 👤 You open SharePoint and check them.

## Phase 2: Self-repair for S3
Where: 🖥️, with 💻 for the core logic.
- **Builds:** golden job + baseline, rescue mode (Claude computer use for one stuck step), learning run (explore, propose, prove by replay, review, approve), versioned screen maps, rollback.
- **Exit:** we deliberately corrupt the screen map, the learning run proposes a fix, the replay matches the baseline, 👤 you approve, and runs work again.

## Phase 3: Command Centre (AWS) + voice
Where: ☁️ and 💻; 🖥️ registers as a station.
- **Builds:** FastAPI + PostgreSQL on AWS Mumbai, Next.js PWA, Entra login, job API, station registry and heartbeat, dashboard, approval cards, Learning-run button, speech-to-text bake-off (O1) → voice confirm card.
- **Exit:** a command spoken on a phone runs on S3, and G2 is approved from the phone.

## Phase 4: S3 complete + go-live
- **Builds:** all 8 layers, union, Peer Set, financial and company-report pulls, failure handling F1–F11.
- **Exit:** a parallel run on 3 industries matches the team's manual results, and 10 unattended runs in a row succeed. 👤 Partner signs go-live.

## Phases 5–8
| Phase | Deliverable | Exit |
|---|---|---|
| 5 | Prowess station (Playwright) on the same core | Prowess run with zero core changes |
| 6 | ACE, Compustat, TP Catalyst (assistant mode) | Per-station parallel run |
| 7 | Hosted Analysis agent (G4–G6), S8 Auditor, S7 TAIGA Enabler | Voice command → TAIGA study, end to end |
| 8 | Monitoring, cost per run, runbooks, backup | Ops handover |
