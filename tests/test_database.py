import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Protocol, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from database import init_database, save_measurement
from error import DatabaseError
from models import CalculationResult, MeasurementPoint


class TypedCursor(Protocol):
    def execute(self, sql: str, parameters: tuple[object, ...], /) -> "TypedCursor": ...
    def fetchone(self) -> tuple[int, ...] | None: ...


def _create_mock_result(has_violations: bool = False) -> CalculationResult:
    points = [
        MeasurementPoint(
            index=i,
            delta_f=100.0,
            f=float(i * 500),
            u_sn=3.0,
            u_n=1.0,
            u_s=2.8284,
            q=2.8284,
            is_violation=has_violations,
            r_i=12.5 if has_violations else None,
        )
        for i in range(1, 21)
    ]
    return CalculationResult(
        points=points,
        has_violations=has_violations,
        measurement_type="voltage",
        w=25.0 if has_violations else None,
        w_n=1000.0 if has_violations else None,
        is_w_violation=False if has_violations else None,
    )


class DatabaseTests(unittest.TestCase):
    def test_init_database_creates_tables_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            init_database(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = cast(TypedCursor, conn.cursor())
                row_meas = cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='measurements'",
                    (),
                ).fetchone()
                if row_meas is None:
                    self.fail("Failed to query sqlite_master for measurements table")
                self.assertEqual(row_meas[0], 1)

                row_idx = cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='index' "
                    "AND name='idx_measurement_points_measurement_id'",
                    (),
                ).fetchone()
                if row_idx is None:
                    self.fail("Failed to query sqlite_master for index")
                self.assertEqual(row_idx[0], 1)

    def test_init_database_invalid_path_raises_database_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dir_path = Path(tmp)
            with self.assertRaises(DatabaseError):
                init_database(dir_path)

    def test_save_measurement_persists_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            init_database(db_path)
            res = _create_mock_result(has_violations=True)

            meas_id = save_measurement(
                db_path=db_path,
                device_name="TestDevice",
                category=1,
                line_number=1,
                line_name="Line 1",
                line_type="power",
                operation_mode="XX",
                measurement_type="voltage",
                resistance=50.0,
                result=res,
            )

            self.assertGreater(meas_id, 0)
            with sqlite3.connect(db_path) as conn:
                cursor = cast(TypedCursor, conn.cursor())
                row = cursor.execute(
                    "SELECT COUNT(*) FROM measurement_points WHERE measurement_id = ?",
                    (meas_id,),
                ).fetchone()
                if row is None:
                    self.fail("Failed to query measurement points count")
                self.assertEqual(row[0], 20)

    def test_save_measurement_cascading_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            init_database(db_path)
            res = _create_mock_result()

            meas_id = save_measurement(
                db_path=db_path,
                device_name="TestDevice",
                category=1,
                line_number=1,
                line_name="Line 1",
                line_type="power",
                operation_mode="XX",
                measurement_type="voltage",
                resistance=50.0,
                result=res,
            )

            with sqlite3.connect(db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                _ = conn.execute("DELETE FROM measurements WHERE id = ?", (meas_id,))
                conn.commit()

                cursor = cast(TypedCursor, conn.cursor())
                row = cursor.execute(
                    "SELECT COUNT(*) FROM measurement_points WHERE measurement_id = ?",
                    (meas_id,),
                ).fetchone()
                if row is None:
                    self.fail("Failed to query measurement points after delete")
                self.assertEqual(row[0], 0)

    # -------------------------------------------------------------------------
    # Негативные тесты: нарушение ограничений базы данных и границ допустимых значений
    # -------------------------------------------------------------------------

    def test_save_measurement_rejects_non_positive_line_number(self) -> None:
        """Database save must reject non-positive line numbers (<= 0)."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            init_database(db_path)
            res = _create_mock_result()
            with self.assertRaises(DatabaseError):
                _ = save_measurement(
                    db_path=db_path,
                    device_name="Device",
                    category=1,
                    line_number=0,
                    line_name="Line 1",
                    line_type="power",
                    operation_mode="XX",
                    measurement_type="voltage",
                    resistance=50.0,
                    result=res,
                )

    def test_save_measurement_rejects_invalid_category_index(self) -> None:
        """Database save must reject negative category values."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            init_database(db_path)
            res = _create_mock_result()
            with self.assertRaises(DatabaseError):
                _ = save_measurement(
                    db_path=db_path,
                    device_name="Device",
                    category=-1,
                    line_number=1,
                    line_name="Line 1",
                    line_type="power",
                    operation_mode="XX",
                    measurement_type="voltage",
                    resistance=50.0,
                    result=res,
                )


if __name__ == "__main__":
    unittest.main()
