from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bmfactory.contracts.stations import (
    Locator,
    ScreenMap,
    StepCatalogue,
    StepDef,
    load_screen_map,
    load_steps,
    missing_targets,
)

ROOT = Path(__file__).resolve().parents[2]
STEPS_YAML = ROOT / "stations/capitaline/steps.yaml"
MAP_YAML = ROOT / "stations/capitaline/screen-map.yaml"
LOC = "{backend: uia, window: Capitaline, control_type: null, auto_id: null, name: X}"
MAP_HEAD = "database: CAP\nversion: 1\nverified: false\napp_version_seen: null\nrecorded_at: null\n"


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


def test_missing_targets_sorted_unique_and_skips_screenshot():
    steps = StepCatalogue(
        database="CAP",
        version=1,
        steps=[
            StepDef(id="a", gate="G2", action="click", target="zeta", sop_ref="x"),
            StepDef(id="b", gate="G2", action="click", target="alpha", sop_ref="x"),
            StepDef(id="c", gate="G2", action="read_text", target="zeta", sop_ref="x"),
            StepDef(id="d", gate="G2", action="screenshot", target=None, sop_ref="x"),
        ],
    )
    smap = ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None, targets={})
    assert missing_targets(steps, smap) == ["alpha", "zeta"]


def test_locator_needs_an_identifier():
    with pytest.raises(ValidationError):
        Locator(backend="uia", window="TP Screener", control_type="Button", auto_id=None, name=None)


def test_locator_empty_identifiers_do_not_count():
    with pytest.raises(ValidationError):
        Locator(backend="uia", window="TP Screener", control_type="Button", auto_id=None, name="", path=[])


def test_locator_path_alone_is_enough():
    loc = Locator(backend="uia", window="TP Screener", control_type=None, auto_id=None, name=None, path=["Filters", "Tables"])
    assert loc.path == ["Filters", "Tables"]


def test_duplicate_step_ids_rejected():
    with pytest.raises(ValidationError):
        StepCatalogue(
            database="CAP",
            version=1,
            steps=[
                StepDef(id="a", gate="G2", action="click", target="t", sop_ref="x"),
                StepDef(id="a", gate="G2", action="click", target="u", sop_ref="x"),
            ],
        )


def test_click_requires_target():
    with pytest.raises(ValidationError):
        StepDef(id="a", gate="G2", action="click", target=None, sop_ref="x")


def test_screenshot_needs_no_target():
    assert StepDef(id="a", gate="G2", action="screenshot", target=None, sop_ref="x").target is None


@pytest.mark.parametrize("bad", ["A", "1a", "a-b", "a b", "", "ａ", "a\n"])
def test_step_id_and_target_names_are_snake_case(bad):
    with pytest.raises(ValidationError):
        StepDef(id=bad, gate="G2", action="click", target="t", sop_ref="x")
    with pytest.raises(ValidationError):
        StepDef(id="a", gate="G2", action="click", target=bad, sop_ref="x")
    with pytest.raises(ValidationError):
        ScreenMap(
            database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None,
            targets={bad: Locator(backend="uia", window="Capitaline", control_type=None, auto_id=None, name="X")},
        )


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        StepDef(id="a", gate="G2", action="click", target="t", sop_ref="x", extra="y")
    with pytest.raises(ValidationError):
        Locator(backend="uia", window="Capitaline", control_type=None, auto_id=None, name="X", xpath="//x")
    with pytest.raises(ValidationError):
        StepCatalogue(database="CAP", version=1, steps=[], extra="y")
    with pytest.raises(ValidationError):
        ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None, targets={}, extra="y")


def test_control_characters_rejected():
    with pytest.raises(ValidationError):
        StepDef(id="a", gate="G2", action="type", target="t", params={"value": "x\x00y"}, sop_ref="x")
    with pytest.raises(ValidationError):
        Locator(backend="uia", window="Capitaline", control_type=None, auto_id=None, name="Run\u202eQuery")


def test_unknown_database_rejected():
    with pytest.raises(ValidationError):
        StepCatalogue(database="XYZ", version=1, steps=[])


def test_version_must_be_positive():
    with pytest.raises(ValidationError):
        StepCatalogue(database="CAP", version=0, steps=[])


def _seed_steps():
    return load_steps(STEPS_YAML).steps


def test_seed_has_30_unique_steps_and_gate_split():
    steps = _seed_steps()
    ids = [s.id for s in steps]
    assert len(steps) == 30 and len(set(ids)) == 30
    assert [s.gate for s in steps] == ["G2"] * 23 + ["G3"] * 7
    assert ids[0] == "open_tp_screener" and ids[-1] == "confirm_save"


def test_seed_run_query_is_g2_after_capture_sql():
    steps = _seed_steps()
    ids = [s.id for s in steps]
    by_id = {s.id: s for s in steps}
    assert by_id["run_query"].gate == "G2"
    assert ids.index("run_query") > ids.index("capture_sql")


def test_seed_parse_immediately_before_show_sql():
    ids = [s.id for s in _seed_steps()]
    assert ids.index("parse_query") + 1 == ids.index("show_sql")


