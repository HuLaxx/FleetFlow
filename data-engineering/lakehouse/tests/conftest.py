import sys
from datetime import date
from pathlib import Path

import pytest

# Make `import lakehouse` work when pytest runs from the repo root or data-engineering/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lakehouse.generate import generate  # noqa: E402


@pytest.fixture(scope="session")
def lake(tmp_path_factory):
    root = tmp_path_factory.mktemp("lake")
    summary = generate(root, date(2026, 1, 1), days=3, orders_per_day=500, seed=7, defect_rate=0.02)
    return root, summary
