---
name: capitaline-tp-search
description: Run SBC's Capitaline TP comparable search end to end on the Windows System 3 desktop (Capitaline desktop application via computer use; Claude in Chrome only for SharePoint/web) (BM Factory System 3) from a one-line command (FY + industry + product): eight-layer Screener sweep, quantitative and qualitative screens, Rule 10CA range, evidence, gates, SharePoint BM Backup and TAIGA hand-off. Use for "CAP |", "Capitaline search", "run BM on Capitaline".
---

# Capitaline TP Search Agent (BM Factory · System 3)

SOP of record: `Cap-SOP.docx` (BM AGENTS project). Workings template: `Cap-Matrix.xlsx`. IT/TAIGA dependencies: `Cap-Fix.docx`. Desktop file watcher: `Cap-Watcher.ps1`.
Law: s.92C, Rules 10B, 10C, 10CA, 10D (IT Act 1961 / Rules 1962) for FY 2025-26; map to Income-tax Act 2025 for tax year 2026-27 onward.

## 0. Before every run
1. Read `BM Factory/Lessons/Lessons-Register.xlsx` (Active rows) and the industry library index. State in the run record which lessons you applied.
2. Confirm the licence-gate flag in Lessons (C-MOTS confirmation). If not yet confirmed, run only on SBC engagements, human-paced, one tab, and say so in the digest.
3. SBC's Capitaline subscription is the **desktop application (Windows)** — confirmed by the Founder 7 Nov 2026; it does not run on Mac. Operate it with computer use on the Windows System 3 desktop (screenshot → click/type → screenshot). Use Claude in Chrome only for SharePoint, company websites and web pages. No API, one Capitaline window at a time, human pace, no other database seat.

## 1. Command → plan (G0)
Grammar: `CAP | FY <yyyy-yy> | Industry: <text|NIC> | Product: <a; b> [| Client: ] [| PLI: ] [| TP sales: ₹ cr] [| Tested party: ] [| Mode: run|strategy-only|refresh]`.
Defaults: FY = current compliance year. Year codes = YYYY03 for the current FY and the two preceding years. PLI by tested-party type: services OP/OC, distributor OP/OR, manufacturer OP/OC. Turnover band = 0.1×–10× TP sales, else ₹1–200 cr (flag it).
Resolve industry → NIC-2008 class, group and division plus Capitaline industry names. Resolve product → synonyms, ITC-HS 4/6/8-digit codes and raw materials. Issue `RunID = CAP-<FY>-<client|LIB>-<YYYYMMDD>-<nn>` and write `00-Command/command.json`. Write the job JSON `{run_id, dest}` to `BM Factory/_jobs/running` so the watcher files the downloads.
Missing industry or product → ask once in the chat. If nobody answers in 15 min, run strategy-only.

## 2. Environment (G1)
Take a screenshot of System 3; open the Capitaline desktop application (Start menu / desktop shortcut) if not running. Capture the logged-in banner and the data date. Logged out → do not submit credentials yourself; post "Capitaline sign-in needed on System 3" to the partner/Revanth (desktop app sign-in) and pause with a resume code. Watcher heartbeat older than 5 min → alert IT and carry on (files stay in `_landing`).
First run on a new desktop = **learning run**: record the real menu labels and selectors for every step below into the Lessons Register.

