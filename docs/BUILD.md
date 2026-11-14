# How We Build

This covers setup, the agent team, rules and the definition of done. What to build is in `docs/PLAN.md`; why is in `docs/ARCHITECTURE.md`.

## 1. Machines
| Machine | Used for | Never used for |
|---|---|---|
| 💻 Dev PC (`D:\capitaline agent`) | Writing code, offline tests, plans, reviews | Driving Capitaline |
| 🖥️ System 3, via **Iperius Remote** | Live Capitaline tests, inspector, learning runs, and later the station service | Day-to-day coding (pull from the repo instead) |
| ☁️ AWS ap-south-1 | Command Centre (Phase 3+) | — |

Code moves between machines **only through the git repo** (O4). Never use Iperius file transfer for code.

## 2. One-time setup
Both machines (Git Bash):
```bash
git clone <repo-url> "capitaline agent" && cd "capitaline agent"
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]" -c constraints.txt   # 🖥️ System 3: -e ".[dev,station]" -c constraints.txt
.venv/Scripts/python -m pytest                            # must be green before any work
```

System 3 only:
- Windows never sleeps, there is no lock screen, auto-login is on, display is 1920×1080 at 100%.
- Capitaline stays open and logged in.
- Iperius has unattended access with a strong password. **Never paste the Iperius ID or password into chat, code or docs.**

## 3. Rules on System 3 while a bot runs
- Don't touch the mouse or keyboard in the Iperius window while a script is driving Capitaline. Watch only.
- Keep one Capitaline window. Don't open a second session.
- Before you disconnect, leave the desktop unlocked and the session connected to the screen (checked by Phase 0 step 0.3).
- Live tests write only to the SharePoint **test** folder until go-live.

## 4. The agent team
| Role | Who | Does | Never |
|---|---|---|---|
| Controller | The main Claude Code session | Runs the plan, dispatches agents, keeps the ledger, makes rulings | Writes task code itself |
| Implementer | Fresh subagent per task (`subagent-driven-development/implementer-prompt.md`) | Test first, then code, run tests, commit, report | Reviews its own work or spawns reviewers |
| Task reviewer | Fresh subagent (`task-reviewer-prompt.md`) | Checks the spec was met and the code quality | Edits code |
| SOP reviewer | `tp-sop-reviewer` agent | Checks conformance to SKILL.md and the SOP | Edits code |
| Security/licence reviewer | `security-licence-reviewer` agent | Checks secrets, inputs, licence behaviour, confidentiality | Edits code |
| Final reviewer | Fresh subagent on the most capable model | Reviews the whole branch at the end of the phase | Edits code |
| Human | 👤 You, plus the TP manager for SOP questions | Approves each phase gate, live-seat steps and merges | — |

**Models (set by the user, 2026-11-14):**
| Role | Model |
|---|---|
| Controller / planner (main session) | Fable (`claude-fable-5-2`) |
| Implementer (writes the code) | Opus (`claude-opus-5-5`); dispatch with `model: "opus"` |
| Task, SOP and security reviewers | Sonnet (`claude-sonnet-5-5`), as set in the agent files |
| Final whole-branch reviewer | Fable |

Always pass the model explicitly when dispatching a subagent. An omitted model inherits the session's model.

**The loop for every task:**
```
brief → implementer (TDD, commit) → [task reviewer ∥ SOP reviewer ∥ security reviewer]
      → fix loop (scoped re-review each round) → ledger: "Task N complete" → next task
end of phase → final whole-branch review → 👤 gate → merge
```

The security reviewer joins whenever a diff touches credentials, Graph, job intake, Claude calls, logging, the inspector or the Capitaline driver.

## 5. How to run a phase (what you type in Claude Code)
1. `Use writing-plans to write the Phase N plan from docs/PLAN.md and docs/ARCHITECTURE.md`. The plan is saved in `docs/plans/`.
2. **Plan review before any code** (added after Phase 0, where 6 of 8 first-review findings were plan gaps): dispatch `tp-sop-reviewer` and `security-licence-reviewer` on the plan file itself. The SOP reviewer checks every procedure step against **both** `SKILL (9).md` and `docs/source/Cap-SOP.txt`. Fix the plan, then 👤 review it.
3. `Execute docs/plans/<plan>.md with subagent-driven-development`.
4. Tasks marked 🖥️: open Claude Code **on System 3** (via Iperius), `git pull`, then run the same command for those tasks.
5. 👤 Phase gate → merge the branch.

## 6. Tests
- `pytest` runs offline unit tests on any machine. They are mandatory, and must stay green.
- `pytest -m system3` runs live tests that need Capitaline. They only run when `BM_SYSTEM3=1` is set, and are skipped everywhere else.
- **Golden job** (from Phase 2): `CAP | FY 2025-26 | NIC 6201 | Product: software development`. Its baseline counts and files are kept for replay checks.

## 7. Git
- Branch per phase: `phase-<n>-<name>`. One commit per task step, as the plan specifies.
- Stage files explicitly; never `git add -A`. Never commit `.env`, secrets, Iperius details or client data.
- Merges to `main` and pushes of shared branches happen only after 👤 approval.

## 8. Definition of done (for a task)
- Its tests were written first, seen failing, and now pass. The full `pytest` run is green.
- All applicable reviewers passed, or every open finding is parked with a ruling in the ledger.
- For 🖥️ tasks, the live check ran on System 3 and the evidence (output or screenshot) is linked in the report.
- No new dependency outside the plan's Global Constraints.

## 8a. Input rules every plan must carry in its Global Constraints
Anything read from a person, a file, SharePoint, the screen or Claude is untrusted. State these in the plan so each task starts with them:
- Free text: maximum length set, control and format characters rejected.
- Patterns: `fullmatch`, ASCII digit classes; never `$` or `\d` on untrusted text.
- Paths: relative, no `..`, no drive or scheme, Windows reserved names rejected, confined to a named root.
- URLs: `https`, host allowlist checked on the raw host, no userinfo or port.
- Models: unknown fields rejected (`extra="forbid"`), list sizes capped.
- Error messages: echoed input truncated to 50 characters.
- Screen reads: record structure, not database content; raw captures go to a git-ignored folder.

## 9. Secrets
- Secrets come from environment variables or Windows Credential Manager only. Never from code, YAML, tests or logs.
- Capitaline credentials are never handled by the bot (D7).
