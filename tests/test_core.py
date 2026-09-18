import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Protocol, cast, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PyQt6.QtCore import QMimeData, Qt, QUrl

from calculation import (
    calculate,
    calculate_intermediate_u,
    calculate_q,
    calculate_w,
)
from config_loader import load_config
from database import init_database, save_measurement
from error import (
    CalculationError,
    ConfigNotFoundError,
    ConfigValidationError,
    SpectrumMissingFrequencyError,
    SpectrumNotFoundError,
)
from spectrum_reader import read_required_frequencies
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
k_i = [0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1]
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
            self.assertEqual(result.points[0].q, 0.0)
            self.assertFalse(result.points[0].is_violation)
            self.assertEqual(result.measurement_type, "voltage")
            self.assertIsNone(result.w)
            self.assertIsNone(result.points[0].r_i)

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

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=None)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=0.0)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, noise_path, config, 0, "power", "voltage", resistance=-10.0)

    def test_unified_q_and_w_interfaces(self) -> None:
        u_val = calculate_intermediate_u(1.12, "symmetrical")
        self.assertEqual(u_val, 1.12)

        q_v = calculate_q(
            signal_level=2.24,
            intermediate_u=u_val,
            measurement_type="voltage",
            resistance=50.0,
        )
        self.assertAlmostEqual(q_v, 2.0, places=4)

        q_i = calculate_q(
            signal_level=2.0,
            intermediate_u=u_val,
            measurement_type="current",
            resistance=50.0,
        )
        self.assertAlmostEqual(q_i, (2.0 * 50.0) / 1.12, places=4)

        w = calculate_w(15.5)
        self.assertEqual(w, 15.5)

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

    def test_parser_raises_on_missing_file_and_frequencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            non_existent = Path(tmp) / "does_not_exist.txt"
            with self.assertRaises(SpectrumNotFoundError):
                _ = read_required_frequencies(non_existent, list(range(1, 21)))

            incomplete = Path(tmp) / "incomplete.txt"
            incomplete.write_text("1\t10.0\n2\t20.0\n", encoding="utf-8")
            with self.assertRaises(SpectrumMissingFrequencyError) as context:
                _ = read_required_frequencies(incomplete, list(range(1, 21)))
            self.assertEqual(context.exception.filename, "incomplete.txt")
            self.assertIn(3, context.exception.missing_frequencies)

    def test_config_loader_validations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_cfg = Path(tmp) / "absent.toml"
            with self.assertRaises(ConfigNotFoundError):
                _ = load_config(missing_cfg)

            invalid_syntax = Path(tmp) / "syntax_error.toml"
            invalid_syntax.write_text("key = [broken", encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(invalid_syntax)

            bad_structure = Path(tmp) / "bad_structure.toml"
            bad_structure.write_text("frequency_constants = 123\n", encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(bad_structure)

    def test_config_contains_expected_frequency_count(self) -> None:
        config = load_config(Path(__file__).resolve().parent.parent / "config.toml")
        count = config.frequency_constants.number_of_constants
        self.assertGreater(count, 0)
        self.assertEqual(len(config.frequency_constants.f_i), count)
        self.assertEqual(len(config.frequency_constants.delta_f_i), count)
        self.assertEqual(len(config.frequency_constants.k_i), count)
        self.assertEqual(len(config.frequency_constants.delta_a_i), count)
        self.assertEqual(len(config.norm_noise_by_line.symmetrical), count)
        self.assertEqual(len(config.norm_noise_by_line.asymmetrical), count)
        self.assertEqual(len(config.norm_noise_by_line.power), count)

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
                measurement_type="Напряжение",
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
