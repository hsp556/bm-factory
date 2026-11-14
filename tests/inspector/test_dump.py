import re
from pathlib import Path

import pytest

from bmfactory.inspector.dump import MAX_CONTROLS, walk

_ALLOWED_INFO = {"control_type", "automation_id", "class_name"}


class _Info:
    def __init__(self, control_type, automation_id, class_name):
        self.__dict__["_d"] = {"control_type": control_type, "automation_id": automation_id, "class_name": class_name}

    def __getattr__(self, name):
        if name in _ALLOWED_INFO:
            return self.__dict__["_d"][name]
        raise AssertionError(f"inspector touched element_info.{name}")

    def __setattr__(self, name, value):
        raise AssertionError(f"inspector set element_info.{name}")


class Fake:
    """Element exposing only the read-only surface; touching anything else (click, set_focus, ...) fails the test."""

    def __init__(self, text="", ctype="Button", auto_id="", cls="", kids=()):
        self.__dict__["_text"] = text
        self.__dict__["_kids"] = list(kids)
        self.__dict__["_info"] = _Info(ctype, auto_id, cls)

    def __getattr__(self, name):
        d = self.__dict__
        if name == "children":
            return lambda: d["_kids"]
        if name == "window_text":
            return lambda: d["_text"]
        if name == "element_info":
            return d["_info"]
        raise AssertionError(f"inspector touched {name}")

    def __setattr__(self, name, value):
        raise AssertionError(f"inspector set {name}")


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
        ("TP Screener", "Window", "w1", "TP Screener", "WinCls", 0),
        ("TP Screener", "Button", "btnRun", "Run Query", "Btn", 1),
    ]


def test_walk_stops_at_max_depth():
    out = walk(chain(10), max_depth=3)
    assert max(c.depth for c in out) == 3 and len(out) == 4


def test_walk_caps_at_max_controls():
    root = Fake("W", "Window", kids=[Fake(f"b{i}") for i in range(MAX_CONTROLS + 50)])
    assert MAX_CONTROLS == 5000
    assert len(walk(root, max_depth=12)) == MAX_CONTROLS


@pytest.mark.parametrize("ctype", ["DataItem", "Edit", "Document"])
def test_content_bearing_controls_have_name_blanked(ctype):
    root = Fake("W", "Window", kids=[Fake("ACME LTD 123.45", ctype, "cell1")])
    c = walk(root, max_depth=12)[1]
    assert (c.name, c.auto_id, c.control_type) == ("", "cell1", ctype)


def test_text_is_truncated_and_control_chars_stripped():
    long = "A" * 200
    root = Fake("W", "Window", kids=[Fake("Run\x00\x1b[31m​Query\n", "Button", long, long)])
    c = walk(root, max_depth=12)[1]
    assert c.name == "Run[31mQuery"
    assert c.auto_id == "A" * 120 and c.class_name == "A" * 120


def test_none_attributes_become_empty_strings():
    c = walk(Fake(None, None, None, None), max_depth=12)[0]
    assert (c.window, c.control_type, c.auto_id, c.name, c.class_name) == ("", "", "", "", "")


def test_inspector_source_has_no_state_changing_calls():
    src_dir = Path(__file__).resolve().parents[2] / "src/bmfactory/inspector"
    banned = ["click", "type_keys", "set_focus", "set_text", "set_edit_text", "select(", "invoke",
              "send_keys", "SendKeys", "mouse", "keyboard"]
    files = sorted(src_dir.glob("*.py"))
    assert files
    for f in files:
        text = f.read_text(encoding="utf-8")
        hits = [b for b in banned if b in text]
        assert hits == [], f"{f.name} contains {hits}"


def test_only_dump_module_imports_pywinauto():
    src = Path(__file__).resolve().parents[2] / "src/bmfactory"
    pattern = re.compile(r"^\s*(import|from)\s+pywinauto", re.M)
    offenders = [f.name for f in src.rglob("*.py") if pattern.search(f.read_text(encoding="utf-8"))]
    assert offenders == ["dump.py"]
