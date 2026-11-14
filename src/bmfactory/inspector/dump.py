"""Read the control tree of one live top-level window. Look only: this module reads four properties and the
child list of each element and calls nothing else on it.

Licence (ruling R11): the dump records UI structure, not database content. A control's name is recorded only
for chrome types (NAME_TYPES) or when it equals a label the screen map already names; every string is cleaned
and truncated. The raw dump still holds the live window title, so it is written to a git-ignored folder.
Safety (ruling R12): the title pattern must match one whole window title, and only one window.
"""

import re
import unicodedata

from bmfactory.inspector.coverage import NAME_TYPES, TEXT_MAX, ControlInfo, norm_name

MAX_CONTROLS = 5000  # per window
PATTERN_MAX = 100


def _clean(value: object) -> str:
    if value is None:
        return ""
    s = "".join(c for c in str(value) if not unicodedata.category(c).startswith("C"))
    return s[:TEXT_MAX]


def compile_title_pattern(title_regex: str) -> re.Pattern:
    """The operator's window-title regex; ValueError when longer than PATTERN_MAX or not a valid regex."""
    if len(title_regex) > PATTERN_MAX:
        raise ValueError(f"window pattern is longer than {PATTERN_MAX} characters")
    try:
        return re.compile(title_regex)
    except re.error as e:
        raise ValueError(f"invalid window pattern: {e}") from e


def top_level_windows() -> list:
    """Enumerate the desktop's top-level windows (no walk). Needs the station extra."""
    from pywinauto import Desktop  # station extra, installed on System 3 only

    return Desktop(backend="uia").windows()


def matching_windows(windows: list, pattern: re.Pattern) -> list:
    """The windows whose whole title matches `pattern`."""
    return [w for w in windows if pattern.fullmatch(w.window_text() or "")]


def walk(root, max_depth: int, keep_names: frozenset[str] = frozenset()) -> list[ControlInfo]:
    """Pre-order walk of `root` and its descendants down to `max_depth`, at most MAX_CONTROLS entries.

    `root` and its descendants need only `children()`, `window_text()` and `element_info.control_type`,
    `.automation_id` and `.class_name`; nothing else is touched. A name is kept only for NAME_TYPES or when it
    equals (normalised) one of `keep_names`; all other names are stored as "".
    """
    keep = frozenset(norm_name(k) for k in keep_names) - {""}
    window = _clean(root.window_text())
    out: list[ControlInfo] = []
    stack = [(root, 0)]
    while stack and len(out) < MAX_CONTROLS:
        el, depth = stack.pop()
        info = el.element_info
        ctype = _clean(info.control_type)
        text = _clean(el.window_text())
        name = text if ctype in NAME_TYPES or norm_name(text) in keep else ""
        out.append(ControlInfo(window=window, control_type=ctype, auto_id=_clean(info.automation_id), name=name,
                               class_name=_clean(info.class_name), depth=depth))
        if depth < max_depth:
            stack.extend((child, depth + 1) for child in reversed(el.children()))
    return out


def dump_window(title_regex: str, max_depth: int = 12, keep_names: frozenset[str] = frozenset()) -> list[ControlInfo]:
    """Controls of the one top-level window whose whole title matches `title_regex`.

    ValueError for a bad pattern, or when no window or more than one window matches.
    """
    found = matching_windows(top_level_windows(), compile_title_pattern(title_regex))
    if not found:
        raise ValueError("no window title fully matches the pattern")
    if len(found) > 1:
        raise ValueError(f"{len(found)} windows match the pattern; make it more specific")
    return walk(found[0], max_depth, keep_names)