## 3. Eight-layer Screener sweep (G2 → G3)
Path for each layer: Screener → Domain: All companies → move to the right box → Filter → Table → Field → Criteria (pick via **Show Criteria Values**; never free-type a code) → Year Selection ≥ earliest code and ≤ current code → **Parse** → **Show sql** (copy into strategy.json) → **Run Query** → **Save** (CSV) and **Export → MS-Excel**.
| L | Field | Pattern |
|---|---|---|
| L1 | NIC Code | exact classes, then the parent group as a widening pass |
| L2 | NIC Activity | like "%synonym%" for each synonym |
| L3 | Industry / Sector | mapped Capitaline industries |
| L4 | Finished Product Code (ITC-HS) | 4- and 6-digit |
| L5 | Finished Product name | like "%product%" for each synonym |
| L6 | Raw Materials | inputs (manufacturers only) |
| L7 | Segment Finance segment name | catches diversified companies |
| L8 | Background / business text | catches misclassified companies |
Run every layer alone (for attributable counts), then build the unions: classification universe (L1∪L2∪L3), product universe (L4∪L5∪L6), plus the L7 and L8 catch-nets. De-duplicate on Capitaline company code (else CIN, else normalised name). Reconcile counts. Save the union as Peer Set `<RunID>-UNIVERSE`.
G2 gate: the NIC + product key is already in the library with a manager-approved strategy → auto-pass. Otherwise post the strategy card and wait for `APPROVE <RunID> G2`.

## 3D. Desktop route — Capitaline desktop application (PRIMARY for SBC; screen map from the ICAI Bengaluru session, 23 Oct 2018 recording)
Window: menu bar **File · Window · Tools · Administration · Data Export · Help**; company search box with "Select Company / Select Corporate Action"; **TP Screener** button top-right. Left navigation pane tabs: MyItems · Screener · Custom Screener · Updates · MyAlerts; tree: COMPANY (GENERAL, FINANCE, EQUITY, SHARE PRICE, PRODUCTS, REPORTS, RESEARCH, CA ANALYTICAL TOOLS, NEWS, CUSTOMISED SCREENS, TEMPLATES → **TRANSFER PRICING**) · INDUSTRY · HOUSE · PEERSET · CORPORATE ACTION · FACT SHEET.
**TP Screener / Screener window — four tabs: Domain · Filters · Output · Formula.**
1. **Domain**: Select Portfolio = **Non Aggregate**; leave "Select Only Listed Companies" OFF (unlisted comparables count); BSE/NSE unticked. Expand **Company Domain** tree (Capitaline industries, e.g. "Computers – Software – Medium / Small") → tick industries → companies appear in **Selected Company Domain** (right). Bottom: Companies dropdown + search + Select · Select All · Deselect All · Clear · **Save**. Buttons **Delete Peerset · Import Peerset · Export Peerset** — save the universe as Peerset `<RunID>-UNIVERSE`.
2. **Filters**: left **Tables** tree (Finance → Financial Overview → Manufacturing / Bank / Software / Finance / Power / Shipping / Hotel; Financial Overview Consolidated; Balance Sheet; Profit and Loss; Forex; R&D; Related Party; NIC; Products …) with "Show Search Text"; middle **Fields** checklist (e.g. Net Sales, Value of Output, Cost of Production, Selling Cost, PBIDT, PBDT, PBIT, PBT, Adjusted PAT, CP, Revenue earnings in forex, Revenue expenses in forex …); right **Select Screener** (User Screener), **Criteria Values** From / To, **Display Criteria Values**. Lower grid per selected field: Formula · Column Name · Table Name · Display ✓ · Order · **Year/Date/Range** (YYYYMM, e.g. 202603) · Parameter / Custom Col · **Criteria**. Bottom buttons: **Run Query · Show SQL · Save · Save/Load · Currency · Refresh · Clear · Exit**.
3. **Output**: result grid → **Data Export** menu or right-click → Export to Excel; in the Save As dialog type `C:\BM-Factory\_landing\<RunID>_L<n>_<field>.xls` (watcher files it). Also Save the screener (CSV) and copy Show SQL text into strategy.json.
4. **Formula**: define custom ratios once and save in the User Screener: OP/OC = PBIT ÷ (Total Expenditure + Depreciation − Other Income items), RPT % = RPT transactions ÷ Net Sales, Employee cost %, Export %. Reuse by name every run.
Layers L1–L8 (§3) map to Filters tables: L1 NIC Code · L2 NIC Activity · L3 Domain industry tree / Sector · L4 Finished Products code · L5 Finished Products name · L6 Raw Materials · L7 Segment Finance · L8 Background text.
**Company checks (G5)**: type company in the search box → FINANCE → Financial Overview, Balance Sheet, Profit and Loss, Segment Finance, Forex Data, Deferred Tax, R&D, **Related Parties (Related Party Trans / Related Party Relationship)**, Subsidiaries; REPORTS → Directors Report, Notes, MD&A; PRODUCTS → Finished Goods / Raw Materials; TEMPLATES → **TRANSFER PRICING** (PBT/Operating Income, PBT/Operating Cost, PBT/Total Cost; RPT by nature — sale/purchase of services, assets, dividend, commission, rent, remuneration, others — by party type: KMP relatives, JV, individuals, others, holding company, with Total and % Sales). Export each screen (Data Export) to 05-Annual-Reports.
Desktop hygiene: maximise the window; screenshot before every click; never close dialogs you did not open; if a modal error appears, screenshot it into 04-Screens-Evidence, press Esc/OK once, retry once, then follow §9.

