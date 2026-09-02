from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

from ui.vinyl_widget import VinylWidget
from ui.waveform_widget import WaveformWidget
from ui.fader_widget import FaderWidget
from ui.tonearm_widget import ToneArmWidget  # Importa il nuovo widget
import os

class DeckWidget(QFrame):

    def __init__(self, name):
        super().__init__()

        self.setObjectName("deck")

        self.setStyleSheet("""
            QFrame#deck{
                background:#1a1a1a;
                border:2px solid #333;
                border-radius:18px;
            }
        """)

        layout = QVBoxLayout(self)

        self.titleLabel = QLabel(name)
        self.titleLabel.setFont(QFont("Arial", 16, QFont.Bold))
        self.titleLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.titleLabel)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(15)

        self.fader = FaderWidget()
        self.vinyl = VinylWidget()
        
        self.cover = QLabel()
        self.cover.setFixedSize(240, 240)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet("""
            background:#111;
            border-radius:10px;
        """)

        top.addWidget(self.fader)
        top.addWidget(self.vinyl)
        top.addWidget(self.cover)
        
        layout.addLayout(top)

        self.trackTitle = QLabel("No Track")
        self.artist = QLabel("")
        self.info = QLabel("")

        for w in [self.trackTitle, self.artist, self.info]:
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet("color:#ccc;")
            w.setWordWrap(False)
            # FIX: il testo non deve poter influenzare la larghezza del deck.
            # Con QSizePolicy.Ignored un titolo lungo non sposta il layout.
            w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            w.setMinimumWidth(0)
            layout.addWidget(w)

        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)

        # AGGIUNTA OVERLAY DEL BRACCETTO
        self.tonearm = ToneArmWidget(self)
        self.tonearm.setGeometry(0, 0, self.width(), self.height())
        self.tonearm.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Aggiorna la dimensione dell'overlay quando il deck cambia dimensione
        if hasattr(self, 'tonearm'):
            self.tonearm.setGeometry(0, 0, self.width(), self.height())

    def _short(self, text, limit=38):
        text = (text or "").strip()
        if len(text) > limit:
            return text[:limit - 1].rstrip() + "…"
        return text

    def set_track(self, track):
        self.track = track

        # FIX: titolo/autore sempre tagliati, il testo completo sta nel tooltip
        self.trackTitle.setText(self._short(track["title"]))
        self.trackTitle.setToolTip(track["title"])
        self.artist.setText(self._short(track["artist"], 26))
        self.artist.setToolTip(track["artist"])

        mins = int(track["duration"] // 60)
        secs = int(track["duration"] % 60)
        self.info.setText(f"{int(track['tempo'])} BPM • {mins}:{secs:02d}")

        cover_path = track.get("cover")
        if cover_path and os.path.exists(cover_path):
            pix = QPixmap(cover_path).scaled(
                240, 240, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.cover.setPixmap(pix)
            self.vinyl.set_cover(cover_path)
        else:
            na_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "assets", "NA.png")
            if os.path.exists(na_path):
                pix = QPixmap(na_path).scaled(
                    240, 240, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                self.cover.setPixmap(pix)
                self.vinyl.set_cover(na_path)
            else:
                self.cover.clear()
                self.vinyl.set_cover(None)

    def set_active(self, active):
        if active:
            self.setStyleSheet("""
                QFrame#deck{
                    background:#1d1d1d;
                    border:3px solid #00ff88;
                    border-radius:18px;
                }
            """)
            # BRACCETTO GIÙ (suona)
            self.tonearm.set_tonearm_active(True)
        else:
            self.setStyleSheet("""
                QFrame#deck{
                    background:#1a1a1a;
                    border:2px solid #333;
                    border-radius:18px;
                }
            """)
            # BRACCETTO SU (riposo)
            self.tonearm.set_tonearm_active(False)