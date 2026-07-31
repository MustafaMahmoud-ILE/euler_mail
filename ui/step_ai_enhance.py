"""
Step 3 — AI Enhancement.
Style selector → Enhance button → editable code view → Preview in browser.
"""
import logging
import os
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QScrollArea, QSizePolicy, QLineEdit, QSplitter, QGroupBox,
)
from euler_mail.config.settings import STYLE_PALETTES, OPENROUTER_MODELS, DEFAULT_MODEL
from euler_mail.ai.openrouter_client import enhance_draft
from euler_mail.ui.widgets.code_editor import CodeEditor
from euler_mail.utils.temp_preview import open_preview

logger = logging.getLogger(__name__)


# ── Background AI worker ──────────────────────────────────────────────────────

class _EnhanceWorker(QObject):
    progress = Signal(str)
    success = Signal(str, str)   # subject, html_body
    failure = Signal(str)

    def __init__(self, plain_text, style_name, model, api_key):
        super().__init__()
        self._text = plain_text
        self._style = style_name
        self._model = model
        self._key = api_key

    def run(self):
        result = enhance_draft(
            self._text, self._style, self._model, self._key,
            progress_callback=lambda m: self.progress.emit(m),
        )
        if "error" in result:
            self.failure.emit(result["error"])
        else:
            self.success.emit(result["subject"], result["html_body"])


# ── Style card ────────────────────────────────────────────────────────────────

