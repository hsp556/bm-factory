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
