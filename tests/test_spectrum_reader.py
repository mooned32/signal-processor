import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from error import (
    CalculationError,
    SpectrumFormatError,
    SpectrumMissingFrequencyError,
    SpectrumNotFoundError,
)
from spectrum_reader import read_required_frequencies


class SpectrumReaderTests(unittest.TestCase):
    def test_read_frequencies_valid_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum.txt"
            path.write_text(
                "\n".join(f"{i}.0\t{i * 0.5:.2f}" for i in range(1, 1001)),
                encoding="utf-8",
            )
            results = read_required_frequencies(path, [10.0, 50.0, 100.0])
            self.assertEqual(results, [5.0, 25.0, 50.0])

    def test_read_frequencies_handles_comma_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum_comma.txt"
            path.write_text("100,0\t12,50\n200,0\t25,00\n", encoding="utf-8")
            results = read_required_frequencies(path, [100.0, 200.0])
            self.assertEqual(results, [12.5, 25.0])

    def test_read_frequencies_skips_comments_and_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum_comments.txt"
            content = (
                "# Header comment\n"
                "[Section header]\n"
                "(Auxiliary note)\n"
                "\n"
                "100.0\t1.5\n"
                "   \n"
                "200.0\t3.0\n"
            )
            path.write_text(content, encoding="utf-8")
            results = read_required_frequencies(path, [100.0, 200.0])
            self.assertEqual(results, [1.5, 3.0])

    def test_read_frequencies_skips_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spectrum_corrupt_lines.txt"
            content = "SINGLE_COLUMN\n100.0\tCORRUPT\n100.0\t4.5\n"
            path.write_text(content, encoding="utf-8")
            results = read_required_frequencies(path, [100.0])
            self.assertEqual(results, [4.5])

    def test_read_frequencies_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            non_existent = Path(tmp) / "missing.txt"
            with self.assertRaises(SpectrumNotFoundError):
                _ = read_required_frequencies(non_existent, [100.0])

    def test_read_frequencies_missing_frequencies_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "incomplete.txt"
            path.write_text("100.0\t1.0\n", encoding="utf-8")
            with self.assertRaises(SpectrumMissingFrequencyError) as ctx:
                _ = read_required_frequencies(path, [100.0, 200.0])
            self.assertEqual(ctx.exception.filename, "incomplete.txt")
            self.assertIn(200.0, ctx.exception.missing_frequencies)

    def test_read_frequencies_empty_request_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.txt"
            path.write_text("100.0\t1.0\n", encoding="utf-8")
            with self.assertRaises(CalculationError):
                _ = read_required_frequencies(path, [])

    # -------------------------------------------------------------------------
    # Негативные тесты: нарушение физических границ и повреждение данных
    # -------------------------------------------------------------------------

    def test_reader_rejects_negative_frequencies(self) -> None:
        """Spectrum file with negative frequency records must trigger SpectrumFormatError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "negative_f.txt"
            path.write_text("-500.0\t1.5\n", encoding="utf-8")
            with self.assertRaises(SpectrumFormatError):
                _ = read_required_frequencies(path, [-500.0])

    def test_reader_rejects_negative_voltage_levels(self) -> None:
        """Spectrum file with negative voltage amplitudes must trigger SpectrumFormatError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "negative_v.txt"
            path.write_text("500.0\t-2.5\n", encoding="utf-8")
            with self.assertRaises(SpectrumFormatError):
                _ = read_required_frequencies(path, [500.0])

    def test_reader_rejects_duplicate_conflicting_frequency_records(self) -> None:
        """Duplicate records for same frequency point must trigger SpectrumFormatError."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicates.txt"
            path.write_text("500.0\t1.0\n500.0\t9.0\n", encoding="utf-8")
            with self.assertRaises(SpectrumFormatError):
                _ = read_required_frequencies(path, [500.0])


if __name__ == "__main__":
    unittest.main()
