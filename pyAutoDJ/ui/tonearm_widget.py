from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
import math

class ToneArmWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        
        self.tonearm_angle = 135  # Angolo originale a riposo
        
        self.arm_anim = QPropertyAnimation(self, b"tonearm")
        self.arm_anim.setDuration(1965) # Durata animazione braccetto
        self.arm_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Trasparente agli eventi del mouse
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.raise_()  # Metti sopra tutti
        
    def set_tonearm_active(self, active: bool):
        target = 156 if active else 135  # Angoli originali
        
        self.arm_anim.stop()
        self.arm_anim.setTargetObject(self)
        self.arm_anim.setPropertyName(b"tonearm")
        self.arm_anim.setStartValue(float(self.tonearm_angle))
        self.arm_anim.setEndValue(float(target))
        self.arm_anim.start()
        
        self.tonearm_angle = target
        self.update()
        
    def get_tonearm(self):
        return self.tonearm_angle

    def set_tonearm(self, value):
        self.tonearm_angle = value
        self.update()

    tonearm = pyqtProperty(float, get_tonearm, set_tonearm)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Prendi le dimensioni dal parent (DeckWidget)
        cx = self.width() // 2
        cy = self.height() // 2
        
        # Coordinate ORIGINALI che funzionavano
        arm_base_x = cx + 98
        arm_base_y = cy - 200
        
        p.translate(arm_base_x, arm_base_y)
        p.rotate(self.tonearm_angle)
        
        # =========================
        # GEOMETRIA REALISTICA BRACCIO
        # =========================
        # Simulazione di un braccio a offset (tipo S-shape o straight con offset)
        # Il giunto è più vicino al perno, la parte finale è lunga e inclinata.
        
        pen = QPen(QColor(185, 185, 185), 7)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        
        # Lunghezze relative
        len1 = 60   # Prima parte (dal perno al giunto) - più corta
        len2 = 110  # Seconda parte (dal giunto alla testina) - più lunga
        
        # Angolo del primo segmento (direzione base)
        # -45 gradi circa verso il basso-sinistra
        angle1_rad = math.radians(-45) 
        
        # Coordinate del giunto
        joint_x = len1 * math.cos(angle1_rad)
        joint_y = len1 * math.sin(angle1_rad)
        
        # Offset dell'angolo reale (circa 22-25 gradi tipici dei giradischi)
        # Questo fa sì che la testina sia quasi tangente al disco
        offset_deg = 21 
        offset_rad = math.radians(offset_deg)
        
        # Angolo del secondo segmento (primo + offset)
        angle2_rad = angle1_rad + offset_rad
        
        # Coordinate della testina
        end_x = joint_x + len2 * math.cos(angle2_rad)
        end_y = joint_y + len2 * math.sin(angle2_rad)
        
        # Disegna il primo segmento (dal perno al giunto)
        p.drawLine(0, 0, int(joint_x), int(joint_y))
        
        # Disegna il secondo segmento (dal giunto alla testina)
        p.drawLine(int(joint_x), int(joint_y), int(end_x), int(end_y))
        
        # =========================
        # TESTINA (CARTRIDGE)
        # =========================
        # La testina è orientata lungo il secondo segmento, ma leggermente ruotata
        # per simulare l'angolo di trascinamento reale (spesso la testina è inclinata)
        cart_angle_deg = math.degrees(angle2_rad) - -45 # Leggera inclinazione aggiuntiva
        
        p.setBrush(QColor(35, 35, 35))
        p.setPen(Qt.NoPen)
        
        p.save()
        p.translate(end_x, end_y)
        p.rotate(cart_angle_deg)
        # Disegna la testina (rettangolo allungato)
        p.drawRect(-8, -10, 28, 20)
        p.restore()
        
        # =========================
        # AGO (STYLUS)
        # =========================
        p.setPen(QPen(QColor(255, 80, 80), 2))
        # L'ago punta verso il centro del disco (opposto alla direzione del braccio)
        stylus_angle_deg = cart_angle_deg + 180
        
        p.save()
        p.translate(end_x, end_y)
        p.rotate(stylus_angle_deg)
        # Ago più lungo e visibile
        p.drawLine(0, 0, 8, 8) 
        p.restore()
        p.end()