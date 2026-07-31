"""
Step 1 — Load Recipient Excel Sheet.
File picker → parse headers/rows → preview table → validation panel.
"""
import logging
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QScrollArea,
    QSizePolicy, QTextEdit,
)
from euler_mail.data.excel_loader import load_excel, get_mail_column
from euler_mail.data.models import ValidationError

logger = logging.getLogger(__name__)

MAX_PREVIEW_ROWS = 10


class StepLoadExcel(QWidget):
    """
    Signals:
        excel_loaded(headers: list, rows: list, mail_column: str)
    """
    excel_loaded = Signal(list, list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers = []
        self._rows = []
        self._mail_col = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # ── Title ──────────────────────────────────────────────────────────
        title = QLabel("Load Recipient List")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1B2A4A;")
        layout.addWidget(title)

        desc = QLabel(
            "Select an Excel file (.xlsx or .xls). The first row must contain column headers. "
            "One column must be named <b>mail</b> or <b>email</b> — this is the recipient address."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#4A5568; font-size:13px; line-height:1.5;")
        layout.addWidget(desc)

        # ── File picker card ───────────────────────────────────────────────
        pick_card = QFrame()
        pick_card.setStyleSheet("""
            QFrame { background:#F7F8FA; border:2px dashed #CBD5E0;
                     border-radius:10px; }
        """)
        pick_layout = QVBoxLayout(pick_card)
        pick_layout.setSpacing(10)
        pick_layout.setContentsMargins(24, 20, 24, 20)
        pick_layout.setAlignment(Qt.AlignCenter)

        file_icon = QLabel("📊")
        file_icon.setAlignment(Qt.AlignCenter)
        file_icon.setStyleSheet("font-size:36px; border:none;")
        pick_layout.addWidget(file_icon)

        self._file_lbl = QLabel("No file selected")
        self._file_lbl.setAlignment(Qt.AlignCenter)
        self._file_lbl.setStyleSheet("color:#6B6F76; font-size:13px; border:none;")
        pick_layout.addWidget(self._file_lbl)

        self._btn_pick = QPushButton("Browse for Excel File…")
        self._btn_pick.setFixedHeight(40)
        self._btn_pick.setCursor(Qt.PointingHandCursor)
        self._btn_pick.setStyleSheet("""
            QPushButton {
                background:#1B2A4A; color:#FFF; border:none; border-radius:20px;
                font-size:13px; font-weight:600; padding:0 20px;
            }
            QPushButton:hover { background:#243853; }
        """)
        self._btn_pick.clicked.connect(self._pick_file)
        pick_layout.addWidget(self._btn_pick, alignment=Qt.AlignCenter)

        layout.addWidget(pick_card)

        # ── Validation panel ───────────────────────────────────────────────
        self._val_frame = QFrame()
        self._val_frame.setVisible(False)
        val_layout = QVBoxLayout(self._val_frame)
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_layout.setSpacing(4)

        self._val_title = QLabel()
        self._val_title.setStyleSheet("font-size:13px; font-weight:600;")
        val_layout.addWidget(self._val_title)

        self._val_text = QTextEdit()
        self._val_text.setReadOnly(True)
        self._val_text.setMaximumHeight(80)
        self._val_text.setStyleSheet("""
            QTextEdit { background:#FCEEED; border:1px solid #EFC9C6;
                        border-radius:6px; color:#B3261E; font-size:12px; padding:6px; }
        """)
        val_layout.addWidget(self._val_text)
        layout.addWidget(self._val_frame)

        # ── Column chips ───────────────────────────────────────────────────
        self._chip_frame = QFrame()
        self._chip_frame.setVisible(False)
        chip_layout = QVBoxLayout(self._chip_frame)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(8)

        chip_title = QLabel("Detected Columns:")
        chip_title.setStyleSheet("color:#1B2A4A; font-size:13px; font-weight:600;")
        chip_layout.addWidget(chip_title)

        self._chip_scroll = QScrollArea()
        self._chip_scroll.setFrameShape(QScrollArea.NoFrame)
        self._chip_scroll.setFixedHeight(44)
        self._chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chip_container = QWidget()
        self._chip_row = QHBoxLayout(self._chip_container)
        self._chip_row.setContentsMargins(0, 4, 8, 4)
        self._chip_row.setSpacing(6)
        self._chip_row.addStretch()
        self._chip_scroll.setWidget(self._chip_container)
        self._chip_scroll.setWidgetResizable(True)
        chip_layout.addWidget(self._chip_scroll)
        layout.addWidget(self._chip_frame)

        # ── Preview table ──────────────────────────────────────────────────
        self._preview_title = QLabel()
        self._preview_title.setStyleSheet("color:#1B2A4A; font-size:13px; font-weight:600;")
        self._preview_title.setVisible(False)
        layout.addWidget(self._preview_title)

        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.setVisible(False)
        self._preview_table.setStyleSheet("""
            QTableWidget { background:#FFF; alternate-background-color:#F7F8FA;
                           gridline-color:#E2E5EA; border:1px solid #E2E5EA; border-radius:6px; }
            QHeaderView::section { background:#1B2A4A; color:#FFF; padding:6px 10px;
                                    font-weight:bold; font-size:12px; border:none; }
        """)
        layout.addWidget(self._preview_table, stretch=1)

        layout.addStretch()

    # ── File picker ────────────────────────────────────────────────────────

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if not path:
            return
        self._load(Path(path))

    def _load(self, path: Path):
        self._file_lbl.setText(f"Loading {path.name}…")
        headers, rows, errors = load_excel(path)

        # Validation
        fatal_errors = [e for e in errors if e.row_index == 0]
        row_errors = [e for e in errors if e.row_index > 0]

        if fatal_errors:
            self._show_errors(fatal_errors + row_errors)
            self._file_lbl.setText(f"⚠  {path.name}")
            return

        self._headers = headers
        self._rows = rows
        self._mail_col = get_mail_column(headers) or ""
        self._file_lbl.setText(f"✓  {path.name}  ({len(rows)} recipients)")
        self._file_lbl.setStyleSheet("color:#2E7D32; font-size:13px; font-weight:600; border:none;")

        if row_errors:
            self._show_errors(row_errors)
        else:
            self._val_frame.setVisible(False)

        self._show_chips(headers)
        self._show_preview(headers, rows)

        # Emit
        self.excel_loaded.emit(headers, rows, self._mail_col)

    def _show_errors(self, errors: list):
        self._val_frame.setVisible(True)
        if any(e.row_index == 0 for e in errors):
            self._val_title.setText("❌ Critical Errors")
            self._val_title.setStyleSheet("color:#B3261E; font-size:13px; font-weight:600;")
        else:
            self._val_title.setText(f"⚠  {len(errors)} row(s) with issues (these rows will be skipped)")
            self._val_title.setStyleSheet("color:#E0A11C; font-size:13px; font-weight:600;")
        self._val_text.setPlainText("\n".join(e.message for e in errors))

    def _show_chips(self, headers: list):
        # Clear old chips
        while self._chip_row.count() > 1:
            item = self._chip_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mail_col = get_mail_column(headers)
        for h in headers:
            is_mail = h == mail_col
            chip = QLabel(h)
            chip.setFixedHeight(28)
            chip.setContentsMargins(10, 0, 10, 0)
            if is_mail:
                chip.setStyleSheet("""
                    background:#C9A227; color:#FFF; border-radius:14px;
                    font-size:12px; font-weight:700; padding:2px 10px;
                """)
                chip.setToolTip("Email column (required)")
            else:
                chip.setStyleSheet("""
                    background:#EEF2FF; color:#1B2A4A; border:1px solid #CBD5E0;
                    border-radius:14px; font-size:12px; padding:2px 10px;
                """)
            self._chip_row.insertWidget(self._chip_row.count() - 1, chip)

        self._chip_frame.setVisible(True)

    def _show_preview(self, headers: list, rows: list):
        n_preview = min(MAX_PREVIEW_ROWS, len(rows))
        self._preview_title.setText(
            f"Preview — first {n_preview} of {len(rows)} rows:"
        )
        self._preview_title.setVisible(True)

        self._preview_table.setColumnCount(len(headers))
        self._preview_table.setHorizontalHeaderLabels(headers)
        self._preview_table.setRowCount(n_preview)

        for r, row in enumerate(rows[:n_preview]):
            for c, h in enumerate(headers):
                item = QTableWidgetItem(str(row.get(h, "")))
                self._preview_table.setItem(r, c, item)

        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._preview_table.setVisible(True)
