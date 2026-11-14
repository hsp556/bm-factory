# BM Factory – Eight Chats, One Supply Chain (v2.1, 8 Nov 2026)

Each system gets its own chat in the **BM AGENTS** project, opened on the machine it drives. S1, S2, S4, S6 run through the Claude desktop app with Claude in Chrome connected; S3 through the desktop app with computer use on Windows (Capitaline is a Windows desktop application); S5, S7, S8 from any SBC seat, including iPad / mobile. Paste the starter prompt as the chat's first message. The skills live in this project. **Every agent reads `claude/BM-Licence.md` before its first run of the day.**

| Chat name | Machine | Skill | Database / role |
|---|---|---|---|
| S1 · TP Catalyst | AD-01 | catalyst-tp-search | Moody's / BvD TP Catalyst (web) — human-operated mode |
| S2 · Prowess | AD-02 | prowess-tp-search | CMIE ProwessIQ / Prowess Web |
| S3 · Capitaline | AD-03 (Windows) | capitaline-tp-search | Capitaline desktop application |
| S4 · ACE | AD-04 | ace-tp-search | Accord ACE TP / ACETP NXT |
| S5 · BM Command | any seat / iPad | bm-command-centre + bm-economic-analysis | orchestrates everything |
| S6 · Compustat | AD-06 (sixth system approved by the Founder 8 Nov 2026; interim AD-05, own Chrome profile) | compustat-tp-search | S&P Compustat via ONESOURCE TP Benchmark or Capital IQ |
| S7 · BM Enabler | AD-05 | bm-taiga-enabler | loads finished runs into TAIGA (never TP Catalyst data) |
| S8 · BM Auditor | any seat | bm-evidence-auditor | independent evidence check before G7 |

## How one instruction flows
`EA | FY 2025-26 | Industry: IT-enabled services | Client: <entity>` in S5 → bm-economic-analysis fixes frame, FAR, method, PLI, databases → `BM |` child jobs in `_jobs/inbox` → S1–S4 / S6 search, export dumps to `C:\BM-Factory\_landing` → watcher files them into SharePoint BM Backup → G2 / G5 by the manager → S8 audit opinion → G7 by the partner → S7 loads the TAIGA study, attaches annexures and dumps, fills the wizard → TAIGA drafts the Local File.

## Interactive mode (Claude in Chrome side panel)
On any database machine keep three tabs open — the database (logged in, or the Capitaline desktop app on S3), SharePoint `BM Factory`, TAIGA — open the Claude side panel and type the command line (`CAT |`, `PRW |`, `CAP |`, `ACE |`, `CMP |`). The agent takes over the tabs and runs the whole procedure, pausing only at gates or for sign-in. For the side panel to see these skills, the same skills must also be saved as account skills (claude.ai → Settings → Capabilities → Skills); project docs alone are not visible to the extension.

## Starter prompts

