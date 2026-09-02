from PyQt5.QtCore import QRunnable
from analysis.audio_analysis import analyze_track


class AnalyzeWorker(QRunnable):

    def __init__(self, path, signals, item):

        super().__init__()

        self.path = path
        self.signals = signals
        self.item = item

    def progress(self, text, percent):

        self.signals.taskUpdate.emit(
            text,
            percent
        )

    def run(self):

        track = analyze_track(
            self.path,
            self.progress
        )

        self.signals.trackAnalyzed.emit(
            track,
            self.item
        )