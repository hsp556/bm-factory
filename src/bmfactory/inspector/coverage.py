"""Screen-map coverage: for each map target, can it be found among the controls an inspector dump recorded?

Pure (no pywinauto), so it runs and is tested anywhere.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from bmfactory.contracts.stations import Locator, ScreenMap

TEXT_MAX = 120

_Str = Annotated[str, StringConstraints(max_length=TEXT_MAX)]
_Strict = ConfigDict(extra="forbid")


class ControlInfo(BaseModel):
    model_config = _Strict

    window: _Str
    control_type: _Str
    auto_id: _Str
    name: _Str
    class_name: _Str
    depth: Annotated[int, Field(ge=0)]


class TargetScore(BaseModel):
    model_config = _Strict

    target: str
    rating: Literal["green", "amber", "red"]
    matches: Annotated[int, Field(ge=0)]
    reason: str


# Control types whose labels are buttons, menus, tabs and similar chrome, never database content (ruling R11).
NAME_TYPES = frozenset({"Button", "SplitButton", "MenuItem", "Menu", "MenuBar", "Tab", "TabItem", "CheckBox",
                        "RadioButton", "ComboBox", "ToolBar", "TitleBar", "Group"})


def norm_name(s: str) -> str:
    return s.replace("&", "").strip().casefold()


def _code(s: str) -> str:
    return "`" + s.replace("`", "") + "`"


def _score(target: str, loc: Locator, controls: list[ControlInfo]) -> TargetScore:
    def score(rating, matches, reason):
        return TargetScore(target=target, rating=rating, matches=matches, reason=reason)

    auto_id = (loc.auto_id or "").strip()
    name = norm_name(loc.name or "")
    if not auto_id and not name:
        return score("red", 0, "path-only locator; the inspector cannot check paths")

    id_note = ""
    if auto_id:
        by_id = [c for c in controls if c.auto_id.strip() == auto_id]
        if len(by_id) == 1:
            return score("green", 1, "unique auto_id")
        if by_id:
            return score("amber", len(by_id), f"{len(by_id)} controls share this auto_id")
        id_note = "auto_id not found; "

    by_name = [c for c in controls if name and norm_name(c.name) == name]
    if not by_name:
        if loc.control_type not in NAME_TYPES:
            kind = _code(loc.control_type) if loc.control_type else "an unset type"
            return score("red", 0, id_note + f"no control matches; names of {kind} are only recorded when they equal "
                                              "the map label, so capture an auto_id from the raw dump")
        return score("red", 0, id_note + "no control matches")
    typed = [c for c in by_name if loc.control_type is not None and c.control_type.casefold() == loc.control_type.casefold()]
    if len(typed) == 1:
        if id_note:  # the map's auto_id is stale, so the bot's locator would fail: never green
            return score("amber", 1, id_note + "unique name+type")
        return score("green", 1, "unique name+type")
    if typed:
        return score("amber", len(typed), id_note + f"{len(typed)} controls match name+type; capture an auto_id")
    if loc.control_type is None:
        why = "control type unset in map"
    else:
        found = ", ".join(_code(t or "?") for t in sorted({c.control_type for c in by_name}))
        why = f"type {_code(loc.control_type)} expected, found {found}"
    return score("amber", len(by_name), id_note + f"{len(by_name)} matched on name only ({why})")


def score_targets(smap: ScreenMap, controls: list[ControlInfo]) -> list[TargetScore]:
    """Score every target whose window was dumped (case-insensitive substring of a dumped window title)."""
    windows = {c.window.casefold() for c in controls}
    scores = []
    for target, loc in sorted(smap.targets.items()):
        want = loc.window.casefold()
        if not any(want in w for w in windows):
            continue
        scores.append(_score(target, loc, [c for c in controls if want in c.window.casefold()]))
    return scores


def _cell(s: str) -> str:
    return s.replace("|", "\\|")


def render_report(scores: list[TargetScore], windows: list[str]) -> str:
    """Markdown section: the screen map's window names that were matched, a rating summary, then one row per
    target. Callers pass map window names, never live window titles; no control name ever reaches this text."""
    counts = {r: sum(s.rating == r for s in scores) for r in ("green", "amber", "red")}
    lines = [
        "### Screen-map coverage",
        "",
        "Windows: " + (", ".join(_cell(w) for w in windows) or "(none)"),
        "",
        "Summary: " + ", ".join(f"{r}: {n}" for r, n in counts.items()),
        "",
        "| target | rating | matches | reason |",
        "|---|---|---|---|",
    ]
    lines += [f"| {_cell(s.target)} | {s.rating} | {s.matches} | {_cell(s.reason)} |" for s in scores]
    return "\n".join(lines) + "\n"
