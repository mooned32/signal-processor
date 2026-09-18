from collections.abc import Callable
from pathlib import Path
from typing import override

from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QResizeEvent,
)
from PyQt6.QtWidgets import QLineEdit, QWidget


def extract_local_file(mime_data: QMimeData | None) -> Path | None:
    if mime_data is None or not mime_data.hasUrls():
        return None
    urls = mime_data.urls()
    if len(urls) != 1:
        return None
    first_url = urls[0]
    if not first_url.isLocalFile():
        return None
    candidate = Path(first_url.toLocalFile())
    if not candidate.is_file():
        return None
    return candidate


class FileDropLineEdit(QLineEdit):
    def __init__(
        self,
        placeholder: str,
        on_file_dropped: Callable[[Path], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_file_dropped = on_file_dropped
        self._full_path = ""
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)

    def set_file_path(self, path: Path) -> None:
        self._full_path = str(path.resolve())
        self.setToolTip(self._full_path)
        self._update_display_text()

    def _update_display_text(self) -> None:
        if not self._full_path:
            self.setText("")
            return

        available_width = max(10, self.contentsRect().width() - 12)
        metrics = self.fontMetrics()
        elided = metrics.elidedText(
            self._full_path,
            Qt.TextElideMode.ElideMiddle,
            available_width,
        )
        self.setText(elided)
        self.setCursorPosition(0)

    @override
    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._update_display_text()

    @override
    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:
        if a0 is None:
            return
        if extract_local_file(a0.mimeData()) is not None:
            self.setStyleSheet("border: 2px dashed #2563EB;")
            a0.acceptProposedAction()
            return
        a0.ignore()

    @override
    def dragMoveEvent(self, e: QDragMoveEvent | None) -> None:
        if e is None:
            return
        if extract_local_file(e.mimeData()) is not None:
            e.acceptProposedAction()
            return
        e.ignore()

    @override
    def dragLeaveEvent(self, e: QDragLeaveEvent | None) -> None:
        self.setStyleSheet("")
        if e is not None:
            e.accept()

    @override
    def dropEvent(self, a0: QDropEvent | None) -> None:
        self.setStyleSheet("")
        if a0 is None:
            return
        file_path = extract_local_file(a0.mimeData())
        if file_path is not None:
            self._on_file_dropped(file_path)
            a0.acceptProposedAction()
            return
        a0.ignore()
