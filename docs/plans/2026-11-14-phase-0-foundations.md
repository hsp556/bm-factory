# Phase 0: Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the shared contracts every BM station and the Command Centre will use (RunID, FY/year codes, Command, Job, Manifest, step catalogue, screen map), and seed the Capitaline step catalogue + screen map v0.

**Architecture:** One Python package `bmfactory` (src layout). `bmfactory.contracts` holds Pydantic v2 models and pure functions with no I/O apart from YAML loading and JSON Schema export. Station data files live in `stations/<db>/`. JSON Schemas are exported to `contracts/schemas/` for non-Python consumers.

**Tech Stack:** Python 3.12, Pydantic ≥2.7, PyYAML ≥6, pytest ≥8.

**Spec:** `docs/ARCHITECTURE.md` (decisions D1–D6, §4, §7). Procedure source: `SKILL (9).md` §1 and §3D.

## Global Constraints
- Python `>=3.12`. Runtime dependencies: only `pydantic>=2.7` and `pyyaml>=6`. Dev dependency: only `pytest>=8`. Optional extra `station = ["pywinauto>=0.6.8"]`, installed on System 3 only; no module outside `bmfactory.inspector.dump` may import pywinauto.
- Live tests carry `@pytest.mark.system3` and are skipped unless the environment variable `BM_SYSTEM3=1` is set.
- The inspector is read-only: it never clicks, types, sets focus or changes any control.
- Package `bmfactory` lives at `src/bmfactory/`. Tests live at `tests/`. Tests run offline, with no network, Capitaline, SharePoint or Claude calls.
- Database codes: `CAP`, `PRW`, `ACE`, `CAT`, `CMP`.
- RunID: `<DB>-FY<yy><yy>-<client-slug|LIB>-<YYYYMMDD>-<nn>`, e.g. `CAP-FY2526-LIB-20261114-01` (D6).
- Year codes = `YYYY03` for the FY end year and the two preceding years, newest first. FY 2025-26 → `["202603","202503","202403"]`.
- Run folders (first path segment of every manifest file): `00-Command`, `01-Search-Strategy`, `02-Raw-Dumps`, `03-Financials`, `04-Screens-Evidence`, `05-Annual-Reports`, `06-Workings`, `07-Annexures`, `99-Logs`.
- Raw dump name: `02-Raw-Dumps/<RunID>_L<n>_<field>_<seq3>.<csv|xls|xlsx>`, with n in 1–8.
- PLI defaults by tested party: service `OP/OC`, distributor `OP/OR`, manufacturer `OP/OC`. Allowed PLIs: `OP/OC`, `OP/OR`, `GP/Sales`.
- Never store credentials in code, fixtures or YAML.
- Commits go on branch `phase-0-contracts` only. Merging or pushing needs human approval.

## Review Focus
1. FY typed or spoken loosely ("FY25-26", "25-26", "2025-2026") must normalise to `2025-26`. Non-consecutive years ("2025-27") must be rejected. Covered in Task 1.
2. Client names with spaces, dots or hyphens must survive a RunID round trip (slug → id → parse). Covered in Task 1.
3. Sloppy command text must still parse: mixed-case keys, extra spaces, a trailing `;` in products, "₹ 45 cr". Covered in Task 2.
4. Manifest paths with `..`, absolute paths, drive letters or Windows-reserved names (`CON`, `nul.csv`) must be rejected. Covered in Task 3.
5. A step that references a target missing from the screen map must be reported, not crash. A locator with no identifier must be rejected. Covered in Task 4.

