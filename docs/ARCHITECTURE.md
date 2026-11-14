# BM Factory Suite: Architecture (spec)

Status: v0.1, 2026-11-14. The source procedure is `SKILL (9).md`, `BM-Chats (2).md` and `docs/source/Cap-SOP.txt`. This file records how we build it.

## 1. Decisions (locked)
| # | Decision | Date |
|---|---|---|
| D1 | Hybrid build: a deterministic script drives each database. Claude does planning, rescue (one step) and learning runs (all screens). | 2026-11-14 |
| D2 | Hosting is **AWS ap-south-1 (Mumbai)**, alongside TAIGA (EC2). | 2026-11-14 |
| D3 | Learning-run changes deploy **only after a human clicks Approve**, and every deploy can be rolled back. | 2026-11-14 |
| D4 | Build order: **S3 Capitaline first**, then the hosted Command Centre, then the other stations. | 2026-11-14 |
| D5 | Each station ends at "files + manifest on SharePoint, job → `_jobs/enable`". Stations make no accept/reject decisions. | 2026-11-14 |
| D6 | RunID FY token = `FY` + 2+2 digits, e.g. `CAP-FY2526-LIB-20261114-01`. This is a ruling: the SOP leaves the FY format open, and a hyphenated FY would break splitting on `-`. | 2026-11-14 (confirm) |
| D7 | The Capitaline seat on System 3 is licensed and stays logged in. The user confirmed the licence position, so the bot never handles sign-in. | 2026-11-14 |
| D8 | Development access to System 3 is through **Iperius Remote**, which shares the console session. Production needs no remote access, because stations call out to the Command Centre. | 2026-11-14 |
| D9 | Claude is reached through the **direct Anthropic API** (was O2). All calls go through one small interface (`LLMClient`), so the route can be swapped later. Computer use for rescue and learning runs uses the same route. | 2026-11-14 |
| D10 | **No region input for Capitaline.** Capitaline covers Indian companies only, so region is fixed. Region may become an input for stations with global data (for example Compustat). | 2026-11-14 |

## 2. Open decisions
| # | Question | Options | Decide by |
|---|---|---|---|
| O1 | Speech-to-text provider | ElevenLabs Scribe vs Sarvam Saaras. Choose by a bake-off on recorded partner commands (§6) | Phase 3 |
| O3 | Command Centre runtime on AWS | One EC2 with Docker Compose (matches TAIGA ops) vs ECS | Phase 3 |
| O4 | Shared code repository, needed by both this dev PC and System 3 | Private GitHub repo (recommended) vs Azure DevOps vs a self-hosted git on AWS | Before Task 5 |

## 3. Topology
- **Command Centre (hosted, AWS Mumbai):**
  - Web app/PWA with voice input
  - Orchestrator (S5), job queue, approvals, dashboard, station registry, Learning-run button
  - Hosted agents: economic-analysis planner, Analysis agent (G4–G6), S8 Auditor, S7 TAIGA Enabler
  - PostgreSQL for state; Entra ID login
- **Stations (on-prem, one PC per licensed seat):** S3 Capitaline (Windows app, pywinauto), S2 Prowess, S4 ACE and S6 Compustat (web, Playwright), S1 TP Catalyst (assistant mode, a human clicks). Stations call out to the Command Centre over HTTPS. Nothing calls in.
- **SharePoint** is the system of record for files (Microsoft Graph). **TAIGA** is downstream.
- Until Phase 3, S3 runs standalone, with jobs started by hand on the PC.
- **Network:** stations need outbound HTTPS only, to the Claude API route, `graph.microsoft.com`, `login.microsoftonline.com`, `*.sharepoint.com` and the Command Centre domain (plus `pypi.org` and `github.com` during setup). No inbound ports.

## 3a. Machines
| Machine | Role | Runs |
|---|---|---|
| Dev PC (`D:\capitaline agent`) | Build, offline tests, plans, reviews | Claude Code, contracts and core code, unit tests |
| System 3 (Windows, Capitaline logged in) | S3 station, reached through Iperius Remote during development | Claude Code, inspector, live tests (`-m system3`), and later the station service |
| AWS ap-south-1 | Command Centre (Phase 3+) | API, PWA, PostgreSQL, hosted agents |

