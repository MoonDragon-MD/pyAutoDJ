import os, sys

# Per avviare con due istanze su Linux usare (su Windows viene ignorato):
# python3 main.py -2vlc   oppure   python3 main.py --dual-vc

# ==== VLC PORTABLE BOOTSTRAP (decommentare per usare vlc portable) ====
# vlc/
# ├── libvlc.dll
# ├── libvlccore.dll
# └── plugins/   (full directory)
# base = os.path.dirname(os.path.abspath(__file__))
# vlc_dir = os.path.join(base, "vlc")
# if os.path.isdir(vlc_dir):
#     os.environ["PYTHON_VLC_LIB_PATH"] = os.path.join(vlc_dir, "libvlc.dll")
#     if hasattr(os, "add_dll_directory"):
#         os.add_dll_directory(vlc_dir)
#     os.environ["PATH"] = vlc_dir + os.pathsep + os.environ.get("PATH", "")
# ==============================================================

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

from ui.main_window import AutoDJWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    base = os.path.dirname(os.path.abspath(__file__))

    # Icona multi-risoluzione
    app_icon = QIcon()
    app_icon.addFile(os.path.join(base, "assets/icons", "16.png"),  size=QSize(16, 16))
    app_icon.addFile(os.path.join(base, "assets/icons", "32.png"),  size=QSize(32, 32))
    app_icon.addFile(os.path.join(base, "assets/icons", "48.png"),  size=QSize(48, 48))
    app_icon.addFile(os.path.join(base, "assets/icons", "256.png"), size=QSize(256, 256))
    app.setWindowIcon(app_icon)

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
