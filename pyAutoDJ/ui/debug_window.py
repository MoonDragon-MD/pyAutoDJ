from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

class DebugWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debug Console")
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 10))
        self.text_edit.setStyleSheet("""
            QTextEdit { background-color: #111; color: #00ff88; border: 1px solid #444; }
        """)
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_close = QPushButton("Close")
        self.btn_clear.clicked.connect(self.text_edit.clear)
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    @pyqtSlot(str)
    def append_log(self, text):
        """Slot per ricevere i log dal segnale"""
        self.text_edit.insertPlainText(text)
        # Scroll automatico
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
