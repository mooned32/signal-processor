import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calculation import (
    calculate,
    calculate_intermediate_u,
    calculate_q,
    calculate_w,
)
from error import CalculationError
from models import (
    AppConfig,
    FrequencyConstantsConfig,
    LineConfig,
    NormNoiseByLineConfig,
    NormParamsConfig,
)


def _create_mock_config(
    count: int = 20,
    delta_stn: float = 2.0,
    w_n: float = 1000.0,
    f_i: list[float] | None = None,
) -> AppConfig:
    frequencies = [float(i) for i in range(1, count + 1)] if f_i is None else f_i
    return AppConfig(
        frequency_constants=FrequencyConstantsConfig(
            number_of_constants=count,
            f_i=frequencies,
            delta_f_i=[100.0] * count,
            k_i=[0.05] * count,
            delta_a_i=[1.5] * count,
        ),
        norm_params=NormParamsConfig(
            delta_stn=[delta_stn, delta_stn * 2, delta_stn * 3],
            w_n=[w_n, w_n * 2, w_n * 3],
        ),
        norm_noise_by_line=NormNoiseByLineConfig(
            symmetrical=[1.0] * count,
            asymmetrical=[1.0] * count,
            power=[1.0] * count,
        ),
        lines=LineConfig(
            symmetrical=["Line {}"],
            asymmetrical=["Antenna"],
            power=["Power ({})"],
        ),
        operation_modes=["XX", "DR", "RR"],
    )


def _create_spectrum_files(
    root: Path,
    count: int = 20,
    sn_val: float = 5.0,
    n_val: float = 3.0,
) -> tuple[Path, Path]:
    sn_path = root / "signal_noise.txt"
    n_path = root / "noise.txt"
    sn_path.write_text(
        "\n".join(f"{i}.0\t{sn_val:.4f}" for i in range(1, count + 1)),
        encoding="utf-8",
    )
    n_path.write_text(
        "\n".join(f"{i}.0\t{n_val:.4f}" for i in range(1, count + 1)),
        encoding="utf-8",
    )
    return sn_path, n_path


class CalculationTests(unittest.TestCase):
    def test_calculate_voltage_without_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root, sn_val=2.0, n_val=1.9)
            cfg = _create_mock_config(delta_stn=10.0)

            result = calculate(
                signal_noise_path=sn_path,
                noise_path=n_path,
                config=cfg,
                category_index=0,
                line_type="power",
                measurement_type="voltage",
                resistance=50.0,
            )

            self.assertFalse(result.has_violations)
            self.assertEqual(result.measurement_type, "voltage")
            self.assertIsNone(result.w)
            self.assertIsNone(result.w_n)
            self.assertIsNone(result.is_w_violation)
            self.assertEqual(len(result.points), 20)
            self.assertIsNone(result.points[0].r_i)

    def test_calculate_voltage_with_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root, sn_val=5.0, n_val=1.0)
            cfg = _create_mock_config(delta_stn=1.0, w_n=10.0)

            result = calculate(
                signal_noise_path=sn_path,
                noise_path=n_path,
                config=cfg,
                category_index=0,
                line_type="power",
                measurement_type="voltage",
                resistance=50.0,
            )

            self.assertTrue(result.has_violations)
            self.assertIsNotNone(result.w)
            self.assertIsNotNone(result.w_n)
            self.assertIsNotNone(result.is_w_violation)
            self.assertIsNotNone(result.points[0].r_i)

    def test_calculate_current_measurement_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root, sn_val=5.0, n_val=1.0)
            cfg = _create_mock_config(delta_stn=1000.0)

            result = calculate(
                signal_noise_path=sn_path,
                noise_path=n_path,
                config=cfg,
                category_index=0,
                line_type="symmetrical",
                measurement_type="current",
                resistance=50.0,
            )

            self.assertEqual(result.measurement_type, "current")
            self.assertEqual(result.points[0].q, 244.949)

    def test_calculate_clamps_negative_signal_power(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root, sn_val=1.0, n_val=2.0)
            cfg = _create_mock_config()

            result = calculate(
                signal_noise_path=sn_path,
                noise_path=n_path,
                config=cfg,
                category_index=0,
                line_type="power",
                measurement_type="voltage",
                resistance=50.0,
            )

            self.assertEqual(result.points[0].u_s, 0.0)
            self.assertEqual(result.points[0].q, 0.0)
            self.assertFalse(result.points[0].is_violation)

    def test_calculate_validates_resistance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root)
            cfg = _create_mock_config()

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, 0, "power", "voltage", resistance=None)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, 0, "power", "voltage", resistance=0.0)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, 0, "power", "voltage", resistance=-10.0)

    def test_calculate_validates_category_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root)
            cfg = _create_mock_config()

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, -1, "power", "voltage", resistance=50.0)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, 10, "power", "voltage", resistance=50.0)

    def test_calculate_validates_constants_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root)
            cfg = _create_mock_config(count=20, f_i=[100.0] * 19)

            with self.assertRaises(CalculationError):
                _ = calculate(sn_path, n_path, cfg, 0, "power", "voltage", resistance=50.0)

    def test_calculate_intermediate_u_all_line_types(self) -> None:
        for line_type in ("symmetrical", "asymmetrical", "power"):
            val = calculate_intermediate_u(
                resistance=50.0,
                delta_f=100.0,
                norm_noise=1.25,
                line_type=line_type,
            )
            self.assertEqual(val, 1.25)

    def test_calculate_w_identity(self) -> None:
        self.assertEqual(calculate_w(99.45), 99.45)

    # -------------------------------------------------------------------------
    # Негативные тесты: необработанные граничные условия и пределы расчёта
    # -------------------------------------------------------------------------

    def test_calculate_intermediate_u_zero_division_guard(self) -> None:
        with self.assertRaises(CalculationError):
            _ = calculate_q(
                signal_level=5.0,
                intermediate_u=0.0,
                measurement_type="voltage",
                resistance=50.0,
            )

    def test_calculate_rejects_negative_frequency_constant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path = root / "signal_noise.txt"
            n_path = root / "noise.txt"
            sn_path.write_text(
                "-100.0\t5.0\n" + "\n".join(f"{i}.0\t5.0" for i in range(2, 21)), encoding="utf-8"
            )
            n_path.write_text(
                "-100.0\t1.0\n" + "\n".join(f"{i}.0\t1.0" for i in range(2, 21)), encoding="utf-8"
            )

            cfg = _create_mock_config(
                delta_stn=100.0,
                f_i=[-100.0] + [float(i) for i in range(2, 21)],
            )
            with self.assertRaises(CalculationError):
                _ = calculate(
                    signal_noise_path=sn_path,
                    noise_path=n_path,
                    config=cfg,
                    category_index=0,
                    line_type="power",
                    measurement_type="voltage",
                    resistance=50.0,
                )

    def test_calculate_rejects_excessive_resistance_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sn_path, n_path = _create_spectrum_files(root)
            cfg = _create_mock_config()
            with self.assertRaises(CalculationError):
                _ = calculate(
                    signal_noise_path=sn_path,
                    noise_path=n_path,
                    config=cfg,
                    category_index=0,
                    line_type="power",
                    measurement_type="voltage",
                    resistance=1e12,
                )


if __name__ == "__main__":
    unittest.main()
