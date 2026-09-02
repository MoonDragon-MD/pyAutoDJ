from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QPainterPath
import os
from PyQt5.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty
)

base = os.path.dirname(os.path.dirname(__file__))

class VinylWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.angle = 0.0
        self.spinning = False
        self.cover = None

        self.setMinimumSize(260, 260)
        
        # Il braccetto è stato rimosso da qui e spostato in ToneArmWidget
        
        # Carica il vinile
        self.lp_pix = QPixmap(os.path.join(base, "assets", "LP.png"))
        if self.lp_pix.isNull():
            # Fallback se l'immagine manca (crea un cerchio grigio)
            self.lp_pix = QPixmap(250, 250)
            self.lp_pix.fill(Qt.transparent)
            painter = QPainter(self.lp_pix)
            painter.setBrush(QColor(30, 30, 30))
            painter.setPen(QPen(QColor(50, 50, 50), 2))
            painter.drawEllipse(0, 0, 250, 250)
            painter.end()

        # TIMERS DEDICATI PER FLUIDITÀ
        # Usiamo un timer fisso a 16ms (circa 60 FPS)
        self.spin_timer = QTimer(self)
        self.spin_timer.timeout.connect(self._on_spin_tick)
        self.spin_timer.setSingleShot(False)
        
        # Velocità di rotazione (gradi per tick)
        # 16ms * 60fps = 1 secondo. Se vuoi 33 giri/min (0.55 giri/sec)
        # 0.55 * 360 = 198 gradi al secondo -> 198 / 60 = 3.3 gradi per tick
        self.rotation_speed = 3.3 

    def set_cover(self, path):
        if path and os.path.exists(path):
            self.cover = QPixmap(path)
        else:
            self.cover = None
        self.update()

    def set_spinning(self, spinning: bool):
        if spinning == self.spinning:
            return

        self.spinning = spinning
        
        if spinning:
            # Avvia il timer dedicato
            self.spin_timer.start(16) # 16ms = ~60 FPS
        else:
            # Ferma il timer
            self.spin_timer.stop()
            self.update() # Ridisegna una volta per fermarsi

    def _on_spin_tick(self):
        """Aggiorna l'angolo e forza il ridisegno"""
        self.angle = (self.angle + self.rotation_speed) % 360
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        cx = self.width() // 2
        cy = self.height() // 2
        
        p.save()
        p.translate(cx, cy)
        p.rotate(self.angle)

        # Disegna il vinile (LP)
        if not self.lp_pix.isNull():
            lp = self.lp_pix.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(-125, -125, lp)

        # Disegna la copertina centrale
        if self.cover:
            size = 90
            path = QPainterPath()
            path.addEllipse(-size // 2, -size // 2, size, size)
            p.setClipPath(path)

            pix = self.cover.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap(-size // 2, -size // 2, pix)  
        
        p.restore()
        p.end()
        # Il disegno del braccetto è stato rimosso da qui.
        # Ora è gestito esclusivamente da ToneArmWidget.