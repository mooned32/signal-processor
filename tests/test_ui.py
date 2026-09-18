import sys
import tempfile
import unittest
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PyQt6.QtCore import QMimeData, QModelIndex, Qt, QUrl
from PyQt6.QtGui import QColor, QValidator
from PyQt6.QtWidgets import QApplication

from models import MeasurementPoint
from ui.file_drop_line_edit import extract_local_file
from ui.line_template_widget import LineTemplateWidget
from ui.main_window import DoubleValidator
from ui.table_model import MeasurementTableModel

_qapp: QApplication | None = None


def _get_qapp() -> QApplication:
    global _qapp
    if _qapp is None:
        existing = QApplication.instance()
        if isinstance(existing, QApplication):
            _qapp = existing
        else:
            empty_args: list[str] = []
            _qapp = QApplication(empty_args)
    return _qapp


class FakeMimeData(QMimeData):
    def __init__(self, urls: list[QUrl] | None = None) -> None:
        super().__init__()
        self._urls: list[QUrl] = [] if urls is None else urls

    @override
    def hasUrls(self) -> bool:
        return bool(self._urls)

    @override
    def urls(self) -> list[QUrl]:
        return list(self._urls)


class UITests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        _ = _get_qapp()

    def test_extract_local_file_success(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            path = Path(tmp.name).resolve()
            mime = FakeMimeData([QUrl.fromLocalFile(str(path))])
            self.assertEqual(extract_local_file(mime), path)

    def test_extract_local_file_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir).resolve()
            mime = FakeMimeData([QUrl.fromLocalFile(str(path))])
            self.assertIsNone(extract_local_file(mime))

    def test_extract_local_file_rejects_multiple_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = Path(tmp_dir) / "1.txt"
            f2 = Path(tmp_dir) / "2.txt"
            f1.write_text("a", encoding="utf-8")
            f2.write_text("b", encoding="utf-8")
            mime = FakeMimeData([QUrl.fromLocalFile(str(f1)), QUrl.fromLocalFile(str(f2))])
            self.assertIsNone(extract_local_file(mime))

    def test_double_validator_locale_comma_and_dot(self) -> None:
        validator = DoubleValidator(0.0, 1000.0, 4)
        state_dot, _, _ = validator.validate("50.25", 0)
        state_comma, _, _ = validator.validate("50,25", 0)
        self.assertEqual(state_dot, QValidator.State.Acceptable)
        self.assertEqual(state_comma, QValidator.State.Acceptable)

    def test_table_model_row_and_column_counts(self) -> None:
        model = MeasurementTableModel()
        self.assertEqual(model.columnCount(), 0)
        self.assertEqual(model.rowCount(), 0)

        points = [
            MeasurementPoint(
                index=1,
                delta_f=500.0,
                f=500.0,
                u_sn=2.0,
                u_n=1.0,
                u_s=1.7321,
                q=1.7321,
                is_violation=True,
                r_i=None,
            )
        ]
        model.update_data(points, "voltage")
        self.assertEqual(model.columnCount(), 7)
        self.assertEqual(model.rowCount(), 1)
        self.assertEqual(model.headerData(3, Qt.Orientation.Horizontal), "U_сш")

        color_item = model.data(
            model.index(0, 6, QModelIndex()), int(Qt.ItemDataRole.BackgroundRole)
        )
        self.assertEqual(color_item, QColor("#FEE2E2"))

        model.clear()
        self.assertEqual(model.columnCount(), 0)
        self.assertEqual(model.rowCount(), 0)

    def test_line_template_widget_lifecycle(self) -> None:
        widget = LineTemplateWidget()
        widget.set_template("ЛВС {} - {}")
        self.assertFalse(widget.is_valid())

        widget.full_name()
        widget.clear_inputs()

    # -------------------------------------------------------------------------
    # Негативные тесты: валидация интерфейса и некорректные шаблоны
    # -------------------------------------------------------------------------

    def test_double_validator_rejects_out_of_range_maximum(self) -> None:
        """Validator must classify values exceeding upper bound as Invalid."""
        validator = DoubleValidator(0.0, 100.0, 2)
        state, _, _ = validator.validate("9999.99", 0)
        self.assertEqual(state, QValidator.State.Invalid)

    def test_line_template_widget_rejects_unbalanced_braces(self) -> None:
        """Widget must reject unbalanced brace syntax in line templates."""
        widget = LineTemplateWidget()
        widget.set_template("Line {param")
        self.assertFalse(widget.is_valid())


if __name__ == "__main__":
    unittest.main()
