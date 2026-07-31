"""
ProgressTable — live-updating send-status table for Euler Mail.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView


class ProgressTable(QTableWidget):
    COLUMNS = ["#", "Recipient Email", "Status", "Details"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLUMNS), parent)

        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)

        self.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F7F8FA;
                gridline-color: #E2E5EA;
                border: 1px solid #E2E5EA;
                border-radius: 6px;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #1B2A4A;
                color: #FFFFFF;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-right: 1px solid #243853;
            }
            QTableWidget::item:selected {
                background: #EAF1FB;
                color: #1B2A4A;
            }
        """)

    def populate(self, recipients: list) -> None:
        """Set up the table with one row per recipient (all Pending)."""
        self.setRowCount(len(recipients))
        for i, r in enumerate(recipients):
            email = r.email if hasattr(r, "email") else r.get("email", "")
            self._set_row(i, email, "Pending", "")

    def update_row(self, index: int, email: str, status: str, detail: str) -> None:
        """Update a single row's status and detail columns."""
        if index >= self.rowCount():
            self.setRowCount(index + 1)
        self._set_row(index, email, status, detail)

        # Scroll to the active row
        item = self.item(index, 0)
        if item:
            self.scrollToItem(item)

    def _set_row(self, i: int, email: str, status: str, detail: str) -> None:
        num_item = QTableWidgetItem(str(i + 1))
        num_item.setTextAlignment(Qt.AlignCenter)

        email_item = QTableWidgetItem(email)
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignCenter)
        detail_item = QTableWidgetItem(detail)

        # Color code status
        if "✅" in status or status.lower() == "sent":
            status_item.setForeground(QColor("#2E7D32"))
        elif "❌" in status or "failed" in status.lower():
            status_item.setForeground(QColor("#B3261E"))
            detail_item.setForeground(QColor("#B3261E"))
        elif "sending" in status.lower():
            status_item.setForeground(QColor("#1B2A4A"))
        else:
            status_item.setForeground(QColor("#6B6F76"))

        self.setItem(i, 0, num_item)
        self.setItem(i, 1, email_item)
        self.setItem(i, 2, status_item)
        self.setItem(i, 3, detail_item)
