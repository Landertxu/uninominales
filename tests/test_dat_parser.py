"""Unit tests for the INE DAT parser."""

import os
import tempfile

import pytest

from src.dat_parser import parse_dat_file


# Helper to build a valid 36-char DAT line
def make_line(cusec, cand, votes):
    """Build a 36-char INE type-10 record."""
    return f"02201512010{cusec:10} 1{cand:06}{votes:07d}"


def test_parse_dat_file_returns_correct_tuples(sample_dat_file):
    records = list(parse_dat_file(sample_dat_file))
    # Two records aggregate for mesa 2800100100 code 000005, so 3 unique (cusec,cand)
    assert len(records) == 3

    # First record: mesa 2800100100, code 000005, 1234 + 99 = 1333 votes
    cusec, candidatura, votos = records[0]
    assert cusec == "2800100100"
    assert candidatura == "000005"
    assert votos == 1333


def test_parse_dat_file_aggregates_duplicate_mesa_code(sample_dat_file):
    # Code 5 appears twice for mesa 2800100100 (1234 + 99 votes)
    records = {(cusec, cand): votos for cusec, cand, votos in parse_dat_file(sample_dat_file)}
    assert records[("2800100100", "000005")] == 1333
    # Code 2 also appears once for mesa 2800100100
    assert records[("2800100100", "000002")] == 10056
    # Code 29 appears once for mesa 3100100100
    assert records[("3100100100", "000029")] == 88


def test_parse_dat_file_skips_short_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".DAT", delete=False) as f:
        f.write("short line\n")
        f.write(make_line("2800100100", "000005", 1) + "\n")
        path = f.name

    try:
        records = list(parse_dat_file(path))
        assert len(records) == 1
        assert records[0] == ("2800100100", "000005", 1)
    finally:
        os.unlink(path)


def test_parse_dat_file_ignores_non_numeric_votes():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".DAT", delete=False) as f:
        f.write("02201512012800100100 1000005XXXXXXX\n")
        f.write(make_line("2800100100", "000002", 1) + "\n")
        path = f.name

    try:
        records = list(parse_dat_file(path))
        assert len(records) == 1
        assert records[0] == ("2800100100", "000002", 1)
    finally:
        os.unlink(path)


def test_parse_dat_file_returns_int_votes(sample_dat_file):
    records = list(parse_dat_file(sample_dat_file))
    for _, _, votos in records:
        assert isinstance(votos, int)
        assert votos >= 0


def test_parse_dat_file_line_format():
    """Verify the helper creates a 36-char line that parses correctly."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".DAT", delete=False) as f:
        f.write(make_line("2800100100", "000005", 9999999) + "\n")
        path = f.name

    try:
        records = list(parse_dat_file(path))
        assert len(records) == 1
        assert records[0] == ("2800100100", "000005", 9999999)
    finally:
        os.unlink(path)