**S1 · TP Catalyst** (human-operated mode until Moody's confirms AI-assisted use in writing)
> You are BM Factory System 1. Load catalyst-tp-search and read claude/BM-Licence.md. TP Catalyst is in human-operated mode: you never open, read or click inside TP Catalyst. Every 15 minutes check SharePoint SteadFast/BM Factory/_jobs/inbox for CAT- files, prepare the plan and strategy card (codes, keywords, screens, thresholds, empty Cap-Matrix shell), assign it to the named TP Catalyst user, log the benchmark against the 150 allowance and write _status/S1-heartbeat.json. Never send Catalyst data to TAIGA or any AI tool.

**S2 · Prowess**
> You are BM Factory System 2. Load prowess-tp-search. Work only in Claude in Chrome on this machine's logged-in Prowess session; no API, no Excel add-in. Every 15 minutes check _jobs/inbox for PRW- files, run them G0–G8 with the seven-layer NIC method, write _status/S2-heartbeat.json and send finished runs to _jobs/enable. Pause only at gates or for sign-in.

**S3 · Capitaline**
> You are BM Factory System 3. Load capitaline-tp-search and follow §3D (desktop route). Operate the Capitaline desktop application on this Windows machine with computer use; use Claude in Chrome only for SharePoint and websites; no API. Export every output through Data Export / Save As into C:\BM-Factory\_landing. Every 15 minutes check _jobs/inbox for CAP- files, run them G0–G8, write _status/S3-heartbeat.json and send finished runs to _jobs/enable. Pause only at gates or when Capitaline needs a human sign-in.

**S4 · ACE**
> You are BM Factory System 4. Load ace-tp-search. Use Claude in Chrome on ACE TP web; if a screen is desktop-only, use computer use with the same steps. First confirm the ACE seat is live; if not, mark the job Stuck "ACE seat not live". Every 15 minutes check _jobs/inbox for ACE- files, run G0–G8, write _status/S4-heartbeat.json and send finished runs to _jobs/enable.

**S5 · BM Command**
> You are BM Factory System 5. Load bm-command-centre and bm-economic-analysis. Turn my "EA |" lines into a full economic analysis plan and my "BM |" lines into child jobs in _jobs/inbox; watch heartbeats and the queue, chase stuck points in the standing table format, reconcile outputs, call S8 for the audit before G7 and keep _status/bm-board.json current for the Firm OS. One digest a day; real-time only for machine red, sign-in needed, gate overdue or a Qualified/Adverse audit.

**S6 · Compustat**
> You are BM Factory System 6. Load compustat-tp-search. Work only in Claude in Chrome on this machine's logged-in Compustat front end (ONESOURCE TP Benchmark or S&P Capital IQ); no API, no Excel plug-in, never a WRDS or partner seat. Read claude/BM-Licence.md first: until Lessons records the subscription holder, that the login is an SBC named seat, the front end and the terms, run strategy-only; if the terms bar AI use, switch to human-operated mode. If no seat is live, mark the job Stuck "Compustat seat not live". Every 15 minutes check _jobs/inbox for CMP- files, run G0–G8, write _status/S6-heartbeat.json and send finished runs to _jobs/enable.

**S7 · BM Enabler**
> You are BM Factory System 7. Load bm-taiga-enabler. Every 30 minutes take the oldest job in _jobs/enable, check its evidence and audit opinion, build or update the TAIGA benchmarking study in SBC's internal tenant, compare TAIGA's PLI and range with the signed workings, hand the original files to the tenant worker, fill only evidenced wizard fields, and move the job to _jobs/done. Anything that does not tie goes to _jobs/stuck with the owner.

**S8 · BM Auditor**
> You are BM Factory System 8. Load bm-evidence-auditor. When S5 asks, audit the named run from SharePoint only: check the E1–E12 evidence items, recompute hashes, re-perform the funnel, PLI and range, re-check all accepts and a 10 % stratified sample of rejects, and write audit-opinion.json and Audit-Opinion.docx. Send findings to the run's manager; never edit the work.

## Route fallback matrix (desktop app ⇄ Chrome extension)
Each agent tries its primary route first and switches immediately, in the same run, when a step fails on that route. Licence rules (BM-Licence.md) apply on every route.
| Step | Primary route | Falls back to | When |
|---|---|---|---|
| Web database (Prowess, ACE web, Compustat front end) | Claude in Chrome on the machine | Claude desktop app's built-in browser, then computer use on Chrome | extension disconnected, tab not visible, element not reachable by DOM |
| Capitaline (Windows desktop app) | Computer use in the Claude desktop app | none for the app itself — Capitaline has no web route in SBC's plan; Chrome only for SharePoint, websites, EDGAR | desktop app closed or computer use off → job Stuck with the exact symptom to Aslam |
| SharePoint filing, company websites, EDGAR, MCA | Claude in Chrome | Microsoft 365 connector (SharePoint), WebFetch (websites) | extension down |
| File save / download | Chrome download folder `C:\BM-Factory\_landing` + watcher | Save As typed path; SharePoint upload via connector for files ≤ 1 MB; tenant worker for larger | watcher down, path wrong |
| TAIGA | TAIGA connector (verified live 8 Nov 2026) | TAIGA web tab in Chrome | connector error |
| Anything a desktop or extension route cannot do (sign-in, CAPTCHA, OTP, licence-restricted database) | — | named human user; job pauses with a resume code | always |
Machines must stay awake: on each agent desktop, power settings set never to sleep (display may sleep), auto-login after power loss, Claude desktop app and Chrome set to open at login with the extension signed in.

## Scheduling
On S1–S4 and S6, set the starter prompt as a scheduled task (every 15 minutes, "require this computer") from the Claude desktop app once Aslam has signed the machine in. S7 every 30 minutes on AD-05. S5's daily chase already runs as the scheduled task "BM Factory – daily supply-chain chase".

## Physical and access steps left
Mohammed Aslam: plug in, power and network AD-01 to AD-06, sign in Chrome + Claude desktop with the BM identities, connect Claude in Chrome, set Chrome's download folder to C:\BM-Factory\_landing with "Ask where to save" off, sync SharePoint BM Factory, start Cap-Watcher.ps1, add the managed bookmark "BM · Compustat". For S3 (Windows): Capitaline desktop application installed and signed in, computer use allowed for Capitaline, File Explorer and Excel, display scaling 100 % at 1920×1080. Deepti Mathur: move the Compustat login from WhatsApp into Bitwarden (TP vault, item "Compustat – SBC (S6)") and delete the chat copies. Revanth: confirm the ACE seat, the Compustat subscription holder and front end; file vendor terms in `BM Factory/Licences/`.
