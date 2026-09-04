@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  ==============================================================
echo                pyAutoDJ Installer (Windows)
echo  ==============================================================
echo.

REM ================================================================
REM 1. Verify we're in the correct pyAutoDJ folder
REM ================================================================
if not exist "%~dp0main.py" goto WRONG_FOLDER

echo  [OK] pyAutoDJ folder detected: %~dp0
echo.

REM ================================================================
REM 2. Ask where to install permanently
REM ================================================================
set "DEFAULT_INSTALL=%USERPROFILE%\Documents\pyAutoDJ"
set "INSTALL_DIR="

set /p INSTALL_DIR="Where do you want to install pyAutoDJ? [%DEFAULT_INSTALL%]: "
if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%DEFAULT_INSTALL%"
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"

echo.
echo  [..] Installation path: !INSTALL_DIR!

REM ================================================================
REM 3. Check for existing installation
REM ================================================================
if exist "!INSTALL_DIR!\main.py" (
    echo.
    echo  pyAutoDJ seems to be already installed in this location.
    set /p OVERWRITE="Overwrite existing files? (y/N): "
    if /i not "!OVERWRITE!"=="y" (
        echo  Installation cancelled.
        pause
        goto :eof
    )
)

REM ================================================================
REM 4. Copy files
REM ================================================================
echo  [..] Copying files...
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!"
xcopy "%~dp0*" "!INSTALL_DIR!\" /E /Y /Q >nul
if errorlevel 1 goto COPY_FAIL
echo  [OK] Files copied successfully.

REM ================================================================
REM 5. Verify application icon
REM ================================================================
set "ICON=!INSTALL_DIR!\assets\icona.ico"
if exist "!ICON!" (
    echo  [OK] Icon found: !ICON!
) else (
    echo  [WARN] assets\icona.ico not found: shortcuts will have no icon.
    set "ICON="
)

REM ================================================================
REM 6. Check Python and dependencies
REM ================================================================
where python >nul 2>nul
if errorlevel 1 goto NO_PYTHON

python --version >nul 2>nul
if errorlevel 1 goto NO_PYTHON

echo.
echo  [OK] Python found.
set /p INSTALL_DEPS="Install/update Python dependencies now? (y/N): "
if /i not "!INSTALL_DEPS!"=="y" goto SHORTCUT

echo.
echo  [..] Installing Python dependencies (this may take a few minutes)...
python -m pip install --upgrade pip
python -m pip install PyQt5 python-vlc soundfile numpy librosa mutagen pyqtgraph scipy
if errorlevel 1 (
    echo  [WARN] Some dependencies may have failed. You can retry manually with:
    echo         python -m pip install PyQt5 python-vlc soundfile numpy librosa mutagen pyqtgraph scipy
) else (
    echo  [OK] Dependencies installed.
)

REM ================================================================
REM 7. Check VLC installation
REM ================================================================
:SHORTCUT
echo.
set "VLC_FOUND=0"
if exist "%ProgramFiles%\VideoLAN\VLC\vlc.exe" set "VLC_FOUND=1"
if exist "%ProgramFiles(x86)%\VideoLAN\VLC\vlc.exe" set "VLC_FOUND=1"
if exist "%LOCALAPPDATA%\VideoLAN\VLC\vlc.exe" set "VLC_FOUND=1"

if "!VLC_FOUND!"=="1" (
    echo  [OK] VLC installation detected.
) else (
    echo  [WARN] VLC was not found in the standard locations.
    echo         pyAutoDJ needs VLC to play audio. Download it from:
    echo         https://www.videolan.org/vlc/
    echo         Alternatively, use the portable VLC folder mode with Start-portable.bat
)

REM ================================================================
REM 8. Create shortcuts (Start Menu + Desktop)
REM ================================================================
echo.
echo  [..] Creating shortcuts...

powershell -NoProfile -Command ^
"$ws = New-Object -ComObject WScript.Shell;" ^
"$sm = [Environment]::GetFolderPath('StartMenu') + '\Programs';" ^
"$lnk = $ws.CreateShortcut($sm + '\pyAutoDJ.lnk');" ^
"$lnk.TargetPath = '!INSTALL_DIR!\Start-win.bat';" ^
"$lnk.WorkingDirectory = '!INSTALL_DIR!';" ^
"$lnk.IconLocation = '!INSTALL_DIR!\assets\icona.ico, 0';" ^
"$lnk.Description = 'pyAutoDJ - Automatic DJ mixing';" ^
"$lnk.Save()"

if exist "%USERPROFILE%\Desktop" (
    powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$lnk = $ws.CreateShortcut($env:USERPROFILE + '\Desktop\pyAutoDJ.lnk');" ^
    "$lnk.TargetPath = '!INSTALL_DIR!\Start-win.bat';" ^
    "$lnk.WorkingDirectory = '!INSTALL_DIR!';" ^
    "$lnk.IconLocation = '!INSTALL_DIR!\assets\icona.ico, 0';" ^
    "$lnk.Save()"
)

echo  [OK] Shortcuts created (Start Menu and Desktop).

echo.
echo  ==============================================================
echo                  Installation Complete
echo  ==============================================================
echo.
echo  pyAutoDJ installed at:   !INSTALL_DIR!
echo  Shortcuts created in:    Start Menu and Desktop
echo.
echo  To launch:
echo    - Double-click the "pyAutoDJ" shortcut in the Start Menu
echo    - Or run: !INSTALL_DIR!\Start-win.bat
echo.
echo  Required Python dependencies (if not installed above):
echo    pip install PyQt5 python-vlc librosa numpy mutagen soundfile pyqtgraph scipy
echo.
echo  VLC media player must also be installed:
echo    https://www.videolan.org/vlc/
echo.
pause
goto :eof

REM ================================================================
REM Error exit points
REM ================================================================
:COPY_FAIL
echo  [ERROR] File copy failed. Check permissions and disk space.
pause
goto :eof

:NO_PYTHON
echo.
echo  [ERROR] Python not found in system PATH.
echo.
echo  Install Python from: https://www.python.org/downloads/
echo  IMPORTANT: during installation, check
echo  "Add Python to PATH"
echo.
echo  Alternatively, use the portable mode with Start-portable.bat
echo.
pause
goto :eof
