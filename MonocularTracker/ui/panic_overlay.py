"""
PanicOverlay: Small always-on-top window with a red STOP button.

Clicking STOP immediately invokes the global panic handler to halt tracking, disable cursor
control, and return to the launcher.
"""
from __future__ import annotations

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QPalette, QColor
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class PanicOverlay(QWidget):  # type: ignore[misc]
    def __init__(self, panic_callback=None):  # type: ignore[no-redef]
        super().__init__()
        self._panic_callback = panic_callback
        try:
            self.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
                | Qt.WindowType.FramelessWindowHint
            )
        except Exception:
            pass
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._build_ui()
        self.resize(120, 80)
        self.move(40, 40)

    def _build_ui(self) -> None:
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        btn = QPushButton("STOP")
        try:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #cc0000; color: white; font-weight: bold; font-size: 18px;
                    border: 2px solid #990000; border-radius: 6px; padding: 8px 12px;
                }
                QPushButton:hover { background-color: #e00000; }
                QPushButton:pressed { background-color: #a00000; }
                """
            )
        except Exception:
            pass
        btn.clicked.connect(self._on_stop_clicked)  # type: ignore[attr-defined]
        lay.addWidget(btn)
        self.setLayout(lay)

    def _on_stop_clicked(self) -> None:
        try:
            if callable(self._panic_callback):
                self._panic_callback()
        except Exception:
            pass
