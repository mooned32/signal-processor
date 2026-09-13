import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PyQt6.QtCore import Qt

from calculation.calculation import calculate, calculate_current, calculate_voltage
from calculation.calculator_current import calculate_current_q
from calculation.calculator_voltage import calculate_voltage_q
from config.config_loader import load_config
from spectrum_io.spectrum_reader import read_required_frequencies
from ui.table_model import MeasurementTableModel


class CoreTests(unittest.TestCase):
    def _create_test_config_and_spectrums(self, root: Path) -> tuple[Path, Path, Path]:
        config_path = root / "config.toml"
        config_path.write_text(
            """
[frequency_constants]
number_of_constants = 20
f_i = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
delta_f_i = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
delta_a_i = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

[norm_params_by_category]
delta_stn = [0.12]
w_n = [0.12]

[norm_noise_by_line.symmetrical]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
[norm_noise_by_line.asymmetrical]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
[norm_noise_by_line.power]
values = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

[line.symmetrical]
names = ["ЛВС {} - {}"]
[line.asymmetrical]
names = ["Антенный кабель"]
[line.power]
names = ["Электропитание ({})", "Заземление"]

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
            )
            self.assertEqual(len(result.points), 20)
            self.assertEqual(result.points[0].u_s, 0.0)
            self.assertAlmostEqual(result.points[0].q, 0.9487, places=4)
            self.assertTrue(result.points[0].is_violation)
            self.assertEqual(result.measurement_type, "voltage")

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

            res_voltage = calculate_voltage(sn_path, noise_path, config, 0, "power")
            self.assertEqual(res_voltage.measurement_type, "voltage")

    def test_table_model_columns_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path, sn_path, noise_path = self._create_test_config_and_spectrums(root)
            config = load_config(config_path)

            model = MeasurementTableModel()
            # 1. At startup: no columns
            self.assertEqual(model.columnCount(), 0)

            # 2. Voltage calculation shows U_* columns
            res_v = calculate(sn_path, noise_path, config, 0, "power", "voltage")
            model.update_data(res_v.points, res_v.measurement_type)
            self.assertEqual(model.columnCount(), 7)
            self.assertEqual(model.headerData(3, Qt.Orientation.Horizontal), "U_сш")

            # 3. Current calculation shows I_* columns
            res_i = calculate(sn_path, noise_path, config, 0, "power", "current")
            model.update_data(res_i.points, res_i.measurement_type)
            self.assertEqual(model.columnCount(), 7)
            self.assertEqual(model.headerData(3, Qt.Orientation.Horizontal), "I_сш")

            # 4. Cleared model shows 0 columns
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


if __name__ == "__main__":
    unittest.main()
