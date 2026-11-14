"""The machine-readable list of what a run produced, loaded from JSON (untrusted).

Every file path is relative to the run folder `BM Backup/<DB>/<RunID>/` and must start with one of RUN_FOLDERS.
"""

import re
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from bmfactory.contracts.command import Command, _echo, _printable, _Text
from bmfactory.contracts.ids import check_run_id_matches, parse_run_id

RUN_FOLDERS: tuple[str, ...] = (
    "00-Command",
    "01-Search-Strategy",
    "02-Raw-Dumps",
    "03-Financials",
    "04-Screens-Evidence",
    "05-Annual-Reports",
    "06-Workings",
    "07-Annexures",
    "99-Logs",
)

_PATH_MAX = 400
_URL_MAX = 2000
_SQL_MAX = 20000
_BAD_CHARS = set('<>:"|?*')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
    *(f"{dev}{n}" for dev in ("COM", "LPT") for n in (*"123456789", "¹", "²", "³")),
}
_DRIVE_RE = re.compile(r"[A-Za-z]:")
# re.ASCII matters: without it IGNORECASE lets e.g. U+017F (long s) match "s".
_SHAREPOINT_HOST_RE = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+sharepoint\.com", re.ASCII | re.IGNORECASE)
_RAW_DUMPS = "02-Raw-Dumps"
_COUNTS_JSON = f"{_RAW_DUMPS}/counts.json"


def safe_segments(p: str) -> list[str]:
    """Split a relative folder/file path into checked segments (backslashes count as separators).

    Rejects empty or over-long paths, control/format characters, a leading separator, '.', '..' or empty
    segments, the characters <>:"|?* (which also blocks drive letters and URL schemes) and segments ending
    in a space or dot. Shared by `safe_relative_path` and `Job.dest`.
    """
    if not p:
        raise ValueError("path is empty")
    if len(p) > _PATH_MAX:
        raise ValueError(f"path is longer than {_PATH_MAX} characters: {_echo(p)}")
    _printable(p)
    if p[0] in "/\\":
        raise ValueError(f"path must be relative: {_echo(p)}")
    segments = p.replace("\\", "/").split("/")
    for seg in segments:
        if seg in ("", ".", ".."):
            raise ValueError(f"path has an empty, '.' or '..' segment: {_echo(p)}")
        if _BAD_CHARS.intersection(seg):
            raise ValueError(f"path has a character not allowed on Windows ({''.join(sorted(_BAD_CHARS))}): {_echo(p)}")
        if seg[-1] in " .":
            raise ValueError(f"path segment ends with a space or dot: {_echo(p)}")
    return segments


def safe_relative_path(p: str) -> str:
    """Validate a run-folder-relative file path and return it with forward slashes."""
    if _DRIVE_RE.match(p):
        raise ValueError(f"path must not have a drive letter: {_echo(p)}")
    segments = safe_segments(p)
    for seg in segments:
        if seg.split(".", 1)[0].rstrip(" ").upper() in _RESERVED:
            raise ValueError(f"path uses a Windows-reserved name: {_echo(p)}")
    if segments[0] not in RUN_FOLDERS:
        raise ValueError(f"path must start with one of {', '.join(RUN_FOLDERS)}: {_echo(p)}")
    if len(segments) < 2:
        raise ValueError(f"path must name a file inside a run folder: {_echo(p)}")
    return "/".join(segments)


def _sharepoint_url(v: str) -> str:
    """https URL on a *.sharepoint.com host. The host is checked against a strict pattern, not trusted from urlsplit."""
    if len(v) > _URL_MAX:
        raise ValueError(f"URL is longer than {_URL_MAX} characters")
    _printable(v)
    if "\\" in v or any(c.isspace() for c in v):
        raise ValueError(f"URL must not contain a backslash or whitespace: {_echo(v)}")
    u = urlsplit(v)
    if u.scheme != "https":
        raise ValueError(f"URL must use https: {_echo(v)}")
    if "@" in u.netloc:
        raise ValueError("URL must not contain a username or password")
    if ":" in u.netloc:
        raise ValueError(f"URL must not give a port: {_echo(v)}")
    if not _SHAREPOINT_HOST_RE.fullmatch(u.netloc):
        raise ValueError(f"URL host must be a *.sharepoint.com host: {_echo(v)}")
    return v


