import tempfile
import unittest
from pathlib import Path

from calculation.calculation import calculate
from config.config_loader import load_config
from spectrum_io.spectrum_reader import read_required_frequencies


class CoreTests(unittest.TestCase):
    def test_calculation_clamps_negative_signal_power(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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

            result = calculate(
                sn_path,
                noise_path,
                load_config(config_path),
                0,
                "power",
            )
            self.assertEqual(len(result.points), 20)
            self.assertEqual(result.points[0].u_s, 0.0)
            self.assertAlmostEqual(result.points[0].q, 0.9487, places=4)
            self.assertTrue(result.points[0].is_violation)

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
        config = load_config(Path(__file__).parents[1] / "config.toml")
        self.assertEqual(config.frequency_constants.number_of_constants, 20)
        self.assertEqual(len(config.frequency_constants.f_i), 20)
        self.assertEqual(len(config.frequency_constants.delta_f_i), 20)
        self.assertEqual(len(config.norm_noise_by_line.symmetrical), 20)
        self.assertEqual(len(config.norm_noise_by_line.asymmetrical), 20)
        self.assertEqual(len(config.norm_noise_by_line.power), 20)


if __name__ == "__main__":
    unittest.main()
