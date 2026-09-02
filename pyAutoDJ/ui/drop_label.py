import os

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal


class DropLabel(QLabel):

    filesDropped = pyqtSignal(list)

    def __init__(self):

        super().__init__()

        self.setAcceptDrops(True)
		
        # Forza il widget ad accettare input mouse anche sopra altri
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) 
        self.raise_() 

        self.setAlignment(Qt.AlignCenter)

        self.setText(
            "DROP AUDIO FILES / FOLDER HERE"
        )

        self.setStyleSheet("""
            background:#1a1a1a;
            border:2px dashed #444;
            border-radius:10px;
            color:#888;
        """)

    def dragEnterEvent(self, e):

        if e.mimeData().hasUrls():
            e.accept()

    def dropEvent(self, e):

        files = []

        for url in e.mimeData().urls():

            path = url.toLocalFile()

            if os.path.isdir(path):

                for root, _, names in os.walk(path):

                    for n in names:

                        if n.lower().endswith((
                            ".mp3",
                            ".wav",
                            ".flac",
                            ".ogg"
                        )):

                            files.append(
                                os.path.join(root, n)
                            )

            else:

                if path.lower().endswith((
                    ".mp3",
                    ".wav",
                    ".flac",
                    ".ogg"
                )):

                    files.append(path)

        self.filesDropped.emit(files)
