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

STEPS_YAML = Path("stations/capitaline/steps.yaml")
MAP_YAML = Path("stations/capitaline/screen-map.yaml")


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


def test_seed_gates_and_order():
    steps = load_steps(STEPS_YAML).steps
    assert len(steps) == 17
    assert [s.gate for s in steps] == ["G2"] * 12 + ["G3"] * 5
    assert steps[12].id == "run_query" and steps[-1].id == "confirm_save"


def test_seed_quoted_param_values():
    steps = {s.id: s for s in load_steps(STEPS_YAML).steps}
    assert steps["ensure_listed_only_off"].params == {"value": "off"}
    assert steps["set_portfolio_non_aggregate"].params == {"value": "Non Aggregate"}


def test_seed_save_path_keeps_backslashes():
    steps = {s.id: s for s in load_steps(STEPS_YAML).steps}
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
    with pytest.raises(ValidationError):
        load_steps(p)


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
    with pytest.raises(yaml.YAMLError):
        load_steps(p)
