"""
StepperSidebar — custom-painted vertical step navigator for Euler Mail.
"""
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QPainterPath
from PySide6.QtWidgets import QWidget

STEP_STATES = ("locked", "active", "complete")

# Palette
C_SIDEBAR_BG     = QColor("#0D1B2E")
C_GOLD           = QColor("#C9A227")
C_GOLD_DARK      = QColor("#A07D1A")
C_GREEN          = QColor("#2E7D32")
C_CIRCLE_LOCKED  = QColor("#2A3F5C")
C_TEXT_ACTIVE    = QColor("#FFFFFF")
C_TEXT_LOCKED    = QColor("#4A6080")
C_TEXT_COMPLETE  = QColor("#A8C5DA")
C_CONNECTOR      = QColor("#1E3050")


class StepperSidebar(QWidget):
    CIRCLE_R  = 18          # radius
    STEP_H    = 80          # height per step
    LEFT_PAD  = 28          # left margin for circle center

    def __init__(self, step_labels: list, parent=None):
        super().__init__(parent)
        self._labels = step_labels
        self._states = ["locked"] * len(step_labels)
        if step_labels:
            self._states[0] = "active"
        self.setMinimumWidth(220)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )

    def set_state(self, index: int, state: str) -> None:
        """state: 'locked' | 'active' | 'complete'"""
        if 0 <= index < len(self._states):
            self._states[index] = state
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background
        p.fillRect(self.rect(), C_SIDEBAR_BG)

        n = len(self._labels)
        cx = self.LEFT_PAD + self.CIRCLE_R          # circle center x
        text_x = cx + self.CIRCLE_R + 16            # label start x
        top_offset = 24                              # padding before first step

        for i, (label, state) in enumerate(zip(self._labels, self._states)):
            cy = top_offset + i * self.STEP_H + self.CIRCLE_R

            # ── Connector line (above this step, below if not last) ──────
            if i > 0:
                prev_cy = top_offset + (i - 1) * self.STEP_H + self.CIRCLE_R
                p.setPen(QPen(C_CONNECTOR, 2))
                p.drawLine(cx, prev_cy + self.CIRCLE_R, cx, cy - self.CIRCLE_R)

            # ── Circle ────────────────────────────────────────────────────
            if state == "complete":
                p.setBrush(C_GREEN)
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - self.CIRCLE_R, cy - self.CIRCLE_R,
                              self.CIRCLE_R * 2, self.CIRCLE_R * 2)
                # Checkmark
                p.setPen(QPen(Qt.white, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                x0, y0 = cx - 7, cy
                p.drawLine(x0, y0, x0 + 5, y0 + 6)
                p.drawLine(x0 + 5, y0 + 6, x0 + 12, y0 - 6)

            elif state == "active":
                # Gold filled circle
                p.setBrush(C_GOLD)
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - self.CIRCLE_R, cy - self.CIRCLE_R,
                              self.CIRCLE_R * 2, self.CIRCLE_R * 2)
                # Step number
                f = QFont("Arial", 10, QFont.Bold)
                p.setFont(f)
                p.setPen(QColor("#1B2A4A"))
                p.drawText(
                    QRect(cx - self.CIRCLE_R, cy - self.CIRCLE_R,
                          self.CIRCLE_R * 2, self.CIRCLE_R * 2),
                    Qt.AlignCenter, str(i + 1)
                )

            else:  # locked
                p.setBrush(C_CIRCLE_LOCKED)
                p.setPen(Qt.NoPen)
                p.drawEllipse(cx - self.CIRCLE_R, cy - self.CIRCLE_R,
                              self.CIRCLE_R * 2, self.CIRCLE_R * 2)
                f = QFont("Arial", 10)
                p.setFont(f)
                p.setPen(C_TEXT_LOCKED)
                p.drawText(
                    QRect(cx - self.CIRCLE_R, cy - self.CIRCLE_R,
                          self.CIRCLE_R * 2, self.CIRCLE_R * 2),
                    Qt.AlignCenter, str(i + 1)
                )

            # ── Label text ───────────────────────────────────────────────
            if state == "active":
                color = C_TEXT_ACTIVE
                weight = QFont.Bold
            elif state == "complete":
                color = C_TEXT_COMPLETE
                weight = QFont.Normal
            else:
                color = C_TEXT_LOCKED
                weight = QFont.Normal

            f = QFont("Arial", 10, weight)
            p.setFont(f)
            p.setPen(color)
            p.drawText(
                QRect(text_x, cy - 14, self.width() - text_x - 12, 28),
                Qt.AlignVCenter | Qt.AlignLeft,
                label,
            )

        p.end()

    def sizeHint(self) -> QSize:
        h = 24 + len(self._labels) * self.STEP_H + 24
        return QSize(220, max(h, 400))
