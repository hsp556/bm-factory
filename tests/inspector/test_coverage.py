from bmfactory.contracts.stations import Locator, ScreenMap
from bmfactory.inspector.coverage import ControlInfo, TargetScore, render_report, score_targets, unscored_targets


def ctl(name="", auto_id="", ctype="Button", window="TP Screener"):
    return ControlInfo(window=window, control_type=ctype, auto_id=auto_id, name=name, class_name="", depth=1)

def smap(**targets):
    return ScreenMap(database="CAP", version=1, verified=False, app_version_seen=None, recorded_at=None, targets=targets)

# Task 4's Locator has no field defaults (the YAML spells out nulls), so the helper supplies them.
_UNSET = {"control_type": None, "auto_id": None, "name": None}

def loc(window="TP Screener", **kw): return Locator(backend="uia", window=window, **{**_UNSET, **kw})

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
    other = loc(window="Save As", name="Save", control_type="Button")
    assert score_targets(smap(a=other), [ctl("Save")]) == []

def test_report_has_summary_and_rows():
    md = render_report([TargetScore(target="run", rating="green", matches=1, reason="unique name+type")], ["TP Screener"])
    assert "| run | green | 1 |" in md and "green: 1" in md and "TP Screener" in md


# Additional cases beyond the brief.

def test_duplicate_amber_reason_says_how_many_and_asks_for_auto_id():
    s = score_targets(smap(save=loc(name="Save", control_type="Button")), [ctl("Save"), ctl("Save"), ctl("Save")])
    assert (s[0].rating, s[0].matches) == ("amber", 3)
    assert "3" in s[0].reason and "auto_id" in s[0].reason

def test_name_only_locator_without_type_is_amber():
    s = score_targets(smap(x=loc(name="Save", control_type=None)), [ctl("Save")])
    assert (s[0].rating, s[0].matches) == ("amber", 1)

def test_duplicate_auto_id_is_amber():
    s = score_targets(smap(x=loc(name=None, auto_id="dup", control_type=None)), [ctl("A", "dup"), ctl("B", "dup")])
    assert (s[0].rating, s[0].matches) == ("amber", 2)

def test_auto_id_not_found_falls_back_to_name_but_never_green():
    s = score_targets(smap(x=loc(name="Save", auto_id="gone", control_type="Button")), [ctl("Save", "other")])
    assert (s[0].rating, s[0].matches) == ("amber", 1)
    assert "auto_id" in s[0].reason

def test_window_match_is_case_insensitive_substring_and_controls_from_other_windows_ignored():
    m = smap(run=loc(name="Run Query", control_type="Button"))
    s = score_targets(m, [ctl("Run Query", window="capitaline - tp screener"), ctl("Run Query", window="Other")])
    assert (s[0].rating, s[0].matches) == ("green", 1)

def test_results_sorted_by_target():
    m = smap(b=loc(name="B", control_type="Button"), a=loc(name="A", control_type="Button"))
    assert [t.target for t in score_targets(m, [ctl("A")])] == ["a", "b"]

def test_report_escapes_pipes_from_ui_text():
    md = render_report([TargetScore(target="run", rating="red", matches=0, reason="a|b")], ["Win | 2"])
    assert "a\\|b" in md and "Win \\| 2" in md

def test_report_wraps_control_types_in_code_spans_without_backticks():
    s = score_targets(smap(dom=loc(name="Domain", control_type="TabItem")), [ctl("Domain", ctype="Pa`ne")])
    assert "`TabItem`" in s[0].reason and "`Pane`" in s[0].reason

def test_red_for_type_whose_names_are_not_recorded_points_to_auto_id():
    s = score_targets(smap(x=loc(name="Year/Date/Range", control_type="Edit")), [ctl("", ctype="Edit")])
    assert (s[0].rating, s[0].matches) == ("red", 0)
    assert "only recorded when they equal the map label" in s[0].reason and "auto_id" in s[0].reason and "raw dump" in s[0].reason

def test_path_only_locator_is_red_with_reason():
    s = score_targets(smap(x=loc(path=["a", "b"])), [ctl("a")])
    assert (s[0].rating, s[0].matches) == ("red", 0) and "path-only" in s[0].reason

def test_empty_name_or_auto_id_never_matches():
    blank = [ctl(""), ctl("", " ")]
    assert score_targets(smap(x=loc(name="&", control_type="Button")), blank)[0].rating == "red"
    assert score_targets(smap(x=loc(auto_id=" ", control_type="Button")), blank)[0].rating == "red"


# Final review W5: targets whose window was not dumped are listed, not silently omitted.

def test_unscored_targets_lists_map_targets_whose_window_was_not_dumped():
    m = smap(b=loc(window="Save As", name="Save"), a=loc(window="Capitaline", name="X"), run=loc(name="Run Query"))
    assert unscored_targets(m, [ctl("Run Query")]) == ["a", "b"]
    assert unscored_targets(m, [ctl("x", window="Save As"), ctl("y", window="Capitaline"), ctl("z")]) == []

def test_report_lists_unscored_targets_or_none():
    scores = [TargetScore(target="run", rating="green", matches=1, reason="unique name+type")]
    assert "Not scored (window not dumped): a, b\n" in render_report(scores, ["TP Screener"], ["a", "b"])
    assert "Not scored (window not dumped): none\n" in render_report(scores, ["TP Screener"], [])
    assert "Not scored" not in render_report(scores, ["TP Screener"])
