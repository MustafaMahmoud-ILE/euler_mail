"""
CodeEditor — QTextEdit subclass with HTML syntax highlighting and line numbers.
Used in the AI Enhance step for editing the generated HTML.
"""
import re
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QSyntaxHighlighter, QTextCharFormat,
    QTextFormat,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget


# ── Syntax Highlighter ────────────────────────────────────────────────────────

class _HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        self._rules = [
            # HTML tags  <div ...>  </div>
            (re.compile(r"</?[a-zA-Z][a-zA-Z0-9\-]*"), fmt("#569CD6")),
            # Tag closing bracket
            (re.compile(r"/?>"), fmt("#569CD6")),
            # Attribute names
            (re.compile(r"\b([a-zA-Z\-]+)(?=\s*=)"), fmt("#9CDCFE")),
            # Quoted attribute values
            (re.compile(r'"[^"]*"'), fmt("#CE9178")),
            (re.compile(r"'[^']*'"), fmt("#CE9178")),
            # HTML comments
            (re.compile(r"<!--.*?-->", re.DOTALL), fmt("#6A9955", italic=True)),
            # CSS hex colors inside style=""
            (re.compile(r"#[0-9a-fA-F]{3,8}\b"), fmt("#B5CEA8")),
            # {placeholder} tokens — highlight in gold
            (re.compile(r"\{[^}]+\}"), fmt("#C9A227", bold=True)),
            # DOCTYPE
            (re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE), fmt("#C8C8C8")),
        ]

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ── Line-number gutter ────────────────────────────────────────────────────────

class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, event):
        self._editor._paint_line_numbers(event)


# ── Main widget ───────────────────────────────────────────────────────────────

class CodeEditor(QPlainTextEdit):
    """
    Monospace HTML code editor with:
    - Syntax highlighting ({placeholders} in gold)
    - Line-number gutter
    - Dark VS Code-style colour scheme
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        font = QFont("Cascadia Code", 11)
        font.setStyleHint(QFont.Monospace)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                selection-background-color: #45475A;
            }
        """)

        self._highlighter = _HtmlHighlighter(self.document())
        self._line_area = _LineNumberArea(self)

        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width(0)

    def _line_number_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * (digits + 1)

    def _update_line_area_width(self, _=None) -> None:
        self.setViewportMargins(self._line_number_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(), self._line_number_width(), cr.height()))

    def _paint_line_numbers(self, event):
        p = QPainter(self._line_area)
        p.fillRect(event.rect(), QColor("#181825"))

        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        font = QFont(self.font())
        font.setPointSize(max(8, font.pointSize() - 1))
        p.setFont(font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                p.setPen(QColor("#585B70"))
                p.drawText(
                    0, top, self._line_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignRight | Qt.AlignVCenter,
                    str(num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num += 1