def _sql_text(v: str) -> str:
    """Printable, except that line breaks and tabs are allowed."""
    _printable(v.translate({9: None, 10: None, 13: None}))
    return v


def _valid_run_id(v: str) -> str:
    parse_run_id(v)
    return v


_RunId = Annotated[str, AfterValidator(_valid_run_id)]
_Count = Annotated[int, Field(ge=0)]
_LayerId = Literal["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
_Strict = ConfigDict(extra="forbid")


class FileEntry(BaseModel):
    model_config = _Strict

    path: Annotated[str, AfterValidator(safe_relative_path)]
    kind: Literal["command", "strategy", "raw_dump", "financials", "screenshot", "annual_report", "working", "annexure", "log"]
    layer: _LayerId | None
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    bytes: _Count
    time: AwareDatetime
    sharepoint_url: Annotated[str, AfterValidator(_sharepoint_url)] | None

    @model_validator(mode="after")
    def _kind_fits_folder(self) -> "FileEntry":
        in_raw_dumps = self.path.split("/", 1)[0] == _RAW_DUMPS
        if self.kind == "raw_dump" and not in_raw_dumps:
            raise ValueError(f"kind: a raw_dump must be under {_RAW_DUMPS}/: {self.path!r}")
        if self.path == _COUNTS_JSON and self.kind != "working":
            raise ValueError(f"kind: {_COUNTS_JSON} must have kind 'working', not {self.kind!r}")
        if in_raw_dumps and self.kind != "raw_dump" and self.path != _COUNTS_JSON:
            raise ValueError(f"kind: only raw dumps and counts.json may be under {_RAW_DUMPS}/: {self.path!r}")
        return self


class LayerResult(BaseModel):
    model_config = _Strict

    id: _LayerId
    field: _Text
    sql: Annotated[str, StringConstraints(max_length=_SQL_MAX), AfterValidator(_sql_text)]
    row_count: _Count


class SourceInfo(BaseModel):
    model_config = _Strict

    database: _Text
    data_date: date | None
    year_codes: list[Annotated[str, StringConstraints(pattern=r"^[0-9]{4}03$")]]


class Universe(BaseModel):
    model_config = _Strict

    distinct_companies: _Count
    peer_set: _Text | None


class Manifest(BaseModel):
    model_config = _Strict

    schema_version: Literal["1.0"]
    run_id: _RunId
    command: Command
    source: SourceInfo
    layers: list[LayerResult] = Field(max_length=8)
    universe: Universe | None
    files: list[FileEntry] = Field(max_length=5000)
    status: Literal["complete", "partial", "failed"]
    fallbacks_used: list[_Text] = Field(max_length=100)
    human_touches: _Count

    @model_validator(mode="after")
    def _consistent(self) -> "Manifest":
        check_run_id_matches(self.run_id, self.command.db, self.command.fy)
        ids = [layer.id for layer in self.layers]
        if len(set(ids)) != len(ids):
            raise ValueError(f"layers: duplicate layer id in {ids}")
        seen: set[str] = set()
        for f in self.files:
            key = f.path.casefold()
            if key in seen:
                raise ValueError(f"files: duplicate path {f.path!r} (paths are compared case-insensitively)")
            seen.add(key)
        raw_dump = re.compile(rf"{_RAW_DUMPS}/{re.escape(self.run_id)}_(L[1-8])_[A-Za-z0-9]+_[0-9]{{3}}\.(?:csv|xls|xlsx)")
        for f in self.files:
            if f.kind != "raw_dump":
                continue
            m = raw_dump.fullmatch(f.path)
            if not m:
                raise ValueError(f"files: raw dump {f.path!r} is not named {_RAW_DUMPS}/{self.run_id}_L<n>_<field>_<seq3>.<csv|xls|xlsx>")
            if m.group(1) != f.layer:
                raise ValueError(f"files: raw dump {f.path!r} is for {m.group(1)} but layer is {f.layer!r}")
        return self