## Human track (runs in parallel; not executed by agents)
| # | Action | Owner | Done when |
|---|---|---|---|
| H1 | Licence: confirmed by the user on 2026-11-14 (D7). File any written C-MOTS reply when it arrives | Revanth | Reply filed in `BM Factory/Licences/` |
| H2 | Decide O4 (code repository) and push this folder | You | Repo exists; `main` pushed |
| H3 | System 3 via Iperius Remote: Git, Python 3.12 and Claude Code installed; never sleeps, no lock screen, auto-login, 1920×1080 at 100%; repo cloned; `pip install -e ".[dev,station]"` | Aslam / you | `git`, `python` and `claude --version` run; `pytest` green on System 3 |
| H4 | Iperius disconnect test: run a 3-minute screenshot loop, disconnect, reconnect | You + Claude on System 3 | Screenshots taken while disconnected show the unlocked desktop |
| H5 | After Task 5: open the Capitaline main window, then the TP Screener Domain, Filters and Output tabs, and run the inspector on each | You (opens screens) | `docs/discovery/capitaline-feasibility.md` rates each target green/amber/red |
| H5b | Supervised learning run: Claude on System 3 follows SKILL §3D for layer L1 on the golden job (`CAP \| FY 2025-26 \| NIC 6201 \| Product: software development`) while a TP manager watches through Iperius. Also test Save/Load Screener and Import/Export Peerset | Claude + TP manager | `stations/capitaline/screen-map.yaml` updated to verified v1 by PR; feature results noted |
| H6 | IT: Entra app registration with Graph `Sites.Selected` on the SteadFast test folder | IT | A test file uploads |
| H7 | Decide O2 (Claude route: Anthropic API, Claude Platform on AWS or Bedrock). Confirm computer use and data terms | You + IT | Recorded as a new decision in ARCHITECTURE.md |
| H8 | Create an AWS IAM/project in ap-south-1 for the Command Centre (needed in Phase 3; start early) | IT | Account and role exist |
| H9 | Record ~40 sample voice commands from partners and managers for the O1 bake-off | You | Audio files stored in a restricted SharePoint folder |

---

### Task 1: Project scaffold, FY handling and RunID

**Files:**
- Create: `pyproject.toml`, `src/bmfactory/__init__.py`, `src/bmfactory/contracts/__init__.py`, `src/bmfactory/contracts/ids.py`
- Test: `tests/contracts/test_ids.py`

**Interfaces:**
- Produces, in `bmfactory.contracts.ids`:
  - `DB_CODES: tuple[str, ...] = ("CAP","PRW","ACE","CAT","CMP")`
  - `normalise_fy(text: str) -> str`
  - `current_compliance_fy(today: date) -> str`
  - `year_codes(fy: str) -> list[str]`
  - `slugify_client(name: str) -> str`
  - `make_run_id(db: str, fy: str, client_slug: str | None, run_date: date, seq: int) -> str`
  - `parse_run_id(run_id: str) -> RunIdParts`
  - `class RunIdParts(BaseModel)` with fields `db: str`, `fy: str`, `client_slug: str | None`, `run_date: date`, `seq: int`

- [ ] **Step 1: Create `pyproject.toml`** (hatchling build, src layout, deps per Global Constraints, `[project.optional-dependencies] dev = ["pytest>=8"]`, `[tool.pytest.ini_options] testpaths=["tests"]`). Then create the venv and install: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`.
- [ ] **Step 2: Write failing tests** in `tests/contracts/test_ids.py`:

```python
@pytest.mark.parametrize("raw", ["2025-26", "FY 2025-26", "FY25-26", "25-26", "2025-2026", " fy2025-26 "])
def test_normalise_fy_variants(raw): assert normalise_fy(raw) == "2025-26"

@pytest.mark.parametrize("bad", ["2025-27", "2025", "FY", "26-25", ""])
def test_normalise_fy_rejects(bad):
    with pytest.raises(ValueError): normalise_fy(bad)

@pytest.mark.parametrize("today,fy", [(date(2026,11,14),"2025-26"), (date(2027,2,1),"2025-26"), (date(2027,4,1),"2026-27")])
def test_current_compliance_fy(today, fy): assert current_compliance_fy(today) == fy

def test_year_codes(): assert year_codes("2025-26") == ["202603", "202503", "202403"]

def test_slugify_client(): assert slugify_client("KRKA Pharma Pvt. Ltd.") == "krka-pharma-pvt-ltd"

