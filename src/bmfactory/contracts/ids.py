"""Financial-year handling and RunID construction/parsing.

RunID format: <DB>-FY<yy><yy>-<client-slug|LIB>-<YYYYMMDD>-<nn>
e.g. CAP-FY2526-LIB-20261114-01
"""

import re
from datetime import date, datetime

from pydantic import BaseModel

DB_CODES: tuple[str, ...] = ("CAP", "PRW", "ACE", "CAT", "CMP")

_FY_RE = re.compile(r"([0-9]{4}|[0-9]{2})-([0-9]{4}|[0-9]{2})")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MAX = 30
_LIBRARY = "LIB"
# FY start years whose two-digit RunID form maps back to one year.
_FY_START_MIN, _FY_START_MAX = 2000, 2098


class RunIdParts(BaseModel):
    db: str
    fy: str
    client_slug: str | None
    run_date: date
    seq: int


def normalise_fy(text: str) -> str:
    """Return a financial year as 'YYYY-YY' from 'FY 2025-26', '25-26', '2025-2026' etc."""
    s = text.strip()
    if s[:2].upper() == "FY":
        s = s[2:].strip()
    m = _FY_RE.fullmatch(s)
    if not m:
        raise ValueError(f"unrecognised financial year: {text!r}")
    start_s, end_s = m.groups()
    if len(start_s) == 2 and len(end_s) == 4:
        raise ValueError(f"unrecognised financial year: {text!r}")
    start = int(start_s) if len(start_s) == 4 else 2000 + int(start_s)
    if len(end_s) == 4:
        ok = int(end_s) == start + 1
    else:
        ok = int(end_s) == (start + 1) % 100
    if not ok:
        raise ValueError(f"financial year must span consecutive years: {text!r}")
    if not _FY_START_MIN <= start <= _FY_START_MAX:
        raise ValueError(f"financial year must start in {_FY_START_MIN}-{_FY_START_MAX}: {text!r}")
    return f"{start:04d}-{(start + 1) % 100:02d}"


def current_compliance_fy(today: date) -> str:
    """The FY whose transfer-pricing compliance is due as of `today`."""
    end = today.year if today.month >= 4 else today.year - 1
    return f"{end - 1}-{end % 100:02d}"


def year_codes(fy: str) -> list[str]:
    """YYYY03 codes for the FY end year and the two preceding years, newest first."""
    end = int(normalise_fy(fy)[:4]) + 1
    return [f"{end - i}03" for i in range(3)]


def slugify_client(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = slug[:_SLUG_MAX].strip("-")
    if not slug:
        raise ValueError(f"client name gives an empty slug: {name!r}")
    return slug


def _valid_slug(slug: str) -> bool:
    """A client slug; 'lib' is refused because it equals the LIB marker on case-insensitive SharePoint."""
    return bool(_SLUG_RE.fullmatch(slug)) and len(slug) <= _SLUG_MAX and slug.upper() != _LIBRARY


def make_run_id(db: str, fy: str, client_slug: str | None, run_date: date, seq: int) -> str:
    if db not in DB_CODES:
        raise ValueError(f"unknown database code: {db!r}")
    if not 1 <= seq <= 99:
        raise ValueError(f"seq must be 1-99: {seq}")
    if client_slug is not None and not _valid_slug(client_slug):
        raise ValueError(f"invalid client slug: {client_slug!r}")
    norm = normalise_fy(fy)
    start = int(norm[:4])
    fy_token = f"FY{start % 100:02d}{(start + 1) % 100:02d}"
    client = client_slug if client_slug is not None else _LIBRARY
    return f"{db}-{fy_token}-{client}-{run_date:%Y%m%d}-{seq:02d}"


def parse_run_id(run_id: str) -> RunIdParts:
    tokens = run_id.split("-")
    if len(tokens) < 5:
        raise ValueError(f"malformed RunID: {run_id!r}")
    db, fy_token, *client_tokens, date_token, seq_token = tokens
    if db not in DB_CODES:
        raise ValueError(f"unknown database code in RunID: {run_id!r}")
    m = re.fullmatch(r"FY([0-9]{2})([0-9]{2})", fy_token)
    if not m:
        raise ValueError(f"malformed FY in RunID: {run_id!r}")
    fy = normalise_fy(f"{m.group(1)}-{m.group(2)}")
    if not re.fullmatch(r"[0-9]{8}", date_token):
        raise ValueError(f"malformed date in RunID: {run_id!r}")
    run_date = datetime.strptime(date_token, "%Y%m%d").date()
    if not re.fullmatch(r"[0-9]{2}", seq_token) or int(seq_token) < 1:
        raise ValueError(f"malformed seq in RunID: {run_id!r}")
    client = "-".join(client_tokens)
    if client == _LIBRARY:
        client_slug = None
    elif _valid_slug(client):
        client_slug = client
    else:
        raise ValueError(f"malformed client in RunID: {run_id!r}")
    return RunIdParts(db=db, fy=fy, client_slug=client_slug, run_date=run_date, seq=int(seq_token))


def check_run_id_matches(run_id: str, db: str, fy: str) -> None:
    """Raise if the RunID's database or financial year differs from the command's."""
    parts = parse_run_id(run_id)
    if parts.db != db:
        raise ValueError(f"run_id: database {parts.db} does not match command db {db}")
    if parts.fy != fy:
        raise ValueError(f"run_id: financial year {parts.fy} does not match command fy {fy}")
