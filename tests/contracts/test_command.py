from datetime import date

import pytest

from bmfactory.contracts.command import CommandError, parse_command

T = date(2026, 11, 14)


def test_minimal_defaults():
    c = parse_command("CAP | FY 2025-26 | Industry: software development | Product: application development; IT consulting", T)
    assert (c.db, c.fy, c.industry, c.products) == ("CAP", "2025-26", "software development", ["application development", "IT consulting"])
    assert (c.pli, c.tested_party, c.mode, c.client, c.tp_sales_cr, c.nic_codes) == ("OP/OC", "service", "run", None, None, [])


def test_full_command():
    c = parse_command("CAP | FY 2025-26 | Industry: pharmaceutical formulations | Product: tablets; capsules | Client: KRKA | PLI: OP/OR | Tested party: distributor", T)
    assert (c.client, c.pli, c.tested_party) == ("KRKA", "OP/OR", "distributor")


def test_bare_nic_segment():
    c = parse_command("CAP | FY 2025-26 | NIC 6201 | Product: SaaS | Mode: strategy-only", T)
    assert (c.industry, c.nic_codes, c.mode) == ("NIC 6201", ["6201"], "strategy-only")


def test_fy_defaults_to_compliance_year():
    assert parse_command("CAP | Industry: ITeS | Product: BPO", T).fy == "2025-26"


def test_sloppy_text():
    c = parse_command("  cap|fy25-26 |  INDUSTRY :  ITeS | product: medical transcription ; ;| tp SALES: ₹ 45.5 cr ", T)
    assert (c.db, c.fy, c.products, c.tp_sales_cr) == ("CAP", "2025-26", ["medical transcription"], 45.5)


def test_distributor_default_pli():
    assert parse_command("CAP | Industry: x | Product: y | Tested party: distributor", T).pli == "OP/OR"


@pytest.mark.parametrize("text,field", [
    ("CAP | Product: y", "industry"),
    ("CAP | Industry: x", "product"),
    ("XYZ | Industry: x | Product: y", "db"),
    ("CAP | Industry: x | Product: y | Colour: red", "colour"),
    ("CAP | Industry: x | Product: y | PLI: GP/Sales", "pli"),        # GP/Sales invalid for a service provider (Rule 10C)
    ("CAP | Industry: x | Product: y | TP sales: -3", "tp sales"),
])
def test_rejects_with_field_named(text, field):
    with pytest.raises(CommandError, match=field):
        parse_command(text, T)


# ---- Fix round 1 ----
from pydantic import ValidationError  # noqa: E402

from bmfactory.contracts.command import Command  # noqa: E402

BASE = dict(db="CAP", fy="2025-26", industry="x", nic_codes=[], products=["y"], client=None,
            pli="OP/OC", tp_sales_cr=None, tested_party="service", mode="run")
CMD = "CAP | Industry: x | Product: y"


# F1: units touching the digits
@pytest.mark.parametrize("raw", ["45cr", "₹45cr", "Rs.45", "45 crore", "Rs 45", "45crore", "₹ 45 cr.", "RS45CR"])
def test_tp_sales_units(raw):
    assert parse_command(f"{CMD} | TP sales: {raw}", T).tp_sales_cr == 45.0


# F2: free-text length, product count and control/format characters
@pytest.mark.parametrize("text,field", [
    (f"CAP | Industry: {'x' * 201} | Product: y", "industry"),
    (f"{CMD}; {'z' * 201}", "product"),
    ("CAP | Industry: x | Product: " + "; ".join(f"p{i}" for i in range(21)), "product"),
    (f"{CMD} | Client: {'c' * 201}", "client"),
    ("CAP | Industry: a\nb | Product: y", "industry"),
    ("CAP | Industry: a\rb | Product: y", "industry"),
    ("CAP | Industry: x | Product: a\x00b", "product"),
    ("CAP | Industry: x | Product: a\x1b[31mb", "product"),
    (f"{CMD} | Client: KR‮KA", "client"),
    ("CAP | Industry: x | Product: a​b", "product"),
])
def test_rejects_unsafe_free_text(text, field):
    with pytest.raises(CommandError, match=field):
        parse_command(text, T)


