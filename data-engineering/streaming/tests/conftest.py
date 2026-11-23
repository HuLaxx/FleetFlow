import os
import sys
from pathlib import Path

import pytest

# Make `import streaming` work when pytest runs from the repo root or data-engineering/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from streaming.gps_structured_stream import spark_session  # noqa: E402

KAFKA = os.getenv("KAFKA_BOOTSTRAP")


@pytest.fixture(scope="session")
def spark():
    session = spark_session("fleetflow-gps-stream-tests", kafka=bool(KAFKA))
    yield session
    session.stop()