def test_make_run_id_library(): assert make_run_id("CAP", "2025-26", None, date(2026,11,14), 1) == "CAP-FY2526-LIB-20261114-01"

def test_run_id_round_trip_hyphenated_client():
    rid = make_run_id("PRW", "FY 2025-26", slugify_client("Acme - India Ltd"), date(2026,11,14), 7)
    assert rid == "PRW-FY2526-acme-india-ltd-20261114-07"
    p = parse_run_id(rid)
    assert (p.db, p.fy, p.client_slug, p.run_date, p.seq) == ("PRW", "2025-26", "acme-india-ltd", date(2026,11,14), 7)

def test_parse_run_id_lib_is_none(): assert parse_run_id("CAP-FY2526-LIB-20261114-01").client_slug is None

@pytest.mark.parametrize("bad", ["XYZ-FY2526-LIB-20261114-01", "CAP-FY2526-LIB-20261114-00", "CAP-FY2527-LIB-20261114-01", "CAP-2526-LIB-20261114-01", "CAP-FY2526-LIB-2026111-01"])
def test_parse_run_id_rejects(bad):
    with pytest.raises(ValueError): parse_run_id(bad)

@pytest.mark.parametrize("db,seq", [("XYZ", 1), ("CAP", 0), ("CAP", 100)])
def test_make_run_id_rejects(db, seq):
    with pytest.raises(ValueError): make_run_id(db, "2025-26", None, date(2026,11,14), seq)
```

- [ ] **Step 3: Run** `.venv/Scripts/python -m pytest tests/contracts/test_ids.py -v`. Expected: FAIL (import error).
- [ ] **Step 4: Implement `ids.py`** with these rules:
  - `normalise_fy`: strip, drop an optional case-insensitive `FY`, accept `YYYY-YY`, `YY-YY` (assume the 20YY century) or `YYYY-YYYY`; the end year must equal start + 1.
  - `current_compliance_fy`: `end = today.year if today.month >= 4 else today.year - 1`, then return `f"{end-1}-{end % 100:02d}"`.
  - `slugify_client`: lowercase, runs of non-`[a-z0-9]` become `-`, strip `-`, maximum 30 characters, error if empty.
  - `parse_run_id`: split on `-`. Tokens 0–1 are db and FY; the last two are date and seq; the middle tokens join to the client (`LIB` → `None`).
- [ ] **Step 5: Run** the same pytest command. Expected: all PASS.
- [ ] **Step 6: Commit** `git add pyproject.toml src/bmfactory tests/contracts/test_ids.py && git commit -m "feat(contracts): FY normalisation, year codes and RunID"`

### Task 2: Command grammar parser

**Files:**
- Create: `src/bmfactory/contracts/command.py`
- Test: `tests/contracts/test_command.py`

**Interfaces:**
- Consumes: `normalise_fy`, `current_compliance_fy`, `DB_CODES` (Task 1).
- Produces, in `bmfactory.contracts.command`:
  - `class Command(BaseModel)` with fields:
    - `db: str`, `fy: str`, `industry: str`, `nic_codes: list[str]`, `products: list[str]` (min 1)
    - `client: str | None`, `pli: Literal["OP/OC","OP/OR","GP/Sales"]`, `tp_sales_cr: float | None`
    - `tested_party: Literal["service","manufacturer","distributor"]`, `mode: Literal["run","strategy-only","refresh"]`
  - `class CommandError(ValueError)`
  - `parse_command(text: str, today: date) -> Command`

- [ ] **Step 1: Write failing tests:**

```python
T = date(2026, 11, 14)

def test_minimal_defaults():
    c = parse_command("CAP | FY 2025-26 | Industry: software development | Product: application development; IT consulting", T)
    assert (c.db, c.fy, c.industry, c.products) == ("CAP", "2025-26", "software development", ["application development", "IT consulting"])
    assert (c.pli, c.tested_party, c.mode, c.client, c.tp_sales_cr, c.nic_codes) == ("OP/OC", "service", "run", None, None, [])