def test_accepts_limits():
    products = "; ".join(f"p{i}" for i in range(20))
    c = parse_command(f"CAP | Industry: {'x' * 200} | Product: {products} | Client: {'c' * 200}", T)
    assert (len(c.industry), len(c.products), len(c.client)) == (200, 20, 200)


# F3: ASCII-only NIC digits
def test_non_ascii_nic_segment_rejected():
    with pytest.raises(CommandError, match="segment"):
        parse_command("CAP | NIC ٦٢٠١ | Product: y", T)


def test_non_ascii_nic_industry_has_no_codes():
    assert parse_command("CAP | Industry: NIC ٦٢٠١ | Product: y", T).nic_codes == []


# F2/F3/F5: invariants hold on the model itself (Command(...) and model_validate)
def test_model_accepts_base():
    assert Command(**BASE).db == "CAP"


@pytest.mark.parametrize("override", [
    {"tested_party": "service", "pli": "GP/Sales"},
    {"db": "XYZ"},
    {"db": "cap"},
    {"fy": "FY 2025-26"},
    {"fy": "2025-2026"},
    {"fy": "25-26"},
    {"fy": "2025-27"},
    {"tp_sales_cr": 0},
    {"tp_sales_cr": -1.0},
    {"tp_sales_cr": float("inf")},
    {"tp_sales_cr": float("nan")},
    {"nic_codes": ["٦٢٠١"]},
    {"nic_codes": ["6201\n"]},
    {"nic_codes": ["1"]},
    {"industry": "a\nb"},
    {"industry": "x" * 201},
    {"products": ["a​b"]},
    {"products": [f"p{i}" for i in range(21)]},
    {"products": []},
    {"client": "KR‮KA"},
])
@pytest.mark.parametrize("build", [lambda d: Command(**d), Command.model_validate])
def test_model_rejects(override, build):
    with pytest.raises(ValidationError):
        build({**BASE, **override})


def test_model_allows_gp_sales_for_distributor():
    assert Command(**{**BASE, "tested_party": "distributor", "pli": "GP/Sales"}).pli == "GP/Sales"


# Also-do: error echo is repr'd and truncated; strict TP sales number; untested extra checks
def test_unknown_key_echo_is_repr_and_truncated():
    with pytest.raises(CommandError) as e:
        parse_command(f"{CMD} | {'k' * 100}: v", T)
    msg = str(e.value)
    assert "'kkkk" in msg and "k" * 51 not in msg


def test_unrecognised_segment_echo_truncated():
    with pytest.raises(CommandError) as e:
        parse_command(f"{CMD} | {'s' * 100}", T)
    assert "s" * 51 not in str(e.value)


@pytest.mark.parametrize("text,field", [
    (f"{CMD} | Industry: z", "industry"),                 # duplicate key
    (f"{CMD} | Client:", "client"),                       # empty value
    (f"{CMD} | hello", "segment"),                        # colon-less segment
    (f"{CMD} | TP sales: inf", "tp sales"),
    (f"{CMD} | TP sales: nan", "tp sales"),
    (f"{CMD} | TP sales: 4_5", "tp sales"),
    (f"{CMD} | TP sales: ٤٥", "tp sales"),
    (f"{CMD} | TP sales: 1e3", "tp sales"),
    (f"{CMD} | Mode: dryrun", "mode"),
    (f"{CMD} | Tested party: trader", "tested party"),
    (f"{CMD} | FY: 2025-27", "fy"),
])
def test_rejects_extra_checks(text, field):
    with pytest.raises(CommandError, match=field):
        parse_command(text, T)


def test_fy_key():
    assert parse_command(f"{CMD} | FY: 24-25", T).fy == "2024-25"


def test_industry_nic_value():
    c = parse_command("CAP | Industry: NIC 6201 | Product: y", T)
    assert (c.industry, c.nic_codes) == ("NIC 6201", ["6201"])


# Final review W1: the model rejects unknown keys
@pytest.mark.parametrize("build", [lambda d: Command(**d), Command.model_validate])
def test_model_rejects_unknown_key(build):
    with pytest.raises(ValidationError):
        build({**BASE, "bogus": 1})
