"""Read the control tree of live top-level windows. Look only: this module reads four properties and the
child list of each element and calls nothing else on it.

Licence: the dump records UI structure, not database content. Names of content-bearing controls are never
recorded, and every string is cleaned and truncated.
"""

import re
import unicodedata

from bmfactory.inspector.coverage import TEXT_MAX, ControlInfo

MAX_CONTROLS = 5000  # per window
_BLANK_NAME_TYPES = frozenset({"DataItem", "Edit", "Document"})  # their text is cell or field content


def _clean(value: object) -> str:
    if value is None:
        return ""
    s = "".join(c for c in str(value) if not unicodedata.category(c).startswith("C"))
    return s[:TEXT_MAX]


def walk(root, max_depth: int) -> list[ControlInfo]:
    """Pre-order walk of `root` and its descendants down to `max_depth`, at most MAX_CONTROLS entries.

    `root` and its descendants need only `children()`, `window_text()` and `element_info.control_type`,
    `.automation_id` and `.class_name`; nothing else is touched.
    """
    window = _clean(root.window_text())
    out: list[ControlInfo] = []
    stack = [(root, 0)]
    while stack and len(out) < MAX_CONTROLS:
        el, depth = stack.pop()
        info = el.element_info
        ctype = _clean(info.control_type)
        name = "" if ctype in _BLANK_NAME_TYPES else _clean(el.window_text())
        out.append(ControlInfo(window=window, control_type=ctype, auto_id=_clean(info.automation_id), name=name,
                               class_name=_clean(info.class_name), depth=depth))
        if depth < max_depth:
            stack.extend((child, depth + 1) for child in reversed(el.children()))
    return out


def dump_window(title_regex: str, max_depth: int = 12) -> list[ControlInfo]:
    """Controls of every top-level window whose title matches `title_regex` (re.search); [] when none match."""
    from pywinauto import Desktop  # station extra, installed on System 3 only

    pattern = re.compile(title_regex)
    controls: list[ControlInfo] = []
    for win in Desktop(backend="uia").windows():
        if pattern.search(win.window_text() or ""):
            controls += walk(win, max_depth)
    return controls
