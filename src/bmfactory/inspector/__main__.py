"""python -m bmfactory.inspector --window <title-regex> --map stations/capitaline/screen-map.yaml --out docs/discovery

Writes the raw dump to <out>/controls-<slug>-<YYYYMMDD-HHMMSS>.json and appends a coverage section to
<out>/capitaline-feasibility.md. Exit 1 on an invalid regex, an unreadable map, or no matching window.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from bmfactory.contracts.stations import load_screen_map
from bmfactory.inspector.coverage import render_report, score_targets
from bmfactory.inspector.dump import MAX_CONTROLS, dump_window

_REPORT = "capitaline-feasibility.md"


def _slug(regex: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", regex.lower()).strip("-")[:40].strip("-") or "window"


def main(argv: list[str] | None = None, dump=dump_window) -> int:
    p = argparse.ArgumentParser(prog="python -m bmfactory.inspector", description="Read-only UI inspector")
    p.add_argument("--window", required=True, help="regex matched against top-level window titles")
    p.add_argument("--map", required=True, type=Path, help="screen-map YAML")
    p.add_argument("--out", required=True, type=Path, help="output directory (created if missing)")
    args = p.parse_args(argv)

    try:
        re.compile(args.window)
    except re.error as e:
        print(f"error: invalid --window regex {args.window!r}: {e}", file=sys.stderr)
        return 1
    try:
        smap = load_screen_map(args.map)
    except (OSError, ValueError) as e:
        print(f"error: cannot load screen map: {e}", file=sys.stderr)
        return 1

    controls = dump(args.window)
    if not controls:
        print(f"error: no window title matches {args.window!r}; is the screen open?", file=sys.stderr)
        return 1

    stamp = datetime.now()
    args.out.mkdir(parents=True, exist_ok=True)
    dump_file = args.out / f"controls-{_slug(args.window)}-{stamp:%Y%m%d-%H%M%S}.json"
    dump_file.write_text(json.dumps([c.model_dump() for c in controls], indent=1, ensure_ascii=False), encoding="utf-8")

    per_window = Counter(c.window for c in controls)
    windows = sorted(per_window)
    section = [f"## Inspector run {stamp:%Y-%m-%d %H:%M:%S}", "", f"Dump: `{dump_file.name}` ({len(controls)} controls)", ""]
    section += [f"WARNING: window {w!r} reached the {MAX_CONTROLS}-control cap; its dump is incomplete.\n"
                for w in windows if per_window[w] >= MAX_CONTROLS]
    section.append(render_report(score_targets(smap, controls), windows))
    with (args.out / _REPORT).open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")

    print(f"wrote {dump_file} and appended to {args.out / _REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