## 3A. Web route — Capitaline TP Screener online (secondary; only if SBC adds the online product)
Login: capitaline.com home page → Login ID / Password → Go (the user signs in; the agent never submits credentials). Then Capitaline Databases → top button **TP Screener** ("Introduction tool for TP Report").
Step 1 "Filter companies based on below activities": eight pick-lists, each with search box (min 2–3 characters), year selector and "Load All": **Industry**, **Sector**, **Segment** (Domestic / Outside India / Exports…), **Balance Sheet Abstract**, **NIC Activity (2008)**, **NIC Code (2008)**, **Finished Products** (with %share operator and value), **Finished Product Code** (with operator and value). Tick the values for each layer → Submit. Run each layer alone first, then combined (same L1–L8 logic as §3).
Step 2 filter grid: Select Module (Background / Financial Overview / Balance Sheet / Profit and Loss / Forex Data / R&D) + Select Columns + Output (No. of Years, Default, Load Fields). Rows with Operator + Criteria and live **No. of Cos Matched / Unmatched**: Company Long Name · Year End (Range, e.g. 202404–202603) · Net Sales (> value) · Sales to Total Income (%) · Operating Profit · Operating Profit Margin (%) · PBT (> 0) · Networth · Operating Profit to Total Cost (%) · RPT to Sales (%) (< 25). Record matched/unmatched per row = waterfall.
Buttons: **View Matrix Report** (per company ✓/✗ per filter + Accepted/Rejected status — screenshot + export as AR evidence) · View Report · Reset · **Generate TP Report** · **Get TP Report** (Excel download with one sheet per filter: "<Filter> Matched" / "<Filter> Unmatched") · Sample TP Report.
Company-level checks (desktop / Capitaline Plus): Company → Finance → Transfer Pricing screen shows RPT by party type (KMP relatives, JV, individuals, others, holding company) with Total and % Sales; Segment Finance; Products → Finished Goods.
Licence products seen in the ICAI scheme: Capitaline TP (Online), Capitaline Plus (Online), Capitaline TP (Desktop). Confirm which one SBC holds (mail sent to C-MOTS 7 Nov 2026).

## 4. Quantitative waterfall (G4)
Domain = the Peer Set. Pull three years of P&L, BS, Forex, R&D and Related Party Transaction tables and export each one. Apply in order, logging in/out at every step into the Cap-Matrix **Waterfall** sheet:
Q1 data available (Rule 10CA(3) at 3CEB stage) · Q2 March year-end, 12 months · Q3 turnover band · Q4 positive net worth · Q5 loss in 2 of 3 years · Q6 RPT ≤ 25% of operating revenue (transaction values, not year-end balances) · Q7 service income ≥ 75% (services) · Q8 employee cost ≥ 25% (services) · Q9 export ≥ 75% (optional) · Q10 government / co-operative · Q11 exceptional year.
The same thresholds apply to every company. A command override changes them for the whole run only.

