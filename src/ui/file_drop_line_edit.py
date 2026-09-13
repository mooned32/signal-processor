from collections.abc import Callable
from pathlib import Path
from typing import override

from PyQt6.QtCore import QMimeData
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PyQt6.QtWidgets import QLineEdit, QWidget


def extract_local_file(mime_data: QMimeData | None) -> Path | None:
    """Extract a single local file path from MIME data."""
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
    """Read-only line edit that accepts single-file drag-and-drop operations."""

    def __init__(
        self,
        placeholder: str,
        on_file_dropped: Callable[[Path], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_file_dropped = on_file_dropped
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)

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
