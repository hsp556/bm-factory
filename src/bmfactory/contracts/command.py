"""One-line job command grammar.

e.g. CAP | FY 2025-26 | Industry: software development | Product: app development; IT consulting
     | Client: KRKA | PLI: OP/OC | Tested party: service | TP sales: 45.5 cr | Mode: run

The text is untrusted (it may come from speech-to-text): it is only split and matched, never evaluated.
Data-contract invariants live on `Command`, so a Command loaded from JSON is held to them too.
"""

import math
import re
import unicodedata
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator, model_validator

from bmfactory.contracts.ids import DB_CODES, current_compliance_fy, normalise_fy

_NIC_RE = re.compile(r"nic\s*([0-9]{2,5})", re.IGNORECASE | re.ASCII)
_TP_SALES_RE = re.compile(r"(?:₹|rs\.?)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:crores?|cr\.?)?", re.IGNORECASE | re.ASCII)
_KEYS = ("fy", "industry", "product", "client", "pli", "tested party", "tp sales", "mode")
_PLIS = {"OP/OC": "OP/OC", "OP/OR": "OP/OR", "GP/SALES": "GP/Sales"}
_TESTED_PARTIES = ("service", "manufacturer", "distributor")
_MODES = ("run", "strategy-only", "refresh")
_DEFAULT_PLI = {"service": "OP/OC", "distributor": "OP/OR", "manufacturer": "OP/OC"}
_TEXT_MAX = 200
_PRODUCTS_MAX = 20
_ECHO_MAX = 50
# Model field -> the lowercase name a person uses in the command text.
_FIELD_NAMES = {"products": "product", "tp_sales_cr": "tp sales", "tested_party": "tested party", "nic_codes": "nic codes"}


class CommandError(ValueError):
    pass


def _printable(s: str) -> str:
    """Reject control, format (bidi, zero-width), surrogate and unassigned characters (Unicode category C*)."""
    bad = next((c for c in s if unicodedata.category(c).startswith("C")), None)
    if bad is not None:
        raise ValueError(f"contains a control or format character U+{ord(bad):04X}")
    return s


_Text = Annotated[str, StringConstraints(min_length=1, max_length=_TEXT_MAX), AfterValidator(_printable)]
_NicCode = Annotated[str, StringConstraints(pattern=r"^[0-9]{2,5}$")]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db: str
    fy: str
    industry: _Text
    nic_codes: list[_NicCode]
    products: list[_Text] = Field(min_length=1, max_length=_PRODUCTS_MAX)
    client: _Text | None
    pli: Literal["OP/OC", "OP/OR", "GP/Sales"]
    tp_sales_cr: float | None
    tested_party: Literal["service", "manufacturer", "distributor"]
    mode: Literal["run", "strategy-only", "refresh"]

    @field_validator("db")
    @classmethod
    def _known_db(cls, v: str) -> str:
        if v not in DB_CODES:
            raise ValueError(f"unknown database code {_echo(v)}; expected one of {', '.join(DB_CODES)}")
        return v

    @field_validator("fy")
    @classmethod
    def _normalised_fy(cls, v: str) -> str:
        if normalise_fy(v) != v:
            raise ValueError(f"must be in YYYY-YY form: {_echo(v)}")
        return v

    @field_validator("tp_sales_cr")
    @classmethod
    def _positive_sales(cls, v: float | None) -> float | None:
        if v is not None and not (math.isfinite(v) and v > 0):
            raise ValueError(f"must be a positive amount in crore: {v!r}")
        return v

    @model_validator(mode="after")
    def _pli_fits_tested_party(self) -> "Command":
        if self.pli == "GP/Sales" and self.tested_party == "service":
            raise ValueError("pli: GP/Sales is not allowed for a service provider")
        return self


def _echo(s: str) -> str:
    """Quote untrusted text for an error message, truncated."""
    return repr(s[:_ECHO_MAX] + ("..." if len(s) > _ECHO_MAX else ""))


def _parse_tp_sales(value: str) -> float:
    m = _TP_SALES_RE.fullmatch(value)
    if not m:
        raise CommandError(f"tp sales: not a positive number in crore: {_echo(value)}")
    return float(m.group(1))


def _command_error(e: ValidationError) -> CommandError:
    parts = []
    for err in e.errors():
        msg = err["msg"].removeprefix("Value error, ")
        if err["loc"]:
            field = str(err["loc"][0])
            msg = f"{_FIELD_NAMES.get(field, field)}: {msg}"
        parts.append(msg)
    return CommandError("; ".join(parts))


def parse_command(text: str, today: date) -> Command:
    db_text, *segments = [s.strip() for s in text.split("|")]

    fields: dict[str, str] = {}
    for seg in segments:
        if not seg:
            continue
        if _NIC_RE.fullmatch(seg):
            key, value = "industry", seg
        elif ":" not in seg and seg[:2].upper() == "FY":
            key, value = "fy", seg
        elif ":" in seg:
            raw_key, value = seg.split(":", 1)
            key = " ".join(raw_key.split()).lower()
            value = value.strip()
        else:
            raise CommandError(f"unrecognised segment {_echo(seg)}; expected 'Key: value'")
        if key not in _KEYS:
            raise CommandError(f"{_echo(key)}: unknown key; expected one of {', '.join(_KEYS)}")
        if key in fields:
            raise CommandError(f"{key}: given more than once")
        if not value:
            raise CommandError(f"{key}: empty value")
        fields[key] = value

    if "fy" in fields:
        try:
            fy = normalise_fy(fields["fy"])
        except ValueError as e:
            raise CommandError(f"fy: {e}") from None
    else:
        fy = current_compliance_fy(today)

    if "industry" not in fields:
        raise CommandError("industry: missing (give 'Industry: ...' or 'NIC <code>')")
    industry = fields["industry"]
    nic = _NIC_RE.fullmatch(industry)
    nic_codes = [nic.group(1)] if nic else []

    products = [p.strip() for p in fields.get("product", "").split(";") if p.strip()]
    if not products:
        raise CommandError("product: missing (give 'Product: a; b')")

    tested_party = fields.get("tested party", "service").lower()
    if tested_party not in _TESTED_PARTIES:
        raise CommandError(f"tested party: {_echo(tested_party)} not one of {', '.join(_TESTED_PARTIES)}")

    if "pli" in fields:
        pli = _PLIS.get("".join(fields["pli"].split()).upper())
        if pli is None:
            raise CommandError(f"pli: {_echo(fields['pli'])} not one of {', '.join(_PLIS.values())}")
    else:
        pli = _DEFAULT_PLI[tested_party]

    mode = fields.get("mode", "run").lower()
    if mode not in _MODES:
        raise CommandError(f"mode: {_echo(mode)} not one of {', '.join(_MODES)}")

    tp_sales_cr = _parse_tp_sales(fields["tp sales"]) if "tp sales" in fields else None

    try:
        return Command(
            db=db_text.upper(),
            fy=fy,
            industry=industry,
            nic_codes=nic_codes,
            products=products,
            client=fields.get("client"),
            pli=pli,
            tp_sales_cr=tp_sales_cr,
            tested_party=tested_party,
            mode=mode,
        )
    except ValidationError as e:
        raise _command_error(e) from None
