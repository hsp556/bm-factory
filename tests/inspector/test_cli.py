import json
import re
from pathlib import Path

from bmfactory.inspector.__main__ import main
from bmfactory.inspector.coverage import ControlInfo
from bmfactory.inspector.dump import MAX_CONTROLS

MAP = str(Path(__file__).resolve().parents[2] / "stations/capitaline/screen-map.yaml")


def fake_dump(controls):
    calls = []

    def dump(title_regex):
        calls.append(title_regex)
        return controls

    dump.calls = calls
    return dump


def c(name, ctype="Button", depth=1):
    return ControlInfo(window="TP Screener", control_type=ctype, auto_id="", name=name, class_name="", depth=depth)


def test_no_window_matches_exits_1(tmp_path, capsys):
    out = tmp_path / "out"
    rc = main(["--window", "Nope", "--map", MAP, "--out", str(out)], dump=fake_dump([]))
    assert rc == 1
    assert "no window" in capsys.readouterr().err.lower()
    assert not out.exists() or not any(out.iterdir())


def test_invalid_regex_exits_1_without_dumping(tmp_path, capsys):
    dump = fake_dump([])
    rc = main(["--window", "TP (Screener", "--map", MAP, "--out", str(tmp_path)], dump=dump)
    assert rc == 1 and dump.calls == []
    assert "invalid --window" in capsys.readouterr().err.lower()


def test_bad_map_exits_1(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not a mapping\n", encoding="utf-8")
    rc = main(["--window", "TP", "--map", str(bad), "--out", str(tmp_path)], dump=fake_dump([]))
    assert rc == 1 and "bad.yaml" in capsys.readouterr().err


def test_successful_run_writes_dump_and_appends_report(tmp_path):
    controls = [c("TP Screener", "Window", 0), c("Run Query"), c("Save"), c("Save")]
    out = tmp_path / "new" / "discovery"
    dump = fake_dump(controls)
    rc = main(["--window", "TP Screener.*", "--map", MAP, "--out", str(out)], dump=dump)
    assert rc == 0 and dump.calls == ["TP Screener.*"]

    dumps = list(out.glob("controls-*.json"))
    assert len(dumps) == 1
    assert re.fullmatch(r"controls-tp-screener-\d{8}-\d{6}\.json", dumps[0].name)
    data = json.loads(dumps[0].read_text(encoding="utf-8"))
    assert len(data) == 4 and data[1]["name"] == "Run Query"

    md = (out / "capitaline-feasibility.md").read_text(encoding="utf-8")
    assert "| run_query_button | green | 1 |" in md
    assert "| screener_save_button | amber | 2 |" in md
    assert "tp_screener_button" not in md  # a Capitaline-window target; that window was not dumped

    main(["--window", "TP Screener.*", "--map", MAP, "--out", str(out)], dump=dump)
    md2 = (out / "capitaline-feasibility.md").read_text(encoding="utf-8")
    assert md2.startswith(md) and md2.count("| run_query_button |") == 2


def test_cap_hit_is_reported(tmp_path):
    controls = [c("", "Pane")] * MAX_CONTROLS
    assert main(["--window", "TP", "--map", MAP, "--out", str(tmp_path)], dump=fake_dump(controls)) == 0
    md = (tmp_path / "capitaline-feasibility.md").read_text(encoding="utf-8")
    assert str(MAX_CONTROLS) in md and "incomplete" in md
