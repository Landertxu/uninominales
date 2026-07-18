"""Shared fixtures for the uninominales test suite."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent


def pytest_addoption(parser):
    parser.addoption(
        "--regenerate-golden",
        action="store_true",
        default=False,
        help="Regenerate golden PNG files from current output",
    )


@pytest.fixture(scope="session")
def regenerate_golden(request):
    return request.config.getoption("--regenerate-golden")


def pytest_sessionfinish(session, exitstatus):
    """After all tests, optionally regenerate golden files from output/."""
    if session.config.getoption("--regenerate-golden"):
        output_dir = PROJECT_ROOT / "output"
        golden_dir = PROJECT_ROOT / "tests" / "golden"
        golden_dir.mkdir(parents=True, exist_ok=True)
        for year in ["2008", "2011", "2015", "2016", "2019a", "2019b"]:
            src = output_dir / f"mapa{year}.png"
            dst = golden_dir / f"mapa{year}.png"
            if src.exists():
                shutil.copy2(src, dst)
                print(f"\nRegenerated golden: {dst}")
            else:
                print(f"\nMissing output for {year}, cannot regenerate golden")


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def sample_dat_lines():
    """Return a few synthetic INE type-10 DAT records (36 chars each).

    Format (36 chars):
      [0:2]   process
      [2:6]   year
      [6:8]   month
      [8:11]  round constant
      [11:21] cusec
      [21]    space
      [22]    category letter
      [23:29] candidatura code
      [29:36] votes (7 digits)
    """
    return [
        "022015120102800100100 10000050001234",  # mesa 2800100100, code 5, 1234 votes
        "022015120102800100100 20000020010056",  # same mesa, code 2, 10056 votes
        "022015120102800100100 10000050000099",  # same mesa, code 5, 99 votes (aggregates)
        "022015120103100100100 10000290000088",  # mesa 3100100100, code 29, 88 votes
    ]


@pytest.fixture
def sample_dat_file(sample_dat_lines):
    """Write synthetic DAT records to a temporary file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".DAT", delete=False) as f:
        for line in sample_dat_lines:
            # Ensure exactly 36 characters
            f.write(line[:36] + "\n")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_party_yaml():
    """Return a temporary party YAML file with codes and transfers."""
    content = """
parties:
  PP: [5, 6]
  PSOE: [0]
  IU: [29]
transfers:
  IU:
    PSOE: 0.6
    PP: 0.2
  R:
    PSOE: 0.5
    PP: 0.3
  PP:
    PSOE: 0.2
  PSOE:
    PP: 0.1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_constituency_file():
    """Return a temporary constituency definition file."""
    content = """# Sample constituencies
madrid1:
2800100100
madrid2:
2800100100
2800100200
navarra1:
3100100100
madrid3:
2800100
-2800100200
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dat", delete=False) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)
