from __future__ import annotations

from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

import matplotlib
try:
    matplotlib.use("Qt5Agg")
except Exception:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io

class CalibrationResultsWindow(QWidget):
    def __init__(self, *, screen: tuple[int,int], targets: List[Tuple[int,int]], samples: List[List[Tuple[float,float]]], point_errors: List[float], point_conf: List[float], overall_error: float):
        super().__init__()
        self.setWindowTitle("Calibration Results")
        self.resize(640, 720)
        v = QVBoxLayout()
        self.lbl_summary = QLabel(f"Overall mean error: {overall_error:.1f} px")
        v.addWidget(self.lbl_summary)
        # Text metrics
        txt = QTextEdit(); txt.setReadOnly(True)
        lines = ["Point\tSamples\tMeanErr(px)\tConf"]
        for i, (t, samps, err, conf) in enumerate(zip(targets, samples, point_errors, point_conf)):
            lines.append(f"{i+1}\t{len(samps)}\t{err:.1f}\t{conf:.2f}")
        txt.setText("\n".join(lines))
        v.addWidget(txt)
        # Scatter plot image (normalized samples colored by point)
        try:
            fig, ax = plt.subplots(figsize=(4,4))
            for i, samps in enumerate(samples):
                xs = [p[0] for p in samps]
                ys = [p[1] for p in samps]
                ax.scatter(xs, ys, s=10, alpha=0.6, label=f"P{i+1}")
            ax.set_title("Filtered gaze samples (normalized)")
            ax.set_xlim(0,1); ax.set_ylim(0,1)
            ax.legend(fontsize=6, ncol=2)
            buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format='png'); plt.close(fig)
            buf.seek(0)
            from PyQt5.QtGui import QPixmap
            from PyQt5.QtGui import QImage
            import numpy as np
            arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
            qimg = QImage.fromData(arr, 'PNG')
            lbl_plot = QLabel(); lbl_plot.setPixmap(QPixmap.fromImage(qimg))
            v.addWidget(lbl_plot)
        except Exception:
            pass
        self.setLayout(v)