## 4. Station Core (shared) + adapters
Core (built once):
- job pickup, plus a resumable step engine
- evidence log + screenshots
- collector (rename, sha256, union)
- SharePoint upload, manifest, heartbeat
- Rescue, Learning run

Adapters: one per database. Each is a set of step implementations behind the same interface.

Three layers of station knowledge:
| Layer | File | Changes when | Who changes it |
|---|---|---|---|
| Steps (what) | `stations/<db>/steps.yaml` | The SOP changes | Partner-approved PR |
| Screen map (where) | `stations/<db>/screen-map.yaml`, versioned | The vendor changes its UI | A learning run proposes, a human approves |
| Engine (how) | `src/bmfactory/...` | Rarely | Normal build process |

## 5. Learning run
Trigger: a button in the Command Centre, or a suggestion after 3 rescues on the same step within 7 days.

1. **Explore:** Claude computer use walks every step on the **golden job** (fixed known inputs) and records a screenshot, control id/name/path and timing per step.
2. **Propose:** a coding agent writes a screen-map diff (and a code patch only if behaviour changed) on a branch.
3. **Prove:** the scripted driver is replayed with the new map on the golden job and compared with the last good baseline (row counts, file names, SQL text). All tests must pass.
4. **Review:** the code reviewer, tp-sop-reviewer and security-licence-reviewer check the change.
5. **Approve:** a human reviews the diff, before/after screenshots and the replay result in the Command Centre.
6. **Deploy:** the version is bumped and loaded on the station's next job. Rollback is one click.

## 6. Voice input
1. Push-to-talk on the PWA.
2. Speech-to-text, with a key-term list (NIC, ITeS, OP/OC, Capitaline, client names).
3. Claude turns the transcript into a structured `Command`.
4. A confirm card shows; nothing runs until the person confirms.
5. Approvals by voice go through the same confirm card.

The speech-to-text provider sits behind one small interface so it can be swapped by configuration. O1 bake-off: about 40 recorded commands from partners and managers, scored as "% of commands correct on the confirm card without edits", plus latency, cost and India data residency.

## 7. Contracts (Phase 0 deliverables)
- `Command` (text grammar from SKILL §1)
- `RunId`
- `year_codes(fy)`
- `Job`
- `Manifest`
- `StepDef` / `steps.yaml`
- `ScreenMap` / `screen-map.yaml`

All are Pydantic models, with JSON Schema exported to `contracts/schemas/` for non-Python consumers (the PWA, TAIGA).

## 8. Roadmap
| Phase | Deliverable | Acceptance |
|---|---|---|
| 0 Foundations | Contracts, decisions O2 and O4, System 3 setup, read-only UI inspector, supervised learning run | Contracts merged. Inspector feasibility report and screen map v1 recorded |
| 1 Station Core + S3 tracer | One layer end to end to the SharePoint test folder | Files, manifest and evidence on SharePoint from a real Capitaline run |
| 2 Self-repair (S3) | Rescue, learning run, golden job, replay, versioned maps, rollback | A deliberately broken map is repaired through the learning run and approval |
| 3 Command Centre + voice | PWA, Entra, job API, station registry, approvals, voice confirm card, Learning-run button | A spoken command runs on S3; G2 is approved from a phone |
| 4 S3 complete + go-live | 8 layers, Peer Set, data pulls, F1–F11 | Parallel run on 3 industries; 10 unattended runs; licence reply on file |
| 5 Prowess (web) | Playwright adapter on the same core | A Prowess run with zero core changes |
| 6 ACE, Compustat, TP Catalyst | Remaining adapters, each subject to its licence | Per-station parallel run |
| 7 Hosted agents | Analysis (G4–G6), S8 Auditor, S7 TAIGA Enabler | Voice → TAIGA study, end to end |
| 8 Operations | Monitoring, cost per run, runbooks, backup | Ops handover |