def test_seed_screenshots_have_no_target():
    shots = {s.id: s for s in _seed_steps() if s.action == "screenshot"}
    assert set(shots) == {"screenshot_domain", "screenshot_sql", "screenshot_output"}
    assert all(s.target is None for s in shots.values())
    assert {s.params["name"] for s in shots.values()} == {"domain", "sql", "output"}


def test_seed_quoted_param_values():
    steps = {s.id: s for s in _seed_steps()}
    assert steps["ensure_listed_only_off"].params == {"value": "off"}
    assert steps["ensure_bse_off"].params == {"value": "off"}
    assert steps["ensure_nse_off"].params == {"value": "off"}
    assert steps["set_portfolio_non_aggregate"].params == {"value": "Non Aggregate"}


def test_seed_save_paths_keep_backslashes():
    steps = {s.id: s for s in _seed_steps()}
    assert steps["type_csv_path"].params["value"] == r"C:\BM-Factory\_landing\{run_id}_L{layer}_{field}_{seq}.csv"
    assert steps["type_save_path"].params["value"] == r"C:\BM-Factory\_landing\{run_id}_L{layer}_{field}_{seq}.xls"


def test_seed_screen_map_uses_uia():
    smap = load_screen_map(MAP_YAML)
    assert {loc.backend for loc in smap.targets.values()} == {"uia"}
    assert smap.targets["tp_screener_button"].name == "TP Screener"


def test_unquoted_off_is_rejected(tmp_path):
    p = tmp_path / "steps.yaml"
    p.write_text(
        "database: CAP\nversion: 1\nsteps:\n"
        "  - {id: a, gate: G2, action: select, target: t, params: {value: off}, sop_ref: x}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="steps.yaml") as exc:
        load_steps(p)
    assert isinstance(exc.value.__cause__, ValidationError)


@pytest.mark.parametrize("loader", [load_steps, load_screen_map])
@pytest.mark.parametrize("text", ["- a\n- b\n", "just text\n", ""])
def test_non_mapping_yaml_raises_naming_file(tmp_path, loader, text):
    p = tmp_path / "odd.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="odd.yaml"):
        loader(p)


def test_loader_refuses_python_tags(tmp_path):
    p = tmp_path / "evil.yaml"
    p.write_text("database: !!python/object/apply:os.getcwd []\nversion: 1\nsteps: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="evil.yaml") as exc:
        load_steps(p)
    assert isinstance(exc.value.__cause__, yaml.YAMLError)


def test_malformed_yaml_names_file(tmp_path):
    p = tmp_path / "broken.yaml"
    p.write_text("database: [CAP\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken.yaml") as exc:
        load_steps(p)
    assert isinstance(exc.value.__cause__, yaml.YAMLError)


def test_bad_utf8_names_file(tmp_path):
    p = tmp_path / "latin.yaml"
    p.write_bytes(b"database: CAP\xff\n")
    with pytest.raises(ValueError, match="latin.yaml"):
        load_steps(p)


def test_schema_invalid_names_file(tmp_path):
    p = tmp_path / "schema.yaml"
    p.write_text(MAP_HEAD + "targets:\n  run_query_button: {backend: uia, window: Capitaline, control_type: null, auto_id: null, name: null}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema.yaml") as exc:
        load_screen_map(p)
    assert isinstance(exc.value.__cause__, ValidationError)


@pytest.mark.parametrize("loader", [load_steps, load_screen_map])
def test_file_over_256_kib_rejected(tmp_path, loader):
    p = tmp_path / "big.yaml"
    body = b"database: CAP\nversion: 1\nsteps: []\n"
    p.write_bytes(body + b"#" * (256 * 1024 + 1 - len(body)))
    with pytest.raises(ValueError, match=r"big\.yaml.*256 KiB"):
        loader(p)


def test_file_at_256_kib_is_read(tmp_path):
    p = tmp_path / "edge.yaml"
    body = b"database: CAP\nversion: 1\nsteps: []\n"
    p.write_bytes(body + b"#" * (256 * 1024 - len(body)))
    assert load_steps(p).steps == []


def test_duplicate_target_name_rejected(tmp_path):
    p = tmp_path / "map.yaml"
    p.write_text(MAP_HEAD + f"targets:\n  run_query_button: {LOC}\n  run_query_button: {LOC}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate key") as exc:
        load_screen_map(p)
    assert "map.yaml" in str(exc.value)


def test_duplicate_params_key_rejected(tmp_path):
    p = tmp_path / "steps.yaml"
    p.write_text(
        "database: CAP\nversion: 1\nsteps:\n"
        "  - {id: a, gate: G2, action: type, target: t, params: {value: \"x\", value: \"y\"}, sop_ref: x}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate key"):
        load_steps(p)


# Final review W2: recorded_at must be timezone-aware when given
def _smap(recorded_at):
    return ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=recorded_at, targets={})


def test_naive_recorded_at_rejected():
    with pytest.raises(ValidationError):
        _smap("2026-11-14T10:00:00")


def test_aware_or_null_recorded_at_accepted():
    assert _smap(None).recorded_at is None
    assert _smap("2026-11-14T10:00:00+05:30").recorded_at.utcoffset() is not None
