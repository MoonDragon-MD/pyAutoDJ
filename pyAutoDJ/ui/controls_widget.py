from PyQt5.QtWidgets import QLabel
from ui.drop_label import DropLabel
from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QHBoxLayout,
    QCheckBox
)

from PyQt5.QtCore import pyqtSignal

class ControlsWidget(QWidget):

    playPause = pyqtSignal()        # Fade a 12.5 sec dalla fine
    randomFade = pyqtSignal()       # Fade manuale immediato
    fadeNextMatch = pyqtSignal()    # Fade al prossimo match disponibile
    loadFiles = pyqtSignal()
    info = pyqtSignal()
    fxToggled = pyqtSignal(bool)
    autoFadeToggled = pyqtSignal(bool)   # segnale corretto

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        self.playBtn = QPushButton("PLAY")
        self.fadeBtn = QPushButton("FADE NOW")          # Manual fade
        self.fadeMatchBtn = QPushButton("FADE NEXT MATCH") # Fade al prossimo match disponibile
        self.fxCheck = QCheckBox("FX")
        self.loadBtn = QPushButton("LOAD FILES / FOLDER")
        self.infoBtn = QPushButton("INFO")
        self.autoFadeCheck = QCheckBox("Auto Random Fade")

        button_style = """
            QPushButton{
                background:#1e1e1e;
                border:1px solid #333;
                border-radius:10px;
            }
            QPushButton:hover{
                border:1px solid #00ff88;
            }
            QPushButton:checked{
                background:#00aa66;
                border:2px solid #00ff88;
            }
        """
        self.default_button_style = button_style
        # Stile normale
        for b in [self.playBtn, self.fadeBtn, self.fadeMatchBtn, self.loadBtn, self.infoBtn]:
            b.setMinimumHeight(50)
            b.setStyleSheet(button_style)

        self.autoFadeCheck.setStyleSheet("""
            QCheckBox { 
                color: #ddd; 
                padding: 8px; 
                font-size: 14px;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QCheckBox::indicator { 
                width: 20px; 
                height: 20px;
                border: 2px solid #00ff88;
                border-radius: 3px;
                background: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background: #00aa66;
                border: 2px solid #00ff88;
            }
        """)
        
        self.fxCheck.setStyleSheet("""
            QCheckBox { 
                color: #ddd; 
                padding: 8px; 
                font-size: 14px;
                border: 1px solid #555;
                border-radius: 4px;
            }

            QCheckBox::indicator { 
                width: 20px; 
                height: 20px;
                border: 2px solid #00ff88;
                border-radius: 3px;
                background: #1a1a1a;
            }

            QCheckBox::indicator:checked {
                background: #00aa66;
                border: 2px solid #00ff88;
            }
        """)

        self.dropLabel = DropLabel()
        self.dropLabel.setMinimumHeight(100)
        self.dropLabel.setStyleSheet("""
            background:#1a1a1a;
            border:2px dashed #444;
            border-radius:10px;
            color:#888;
        """)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar{ background:#111; border:none; }
            QProgressBar::chunk{ background:#00ff88; }
        """)
        self.progress.hide()
        
        self.taskLabel = QLabel("")
        self.taskLabel.setStyleSheet("""
            color:#00ff88;
            font-size:12px;
        """)
		
        layout.addWidget(self.taskLabel)

        layout.addWidget(self.playBtn)
        layout.addWidget(self.fadeBtn)
        layout.addWidget(self.fadeMatchBtn)
        checks = QHBoxLayout()

        checks.addWidget(self.autoFadeCheck)
        checks.addWidget(self.fxCheck)

        layout.addLayout(checks)

        layout.addSpacing(20)
        layout.addWidget(self.loadBtn)
        layout.addWidget(self.dropLabel)
        layout.addSpacing(20)
        layout.addWidget(self.infoBtn)
        layout.addWidget(self.progress)
        layout.addStretch()

        # Connessioni
        self.playBtn.clicked.connect(self.playPause.emit)
        self.fadeBtn.clicked.connect(self.randomFade.emit)
        self.fadeMatchBtn.clicked.connect(self.fadeNextMatch.emit)
        self.loadBtn.clicked.connect(self.loadFiles.emit)
        self.infoBtn.clicked.connect(self.info.emit)
        self.autoFadeCheck.toggled.connect(self.autoFadeToggled.emit)

        self.fxCheck.toggled.connect(
            self.fxToggled.emit
        )

    def set_play_button_text(self, is_playing: bool):
        if is_playing:
            self.playBtn.setText("PAUSE")
        else:
            self.playBtn.setText("PLAY")
			
    def set_match_waiting(self, waiting: bool):

        if waiting:

            self.fadeMatchBtn.setStyleSheet("""
                QPushButton{
                    background:#1e1e1e;
                    border:2px solid #ffaa00;
                    color:#ffaa00;
                    border-radius:10px;
                }
            """)

        else:

            self.fadeMatchBtn.setStyleSheet(
                self.default_button_style
            )  # FADE NEXT MATCH torna allo stile di default
			
    def dropEvent(self, event):
        # Assicurati che l'evento arrivi al dropLabel
        if event.mimeData().hasUrls():
        # Delega direttamente al DropLabel
            self.dropLabel.dropEvent(event)
            event.acceptProposedAction()
        else:
            event.ignore()