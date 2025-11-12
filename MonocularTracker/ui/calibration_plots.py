from __future__ import annotations

from typing import List, Tuple

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QFileDialog
except Exception:  # pragma: no cover
    QMainWindow = object  # type: ignore
    QWidget = object  # type: ignore
    pyqtSignal = lambda *a, **k: None  # type: ignore

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # type: ignore

from MonocularTracker.analysis.error_metrics import (
    PointError,
    compute_point_errors,
    compute_mean_error,
    compute_max_error,
    compute_rms_error,
    compute_error_heatmap,
)
from MonocularTracker.analysis.plots import (
    fig_scatter,
    fig_vectors,
    fig_heatmap,
    fig_histogram,
    fig_summary,
)


class CalibrationPlotsWindow(QMainWindow):  # type: ignore[misc]
    accepted = pyqtSignal()
    retry = pyqtSignal()

    def __init__(self, screen_resolution: Tuple[int, int], true_pts: List[Tuple[int, int]], pred_pts: List[Tuple[int, int]], threshold_px: float = 150.0):  # type: ignore[no-redef]
        super().__init__()
        self.setWindowTitle("Calibration Analysis")
        self.screen_resolution = screen_resolution
        self.true_pts = true_pts
        self.pred_pts = pred_pts
        self.threshold_px = float(threshold_px)

        self.errors: List[PointError] = compute_point_errors(true_pts, pred_pts)
        self.mean_px = compute_mean_error(self.errors)
        self.max_px = compute_max_error(self.errors)
        self.rms_px = compute_rms_error(self.errors)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        v = QVBoxLayout()

        # Top summary bar
        self.lbl_summary = QLabel(f"Mean: {self.mean_px:.1f}px   Max: {self.max_px:.1f}px   RMS: {self.rms_px:.1f}px")
        v.addWidget(self.lbl_summary)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_png = QPushButton("Export PNG")
        btn_csv = QPushButton("Export CSV")
        btn_rerun = QPushButton("Re-run calibration")
        btn_close = QPushButton("Close")
        toolbar.addWidget(btn_png)
        toolbar.addWidget(btn_csv)
        toolbar.addStretch(1)
        toolbar.addWidget(btn_rerun)
        toolbar.addWidget(btn_close)
        v.addLayout(toolbar)

        # Tabs
        tabs = QTabWidget()
        # Scatter
        canv_scatter = FigureCanvas(fig_scatter(self.true_pts, self.pred_pts, self.errors))
        scatter_tab = QWidget()
        lt = QVBoxLayout()
        lt.addWidget(canv_scatter)
        scatter_tab.setLayout(lt)
        tabs.addTab(scatter_tab, "Scatter")
        # Vectors
        canv_vectors = FigureCanvas(fig_vectors(self.true_pts, self.pred_pts))
        vec_tab = QWidget()
        lv = QVBoxLayout()
        lv.addWidget(canv_vectors)
        vec_tab.setLayout(lv)
        tabs.addTab(vec_tab, "Vectors")
        # Heatmap
        heat = compute_error_heatmap(self.errors, self.screen_resolution)
        canv_heat = FigureCanvas(fig_heatmap(heat, self.screen_resolution))
        heat_tab = QWidget()
        lh = QVBoxLayout()
        lh.addWidget(canv_heat)
        heat_tab.setLayout(lh)
        tabs.addTab(heat_tab, "Heatmap")
        # Distribution
        canv_hist = FigureCanvas(fig_histogram(self.errors))
        hist_tab = QWidget()
        lhist = QVBoxLayout()
        lhist.addWidget(canv_hist)
        hist_tab.setLayout(lhist)
        tabs.addTab(hist_tab, "Distribution")
        # Summary
        canv_sum = FigureCanvas(fig_summary(self.mean_px, self.max_px, self.rms_px))
        sum_tab = QWidget()
        ls = QVBoxLayout()
        ls.addWidget(canv_sum)
        sum_tab.setLayout(ls)
        tabs.addTab(sum_tab, "Summary")
        v.addWidget(tabs, stretch=1)

        # Bottom bar
        bottom = QHBoxLayout()
        btn_accept = QPushButton("Accept calibration")
        btn_retry = QPushButton("Retry calibration")
        bottom.addStretch(1)
        bottom.addWidget(btn_accept)
        bottom.addWidget(btn_retry)
        v.addLayout(bottom)

        central.setLayout(v)
        self.setCentralWidget(central)

        # Connections
        btn_close.clicked.connect(self.close)  # type: ignore[attr-defined]
        btn_rerun.clicked.connect(self._on_retry)  # type: ignore[attr-defined]
        btn_accept.clicked.connect(self.accepted)  # type: ignore[attr-defined]
        btn_retry.clicked.connect(self._on_retry)  # type: ignore[attr-defined]
        btn_png.clicked.connect(self._export_png)  # type: ignore[attr-defined]
        btn_csv.clicked.connect(self._export_csv)  # type: ignore[attr-defined]

        # Warn if mean error exceeds threshold
        if self.mean_px > self.threshold_px:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Calibration Warning", "Calibration unstable — consider recalibrating.")
            except Exception:
                pass

    def _on_retry(self):
        self.retry.emit()
        self.close()

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", filter="PNG Files (*.png)")
        if not path:
            return
        # Export the scatter plot as canonical image
        fig = fig_scatter(self.true_pts, self.pred_pts, self.errors)
        fig.savefig(path, dpi=150)
        try:
            import matplotlib.pyplot as plt  # type: ignore
            plt.close(fig)
        except Exception:
            pass

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", filter="CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("true_x,true_y,pred_x,pred_y,dist_px\n")
                for e in self.errors:
                    f.write(f"{e.true_xy[0]},{e.true_xy[1]},{e.pred_xy[0]},{e.pred_xy[1]},{e.dist_px:.2f}\n")
        except Exception:
            pass
