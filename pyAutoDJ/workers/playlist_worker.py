from PyQt5.QtCore import QRunnable

from core.playlist_engine import build_playlist


class PlaylistWorker(QRunnable):

    def __init__(self, library, signals):

        super().__init__()

        self.library = library.copy()
        self.signals = signals

    def progress(self, text, percent):

        self.signals.taskUpdate.emit(
            text,
            percent
        )

    def run(self):

        playlist = build_playlist(
            self.library,
            self.progress
        )

        self.signals.playlistReady.emit(
            playlist
        )