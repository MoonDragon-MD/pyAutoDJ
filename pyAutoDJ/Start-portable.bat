@echo off
cd /d "%~dp0"

if not exist "python\python.exe" goto SETUP_MISSING

python\python.exe main.py %*
goto :eof

:SETUP_MISSING
echo.
echo  ===============================================
echo   Python non trovato nella cartella "python"!
echo ===============================================
echo.
echo  Configurazione manuale (una volta sola):
echo.
echo  1. Scarica Python embeddable:
echo     https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip
echo.
echo  2. Estrai il contenuto dello zip in una cartella "python"
echo     accanto a questo file bat:
echo.
echo     pyAutoDJ\
echo       Start-portable.bat
echo       main.py
echo       python\           ^<-- qui dentro python.exe
echo.
echo  3. Apri un prompt dei comandi in questa cartella e lancia:
echo.
echo     cd python
echo     curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
echo     python get-pip.py
echo     python -m pip install PyQt5 python-vlc soundfile numpy librosa mutagen pyqtgraph scipy
echo.
echo  4. Modifica il file python\python312._pth aggiungendo/modificando:
echo.
echo     python312.zip
echo     .
echo     Lib
echo     Lib\site-packages
echo     Scripts
echo     ..
echo.
echo     # Uncomment to run site.main() automatically
echo     import site
echo.
echo  5. Rilancia Start-portable.bat
echo.
pause
