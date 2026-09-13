from typing import override

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt
from PyQt6.QtGui import QColor

from calculation.models import MeasurementKind, MeasurementPoint


class MeasurementTableModel(QAbstractTableModel):
    VOLTAGE_COLUMNS: tuple[str, ...] = ("№", "Δf, Гц", "f, Гц", "U_сш", "U_ш", "U_с", "q")
    CURRENT_COLUMNS: tuple[str, ...] = ("№", "Δf, Гц", "f, Гц", "I_сш", "I_ш", "I_с", "q")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._points: list[MeasurementPoint] = []
        self._columns: tuple[str, ...] = ()

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._points)

    @override
    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._columns)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._points):
            return None

        point = self._points[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.BackgroundRole:
            if column == 6 and point.is_violation:
                return QColor("#FEE2E2")
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            match column:
                case 0:
                    return str(point.index)
                case 1:
                    return (
                        str(int(point.delta_f))
                        if point.delta_f.is_integer()
                        else f"{point.delta_f:.2f}"
                    )
                case 2:
                    return str(int(point.f)) if point.f.is_integer() else f"{point.f:.2f}"
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
            if column == 0:
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
            if 0 <= section < len(self._columns):
                return self._columns[section]
        return None

    def update_data(
        self,
        points: list[MeasurementPoint],
        measurement_type: MeasurementKind | None = None,
    ) -> None:
        self.beginResetModel()
        self._points = list(points)
        if not self._points or measurement_type is None:
            self._columns = ()
        elif measurement_type == "voltage":
            self._columns = self.VOLTAGE_COLUMNS
        else:
            self._columns = self.CURRENT_COLUMNS
        self.endResetModel()

    def clear(self) -> None:
        self.update_data([], None)
