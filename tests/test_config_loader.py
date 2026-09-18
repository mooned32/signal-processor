import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config_loader import load_config
from error import ConfigNotFoundError, ConfigValidationError
from models import AppConfig


def _create_toml_content(
    num_constants: int = 1,
    f_i: str = "[500.0]",
    delta_f_i: str = "[100.0]",
    k_i: str = "[0.01]",
    delta_a_i: str = "[1.5]",
    delta_stn: str = "[2.0]",
    w_n: str = "[1000.0]",
    noise_sym: str = "[1.0]",
    noise_asym: str = "[1.0]",
    noise_power: str = "[1.0]",
    modes: str = '["XX", "DR"]',
) -> str:
    return f"""
[frequency_constants]
number_of_constants = {num_constants}
f_i = {f_i}
delta_f_i = {delta_f_i}
k_i = {k_i}
delta_a_i = {delta_a_i}

[norm_params_by_category]
delta_stn = {delta_stn}
w_n = {w_n}

[norm_noise_by_line.symmetrical]
values = {noise_sym}
[norm_noise_by_line.asymmetrical]
values = {noise_asym}
[norm_noise_by_line.power]
values = {noise_power}

[line.symmetrical]
names = ["Line {{}}"]
[line.asymmetrical]
names = ["Antenna"]
[line.power]
names = ["Power ({{}})"]

[operation_modes]
modes = {modes}
""".strip()


class ConfigLoaderTests(unittest.TestCase):
    def test_load_config_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.toml"
            cfg_path.write_text(_create_toml_content(), encoding="utf-8")
            config = load_config(cfg_path)
            self.assertIsInstance(config, AppConfig)
            self.assertEqual(config.frequency_constants.number_of_constants, 1)

    def test_load_config_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.toml"
            with self.assertRaises(ConfigNotFoundError):
                _ = load_config(missing)

    def test_load_config_syntax_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "invalid.toml"
            cfg_path.write_text("broken = [unclosed", encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_load_config_invalid_number_of_constants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "invalid_count.toml"
            cfg_path.write_text(
                _create_toml_content(num_constants=0),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_load_config_constants_length_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "mismatch.toml"
            cfg_path.write_text(
                _create_toml_content(num_constants=2, f_i="[500.0]"),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_load_config_non_numeric_float_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "non_numeric.toml"
            cfg_path.write_text(
                _create_toml_content(f_i='["text"]'),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_load_config_line_noise_length_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "noise_mismatch.toml"
            cfg_path.write_text(
                _create_toml_content(num_constants=1, noise_sym="[1.0, 2.0]"),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_project_root_config_is_valid(self) -> None:
        root_cfg = Path(__file__).resolve().parent.parent / "config.toml"
        config = load_config(root_cfg)
        count = config.frequency_constants.number_of_constants
        self.assertEqual(count, 20)
        self.assertEqual(len(config.frequency_constants.f_i), count)

    # -------------------------------------------------------------------------
    # Негативные тесты: необработанное повреждение конфигурации и недопустимые диапазоны
    # -------------------------------------------------------------------------

    def test_config_rejects_negative_frequencies(self) -> None:
        """Config loader must reject negative central frequencies in f_i."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "neg_f.toml"
            cfg_path.write_text(_create_toml_content(f_i="[-500.0]"), encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_config_rejects_negative_norm_noise(self) -> None:
        """Config loader must reject negative baseline noise in norm_noise_by_line."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "neg_noise.toml"
            cfg_path.write_text(_create_toml_content(noise_sym="[-1.5]"), encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)

    def test_config_rejects_empty_operation_modes(self) -> None:
        """Config loader must reject empty operation mode lists."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "empty_modes.toml"
            cfg_path.write_text(_create_toml_content(modes="[]"), encoding="utf-8")
            with self.assertRaises(ConfigValidationError):
                _ = load_config(cfg_path)


if __name__ == "__main__":
    unittest.main()
