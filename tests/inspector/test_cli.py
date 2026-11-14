import json
import re
from datetime import datetime
from pathlib import Path

from bmfactory.contracts.stations import load_screen_map
from bmfactory.inspector.__main__ import main
from bmfactory.inspector.dump import MAX_CONTROLS, walk
from fakes import Fake

ROOT = Path(__file__).resolve().parents[2]
MAP = str(ROOT / "stations/capitaline/screen-map.yaml")
NOW = datetime(2026, 11, 14, 10, 30, 0)
LIVE_TITLE = "TP Screener - ACME Ltd"


def screener():
    return Fake(LIVE_TITLE, "Window", "", "WinCls", kids=[
        Fake("Run Query", "Button"), Fake("Save", "Button"), Fake("Save", "Button"), Fake("ACME Ltd", "Button"),
        Fake("ACME Ltd 123.45", "DataItem"),
    ])


class Spy:
    def __init__(self, wins=None, answer=False):
        self.wins = [screener()] if wins is None else wins
        self.answer = answer
        self.walked = []
        self.prompts = []

    def windows(self):
        return self.wins

    def confirm(self, prompt):
        self.prompts.append(prompt)
        return self.answer

    def walk(self, root, max_depth, keep_names):
        self.walked.append(keep_names)
        return walk(root, max_depth, keep_names)


def run(tmp_path, spy, *extra, window="TP Screener.*", now=NOW):
    argv = ["--window", window, "--map", MAP, "--out", str(tmp_path / "out"), *extra]
    return main(argv, windows=spy.windows, confirm=spy.confirm, walk=spy.walk, now=lambda: now)


def files(tmp_path):
    out = tmp_path / "out"
    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()) if out.exists() else []


def test_no_window_matches_exits_1(tmp_path, capsys):
    assert run(tmp_path, Spy(), "--yes", window="Nope") == 1
    assert "no window" in capsys.readouterr().err.lower()
    assert files(tmp_path) == []


def test_partial_title_does_not_match(tmp_path):
    spy = Spy()
    assert run(tmp_path, spy, "--yes", window="TP Screener") == 1
    assert spy.walked == [] and files(tmp_path) == []


def test_two_matching_windows_exit_1_and_write_nothing(tmp_path, capsys):
    spy = Spy(wins=[screener(), screener()])
    assert run(tmp_path, spy, "--yes") == 1
    err = capsys.readouterr().err
    assert "2 windows" in err and "more specific" in err
    assert spy.walked == [] and files(tmp_path) == []


def test_invalid_regex_exits_1_without_enumerating(tmp_path, capsys):
    spy = Spy(wins=None)
    spy.windows = lambda: (_ for _ in ()).throw(AssertionError("enumerated"))
    assert run(tmp_path, spy, "--yes", window="TP (Screener") == 1
    assert "invalid --window" in capsys.readouterr().err.lower()


def test_over_long_pattern_exits_1(tmp_path, capsys):
    assert run(tmp_path, Spy(), "--yes", window="T" * 101) == 1
    assert "100" in capsys.readouterr().err