class _StyleCard(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, info: dict, parent=None):
        super().__init__(parent)
        self._key = key
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._primary = info["primary"]
        self._accent = info["accent"]
        self._build(info)
        self._apply_style()

    def _build(self, info: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Color swatch bar
        swatch = QFrame()
        swatch.setFixedHeight(6)
        swatch.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {self._primary}, stop:1 {self._accent});"
            f"border-radius:3px;"
        )
        layout.addWidget(swatch)

        lbl = QLabel(info["label"])
        lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{self._primary}; border:none;")
        layout.addWidget(lbl)

        tone = QLabel(info["tone_keyword"])
        tone.setStyleSheet(f"font-size:11px; color:{self._accent}; font-weight:600; border:none;")
        layout.addWidget(tone)

        desc = QLabel(info["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:11px; color:#6B6F76; border:none;")
        layout.addWidget(desc)

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background:#FFFFFF; border:2px solid {self._primary};
                    border-radius:10px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background:#F7F8FA; border:1.5px solid #E2E5EA; border-radius:10px;
                }
                QFrame:hover { border:1.5px solid #CBD5E0; background:#FFFFFF; }
            """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def mousePressEvent(self, _):
        self.clicked.emit(self._key)


# ── Main step widget ──────────────────────────────────────────────────────────

class StepAIEnhance(QWidget):
    """
    Signals:
        enhancement_ready(subject: str, html_body: str)
    """
    enhancement_ready = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_style = "Academic"
        self._plain_text = ""
        self._thread = None
        self._worker = None
        self._style_cards: dict[str, _StyleCard] = {}
        self._build_ui()

    def set_draft(self, plain_text: str, subject_hint: str = "") -> None:
        self._plain_text = plain_text
        if subject_hint and not self._subject_preview.text():
            self._subject_preview.setText(subject_hint)

    # ── Build UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        # Title
        title = QLabel("AI Email Enhancement")
        title.setStyleSheet("font-size:20px; font-weight:700; color:#1B2A4A;")
        outer.addWidget(title)

        desc = QLabel(
            "Choose a style preset, then click <b>Enhance with AI</b>. "
            "The AI will correct grammar, apply the style's colours and structure, "
            "and return a complete HTML email. You can edit the result below."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#4A5568; font-size:13px;")
        outer.addWidget(desc)

        # ── Style cards ───────────────────────────────────────────────────
        cards_title = QLabel("Style Preset")
        cards_title.setStyleSheet("font-size:14px; font-weight:600; color:#1B2A4A;")
        outer.addWidget(cards_title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        for key, info in STYLE_PALETTES.items():
            card = _StyleCard(key, info)
            card.clicked.connect(self._select_style)
            self._style_cards[key] = card
            cards_row.addWidget(card)
        outer.addLayout(cards_row)
        self._style_cards["Academic"].set_selected(True)

        # ── API / Model row ───────────────────────────────────────────────
        api_row = QHBoxLayout()
        api_row.setSpacing(10)

        api_lbl = QLabel("OpenRouter Key:")
        api_lbl.setStyleSheet("color:#4A5568; font-size:12px; font-weight:600;")
        api_row.addWidget(api_lbl)

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText("sk-or-v1-…")
        self._api_key.setFixedHeight(34)
        self._api_key.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._api_key.setStyleSheet("""
            QLineEdit { background:#FFF; border:1px solid #CBD5E0; border-radius:6px;
                        font-size:12px; padding:0 10px; }
            QLineEdit:focus { border:1.5px solid #C9A227; }
        """)
        # Pre-fill from env
        self._api_key.setText(os.environ.get("OPENROUTER_API_KEY", ""))
        api_row.addWidget(self._api_key)

        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet("color:#4A5568; font-size:12px; font-weight:600;")
        api_row.addWidget(model_lbl)

        self._model_combo = QComboBox()
        self._model_combo.setFixedHeight(34)
        self._model_combo.setStyleSheet("""
            QComboBox { background:#FFF; border:1px solid #CBD5E0; border-radius:6px;
                        font-size:12px; padding:0 10px; min-width:200px; }
            QComboBox::drop-down { border:none; }
        """)
        for label, value in OPENROUTER_MODELS:
            self._model_combo.addItem(label, value)
        # Set default
        for i, (_, v) in enumerate(OPENROUTER_MODELS):
            if v == DEFAULT_MODEL:
                self._model_combo.setCurrentIndex(i)
                break
        api_row.addWidget(self._model_combo)

        outer.addLayout(api_row)

        # ── Enhance button + status ───────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._btn_enhance = QPushButton("✨  Enhance with AI")
        self._btn_enhance.setFixedHeight(44)
        self._btn_enhance.setCursor(Qt.PointingHandCursor)
        self._btn_enhance.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1B2A4A, stop:1 #2E5EAA);
                color:#FFF; border:none; border-radius:22px;
                font-size:14px; font-weight:700; padding:0 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #243853, stop:1 #3A6DBE);
            }
            QPushButton:disabled { background:#AAB4C0; }
        """)
        self._btn_enhance.clicked.connect(self._start_enhance)
        btn_row.addWidget(self._btn_enhance)

        self._btn_preview = QPushButton("🔍  Preview in Browser")
        self._btn_preview.setFixedHeight(44)
        self._btn_preview.setCursor(Qt.PointingHandCursor)
        self._btn_preview.setEnabled(False)
        self._btn_preview.setStyleSheet("""
            QPushButton {
                background:#EEF2FF; color:#1B2A4A; border:1.5px solid #CBD5E0;
                border-radius:22px; font-size:13px; font-weight:600; padding:0 20px;
            }
            QPushButton:hover { background:#E2E8F0; border-color:#AAB4C0; }
            QPushButton:disabled { color:#AAB4C0; }
        """)
        self._btn_preview.clicked.connect(self._preview)
        btn_row.addWidget(self._btn_preview)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#6B6F76; font-size:12px;")
        outer.addWidget(self._status_lbl)

        # ── Subject preview ───────────────────────────────────────────────
        subj_row = QHBoxLayout()
        subj_lbl = QLabel("AI-suggested Subject:")
        subj_lbl.setStyleSheet("color:#4A5568; font-size:12px; font-weight:600; min-width:150px;")
        subj_row.addWidget(subj_lbl)
        self._subject_preview = QLineEdit()
        self._subject_preview.setPlaceholderText("Will be filled after enhancement…")
        self._subject_preview.setFixedHeight(34)
        self._subject_preview.setStyleSheet("""
            QLineEdit { background:#FFF; border:1px solid #CBD5E0; border-radius:6px;
                        font-size:13px; color:#1B2A4A; padding:0 10px; }
            QLineEdit:focus { border:1.5px solid #C9A227; }
        """)
        subj_row.addWidget(self._subject_preview)
        outer.addLayout(subj_row)

        # ── Code editor ───────────────────────────────────────────────────
        editor_title = QLabel("HTML Output  (editable — paste or modify as needed)")
        editor_title.setStyleSheet("font-size:13px; font-weight:600; color:#1B2A4A;")
        outer.addWidget(editor_title)

        self._editor = CodeEditor()
        self._editor.setMinimumHeight(300)
        self._editor.setPlaceholderText(
            "Click 'Enhance with AI' to generate HTML here, or paste your own HTML…"
        )
        outer.addWidget(self._editor, stretch=1)

    # ── Event handlers ─────────────────────────────────────────────────────

    def _select_style(self, key: str) -> None:
        for k, card in self._style_cards.items():
            card.set_selected(k == key)
        self._selected_style = key

    def _start_enhance(self) -> None:
        text = self._plain_text
        if not text:
            self._set_status("❌  No draft text found. Please complete the Compose step first.", error=True)
            return

        api_key = self._api_key.text().strip()
        if not api_key:
            self._set_status("❌  Please enter an OpenRouter API key.", error=True)
            return

        model = self._model_combo.currentData()
        self._btn_enhance.setEnabled(False)
        self._btn_enhance.setText("⏳  Enhancing…")
        self._set_status(f"Sending to {model}…")

        self._worker = _EnhanceWorker(text, self._selected_style, model, api_key)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._set_status)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._worker.success.connect(self._thread.quit)
        self._worker.failure.connect(self._thread.quit)
        self._thread.start()

    def _on_success(self, subject: str, html_body: str) -> None:
        self._btn_enhance.setEnabled(True)
        self._btn_enhance.setText("✨  Enhance with AI")
        self._btn_preview.setEnabled(True)
        self._set_status("✅  Enhancement complete! Review and edit below, then click Next.", success=True)
        self._subject_preview.setText(subject)
        self._editor.setPlainText(html_body)
        self.enhancement_ready.emit(subject, html_body)

    def _on_failure(self, error: str) -> None:
        self._btn_enhance.setEnabled(True)
        self._btn_enhance.setText("✨  Enhance with AI")
        self._set_status(f"❌  {error}", error=True)

    def _preview(self) -> None:
        html = self._editor.toPlainText()
        if not html.strip():
            self._set_status("Nothing to preview — editor is empty.", error=True)
            return
        try:
            open_preview(html)
        except Exception as exc:
            self._set_status(str(exc), error=True)

    def _set_status(self, msg: str, error: bool = False, success: bool = False) -> None:
        if error:
            style = "color:#B3261E; font-size:12px;"
        elif success:
            style = "color:#2E7D32; font-size:12px; font-weight:600;"
        else:
            style = "color:#6B6F76; font-size:12px;"
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(style)

    # ── Public getters ─────────────────────────────────────────────────────

    def get_subject(self) -> str:
        return self._subject_preview.text().strip()

    def get_html_body(self) -> str:
        return self._editor.toPlainText().strip()
