"""python -m bmfactory.inspector --window <title-regex> --map stations/capitaline/screen-map.yaml --out docs/discovery

The regex must match one whole window title, and only one window. The operator confirms that window (or passes
--yes) before it is walked. Writes the raw dump to <out>/raw/controls-<slug>-<YYYYMMDD-HHMMSS>.json (git-ignored:
it holds the live window title) and appends a coverage section, free of UI text, to <out>/capitaline-feasibility.md.
Exit 1 on a bad pattern or map, zero or several matching windows, a declined confirmation, or any failure.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bmfactory.contracts.stations import load_screen_map
from bmfactory.inspector.coverage import render_report, score_targets
from bmfactory.inspector.dump import MAX_CONTROLS, compile_title_pattern, matching_windows, top_level_windows, walk

_REPORT = "capitaline-feasibility.md"
_MAX_DEPTH = 12


def _slug(regex: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", regex.lower()).strip("-")[:40].strip("-") or "window"


def _ask(prompt: str) -> bool:
    print(prompt, end="", file=sys.stderr, flush=True)
    try:
        return input().strip().lower() == "y"
    except EOFError:
        return False


def _fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None, windows=top_level_windows, confirm=_ask, walk=walk, now=datetime.now) -> int:
    p = argparse.ArgumentParser(prog="python -m bmfactory.inspector", description="Read-only UI inspector")
    p.add_argument("--window", required=True, help="regex that must match one whole top-level window title")
    p.add_argument("--map", required=True, type=Path, help="screen-map YAML")
    p.add_argument("--out", required=True, type=Path, help="output directory (created if missing)")
    p.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = p.parse_args(argv)

    try:
        pattern = compile_title_pattern(args.window)
    except ValueError as e:
        return _fail(f"invalid --window: {e}")
    try:
        smap = load_screen_map(args.map)
    except (OSError, ValueError) as e:
        return _fail(f"cannot load screen map: {e}")
    keep_names = frozenset(loc.name for loc in smap.targets.values() if loc.name)

    try:
        found = matching_windows(windows(), pattern)
    except ImportError as e:
        return _fail(f'{e}; install the station extra on System 3: pip install -e ".[station]"')
    except Exception as e:  # noqa: BLE001 — any UI Automation failure ends the run visibly
        return _fail(f"listing windows failed: {type(e).__name__}: {e}")
    if not found:
        return _fail(f"no window title fully matches {args.window!r}; is the screen open?")
    if len(found) > 1:
        for w in found:  # terminal only, never written to a file
            print(f"  matched: {w.window_text()!r}", file=sys.stderr)
        return _fail(f"{len(found)} windows match {args.window!r}; make the pattern more specific")

    win = found[0]
    try:
        print(f"window: {win.window_text()!r}  class: {win.element_info.class_name!r}", file=sys.stderr)
        if not (args.yes or confirm("Inspect this window (read-only)? [y/N] ")):
            return _fail("not confirmed; nothing was inspected")
        controls = walk(win, _MAX_DEPTH, keep_names)
    except Exception as e:  # noqa: BLE001
        return _fail(f"inspecting the window failed: {type(e).__name__}: {e}")

    stamp = now()
    raw_dir = args.out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dump_file = raw_dir / f"controls-{_slug(args.window)}-{stamp:%Y%m%d-%H%M%S}.json"
    try:
        with dump_file.open("x", encoding="utf-8") as f:
            f.write(json.dumps([c.model_dump() for c in controls], indent=1, ensure_ascii=False))
    except FileExistsError:
        return _fail(f"{dump_file} already exists; wait a second and run again")

    scores = score_targets(smap, controls)
    map_windows = sorted({smap.targets[s.target].window for s in scores})
    section = [f"## Inspector run {stamp:%Y-%m-%d %H:%M:%S}", "", f"Dump: `raw/{dump_file.name}` ({len(controls)} controls)", ""]
    if len(controls) >= MAX_CONTROLS:
        section.append(f"WARNING: the walk reached the {MAX_CONTROLS}-control cap; the dump is incomplete.\n")
    section.append(render_report(scores, map_windows))
    with (args.out / _REPORT).open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")

    print(f"wrote {dump_file} and appended to {args.out / _REPORT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
