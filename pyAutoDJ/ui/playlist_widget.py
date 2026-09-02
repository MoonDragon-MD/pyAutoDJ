from PyQt5.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView          # per sistema dinamico colonne
)
from PyQt5.QtCore import Qt


class PlaylistWidget(QTreeWidget):

    def __init__(self):

        super().__init__()

        self.setColumnCount(3)

        self.setHeaderLabels([
            "TITLE",
            "ARTIST",
            "TIME"
        ])

        self.setAlternatingRowColors(True)

        self.setStyleSheet("""
            QTreeWidget{
                background:#181818;
                border:1px solid #333;
                color:#ddd;
                alternate-background-color:#202020;
            }

            QHeaderView::section{
                background:#202020;
                color:#00ff88;
                padding:6px;
                border:none;
            }
        """)
		
        # ===================== LARGHEZZA DINAMICA COLONNE=====================
        header = self.header()
        
        # Titolo prende la maggior parte dello spazio disponibile
        header.setSectionResizeMode(0, QHeaderView.Stretch)   # TITLE → si espande
        
        # Artista e Time hanno larghezza fissa ma ragionevole
        header.setSectionResizeMode(1, QHeaderView.Interactive)  # ARTIST
        header.setSectionResizeMode(2, QHeaderView.Fixed)        # TIME

        # Larghezze di default
        self.setColumnWidth(0, 420)   # TITLE (verrà espanso)
        self.setColumnWidth(1, 290)   # ARTIST
        self.setColumnWidth(2, 95)    # TIME

        # Larghezza minima per evitare che le colonne diventino troppo piccole
        self.header().setMinimumSectionSize(90)

        # Impedisce che l'ultima colonna prenda tutto lo spazio rimanente
        self.header().setStretchLastSection(False)

    def add_track(self, track):

        mins = int(track["duration"] // 60)
        secs = int(track["duration"] % 60)

        item = QTreeWidgetItem([

            track["title"],
            track["artist"],
            f"{mins}:{secs:02d}"

        ])

        self.addTopLevelItem(item)

        return item