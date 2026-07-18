"""Golden PNG comparison tests for generated maps."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops


PROJECT_ROOT = Path(__file__).parent.parent
GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _generate_png(year):
    """Generate the PNG for a year by invoking run.py."""
    result = subprocess.run(
        ["python3", "run.py", "--year", year],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return OUTPUT_DIR / f"mapa{year}.png"


@pytest.fixture(scope="module")
def ensure_golden_dir():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.slow
@pytest.mark.parametrize("year", ["2008", "2011", "2015", "2016", "2019a", "2019b"])
def test_map_png_matches_golden(ensure_golden_dir, regenerate_golden, year):
    """Compare generated map PNG against the stored golden image."""
    generated = _generate_png(year)
    assert generated.exists(), f"Expected output file not generated: {generated}"

    golden = GOLDEN_DIR / f"mapa{year}.png"

    if regenerate_golden:
        # When regenerating, just ensure the output was generated. The actual
        # copy to golden/ happens in pytest_sessionfinish.
        return

    if not golden.exists():
        pytest.fail(
            f"Golden file missing for {year}: {golden}. "
            "Run pytest with --regenerate-golden to create it."
        )

    with Image.open(generated) as gen_img, Image.open(golden) as gold_img:
        assert gen_img.size == gold_img.size, (
            f"{year}: size mismatch {gen_img.size} vs {gold_img.size}"
        )
        assert gen_img.mode == gold_img.mode, (
            f"{year}: mode mismatch {gen_img.mode} vs {gold_img.mode}"
        )

        # Pixel-by-pixel comparison
        bbox = ImageChops.difference(gen_img, gold_img).getbbox()
        assert bbox is None, (
            f"{year}: generated PNG differs from golden (bounding box: {bbox})"
        )


@pytest.mark.slow
@pytest.mark.parametrize("year", ["2008", "2011", "2015", "2016", "2019a", "2019b"])
def test_map_png_exists_and_is_valid_size(ensure_golden_dir, year):
    """Smoke test: PNG is generated and has reasonable dimensions."""
    generated = _generate_png(year)
    assert generated.exists()

    with Image.open(generated) as img:
        assert img.format == "PNG"
        assert img.width > 1000
        assert img.height > 800
