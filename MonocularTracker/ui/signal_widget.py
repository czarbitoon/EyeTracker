from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, QRect
    from PyQt6.QtGui import QColor, QPainter, QPen, QFont
    from PyQt6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    Qt = None  # type: ignore
    QRect = None  # type: ignore
    QColor = None  # type: ignore
    QPainter = None  # type: ignore
    QPen = None  # type: ignore
    QFont = None  # type: ignore
    QWidget = object  # type: ignore


class SignalWidget(QWidget):  # type: ignore[misc]
    """
    Compact two-row bar showing normalized eye-signal ranges for Δnx and Δny.

    - Draws red/amber/green threshold bands per axis.
    - Draws a marker for the current Δ range value.
    """

    def __init__(self):  # type: ignore[no-redef]
        super().__init__()
        self._rx = 0.0
        self._ry = 0.0
        # OK/Strong thresholds for each axis (normalized units)
        self._x_ok = 0.10
        self._x_strong = 0.18
        self._y_ok = 0.06
        self._y_strong = 0.12
        self.setMinimumHeight(32)

    def set_thresholds(self, x_ok: float, x_strong: float, y_ok: float, y_strong: float) -> None:
        self._x_ok = float(x_ok)
        self._x_strong = float(x_strong)
        self._y_ok = float(y_ok)
        self._y_strong = float(y_strong)
        self.update()

    def set_values(self, rx: float, ry: float) -> None:
        self._rx = max(0.0, float(rx))
        self._ry = max(0.0, float(ry))
        self.update()

    def _draw_bar(self, p: QPainter, r: QRect, ok: float, strong: float, val: float, label: str) -> None:  # type: ignore[name-defined]
        # Leave a small left label area
        lw = 34
        bar = QRect(r.left() + lw, r.top() + 3, r.width() - lw - 6, r.height() - 6)
        # Maximum scale up to 1.5x strong to give headroom
        cap = max(strong * 1.5, strong + 0.05)
        # Segment widths
        def x_for(v: float) -> int:
            v = max(0.0, min(cap, v))
            return int(bar.left() + (v / cap) * bar.width())
        # Background bands
        p.fillRect(QRect(bar.left(), bar.top(), x_for(ok) - bar.left(), bar.height()), QColor(204, 0, 0, 60))
        p.fillRect(QRect(x_for(ok), bar.top(), x_for(strong) - x_for(ok), bar.height()), QColor(212, 160, 23, 60))
        p.fillRect(QRect(x_for(strong), bar.top(), bar.right() - x_for(strong) + 1, bar.height()), QColor(0, 170, 0, 60))
        # Outline
        pen = QPen(QColor(120, 120, 120))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRect(bar)
        # Marker for value
        m_x = x_for(val)
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(m_x, bar.top(), m_x, bar.bottom())
        # Label text
        try:
            p.setPen(QColor(200, 200, 200))
            f = QFont()
            f.setPointSizeF(max(7.5, self.font().pointSizeF() - 1))
            p.setFont(f)
        except Exception:
            pass
        p.drawText(QRect(r.left() + 4, r.top(), lw - 6, r.height()), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), label)

    def paintEvent(self, e):  # type: ignore[override]
        if QPainter is object:
            return
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        h2 = self.height() // 2
        self._draw_bar(p, QRect(0, 0, self.width(), h2), self._x_ok, self._x_strong, self._rx, "Δnx")
        self._draw_bar(p, QRect(0, h2, self.width(), self.height() - h2), self._y_ok, self._y_strong, self._ry, "Δny")
        p.end()
