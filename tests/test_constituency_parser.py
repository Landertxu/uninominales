"""Unit tests for the constituency definition parser."""

from src.constituency_parser import parse_constituency_file


def test_parse_constituency_file_basic(sample_constituency_file):
    constituencies = parse_constituency_file(sample_constituency_file)

    assert len(constituencies) == 4

    names = [c[0] for c in constituencies]
    assert names == ["madrid1", "madrid2", "navarra1", "madrid3"]


def test_parse_constituency_file_inclusions(sample_constituency_file):
    constituencies = parse_constituency_file(sample_constituency_file)

    _, madrid1_inclusions, madrid1_exclusions = constituencies[0]
    assert madrid1_inclusions == ["2800100100"]
    assert madrid1_exclusions == []

    _, madrid2_inclusions, _ = constituencies[1]
    assert madrid2_inclusions == ["2800100100", "2800100200"]


def test_parse_constituency_file_exclusions(sample_constituency_file):
    constituencies = parse_constituency_file(sample_constituency_file)

    _, madrid3_inclusions, madrid3_exclusions = constituencies[3]
    assert madrid3_inclusions == ["2800100"]
    assert madrid3_exclusions == ["2800100200"]


def test_parse_constituency_file_ignores_comments_and_blank_lines():
    import tempfile
    import os

    content = """
# This is a comment

  # indented comment
region1:
01001
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dat", delete=False) as f:
        f.write(content)
        path = f.name

    try:
        constituencies = parse_constituency_file(path)
        assert len(constituencies) == 1
        assert constituencies[0] == ("region1", ["01001"], [])
    finally:
        os.unlink(path)


def test_parse_constituency_file_returns_strings():
    import tempfile
    import os

    content = """region1:
01001
01002
-02002
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dat", delete=False) as f:
        f.write(content)
        path = f.name

    try:
        constituencies = parse_constituency_file(path)
        inclusions = constituencies[0][1]
        exclusions = constituencies[0][2]
        assert all(isinstance(i, str) for i in inclusions)
        assert all(isinstance(e, str) for e in exclusions)
    finally:
        os.unlink(path)
