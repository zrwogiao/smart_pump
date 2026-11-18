import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "pump.db"
    monkeypatch.setenv("SMART_PUMP_DB_PATH", str(db_path))

    from core.database import ensure_demo_device, init_db

    init_db()
    ensure_demo_device()
    return db_path


@pytest.fixture
def make_record():
    def factory(**overrides):
        record = {
            "timestamp": "2026-11-12 10:00:00",
            "device_id": "PUMP-001",
            "status": "正常",
            "stroke_rate": 6.0,
            "motor_current": 32.0,
            "load": 55.0,
            "production": 18.5,
            "power": 10.2,
            "energy": 0.17,
            "condition": "normal",
        }
        record.update(overrides)
        return record

    return factory
