from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):

    trackAnalyzed = pyqtSignal(object, object)
    waveformReady = pyqtSignal(object, object, str)
    playlistReady = pyqtSignal(list)

    loadingStarted = pyqtSignal()
    loadingFinished = pyqtSignal()

    loadingProgress = pyqtSignal(int)

    taskUpdate = pyqtSignal(str, int)

    error = pyqtSignal(str)
    # SEGNALE PER I DEBUG
    debugLog = pyqtSignal(str) 