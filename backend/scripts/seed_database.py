"""Deprecated: use seed_db.py for deterministic local seeding."""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.seed_db import main  # type: ignore

if __name__ == "__main__":
    main()