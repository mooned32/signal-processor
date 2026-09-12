import sqlite3
from pathlib import Path

from calculation.models import CalculationResult, LineType


def init_database(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
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
            """
        )
        connection.commit()


def save_measurement(
    db_path: Path,
    device_name: str,
    category: int,
    line_number: int,
    line_name: str,
    line_type: LineType,
    operation_mode: str,
    measurement_type: int,
    resistance: float | None,
    result: CalculationResult,
) -> int:
    init_database(db_path)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
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
                resistance,
                int(result.has_violations),
            ),
        )
        measurement_id = cursor.lastrowid
        if measurement_id is None:
            raise RuntimeError("Не удалось получить идентификатор созданной записи.")

        connection.executemany(
            """
            INSERT INTO measurement_points (
                measurement_id, point_index, delta_f, f, u_sn, u_n, u_s, q, is_violation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    measurement_id,
                    point.index,
                    point.delta_f,
                    point.f,
                    point.u_sn,
                    point.u_n,
                    point.u_s,
                    point.q,
                    int(point.is_violation),
                )
                for point in result.points
            ],
        )
        connection.commit()
        return int(measurement_id)