def test_full_command():
    c = parse_command("CAP | FY 2025-26 | Industry: pharmaceutical formulations | Product: tablets; capsules | Client: KRKA | PLI: OP/OR | Tested party: distributor", T)
    assert (c.client, c.pli, c.tested_party) == ("KRKA", "OP/OR", "distributor")

def test_bare_nic_segment():
    c = parse_command("CAP | FY 2025-26 | NIC 6201 | Product: SaaS | Mode: strategy-only", T)
    assert (c.industry, c.nic_codes, c.mode) == ("NIC 6201", ["6201"], "strategy-only")

def test_fy_defaults_to_compliance_year():
    assert parse_command("CAP | Industry: ITeS | Product: BPO", T).fy == "2025-26"

def test_sloppy_text():
    c = parse_command("  cap|fy25-26 |  INDUSTRY :  ITeS | product: medical transcription ; ;| tp SALES: ₹ 45.5 cr ", T)
    assert (c.db, c.fy, c.products, c.tp_sales_cr) == ("CAP", "2025-26", ["medical transcription"], 45.5)

def test_distributor_default_pli():
    assert parse_command("CAP | Industry: x | Product: y | Tested party: distributor", T).pli == "OP/OR"

@pytest.mark.parametrize("text,field", [
    ("CAP | Product: y", "industry"),
    ("CAP | Industry: x", "product"),
    ("XYZ | Industry: x | Product: y", "db"),
    ("CAP | Industry: x | Product: y | Colour: red", "colour"),
    ("CAP | Industry: x | Product: y | PLI: GP/Sales", "pli"),        # GP/Sales invalid for a service provider (Rule 10C)
    ("CAP | Industry: x | Product: y | TP sales: -3", "tp sales"),
])
def test_rejects_with_field_named(text, field):
    with pytest.raises(CommandError, match=field): parse_command(text, T)
```

- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/contracts/test_command.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `parse_command`** with these rules:
  - Split on `|` and strip. Segment 0 is the db code (case-insensitive).
  - Keys match case-insensitively, with spaces collapsed.
  - A segment matching `(?i)^nic\s*(\d{2,5})$` sets both industry and nic_codes. An `Industry:` value of that form does the same.
  - TP sales: strip `₹`, `rs`, `cr` and `crore`, then parse as a float that must be > 0.
  - An unknown key raises `CommandError` naming the key.
  - Raise `CommandError` for `GP/Sales` when tested_party is `service`.
- [ ] **Step 4: Run** the same command. Expected: all PASS.
- [ ] **Step 5: Commit** `git add src/bmfactory/contracts/command.py tests/contracts/test_command.py && git commit -m "feat(contracts): command grammar parser"`

### Task 3: Job and Manifest models + JSON Schema export

**Files:**
- Create: `src/bmfactory/contracts/job.py`, `src/bmfactory/contracts/manifest.py`, `src/bmfactory/contracts/schema_export.py`, `contracts/schemas/{command,job,manifest}.schema.json` (generated)
- Test: `tests/contracts/test_manifest.py`, `tests/contracts/test_schemas.py`

**Interfaces:**
- Consumes: `Command` (Task 2), `parse_run_id` (Task 1).
- Produces:
  - In `job.py`: `class Job(BaseModel)` with fields `run_id: str` (validated by `parse_run_id`), `dest: str`, `command: Command`, `created_at: datetime`, `status: Literal["inbox","running","enable","stuck","done"]`.
  - In `manifest.py`:
    - `RUN_FOLDERS: tuple[str, ...]`
    - `safe_relative_path(p: str) -> str`
    - `class FileEntry(BaseModel)`: `path`, `kind: Literal["command","strategy","raw_dump","financials","screenshot","annual_report","working","annexure","log"]`, `layer: str | None`, `sha256: str` (64 lowercase hex), `bytes: int` ≥0, `sharepoint_url: str | None`
    - `class LayerResult(BaseModel)`: `id: Literal["L1",…,"L8"]`, `field: str`, `sql: str`, `row_count: int` ≥0
    - `class SourceInfo(BaseModel)`: `database: str`, `data_date: date | None`, `year_codes: list[str]`
    - `class Universe(BaseModel)`: `distinct_companies: int` ≥0, `peer_set: str | None`
    - `class Manifest(BaseModel)`: `schema_version: Literal["1.0"]`, `run_id`, `command: Command`, `source: SourceInfo`, `layers: list[LayerResult]`, `universe: Universe | None`, `files: list[FileEntry]`, `status: Literal["complete","partial","failed"]`, `fallbacks_used: list[str]`, `human_touches: int` ≥0
  - In `schema_export.py`: `export_schemas(out_dir: Path) -> list[Path]`

- [ ] **Step 1: Write failing tests** in `tests/contracts/test_manifest.py`. Use a `good_manifest()` fixture for run `CAP-FY2526-LIB-20261114-01` with one raw dump `02-Raw-Dumps/CAP-FY2526-LIB-20261114-01_L1_NICCode_001.csv`, layer `L1`.

```python
def test_good_manifest_valid(): Manifest.model_validate(good_manifest())

