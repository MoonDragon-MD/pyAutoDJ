from PyQt5.QtCore import QRunnable

from analysis.waveform import create_waveform


class WaveformWorker(QRunnable):

    def __init__(self, track, signals):

        super().__init__()

        self.track = track
        self.signals = signals

    def progress(self, text, percent):

        self.signals.taskUpdate.emit(
            text,
            percent
        )

    def run(self):

        y = create_waveform(
            self.track["path"],
            self.progress
        )

        deck = getattr(
            self,
            "deck_target",
            "A"
        )

        self.signals.waveformReady.emit(
            y,
            self.track,
            deck
        )