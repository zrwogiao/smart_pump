import os
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pump.db"

RUNNING_FIELDS = (
    "timestamp",
    "device_id",
    "status",
    "stroke_rate",
    "motor_current",
    "load",
    "production",
    "power",
    "energy",
    "condition",
)
NUMERIC_RUNNING_FIELDS = (
    "stroke_rate",
    "motor_current",
    "load",
    "production",
    "power",
    "energy",
)


def get_db_path() -> Path:
    override = os.environ.get("SMART_PUMP_DB_PATH")
    return Path(override).expanduser() if override else DB_PATH


@contextmanager
def get_conn():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                location TEXT,
                status TEXT,
                install_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS running_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                status TEXT,
                stroke_rate REAL,
                motor_current REAL,
                load REAL,
                production REAL,
                power REAL,
                energy REAL,
                condition TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alarm (
                alarm_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                alarm_type TEXT,
                level TEXT,
                rule_id TEXT,
                message TEXT,
                suggestion TEXT,
                status TEXT DEFAULT '未处理',
                event_key TEXT,
                evidence_json TEXT,
                handled_by TEXT,
                handling_note TEXT,
                handled_at TEXT,
                updated_at TEXT
            )
        """)

        # 兼容 V1.0 已创建的数据库，不改动已有记录。
        alarm_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(alarm)").fetchall()
        }
        if "event_key" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN event_key TEXT")
        if "evidence_json" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN evidence_json TEXT")
        if "handled_by" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN handled_by TEXT")
        if "handling_note" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN handling_note TEXT")
        if "handled_at" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN handled_at TEXT")
        if "updated_at" not in alarm_columns:
            conn.execute("ALTER TABLE alarm ADD COLUMN updated_at TEXT")

        # V1.0 只有“未处理/已处理”，新版统一为事件生命周期状态。
        conn.execute(
            "UPDATE alarm SET status = '已关闭' WHERE status = '已处理'"
        )

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_timestamp
            ON running_data(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alarm_timestamp
            ON alarm(timestamp)
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_event_key
            ON alarm(event_key)
            WHERE event_key IS NOT NULL
        """)


def ensure_demo_device():
    from core.config import DEVICE_ID, DEVICE_NAME, LOCATION

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO device
            (device_id, device_name, location, status, install_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (DEVICE_ID, DEVICE_NAME, LOCATION, "正常", "2026-11-11"),
        )


def update_device_status(status: str):
    from core.config import DEVICE_ID

    with get_conn() as conn:
        conn.execute(
            "UPDATE device SET status = ? WHERE device_id = ?",
            (status, DEVICE_ID),
        )


def validate_running_record(record: dict):
    missing = [field for field in RUNNING_FIELDS if field not in record]
    if missing:
        raise ValueError(f"运行数据缺少字段: {', '.join(missing)}")

    try:
        datetime.strptime(str(record["timestamp"]), "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError("timestamp 必须为 YYYY-MM-DD HH:MM:SS 格式") from exc

    for field in NUMERIC_RUNNING_FIELDS:
        try:
            value = float(record[field])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} 必须是数值") from exc
        if value < 0:
            raise ValueError(f"{field} 不能小于 0")


def insert_running(record: dict) -> int:
    validate_running_record(record)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO running_data
            (timestamp, device_id, status, stroke_rate, motor_current,
             load, production, power, energy, condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(record[field] for field in RUNNING_FIELDS),
        )
        conn.execute(
            "UPDATE device SET status = ? WHERE device_id = ?",
            (record["status"], record["device_id"]),
        )
        return int(cursor.lastrowid)


def insert_alarm(
    result: dict,
    device_id: str,
    timestamp: str,
    event_key: str | None = None,
) -> bool:
    if not result.get("has_alarm"):
        return False

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO alarm
            (timestamp, device_id, alarm_type, level, rule_id,
             message, suggestion, status, event_key, evidence_json,
             updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '未处理', ?, ?, ?)
            """,
            (
                timestamp,
                device_id,
                result["alarm_type"],
                result["level"],
                result["rule_id"],
                result["message"],
                result["suggestion"],
                event_key,
                json.dumps(
                    result.get("evidence", []),
                    ensure_ascii=False,
                ),
                timestamp,
            ),
        )
        return cursor.rowcount > 0


def query_running(
    limit: int = 100,
    *,
    ascending: bool = False,
    condition: str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> pd.DataFrame:
    if limit <= 0:
        raise ValueError("limit 必须大于 0")

    clauses = []
    params: list[object] = []
    if condition:
        clauses.append("condition = ?")
        params.append(condition)
    if start_date:
        clauses.append("substr(timestamp, 1, 10) >= ?")
        params.append(str(start_date))
    if end_date:
        clauses.append("substr(timestamp, 1, 10) <= ?")
        params.append(str(end_date))

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    with get_conn() as conn:
        if ascending:
            sql = f"""
                SELECT * FROM (
                    SELECT * FROM running_data
                    {where_sql}
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
            """
        else:
            sql = f"""
                SELECT * FROM running_data
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
            """
        return pd.read_sql_query(sql, conn, params=params)


def query_alarms(
    limit: int = 100,
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> pd.DataFrame:
    if limit <= 0:
        raise ValueError("limit 必须大于 0")

    clauses = []
    params: list[object] = []
    if start_date:
        clauses.append("substr(timestamp, 1, 10) >= ?")
        params.append(str(start_date))
    if end_date:
        clauses.append("substr(timestamp, 1, 10) <= ?")
        params.append(str(end_date))

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    with get_conn() as conn:
        return pd.read_sql_query(
            f"""
            SELECT * FROM alarm
            {where_sql}
            ORDER BY alarm_id DESC
            LIMIT ?
            """,
            conn,
            params=params,
        )


def query_device(device_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT device_id, device_name, location, status, install_date
            FROM device
            WHERE device_id = ?
            """,
            (device_id,),
        ).fetchone()
    if row is None:
        return None
    keys = ("device_id", "device_name", "location", "status", "install_date")
    return dict(zip(keys, row))


VALID_ALARM_STATUSES = {"未处理", "处理中", "已关闭"}


def update_alarm_status(
    alarm_id: int,
    status: str,
    *,
    handled_by: str | None = None,
    handling_note: str | None = None,
) -> bool:
    if status not in VALID_ALARM_STATUSES:
        raise ValueError(f"不支持的报警状态: {status}")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE alarm
            SET status = ?,
                handled_by = COALESCE(?, handled_by),
                handling_note = COALESCE(?, handling_note),
                handled_at = CASE
                    WHEN ? = '已关闭' THEN ?
                    ELSE handled_at
                END,
                updated_at = ?
            WHERE alarm_id = ?
            """,
            (
                status,
                handled_by,
                handling_note,
                status,
                timestamp,
                timestamp,
                alarm_id,
            ),
        )
        return cursor.rowcount > 0


def mark_alarm_processed(alarm_id: int) -> bool:
    return update_alarm_status(
        alarm_id,
        "已关闭",
        handled_by="系统用户",
        handling_note="已确认处理",
    )