@pytest.mark.parametrize("p", ["../x.csv", "/etc/x", "C:\\x.csv", "02-Raw-Dumps/../../x", "02-Raw-Dumps/CON", "02-Raw-Dumps/nul.csv", "Random/x.csv", "02-Raw-Dumps/a|b.csv", ""])
def test_unsafe_paths_rejected(p):
    with pytest.raises(ValueError): safe_relative_path(p)

def test_backslashes_normalised(): assert safe_relative_path("99-Logs\\run-record.json") == "99-Logs/run-record.json"

def test_raw_dump_name_must_match_run_and_layer():
    m = good_manifest(); m["files"][0]["layer"] = "L2"
    with pytest.raises(ValidationError): Manifest.model_validate(m)
    m = good_manifest(); m["files"][0]["path"] = "02-Raw-Dumps/OTHER_L1_NICCode_001.csv"
    with pytest.raises(ValidationError): Manifest.model_validate(m)

def test_duplicate_paths_rejected():
    m = good_manifest(); m["files"].append(dict(m["files"][0]))
    with pytest.raises(ValidationError): Manifest.model_validate(m)

def test_bad_sha_rejected():
    m = good_manifest(); m["files"][0]["sha256"] = "XYZ"
    with pytest.raises(ValidationError): Manifest.model_validate(m)

def test_job_rejects_bad_run_id():
    cmd = parse_command("CAP | Industry: x | Product: y", date(2026, 11, 14))
    with pytest.raises(ValidationError): Job(run_id="bad", dest="x", command=cmd, created_at=datetime(2026, 11, 14), status="inbox")
```

  In `tests/contracts/test_schemas.py`:
  - `test_export_writes_three_schemas(tmp_path)`: the files exist, parse as JSON, and each has a `title`.
  - `test_committed_schemas_match_models(tmp_path)`: export to `tmp_path`, then check it equals the files in `contracts/schemas/` byte for byte. This guards against drift.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/contracts/test_manifest.py tests/contracts/test_schemas.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement the three modules.**
  - `safe_relative_path` rejects: empty, a leading `/` or `\`, a drive letter, any `..` or empty segment, the characters `<>:"|?*`, reserved stems (`CON PRN AUX NUL COM1-9 LPT1-9`, case-insensitive, checked on the stem before the first dot), and a first segment not in `RUN_FOLDERS`. It returns the path with forward slashes.
  - The `Manifest` model validator checks that paths are unique, and that every `raw_dump` path matches `^02-Raw-Dumps/{run_id}_(L[1-8])_[A-Za-z0-9]+_\d{3}\.(csv|xls|xlsx)$` with group 1 equal to `layer`.
  - `export_schemas` writes `json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"`.
