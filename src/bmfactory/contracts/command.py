"""One-line job command grammar.

e.g. CAP | FY 2025-26 | Industry: software development | Product: app development; IT consulting
     | Client: KRKA | PLI: OP/OC | Tested party: service | TP sales: 45.5 cr | Mode: run

The text is untrusted (it may come from speech-to-text): it is only split and matched, never evaluated.
"""

import math
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from bmfactory.contracts.ids import DB_CODES, current_compliance_fy, normalise_fy

_NIC_RE = re.compile(r"(?i)^nic\s*(\d{2,5})$")
_TP_SALES_NOISE_RE = re.compile(r"(?i)₹|\brs\b\.?|\bcrores?\b|\bcr\b\.?")
_KEYS = ("fy", "industry", "product", "client", "pli", "tested party", "tp sales", "mode")
_PLIS = {"OP/OC": "OP/OC", "OP/OR": "OP/OR", "GP/SALES": "GP/Sales"}
_TESTED_PARTIES = ("service", "manufacturer", "distributor")
_MODES = ("run", "strategy-only", "refresh")
_DEFAULT_PLI = {"service": "OP/OC", "distributor": "OP/OR", "manufacturer": "OP/OC"}


class CommandError(ValueError):
    pass


class Command(BaseModel):
    db: str
    fy: str
    industry: str
    nic_codes: list[str]
    products: list[str] = Field(min_length=1)
    client: str | None
    pli: Literal["OP/OC", "OP/OR", "GP/Sales"]
    tp_sales_cr: float | None
    tested_party: Literal["service", "manufacturer", "distributor"]
    mode: Literal["run", "strategy-only", "refresh"]


def _parse_tp_sales(value: str) -> float:
    s = _TP_SALES_NOISE_RE.sub("", value).strip()
    try:
        amount = float(s)
    except ValueError:
        raise CommandError(f"tp sales: not a number: {value!r}") from None
    if not math.isfinite(amount) or amount <= 0:
        raise CommandError(f"tp sales: must be a positive amount in crore: {value!r}")
    return amount


def parse_command(text: str, today: date) -> Command:
    db_text, *segments = [s.strip() for s in text.split("|")]
    db = db_text.upper()
    if db not in DB_CODES:
        raise CommandError(f"db: unknown database code {db_text!r}; expected one of {', '.join(DB_CODES)}")

    fields: dict[str, str] = {}
    for seg in segments:
        if not seg:
            continue
        if _NIC_RE.match(seg):
            key, value = "industry", seg
        elif ":" not in seg and seg[:2].upper() == "FY":
            key, value = "fy", seg
        elif ":" in seg:
            raw_key, value = seg.split(":", 1)
            key = " ".join(raw_key.split()).lower()
            value = value.strip()
        else:
            raise CommandError(f"unrecognised segment {seg!r}; expected 'Key: value'")
        if key not in _KEYS:
            raise CommandError(f"{key}: unknown key; expected one of {', '.join(_KEYS)}")
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
    nic = _NIC_RE.match(industry)
    nic_codes = [nic.group(1)] if nic else []

    products = [p.strip() for p in fields.get("product", "").split(";") if p.strip()]
    if not products:
        raise CommandError("product: missing (give 'Product: a; b')")

    tested_party = fields.get("tested party", "service").lower()
    if tested_party not in _TESTED_PARTIES:
        raise CommandError(f"tested party: {tested_party!r} not one of {', '.join(_TESTED_PARTIES)}")

    if "pli" in fields:
        pli = _PLIS.get("".join(fields["pli"].split()).upper())
        if pli is None:
            raise CommandError(f"pli: {fields['pli']!r} not one of {', '.join(_PLIS.values())}")
    else:
        pli = _DEFAULT_PLI[tested_party]
    if pli == "GP/Sales" and tested_party == "service":
        raise CommandError("pli: GP/Sales is not allowed for a service provider")

    mode = fields.get("mode", "run").lower()
    if mode not in _MODES:
        raise CommandError(f"mode: {mode!r} not one of {', '.join(_MODES)}")

    tp_sales_cr = _parse_tp_sales(fields["tp sales"]) if "tp sales" in fields else None

    try:
        return Command(
            db=db,
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
        raise CommandError(str(e)) from None
