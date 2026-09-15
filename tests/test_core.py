import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Protocol, cast, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PyQt6.QtCore import QMimeData, Qt, QUrl

from calculation.calculation import calculate, calculate_current, calculate_voltage
from calculation.calculator_current import calculate_current_q
from calculation.calculator_voltage import calculate_voltage_q
from config.config_loader import load_config
from database.database import init_database, save_measurement
from spectrum_io.spectrum_reader import read_required_frequencies
from ui.file_drop_line_edit import extract_local_file
from ui.table_model import MeasurementTableModel


class TypedCursor(Protocol):
    """Protocol to isolate untyped sqlite3 cursor methods from reportAny."""

    def execute(self, sql: str, parameters: tuple[object, ...], /) -> "TypedCursor": ...
    def fetchone(self) -> tuple[int, ...] | None: ...


class FakeMimeData(QMimeData):
    """Type-safe MIME data test double without untyped method signatures."""

    def __init__(self, urls: list[QUrl] | None = None) -> None:
        super().__init__()
        self._urls: list[QUrl] = [] if urls is None else urls

    @override
    def hasUrls(self) -> bool:
        return bool(self._urls)

    @override
    def urls(self) -> list[QUrl]:
        return list(self._urls)


class CoreTests(unittest.TestCase):
    def _create_test_config_and_spectrums(
        self, root: Path, delta_stn: float = 0.12, w_n: float = 0.12
    ) -> tuple[Path, Path, Path]:
        config_path = root / "config.toml"
        config_path.write_text(
            f"""
[frequency_constants]
number_of_constants = 20
f_i = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
delta_f_i = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
delta_a_i = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

[norm_params_by_category]
delta_stn = [{delta_stn}]
w_n = [{w_n}]

[norm_noise_by_line.symmetrical]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
[norm_noise_by_line.asymmetrical]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
[norm_noise_by_line.power]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

[line.symmetrical]
names = ["ЛВС {{}} - {{}}"]
[line.asymmetrical]
names = ["Антенный кабель"]
[line.power]
names = ["Электропитание ({{}})", "Заземление"]

[operation_modes]
modes = ["ХХ", "ДР", "РР"]

[report_fields]
ACT_NUMBER = "Номер акта"
DATE = "Дата измерения"
OPERATOR = "ФИО оператора"
OBJECT_NAME = "Наименование объекта"
""".strip(),
            encoding="utf-8",
        )
        sn_path = root / "signal_noise.txt"
        noise_path = root / "noise.txt"
        sn_path.write_text("\n".join(f"{i}\t1.0" for i in range(1, 21)), encoding="utf-8")
        noise_path.write_text("\n".join(f"{i}\t2.0" for i in range(1, 21)), encoding="utf-8")
        return config_path, sn_path, noise_path

    def test_calculation_clamps_negative_signal_power(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(root)

            result = calculate(
                sn_path,
                noise_path,
                load_config(config_path),
                0,
                "power",
                "voltage",
                resistance=50.0,
            )
            self.assertEqual(len(result.points), 20)
            self.assertEqual(result.points[0].u_s, 0.0)
            self.assertAlmostEqual(result.points[0].q, 0.9487, places=4)
            self.assertTrue(result.points[0].is_violation)
            self.assertEqual(result.measurement_type, "voltage")
            self.assertIsNotNone(result.w)
            self.assertIsNotNone(result.points[0].r_i)

    def test_calculation_without_violations_skips_w_and_r_i(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(
                root, delta_stn=100.0, w_n=1.0
            )

            result = calculate(
                sn_path,
                noise_path,
                load_config(config_path),
                0,
                "power",
                "voltage",
                resistance=50.0,
            )
            self.assertFalse(result.has_violations)
            self.assertIsNone(result.w)
            self.assertIsNone(result.w_n)
            self.assertIsNone(result.is_w_violation)
            self.assertIsNone(result.points[0].r_i)

    def test_calculation_requires_positive_resistance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(root)
            config = load_config(config_path)

            with self.assertRaises(ValueError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=None)

            with self.assertRaises(ValueError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=0.0)

            with self.assertRaises(ValueError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=-10.0)

    def test_calculation_separate_pipelines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(root)
            config = load_config(config_path)

            q_v = calculate_voltage_q(
                u_s=1.5,
                frequency=500.0,
                delta_f=500.0,
                delta_a=1.12,
                norm_noise=1.12,
            )
            q_i = calculate_current_q(
                i_s=1.5,
                frequency=500.0,
                delta_f=500.0,
                delta_a=1.12,
                norm_noise=1.12,
                resistance=50.0,
            )
            self.assertIsInstance(q_v, float)
            self.assertIsInstance(q_i, float)

            res_current = calculate_current(
                sn_path,
                noise_path,
                config,
                0,
                "power",
                resistance=50.0,
            )
            self.assertEqual(res_current.measurement_type, "current")
            self.assertEqual(res_current.points[0].i_s, 0.0)

            res_voltage = calculate_voltage(
                sn_path,
                noise_path,
                config,
                0,
                "power",
                resistance=50.0,
            )
            self.assertEqual(res_voltage.measurement_type, "voltage")

    def test_table_model_columns_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(root)
            config = load_config(config_path)

            model = MeasurementTableModel()
            self.assertEqual(model.columnCount(), 0)

            res_v = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=50.0)
            model.update_data(res_v.points, res_v.measurement_type)
            self.assertEqual(model.columnCount(), 7)
            self.assertEqual(model.headerData(3, Qt.Orientation.Horizontal), "U_сш")

            res_i = calculate(sn_path, noise_path, config, 0, "power", "current", resistance=50.0)
            model.update_data(res_i.points, res_i.measurement_type)
            self.assertEqual(model.columnCount(), 7)
            self.assertEqual(model.headerData(3, Qt.Orientation.Horizontal), "I_сш")

            model.clear()
            self.assertEqual(model.columnCount(), 0)

    def test_parser_reads_only_requested_frequencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum.txt"
            path.write_text(
                "\n".join(f"{i}.0\t{i * 0.5}" for i in range(1, 32_001)),
                encoding="utf-8",
            )
            values = read_required_frequencies(path, [500, 12_345, 32_000] + list(range(1, 18)))
            self.assertEqual(values[0], 250.0)
            self.assertEqual(values[1], 6172.5)
            self.assertEqual(values[2], 16000.0)

    def test_config_contains_expected_frequency_count(self) -> None:
        config = load_config(Path(__file__).resolve().parent.parent / "config.toml")
        self.assertEqual(config.frequency_constants.number_of_constants, 20)
        self.assertEqual(len(config.frequency_constants.f_i), 20)
        self.assertEqual(len(config.frequency_constants.delta_f_i), 20)
        self.assertEqual(len(config.norm_noise_by_line.symmetrical), 20)
        self.assertEqual(len(config.norm_noise_by_line.asymmetrical), 20)
        self.assertEqual(len(config.norm_noise_by_line.power), 20)

    def test_extract_local_file(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp_path = Path(tmp.name).resolve()
            mime = FakeMimeData([QUrl.fromLocalFile(str(tmp_path))])
            extracted = extract_local_file(mime)
            self.assertEqual(extracted, tmp_path)

    def test_extract_local_file_rejects_missing_directory_or_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir).resolve()
            mime_dir = FakeMimeData([QUrl.fromLocalFile(str(dir_path))])
            self.assertIsNone(extract_local_file(mime_dir))

            self.assertIsNone(extract_local_file(FakeMimeData()))
            self.assertIsNone(extract_local_file(None))

            file_1 = dir_path / "1.txt"
            file_2 = dir_path / "2.txt"
            file_1.write_text("a", encoding="utf-8")
            file_2.write_text("b", encoding="utf-8")
            mime_multiple = FakeMimeData(
                [QUrl.fromLocalFile(str(file_1)), QUrl.fromLocalFile(str(file_2))]
            )
            self.assertIsNone(extract_local_file(mime_multiple))

    def test_database_persistence_and_cascading_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test_measurements.db"
            init_database(db_path)

            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(Path(tmp))
            config = load_config(config_path)
            res = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=50.0)

            measurement_id = save_measurement(
                db_path=db_path,
                device_name="Test Device",
                category=1,
                line_number=1,
                line_name="Line 1",
                line_type="power",
                operation_mode="XX",
                measurement_type=1,
                resistance=50.0,
                result=res,
            )
            self.assertGreater(measurement_id, 0)

            with sqlite3.connect(db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = cast(TypedCursor, conn.cursor())
                row = cursor.execute(
                    "SELECT COUNT(*) FROM measurement_points WHERE measurement_id = ?",
                    (measurement_id,),
                ).fetchone()
                if row is None:
                    self.fail("Expected count query result, got None")
                self.assertEqual(row[0], 20)

                _ = conn.execute("DELETE FROM measurements WHERE id = ?", (measurement_id,))
                conn.commit()

                row_after = cursor.execute(
                    "SELECT COUNT(*) FROM measurement_points WHERE measurement_id = ?",
                    (measurement_id,),
                ).fetchone()
                if row_after is None:
                    self.fail("Expected count query result after delete, got None")
                self.assertEqual(row_after[0], 0)


if __name__ == "__main__":
    unittest.main()
