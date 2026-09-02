from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QPen,
    QLinearGradient
)
from PyQt5.QtCore import Qt, QRect  # ✅ Aggiunto QRect

class FaderWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.setFixedWidth(50)

        self.level = 1.0

    def set_level(self, value):
        self.level = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # =========================
        # 1. TRACK (La guida verticale)
        # =========================
        track_rect = QRect(w // 2 - 12, 20, 24, h - 40)
        
        grad_track = QLinearGradient(0, 0, 0, h)
        grad_track.setColorAt(0, QColor(40, 40, 40))
        grad_track.setColorAt(0.5, QColor(25, 25, 25))
        grad_track.setColorAt(1, QColor(40, 40, 40))
        
        p.setBrush(grad_track)
        p.setPen(QPen(QColor(60, 60, 60), 1))
        p.drawRoundedRect(track_rect, 6, 6)

        # =========================
        # 2. POSIZIONE DEL POMELLO
        # =========================
        knob_h = 36
        knob_w = 30
        y_center = (h - 40) * (1.0 - self.level) + 20
        
        # =========================
        # 3. IL POMELLO (Knob)
        # =========================
        knob_rect = QRect(
            (w - knob_w) // 2, 
            int(y_center) - knob_h // 2, 
            knob_w, 
            knob_h
        )

        grad_knob = QLinearGradient(
            knob_rect.center().x(), 
            knob_rect.top(), 
            knob_rect.center().x(), 
            knob_rect.bottom()
        )
        grad_knob.setColorAt(0.0, QColor(50, 50, 50))
        grad_knob.setColorAt(0.3, QColor(20, 20, 20))
        grad_knob.setColorAt(0.7, QColor(15, 15, 15))
        grad_knob.setColorAt(1.0, QColor(30, 30, 30))

        p.setBrush(grad_knob)
        p.setPen(QPen(QColor(80, 80, 80), 1))
        p.drawRoundedRect(knob_rect, 4, 4)

        # =========================
        # 4. STRISCETTA ROSSA (Indicatore)
        # =========================
        indicator_rect = QRect(
            knob_rect.x() + 4,
            int(y_center) - 2,
            knob_w - 8,
            4
        )
        
        p.setBrush(QColor(220, 50, 50))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(indicator_rect, 2, 2)

        # =========================
        # 5. DETTAGLIO LUCE (Opzionale)
        # =========================
        if self.level > 0.8:
            p.setBrush(QColor(0, 255, 136, 40))
            p.setPen(Qt.NoPen)
            p.drawEllipse(knob_rect.center().x() - 2, knob_rect.y() - 2, 4, 4)

        # CHIUDI IL PAINTER PER EVITARE WARNING
        p.end()