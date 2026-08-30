"""Unit tests for the party YAML parser."""

from src.party_parser import read_party_file


def test_read_party_file_returns_codes_and_transfers(sample_party_yaml):
    codes, transfers = read_party_file(sample_party_yaml)

    assert codes == {5: "PP", 6: "PP", 0: "PSOE", 29: "IU"}
    assert transfers["IU"]["PSOE"] == 0.6
    assert transfers["IU"]["PP"] == 0.2
    assert transfers["R"]["PSOE"] == 0.5
    assert transfers["R"]["PP"] == 0.3


def test_read_party_file_empty_transfers_are_dict():
    import tempfile
    import os

    content = """
parties:
  PP: [5]
transfers:
  PP:
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        path = f.name

    try:
        codes, transfers = read_party_file(path)
        assert codes == {5: "PP"}
        assert transfers == {"PP": {}}
    finally:
        os.unlink(path)


