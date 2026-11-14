from datetime import date

import pytest

from bmfactory.contracts.ids import (
    current_compliance_fy,
    make_run_id,
    normalise_fy,
    parse_run_id,
    slugify_client,
    year_codes,
)


@pytest.mark.parametrize("raw", ["2025-26", "FY 2025-26", "FY25-26", "25-26", "2025-2026", " fy2025-26 "])
def test_normalise_fy_variants(raw): assert normalise_fy(raw) == "2025-26"

@pytest.mark.parametrize("bad", ["2025-27", "2025", "FY", "26-25", ""])
def test_normalise_fy_rejects(bad):
    with pytest.raises(ValueError): normalise_fy(bad)

@pytest.mark.parametrize("today,fy", [(date(2026,11,14),"2025-26"), (date(2027,2,1),"2025-26"), (date(2027,4,1),"2026-27")])
def test_current_compliance_fy(today, fy): assert current_compliance_fy(today) == fy

def test_year_codes(): assert year_codes("2025-26") == ["202603", "202503", "202403"]

def test_slugify_client(): assert slugify_client("KRKA Pharma Pvt. Ltd.") == "krka-pharma-pvt-ltd"

def test_make_run_id_library(): assert make_run_id("CAP", "2025-26", None, date(2026,11,14), 1) == "CAP-FY2526-LIB-20261114-01"

def test_run_id_round_trip_hyphenated_client():
    rid = make_run_id("PRW", "FY 2025-26", slugify_client("Acme - India Ltd"), date(2026,11,14), 7)
    assert rid == "PRW-FY2526-acme-india-ltd-20261114-07"
    p = parse_run_id(rid)
    assert (p.db, p.fy, p.client_slug, p.run_date, p.seq) == ("PRW", "2025-26", "acme-india-ltd", date(2026,11,14), 7)

def test_parse_run_id_lib_is_none(): assert parse_run_id("CAP-FY2526-LIB-20261114-01").client_slug is None

@pytest.mark.parametrize("bad", ["XYZ-FY2526-LIB-20261114-01", "CAP-FY2526-LIB-20261114-00", "CAP-FY2527-LIB-20261114-01", "CAP-2526-LIB-20261114-01", "CAP-FY2526-LIB-2026111-01"])
def test_parse_run_id_rejects(bad):
    with pytest.raises(ValueError): parse_run_id(bad)

@pytest.mark.parametrize("db,seq", [("XYZ", 1), ("CAP", 0), ("CAP", 100)])
def test_make_run_id_rejects(db, seq):
    with pytest.raises(ValueError): make_run_id(db, "2025-26", None, date(2026,11,14), seq)

# Fix round 1 (F4): no trailing-newline or non-ASCII-digit leaks into RunIDs
def test_make_run_id_rejects_slug_with_trailing_newline():
    with pytest.raises(ValueError): make_run_id("CAP", "2025-26", "abc\n", date(2026,11,14), 1)

@pytest.mark.parametrize("bad", [
    "CAP-FY2526-LIB-20261114-01\n",
    "CAP-FY2526-abc\n-20261114-01",
    "CAP-FY2526-LIB-٢٠٢٦١١١٤-01",
    "CAP-FY٢٥٢٦-LIB-20261114-01",
])
def test_parse_run_id_rejects_newline_and_non_ascii_digits(bad):
    with pytest.raises(ValueError): parse_run_id(bad)

@pytest.mark.parametrize("bad", ["٢٥-٢٦", "2025-26\n-"])
def test_normalise_fy_rejects_non_ascii_digits(bad):
    with pytest.raises(ValueError): normalise_fy(bad)

# Final review W8: FY start year 2000-2098, so the RunID's two-digit form is unambiguous
@pytest.mark.parametrize("bad", ["0001-02", "1999-00", "2099-00", "FY 1999-2000"])
def test_normalise_fy_rejects_out_of_range_years(bad):
    with pytest.raises(ValueError): normalise_fy(bad)

def test_normalise_fy_accepts_last_year_in_range(): assert normalise_fy("2098-99") == "2098-99"

# Final review W9: the client slug "lib" would collide with the LIB marker on case-insensitive SharePoint
def test_make_run_id_rejects_lib_slug():
    with pytest.raises(ValueError): make_run_id("CAP", "2025-26", "lib", date(2026,11,14), 1)

def test_parse_run_id_rejects_lib_slug():
    with pytest.raises(ValueError): parse_run_id("CAP-FY2526-lib-20261114-01")
