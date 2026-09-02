import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import AutoDJWindow

# Per avviare con due istanze su Linux vlc usare (su windows verrà ignorato causa problemi WASAPI)
# python3 main.py -2vlc
# oppure 
# python3 --dual-vc

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # FIX WINDOWS: la dual instance VLC su Windows gracchia nel crossfade
    # (due stream WASAPI con clock indipendenti). La teniamo solo su Linux.
    use_separate_vlc = (
        ("-2vlc" in sys.argv or "--dual-vc" in sys.argv)
        and not sys.platform.startswith("win")
    )
    
    app.setStyleSheet("""
        QWidget{
            background:#0f0f0f;
            color:#ddd;
            font-size:14px;
        }
    """)

    win = AutoDJWindow(use_separate_vlc=use_separate_vlc)
    win.show()

    sys.exit(app.exec_())