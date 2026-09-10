from typing import override

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from core.models import MeasurementPoint


class TableGridDelegate(QStyledItemDelegate):
    """
    Делегат, принудительно отрисовывающий границы ячеек поверх любого фона.
    Предотвращает исчезновение линий сетки при закраске BackgroundRole.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @override
    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        super().paint(painter, option, index)
        if painter is None:
            return

        painter.save()
        painter.setPen(QColor("#CBD5E1"))
        r = option.rect
        # Четкие границы снизу и справа ячейки поверх фоновой заливки
        painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())
        painter.drawLine(r.right(), r.top(), r.right(), r.bottom())
        painter.restore()


class MeasurementTableModel(QAbstractTableModel):
    """Строго типизированная модель отображения точек измерения."""

    _points: list[MeasurementPoint]

    COLUMNS: list[str] = [
        "№",
        "Δf, Гц",
        "f, Гц",
        "U_сш",
        "U_ш",
        "U_с",
        "q",
    ]

    def __init__(self, points: list[MeasurementPoint] | None = None) -> None:
        super().__init__()
        self._points = points if points is not None else []

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._points)

    @override
    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self.COLUMNS)

    @override
    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid():
            return None

        point = self._points[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.BackgroundRole:
            if col == 6 and point.is_violation:
                return QColor("#FEE2E2")
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            match col:
                case 0:
                    return str(point.index)
                case 1:
                    is_int = point.delta_f.is_integer()
                    return f"{int(point.delta_f)}" if is_int else f"{point.delta_f:.2f}"
                case 2:
                    is_int = point.f.is_integer()
                    return f"{int(point.f)}" if is_int else f"{point.f:.2f}"
                case 3:
                    return f"{point.u_sn:.4f}"
                case 4:
                    return f"{point.u_n:.4f}"
                case 5:
                    return f"{point.u_s:.4f}"
                case 6:
                    return f"{point.q:.4f}"
                case _:
                    return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    @override
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    def update_data(self, points: list[MeasurementPoint]) -> None:
        self.beginResetModel()
        self._points = points
        self.endResetModel()