def test_bad_map_exits_1(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not a mapping\n", encoding="utf-8")
    rc = main(["--window", "x", "--map", str(bad), "--out", str(tmp_path / "out"), "--yes"], windows=list)
    assert rc == 1 and "bad.yaml" in capsys.readouterr().err


def test_declined_confirmation_exits_1_without_walking(tmp_path, capsys):
    spy = Spy(answer=False)
    assert run(tmp_path, spy) == 1
    assert len(spy.prompts) == 1 and spy.walked == [] and files(tmp_path) == []
    err = capsys.readouterr().err
    assert LIVE_TITLE in err and "WinCls" in err  # shown to the operator on the terminal before walking


def test_interactive_yes_proceeds(tmp_path):
    spy = Spy(answer=True)
    assert run(tmp_path, spy) == 0 and len(spy.prompts) == 1 and len(spy.walked) == 1


def test_yes_flag_skips_the_prompt(tmp_path):
    spy = Spy(answer=False)
    assert run(tmp_path, spy, "--yes") == 0 and spy.prompts == [] and len(spy.walked) == 1


def test_successful_run_writes_raw_dump_and_a_report_without_ui_text(tmp_path):
    spy = Spy()
    assert run(tmp_path, spy, "--yes") == 0

    smap = load_screen_map(Path(MAP))
    assert spy.walked == [frozenset(l.name for l in smap.targets.values() if l.name)]

    assert files(tmp_path) == ["capitaline-feasibility.md", "raw/.gitignore", "raw/controls-tp-screener-20261114-103000.json"]
    data = json.loads((tmp_path / "out/raw/controls-tp-screener-20261114-103000.json").read_text(encoding="utf-8"))
    assert len(data) == 6 and data[1]["name"] == "Run Query" and data[5]["name"] == ""

    md = (tmp_path / "out/capitaline-feasibility.md").read_text(encoding="utf-8")
    assert "| run_query_button | green | 1 |" in md
    assert "| screener_save_button | amber | 2 |" in md
    assert "| tp_screener_button |" not in md  # a Capitaline-window target; that window was not dumped
    unscored = sorted(t for t, l in smap.targets.items() if l.window.casefold() not in LIVE_TITLE.casefold())
    assert "tp_screener_button" in unscored and "run_query_button" not in unscored
    assert f"Not scored (window not dumped): {', '.join(unscored)}\n" in md
    assert "Windows: TP Screener" in md
    assert "ACME" not in md and LIVE_TITLE not in md


def test_second_run_appends_and_same_second_run_never_overwrites(tmp_path, capsys):
    assert run(tmp_path, Spy(), "--yes") == 0
    raw = tmp_path / "out/raw/controls-tp-screener-20261114-103000.json"
    first_raw = raw.read_text(encoding="utf-8")
    md_path = tmp_path / "out/capitaline-feasibility.md"
    md = md_path.read_text(encoding="utf-8")

    assert run(tmp_path, Spy(), "--yes") == 1  # same timestamp
    assert "exists" in capsys.readouterr().err
    assert raw.read_text(encoding="utf-8") == first_raw and md_path.read_text(encoding="utf-8") == md

    assert run(tmp_path, Spy(), "--yes", now=datetime(2026, 11, 14, 10, 31, 0)) == 0
    md2 = md_path.read_text(encoding="utf-8")
    assert md2.startswith(md) and md2.count("| run_query_button |") == 2


def test_cap_hit_is_reported(tmp_path):
    big = Fake(LIVE_TITLE, "Window", kids=[Fake("", "Pane") for _ in range(MAX_CONTROLS + 5)])
    assert run(tmp_path, Spy(wins=[big]), "--yes") == 0
    md = (tmp_path / "out/capitaline-feasibility.md").read_text(encoding="utf-8")
    assert str(MAX_CONTROLS) in md and "incomplete" in md and LIVE_TITLE not in md


def test_missing_pywinauto_prints_install_hint(tmp_path, capsys):
    def no_pywinauto():
        raise ImportError("No module named 'pywinauto'")

    assert main(["--window", "x", "--map", MAP, "--out", str(tmp_path / "out"), "--yes"], windows=no_pywinauto) == 1
    assert 'pip install -e ".[station]"' in capsys.readouterr().err


def test_walk_failure_exits_1_and_writes_nothing(tmp_path, capsys):
    spy = Spy()

    def broken(root, max_depth, keep_names):
        raise RuntimeError("element vanished")

    spy.walk = broken
    assert run(tmp_path, spy, "--yes") == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "element vanished" in err
    assert files(tmp_path) == []


def test_enumeration_failure_exits_1(tmp_path, capsys):
    def broken():
        raise OSError("COM failure")

    assert main(["--window", "x", "--map", MAP, "--out", str(tmp_path / "out"), "--yes"], windows=broken) == 1
    assert "OSError" in capsys.readouterr().err and files(tmp_path) == []


def test_raw_dumps_are_git_ignored():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "docs/discovery/raw/" in lines


# Final review W6: raw dumps are git-ignored wherever --out points
def test_raw_folder_gets_a_gitignore(tmp_path):
    assert run(tmp_path, Spy(), "--yes") == 0
    assert (tmp_path / "out/raw/.gitignore").read_text(encoding="utf-8") == "*\n"


def test_existing_raw_gitignore_is_kept(tmp_path):
    raw = tmp_path / "out/raw"
    raw.mkdir(parents=True)
    (raw / ".gitignore").write_text("custom\n", encoding="utf-8")
    assert run(tmp_path, Spy(), "--yes") == 0
    assert (raw / ".gitignore").read_text(encoding="utf-8") == "custom\n"
