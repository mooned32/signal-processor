import sqlite3
from pathlib import Path

from .models import LineType, MeasurementPoint


def init_database(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                category INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                line_name TEXT NOT NULL,
                line_type TEXT NOT NULL,
                operation_mode TEXT NOT NULL,
                measurement_type INTEGER NOT NULL,
                parameter_r REAL,
                has_violations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ = cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurement_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER NOT NULL,
                point_index INTEGER NOT NULL,
                delta_f REAL NOT NULL,
                f REAL NOT NULL,
                u_sn REAL NOT NULL,
                u_n REAL NOT NULL,
                u_s REAL NOT NULL,
                q REAL NOT NULL,
                is_violation INTEGER NOT NULL,
                FOREIGN KEY (measurement_id) REFERENCES measurements(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def save_measurement_to_db(
    db_path: Path,
    device_name: str,
    category: int,
    line_number: int,
    line_name: str,
    line_type: LineType,
    operation_mode: str,
    measurement_type: int,
    parameter_r: float | None,
    has_violations: bool,
    points: list[MeasurementPoint],
) -> int:
    init_database(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        _ = cursor.execute(
            """
            INSERT INTO measurements (
                device_name, category, line_number, line_name, line_type,
                operation_mode, measurement_type, parameter_r, has_violations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_name,
                category,
                line_number,
                line_name,
                line_type,
                operation_mode,
                measurement_type,
                parameter_r,
                1 if has_violations else 0,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Не удалось получить идентификатор созданной записи.")
        measurement_id: int = cursor.lastrowid

        rows_to_insert = [
            (
                measurement_id,
                p.index,
                p.delta_f,
                p.f,
                p.u_sn,
                p.u_n,
                p.u_s,
                p.q,
                1 if p.is_violation else 0,
            )
            for p in points
        ]

        _ = cursor.executemany(
            """
            INSERT INTO measurement_points (
                measurement_id, point_index, delta_f, f, u_sn, u_n, u_s, q, is_violation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()
        return measurement_id
