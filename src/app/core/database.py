import sqlite3
from pathlib import Path
from typing import cast

import pandas as pd


def init_database(db_path: Path) -> None:
    """Инициализирует таблицы базы данных SQLite."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                category INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                line_name TEXT NOT NULL,
                line_type TEXT NOT NULL,
                operation_mode TEXT NOT NULL,
                measurement_type INTEGER NOT NULL, -- 1: Ток, 2: Напряжение
                parameter_r REAL,
                has_violations INTEGER NOT NULL,    -- 1 или 0
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
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
    line_type: str,
    operation_mode: str,
    measurement_type: int,
    parameter_r: float | None,
    has_violations: bool,
    df_points: pd.DataFrame,
    violations_mask: list[bool],
) -> int:
    """Сохраняет измерение линии и 20 расчетных точек в SQLite."""
    init_database(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
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
        measurement_id = cast(int, cursor.lastrowid)

        # Сохранение точек
        rows_to_insert: list[tuple[int, int, float, float, float, float, float, float, int]] = []
        for idx in range(len(df_points)):
            p_i = int(df_points["i"].iloc[idx])
            df_val = float(df_points["delta_f_i"].iloc[idx])
            f_val = float(df_points["f_i"].iloc[idx])
            u_sn = float(df_points["U_sn_i"].iloc[idx])
            u_n = float(df_points["U_n_i"].iloc[idx])
            u_s = float(df_points["U_s_i"].iloc[idx])
            q_val = float(df_points["q"].iloc[idx])
            is_bad = 1 if idx < len(violations_mask) and violations_mask[idx] else 0

            rows_to_insert.append(
                (
                    measurement_id,
                    p_i,
                    df_val,
                    f_val,
                    u_sn,
                    u_n,
                    u_s,
                    q_val,
                    is_bad,
                )
            )

        cursor.executemany(
            """
            INSERT INTO measurement_points (
                measurement_id, point_index, delta_f, f, u_sn, u_n, u_s, q, is_violation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )
        conn.commit()
        return measurement_id
