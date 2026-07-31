"""
PlaceholderPicker — a horizontal row of clickable chips that insert
{ColumnName} placeholders at the cursor position of a target QTextEdit/QPlainTextEdit.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
)


class PlaceholderPicker(QWidget):
    """
    Emits ``placeholder_clicked(str)`` when a chip is pressed.
    Call ``set_placeholders(headers)`` whenever the column list changes.
    """
    placeholder_clicked: Signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        lbl = QLabel("Insert:")
        lbl.setStyleSheet("color:#6B6F76; font-size:12px;")
        outer.addWidget(lbl)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._scroll.setFixedHeight(36)

        self._chip_container = QWidget()
        self._chip_layout = QHBoxLayout(self._chip_container)
        self._chip_layout.setContentsMargins(0, 0, 8, 0)
        self._chip_layout.setSpacing(6)
        self._chip_layout.addStretch()

        self._scroll.setWidget(self._chip_container)
        self._scroll.setWidgetResizable(True)
        outer.addWidget(self._scroll)

    def set_placeholders(self, headers: list) -> None:
        # Clear existing chips
        while self._chip_layout.count() > 1:   # keep the stretch at end
            item = self._chip_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for header in headers:
            btn = QPushButton(f"{{{header}}}")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #EEF2FF;
                    color: #1B2A4A;
                    border: 1px solid #C9A227;
                    border-radius: 14px;
                    padding: 0 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #C9A227;
                    color: #FFFFFF;
                }
            """)
            token = f"{{{header}}}"
            btn.clicked.connect(lambda checked=False, t=token: self.placeholder_clicked.emit(t))
            self._chip_layout.insertWidget(self._chip_layout.count() - 1, btn)


# Fix missing Qt import
from PySide6.QtCore import Qt