## 5. Qualitative screen (G5)
For each survivor, open the Company module: Background → Directors' Report → Management Discussion → Notes to Accounts → Related Party Transaction / Relationship → Segment Finance → Finished Goods / Raw Materials → Digital Reports. Check the company website from the workspace (WebFetch), not the Capitaline seat.
Decide Accept / Reject / Borderline with one reason code from R01–R14 (`Reasons` sheet), a one-line rationale quoting the source, and an evidence URL.
Never reject on margin alone (Chryscapital, Delhi HC 2015). Never accept on NIC code alone (Rampgreen, Delhi HC 2015). Verify citations with tp-caselaw-engine before external use.
Post the G5 card (counts, accept list, rejects grouped by reason, borderlines). The **manager approval is mandatory**.

## 6. PLI and range (G6)
Fill the PLI sheet with operating items only: exclude interest, dividend, asset-sale gains, write-backs, non-operating forex, extraordinary and prior-period items, and log every adjustment.
Weighted average = Σ OP ÷ Σ OC over the available years. Range sheet: n ≥ 6 → 35th, median and 65th by the Rule 10CA position rule (n × p; integer → average of that value and the next; otherwise the next higher). n < 6 → mean ± tolerance. Report the tested party's position.

## 7. Package and hand off (G7)
Generate annexures A (search process: layers, SQL, counts, waterfall), B (AR matrix), C (financials) and D (business descriptions) into `07-Annexures`. Check that every file in evidence-log.csv appears in `_manifest.json`.
Write the Doc Enabler job (TAIGA engagement, study "Capitaline · <industry> · FY", PLI, files). The **partner signs G7** before TAIGA generates the Local File.
Folder: `Clients/<Client>/FY <yyyy-yy>/TP Documentation/03 TAIGA & Workings/BM Backup/Capitaline/<RunID>/{00-Command,01-Search-Strategy,02-Raw-Dumps,03-Financials,04-Screens-Evidence,05-Annual-Reports,06-Workings,07-Annexures,99-Logs}`. Put a client-neutral copy in `BM Factory/Library/Capitaline/<FY>/<NIC>-<industry>/`.

## 8. Close and learn (G8)
Send one digest to the partner and no other mail: RunID, funnel counts, range, pending approvals, links. Write `99-Logs/run-record.json` with duration, retries, fallbacks and human touches.
Every REWORK, approval comment or Teams/mail instruction tagged to a RunID becomes a Lessons row: trigger · rule · scope · source quote · giver · status. The lesson becomes **Active** once its giver (or the partner) confirms. Contradictions go to the partner. Raise a skill or SOP edit when a lesson changes a step.

## 9. Self-correction ladder
Detect → classify → retry once → alternate route → degrade gracefully with evidence → escalate **with the fix proposed**. Always report what failed and what you did instead.
F1 Capitaline logged out → human signs in on System 3 (Revanth / Aslam), agent resumes. F2 zero rows → parent NIC / synonyms / Show Criteria Values. F3 export blocked → Data Export menu / right-click export / CSV Save / Ctrl+A Ctrl+C grid into Excel + screenshots. F4 layout changed → locate by text or vision and update the selector note. F5 > 1,500 rows → intersect with NIC class or split by year. F6 concurrent login → wait 10 min, retry once, never force others off. F7 watcher down → continue; files wait in `_landing`. F8 totals don't reconcile → re-pull, else R09. F9 TAIGA down → SharePoint is the system of record; re-queue. F10 chat not linked to the Windows System 3 → queue the job in `_jobs/inbox` for Route B. F11 Save As dialog defaults elsewhere → type the full `C:\\BM-Factory\\_landing\\…` path; never save to Downloads.

## 10. Approval codes
`APPROVE <RunID> G2|G5|G7` · `REWORK <RunID> G<n> "<instruction>"` · `HOLD <RunID>` · `RESUME <RunID>`. Accept them from the BM AGENTS chat, Teams or mail, from SBC internal addresses only.

## 11. Never
Never type or store passwords, OTPs or keys in chat, files or logs. Never edit raw dumps. Never mail clients or authorities. Never run parallel Capitaline sessions. Never let TAIGA's vault serve Capitaline data to white-label tenants. Never mark a gate passed without its evidence file.