- [ ] **Step 4: Generate the committed schemas:** `.venv/Scripts/python -c "from pathlib import Path; from bmfactory.contracts.schema_export import export_schemas; export_schemas(Path('contracts/schemas'))"`.
- [ ] **Step 5: Run** the full suite: `.venv/Scripts/python -m pytest -v`. Expected: all PASS.
- [ ] **Step 6: Commit** `git add src/bmfactory/contracts/{job,manifest,schema_export}.py contracts/schemas tests/contracts/test_manifest.py tests/contracts/test_schemas.py && git commit -m "feat(contracts): job, manifest and JSON schema export"`

### Task 4: Step catalogue + screen map, with the Capitaline seed

**Files:**
- Create: `src/bmfactory/contracts/stations.py`, `stations/capitaline/steps.yaml`, `stations/capitaline/screen-map.yaml`
- Test: `tests/contracts/test_stations.py`

**Interfaces:**
- Produces, in `bmfactory.contracts.stations`:
  - `class StepDef(BaseModel)`:
    - `id: str` (`^[a-z][a-z0-9_]*$`), `gate: Literal["G1","G2","G3"]`
    - `action: Literal["click","select","type","read_text","read_grid","screenshot","wait_for"]`
    - `target: str | None` (required unless action is `screenshot`), `params: dict[str, str] = {}`, `sop_ref: str`
  - `class StepCatalogue(BaseModel)`: `database: str`, `version: int` ≥1, `steps: list[StepDef]` (ids unique)
  - `class Locator(BaseModel)`: `backend: Literal["uia","win32","playwright"]`, `window: str`, `control_type: str | None`, `auto_id: str | None`, `name: str | None`, `path: list[str] = []`. At least one of auto_id, name or path must be set.
  - `class ScreenMap(BaseModel)`: `database: str`, `version: int` ≥1, `verified: bool`, `app_version_seen: str | None`, `recorded_at: datetime | None`, `targets: dict[str, Locator]`
  - `load_steps(path: Path) -> StepCatalogue`, `load_screen_map(path: Path) -> ScreenMap`
  - `missing_targets(steps: StepCatalogue, smap: ScreenMap) -> list[str]` (sorted, unique)

- [ ] **Step 1: Write failing tests:**

```python
def test_seed_files_load_and_are_consistent():
    steps = load_steps(Path("stations/capitaline/steps.yaml"))
    smap = load_screen_map(Path("stations/capitaline/screen-map.yaml"))
    assert steps.database == smap.database == "CAP"
    assert smap.verified is False and smap.version == 1
    assert missing_targets(steps, smap) == []
    assert [s.id for s in steps.steps][:3] == ["open_tp_screener", "open_domain_tab", "set_portfolio_non_aggregate"]

def test_missing_target_reported_not_raised():
    steps = StepCatalogue(database="CAP", version=1, steps=[StepDef(id="a", gate="G2", action="click", target="ghost", sop_ref="x")])
    smap = ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None, targets={})
    assert missing_targets(steps, smap) == ["ghost"]

def test_locator_needs_an_identifier():
    with pytest.raises(ValidationError): Locator(backend="uia", window="TP Screener", control_type="Button", auto_id=None, name=None)

def test_duplicate_step_ids_rejected(): ...   # two StepDef with id "a" → ValidationError
def test_click_requires_target(): ...          # action click, target None → ValidationError
```

- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/contracts/test_stations.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `stations.py`.** Loaders use `yaml.safe_load` only.
- [ ] **Step 4: Write the seed `steps.yaml`** (database `CAP`, version 1). It covers one layer, in this order, as `id: action → target {params}`. `sop_ref` is SKILL §3D.1 for the domain steps, §3D.2 for the filter steps and §3D.3 for the output steps.
  1. `open_tp_screener`: click → `tp_screener_button`
  2. `open_domain_tab`: click → `domain_tab`
  3. `set_portfolio_non_aggregate`: select → `portfolio_dropdown` {value: "Non Aggregate"}
  4. `ensure_listed_only_off`: select → `listed_only_checkbox` {value: "off"}
  5. `open_filters_tab`: click → `filters_tab`
  6. `pick_table`: select → `tables_tree` {value: "{table}"}
  7. `pick_field`: select → `fields_checklist` {value: "{field}"}
  8. `show_criteria_values`: click → `display_criteria_values_button`
  9. `set_criteria`: select → `criteria_values_list` {value: "{criteria}"}
  10. `set_year_range`: type → `year_range_cell` {value: "{year_range}"}
  11. `show_sql`: click → `show_sql_button`
  12. `capture_sql`: read_text → `sql_text_box`
  13. `run_query`: click → `run_query_button` (gate G3 from here on; steps 1–12 are G2)
  14. `read_output`: read_grid → `output_grid`
  15. `open_data_export`: click → `data_export_menu`
  16. `type_save_path`: type → `save_as_filename_box` {value: "C:\\BM-Factory\\_landing\\{run_id}_L{layer}_{field}_{seq}.xls"}
  17. `confirm_save`: click → `save_as_save_button`
- [ ] **Step 5: Write the seed `screen-map.yaml`** (database `CAP`, version 1, `verified: false`, backend `uia`). Use one locator per target above, with `name` set to the SKILL §3D label text (e.g. "TP Screener", "Domain", "Filters", "Run Query", "Show SQL", "Data Export", "Save") and the window "Capitaline" or "TP Screener" as SKILL §3D implies. Add the comment `# v1 seeded from SKILL §3D labels; verify with learning run H3/H4`.
- [ ] **Step 6: Run** the full suite: `.venv/Scripts/python -m pytest -v`. Expected: all PASS.
- [ ] **Step 7: Commit** `git add src/bmfactory/contracts/stations.py stations/capitaline tests/contracts/test_stations.py && git commit -m "feat(contracts): step catalogue and screen map with Capitaline seed"`

### Task 5: Read-only UI inspector and screen-map coverage report

Where: Steps 1–5 on the dev PC (offline). Step 6 on System 3 through Iperius Remote.

**Files:**
- Create: `src/bmfactory/inspector/__init__.py`, `src/bmfactory/inspector/coverage.py`, `src/bmfactory/inspector/dump.py`, `src/bmfactory/inspector/__main__.py`
- Modify: `pyproject.toml` (add the `station` extra and the `system3` pytest marker)
- Test: `tests/inspector/test_coverage.py`, `tests/inspector/test_live_system3.py`

**Interfaces:**
- Consumes: `ScreenMap`, `Locator`, `load_screen_map` (Task 4).
- Produces, in `bmfactory.inspector.coverage` (pure, no pywinauto):
  - `class ControlInfo(BaseModel)`: `window: str`, `control_type: str`, `auto_id: str`, `name: str`, `class_name: str`, `depth: int`
  - `class TargetScore(BaseModel)`: `target: str`, `rating: Literal["green","amber","red"]`, `matches: int`, `reason: str`
  - `score_targets(smap: ScreenMap, controls: list[ControlInfo]) -> list[TargetScore]` (sorted by target)
  - `render_report(scores: list[TargetScore], windows: list[str]) -> str` (Markdown)
- Produces, in `bmfactory.inspector.dump`: `dump_window(title_regex: str, max_depth: int = 12) -> list[ControlInfo]`
- CLI: `python -m bmfactory.inspector --window <title-regex> --map stations/capitaline/screen-map.yaml --out docs/discovery`

Rating rules. Only targets whose `Locator.window` matches a dumped window are scored; the rest are omitted.
- **green:** exactly one control matches on `auto_id` (when the locator has one), or exactly one matches on `name` + `control_type`.
- **amber:** more than one control matches, or the only match is on `name` alone (the control type differs or is unset).
- **red:** no control matches.
- Name comparison is case-insensitive and ignores `&` accelerator marks and surrounding spaces.

- [ ] **Step 1: Write failing tests** in `tests/inspector/test_coverage.py`:

