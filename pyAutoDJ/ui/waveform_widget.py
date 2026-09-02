import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
import numpy as np

class WaveformWidget(QWidget):

    seekRequested = pyqtSignal(float)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.plot = pg.PlotWidget()
        
        # Ottimizzazioni iniziali
        self.plot.setBackground("#101010")
        self.plot.hideAxis("left")
        self.plot.hideAxis("bottom")
        self.plot.setMenuEnabled(False)
        
        # Disabilita il calcolo automatico del range (già fatto, ma rassicurante)
        self.plot.enableAutoRange('x', False)
        self.plot.enableAutoRange('y', False)
        self.plot.setLimits(xMin=0, xMax=1000000) # Limite alto per evitare ricalcoli

        layout.addWidget(self.plot)

        self.wave_data = None
        self.curve = None

        # Creazione playhead ottimizzata
        self.playhead = pg.InfiniteLine(
            pos=0,
            angle=90,
            movable=False,
            pen=pg.mkPen(QColor(220, 50, 50), width=2, cosmetic=True), # cosmetic=True = linea sottile e veloce # colore segna tempo
            name="playhead"
        )
        
        # Aggiungi la linea al plot
        self.plot.addItem(self.playhead)

        # Cache per evitare aggiornamenti ridondanti
        self.last_pos = -1

        self.plot.viewport().installEventFilter(self)

    def set_waveform(self, y):
        if len(y) < 10:
            y = np.zeros(800)

        self.plot.clear()

        # Waveform più visibile
        self.curve = self.plot.plot(
            y,
            pen=pg.mkPen("#00ff88", width=1.3, cosmetic=True), # Colore Wave
            fillLevel=0,
            brush=(0, 255, 136, 50)
        )

        self.plot.addItem(self.playhead)

        self.wave_data = y

        # Imposta limiti corretti
        self.plot.setLimits(
            xMin=0,
            xMax=len(y),
            yMin=-1.05,
            yMax=1.05
        )

        self.plot.setYRange(-1.05, 1.05, padding=0)
        self.plot.setXRange(0, len(y), padding=0)

    def set_position(self, fraction):
        # Sicurezza: se non c'è dati wave, esci subito
        if self.wave_data is None or len(self.wave_data) == 0:
            return

        # Sicurezza: verifica che fraction sia un numero valido
        try:
            if not isinstance(fraction, (int, float)) or fraction != fraction: # Controllo NaN
                return
            
            # Normalizza frazione tra 0.0 e 1.0
            fraction = max(0.0, min(1.0, float(fraction)))
        except:
            return

        # Calcola la posizione in pixel/dati
        new_pos = fraction * len(self.wave_data)
        
        # Cache ottimizzata: aggiorna solo se si è spostato significativamente
        # Evita micro-aggiornamenti che possono bloccare il thread UI
        if abs(new_pos - self.last_pos) < 0.5:
            return

        self.last_pos = new_pos
        
        # Aggiorna la linea con un blocco try/except per evitare crash improvvisi
        try:
            self.playhead.setPos(new_pos)
        except Exception as e:
            # Se PyQtGraph si lamenta, resetta la posizione a 0 (sicurezza)
            # print(f"Debug Waveform Pos Error: {e}")
            pass

    def seek_from_pos(self, pos):

        if self.wave_data is None:
            return

        point = self.plot.plotItem.vb.mapSceneToView(pos)

        fraction = point.x() / len(self.wave_data)

        fraction = max(0.0, min(1.0, fraction))

        self.seekRequested.emit(fraction)

    def eventFilter(self, obj, event):

        if event.type() == event.MouseButtonPress:

            if event.button() == Qt.LeftButton:

                self.seek_from_pos(event.pos())

        elif event.type() == event.MouseMove:

            if event.buttons() & Qt.LeftButton:

                self.seek_from_pos(event.pos())

        return super().eventFilter(obj, event)