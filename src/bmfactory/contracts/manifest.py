"""The machine-readable list of what a run produced, loaded from JSON (untrusted).

Every file path is relative to the run folder `BM Backup/<DB>/<RunID>/` and must start with one of RUN_FOLDERS.
"""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator, model_validator

from bmfactory.contracts.command import Command, _printable
from bmfactory.contracts.ids import parse_run_id

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

_BAD_CHARS = set('<>:"|?*')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_DRIVE_RE = re.compile(r"[A-Za-z]:")


def safe_relative_path(p: str) -> str:
    """Validate a run-folder-relative path and return it with forward slashes."""
    if not p:
        raise ValueError("path is empty")
    _printable(p)
    if p[0] in "/\\":
        raise ValueError(f"path must be relative: {p!r}")
    if _DRIVE_RE.match(p):
        raise ValueError(f"path must not have a drive letter: {p!r}")
    segments = p.replace("\\", "/").split("/")
    for seg in segments:
        if seg in ("", ".", ".."):
            raise ValueError(f"path has an empty, '.' or '..' segment: {p!r}")
        if _BAD_CHARS.intersection(seg):
            raise ValueError(f"path has a character not allowed on Windows ({''.join(sorted(_BAD_CHARS))}): {p!r}")
        if seg[-1] in " .":
            raise ValueError(f"path segment ends with a space or dot: {p!r}")
        if seg.split(".", 1)[0].rstrip(" ").upper() in _RESERVED:
            raise ValueError(f"path uses a Windows-reserved name: {p!r}")
    if segments[0] not in RUN_FOLDERS:
        raise ValueError(f"path must start with one of {', '.join(RUN_FOLDERS)}: {p!r}")
    if len(segments) < 2:
        raise ValueError(f"path must name a file inside a run folder: {p!r}")
    return "/".join(segments)


def _valid_run_id(v: str) -> str:
    parse_run_id(v)
    return v


_RunId = Annotated[str, AfterValidator(_valid_run_id)]
_Count = Annotated[int, Field(ge=0)]


class FileEntry(BaseModel):
    path: Annotated[str, AfterValidator(safe_relative_path)]
    kind: Literal["command", "strategy", "raw_dump", "financials", "screenshot", "annual_report", "working", "annexure", "log"]
    layer: str | None
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    bytes: _Count
    sharepoint_url: str | None


class LayerResult(BaseModel):
    id: Literal["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]
    field: str
    sql: str
    row_count: _Count


class SourceInfo(BaseModel):
    database: str
    data_date: date | None
    year_codes: list[Annotated[str, StringConstraints(pattern=r"^[0-9]{4}03$")]]


class Universe(BaseModel):
    distinct_companies: _Count
    peer_set: str | None


class Manifest(BaseModel):
    schema_version: Literal["1.0"]
    run_id: _RunId
    command: Command
    source: SourceInfo
    layers: list[LayerResult]
    universe: Universe | None
    files: list[FileEntry]
    status: Literal["complete", "partial", "failed"]
    fallbacks_used: list[str]
    human_touches: _Count

    @model_validator(mode="after")
    def _files_consistent(self) -> "Manifest":
        seen: set[str] = set()
        for f in self.files:
            if f.path in seen:
                raise ValueError(f"files: duplicate path {f.path!r}")
            seen.add(f.path)
        raw_dump = re.compile(rf"02-Raw-Dumps/{re.escape(self.run_id)}_(L[1-8])_[A-Za-z0-9]+_[0-9]{{3}}\.(?:csv|xls|xlsx)")
        for f in self.files:
            if f.kind != "raw_dump":
                continue
            m = raw_dump.fullmatch(f.path)
            if not m:
                raise ValueError(f"files: raw dump {f.path!r} is not named 02-Raw-Dumps/{self.run_id}_L<n>_<field>_<seq3>.<csv|xls|xlsx>")
            if m.group(1) != f.layer:
                raise ValueError(f"files: raw dump {f.path!r} is for {m.group(1)} but layer is {f.layer!r}")
        return self