```python
def ctl(name="", auto_id="", ctype="Button", window="TP Screener"):
    return ControlInfo(window=window, control_type=ctype, auto_id=auto_id, name=name, class_name="", depth=1)

def smap(**targets):
    return ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None, targets=targets)

def loc(**kw): return Locator(backend="uia", window="TP Screener", **kw)

def test_unique_name_and_type_is_green():
    s = score_targets(smap(run=loc(name="Run Query", control_type="Button")), [ctl("Run Query"), ctl("Show SQL")])
    assert (s[0].rating, s[0].matches) == ("green", 1)

def test_accelerator_and_case_ignored():
    s = score_targets(smap(run=loc(name="Run Query", control_type="Button")), [ctl(" &run query ")])
    assert s[0].rating == "green"

def test_auto_id_wins_over_duplicate_names():
    s = score_targets(smap(save=loc(name="Save", auto_id="btnSave", control_type="Button")), [ctl("Save", "btnSave"), ctl("Save", "btnSaveAs")])
    assert s[0].rating == "green"

def test_duplicate_name_is_amber():
    s = score_targets(smap(save=loc(name="Save", control_type="Button")), [ctl("Save"), ctl("Save")])
    assert (s[0].rating, s[0].matches) == ("amber", 2)

def test_name_match_wrong_type_is_amber():
    s = score_targets(smap(dom=loc(name="Domain", control_type="TabItem")), [ctl("Domain", ctype="Pane")])
    assert s[0].rating == "amber"

def test_missing_is_red():
    s = score_targets(smap(x=loc(name="Ghost", control_type="Button")), [ctl("Run Query")])
    assert (s[0].rating, s[0].matches) == ("red", 0)

def test_targets_for_other_windows_are_omitted():
    other = Locator(backend="uia", window="Save As", name="Save", control_type="Button")
    assert score_targets(smap(a=other), [ctl("Save")]) == []

def test_report_has_summary_and_rows():
    md = render_report([TargetScore(target="run", rating="green", matches=1, reason="unique name+type")], ["TP Screener"])
    assert "| run | green | 1 |" in md and "green: 1" in md and "TP Screener" in md
```

  In `tests/inspector/test_live_system3.py`, add one test marked `@pytest.mark.system3`: `dump_window("Capitaline")` returns at least 10 controls, and every item is a `ControlInfo`.
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest tests/inspector -v`. Expected: FAIL (import error).
- [ ] **Step 3: Implement `coverage.py`** per the rating rules. Window matching is a case-insensitive substring match of `Locator.window` in `ControlInfo.window`.
- [ ] **Step 4: Implement `dump.py` and `__main__.py`.**
  - `dump.py` imports pywinauto inside `dump_window` only. It connects with `Desktop(backend="uia")`, picks the top-level windows whose title matches the regex, and walks descendants to `max_depth` reading only `control_type`, `automation_id`, `window_text` and `class_name`. It calls no method that clicks, types, focuses or changes state.
  - The CLI writes `<out>/controls-<slug>-<YYYYMMDD-HHMMSS>.json` (the raw dump) and appends a section to `<out>/capitaline-feasibility.md` from `render_report`. It exits 1 with a clear message when no window matches.
  - Add to `pyproject.toml`: the `station` extra, and in `[tool.pytest.ini_options]` the marker `system3: needs the live Capitaline desktop`. Add `tests/conftest.py` that skips `system3` tests unless `BM_SYSTEM3=1`.
- [ ] **Step 5: Run** `.venv/Scripts/python -m pytest -v` on the dev PC. Expected: all PASS, with the live test SKIPPED. Commit: `git add pyproject.toml src/bmfactory/inspector tests/inspector tests/conftest.py && git commit -m "feat(inspector): read-only UI dump and screen-map coverage report"`
- [ ] **Step 6 (System 3):** `git pull`, `pip install -e ".[dev,station]"`, then `BM_SYSTEM3=1 .venv/Scripts/python -m pytest -m system3 -v`. Expected: PASS. Then run the CLI once per screen (human track H5) and commit the files under `docs/discovery/`.
