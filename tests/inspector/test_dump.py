import ast
import re
from pathlib import Path

import pytest

from bmfactory.inspector import dump as dump_mod
from bmfactory.inspector.dump import MAX_CONTROLS, compile_title_pattern, dump_window, matching_windows, walk
from fakes import Fake

SRC = Path(__file__).resolve().parents[2] / "src/bmfactory/inspector"


def chain(depth):
    node = Fake("leaf")
    for i in range(depth):
        node = Fake(f"n{i}", kids=[node])
    return node


def test_fake_rejects_state_changing_calls():
    for name in ("click", "click_input", "set_focus", "type_keys", "set_text", "select", "invoke"):
        with pytest.raises(AssertionError):
            getattr(Fake(), name)


def test_walk_records_root_and_children_with_depth():
    root = Fake("TP Screener", "Window", "w1", "WinCls", kids=[Fake("Run Query", "Button", "btnRun", "Btn")])
    out = walk(root, max_depth=12)
    assert [(c.window, c.control_type, c.auto_id, c.name, c.class_name, c.depth) for c in out] == [
        ("TP Screener", "Window", "w1", "", "WinCls", 0),
        ("TP Screener", "Button", "btnRun", "Run Query", "Btn", 1),
    ]


def test_walk_stops_at_max_depth():
    out = walk(chain(10), max_depth=3)
    assert max(c.depth for c in out) == 3 and len(out) == 4


def test_walk_caps_at_max_controls():
    root = Fake("W", "Window", kids=[Fake(f"b{i}") for i in range(MAX_CONTROLS + 50)])
    assert MAX_CONTROLS == 5000
    assert len(walk(root, max_depth=12)) == MAX_CONTROLS


@pytest.mark.parametrize("ctype", ["Text", "ListItem", "TreeItem", "DataItem", "Edit", "Custom", "Pane", "Document", None])
def test_names_outside_the_allowlist_are_blanked(ctype):
    root = Fake("W", "Window", kids=[Fake("ACME LTD 123.45", ctype, "cell1")])
    c = walk(root, max_depth=12)[1]
    assert (c.name, c.auto_id) == ("", "cell1")


@pytest.mark.parametrize("ctype", ["Button", "SplitButton", "MenuItem", "Menu", "MenuBar", "Tab", "TabItem", "CheckBox",
                                   "RadioButton", "ComboBox", "ToolBar", "TitleBar", "Group"])
def test_allowlisted_types_keep_their_name(ctype):
    c = walk(Fake("W", "Window", kids=[Fake("Run Query", ctype)]), max_depth=12)[1]
    assert c.name == "Run Query"


def test_name_equal_to_a_keep_name_is_kept_after_normalising():
    root = Fake("W", "Window", kids=[Fake(" &file name: ", "Edit"), Fake("secret", "Edit")])
    out = walk(root, max_depth=12, keep_names=frozenset({"File name:"}))
    assert [c.name for c in out[1:]] == [" &file name: ", ""]


def test_text_is_truncated_and_control_chars_stripped():
    long = "A" * 200
    root = Fake("W", "Window", kids=[Fake("Run\x00\x1b[31m​Query\n", "Button", long, long)])
    c = walk(root, max_depth=12)[1]
    assert c.name == "Run[31mQuery"
    assert c.auto_id == "A" * 120 and c.class_name == "A" * 120


def test_none_attributes_become_empty_strings():
    c = walk(Fake(None, None, None, None), max_depth=12)[0]
    assert (c.window, c.control_type, c.auto_id, c.name, c.class_name) == ("", "", "", "", "")


def test_window_title_must_match_in_full():
    wins = [Fake("Capitaline login - Browser", "Window"), Fake("Capitaline", "Window"), Fake(None, "Window")]
    assert [w.window_text() for w in matching_windows(wins, compile_title_pattern("Capitaline"))] == ["Capitaline"]
    assert matching_windows(wins, compile_title_pattern("Capitaline log")) == []


def test_pattern_too_long_or_invalid_is_rejected():
    compile_title_pattern("A" * 100)
    with pytest.raises(ValueError, match="100"):
        compile_title_pattern("A" * 101)
    with pytest.raises(ValueError, match="invalid"):
        compile_title_pattern("TP (Screener")


def test_dump_window_requires_exactly_one_match(monkeypatch):
    wins = [Fake("TP Screener", "Window", kids=[Fake(" &file name: ", "Edit")]), Fake("TP Screener", "Window"), Fake("Other", "Window")]
    monkeypatch.setattr(dump_mod, "top_level_windows", lambda: wins)
    with pytest.raises(ValueError, match="no window"):
        dump_window("Nope")
    with pytest.raises(ValueError, match="2 windows"):
        dump_window("TP Screener")
    monkeypatch.setattr(dump_mod, "top_level_windows", lambda: wins[:1] + wins[2:])
    out = dump_window("TP Screener", keep_names=frozenset({"File name:"}))
    assert [c.name for c in out] == ["", " &file name: "]


# Read-only guarantee, checked on the syntax tree of every inspector module.

_ATTR_ALLOWED = {
    # the read-only element surface (pywinauto Desktop.windows(), element children/text/element_info)
    "windows", "children", "window_text", "element_info", "control_type", "automation_id", "class_name",
    # stdlib: str, list, re, unicodedata, json, argparse, pathlib, sys, datetime
    "casefold", "join", "lower", "replace", "startswith", "strip", "append", "extend", "pop", "items", "values",
    "Pattern", "compile", "error", "fullmatch", "sub", "category", "dumps", "ArgumentParser", "add_argument",
    "parse_args", "mkdir", "open", "write", "stderr", "exit", "now", "__name__",
    # own models and parsed arguments
    "model_dump", "targets", "window", "name", "auto_id", "target", "rating", "matches", "reason", "map", "out", "yes",
}
_CALLS_ALLOWED_IN_DUMP = {
    "frozenset", "str", "len", "reversed", "ControlInfo", "Desktop", "ValueError", "list", "norm_name", "_clean",
    "walk", "matching_windows", "compile_title_pattern", "top_level_windows",
}
_FORBIDDEN = {"getattr", "setattr", "delattr", "eval", "exec", "__import__", "subprocess", "system", "ctypes"}


def _trees():
    files = sorted(SRC.glob("*.py"))
    assert files
    return {f.name: ast.parse(f.read_text(encoding="utf-8")) for f in files}


def test_only_allowlisted_attributes_are_accessed():
    used = {n.attr for tree in _trees().values() for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert used - _ATTR_ALLOWED == set()


def test_dump_calls_only_allowlisted_names():
    tree = _trees()["dump.py"]
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            called.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "?"))
    assert called - _CALLS_ALLOWED_IN_DUMP - _ATTR_ALLOWED == set()


def test_no_dynamic_or_process_calls_in_inspector():
    for name, tree in _trees().items():
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        imports |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert (names | attrs | imports) & _FORBIDDEN == set(), name
        assert "os.system" not in (SRC / name).read_text(encoding="utf-8")


def test_only_dump_module_imports_pywinauto():
    pattern = re.compile(r"^\s*(import|from)\s+pywinauto", re.M)
    src = SRC.parent
    offenders = [f.name for f in src.rglob("*.py") if pattern.search(f.read_text(encoding="utf-8"))]
    assert offenders == ["dump.py"]
