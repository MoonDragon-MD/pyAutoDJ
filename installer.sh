#!/bin/bash

################################################################################
# pyAutoDJ Installer
# Installs pyAutoDJ and creates a shortcut in the applications menu
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR=""
LOCAL_APPS="$HOME/.local/share/applications"
DESKTOP_FILE="$LOCAL_APPS/pyAutoDJ.desktop"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              pyAutoDJ Installer (Linux)                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Verify we're in the correct pyAutoDJ folder
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
    echo -e "${YELLOW}⚠️  main.py file not found in the current folder.${NC}"
    echo "You should run this script from the pyAutoDJ root directory."
    echo ""
    
    read -p "Please enter the full path of the pyAutoDJ folder: " MANUAL_PATH
    SCRIPT_DIR="$MANUAL_PATH"
    
    if [ ! -f "$SCRIPT_DIR/main.py" ]; then
        echo -e "${RED}❌ Error: $SCRIPT_DIR/main.py does not exist.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Detected pyAutoDJ folder at: $SCRIPT_DIR${NC}"
echo ""

# 2. Ask where to install permanently
DEFAULT_INSTALL="$HOME/Documents/pyAutoDJ"
read -p "Where do you want to install pyAutoDJ permanently? [$DEFAULT_INSTALL]: " INSTALL_DIR

if [ -z "$INSTALL_DIR" ]; then
    INSTALL_DIR="$DEFAULT_INSTALL"
fi

# Normalize path (remove trailing slash)
INSTALL_DIR="${INSTALL_DIR%/}"

echo ""
echo -e "${YELLOW}⚙️  Installation path: $INSTALL_DIR${NC}"

# 3. Check if directory exists and already contains pyAutoDJ
if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/main.py" ]; then
    echo -e "${YELLOW}⚠️  pyAutoDJ seems to be already installed in this location.${NC}"
    read -p "Overwrite existing files? (y/N): " OVERWRITE
    
    if [[ "$OVERWRITE" != "y" && "$OVERWRITE" != "Y" ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# 4. Create directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${GREEN}Creating directory: $INSTALL_DIR${NC}"
    mkdir -p "$INSTALL_DIR"
fi

# 5. Copy all files
echo -e "${GREEN}Copying files...${NC}"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Files copied successfully.${NC}"
else
    echo -e "${RED}❌ Error copying files.${NC}"
    exit 1
fi

# 6. Make scripts executable
chmod +x "$INSTALL_DIR/avvia.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/avvia_2vlc.sh" 2>/dev/null || true

# 7. Create assets/icons directory if it doesn't exist
mkdir -p "$INSTALL_DIR/assets"

# 8. Copy icon if exists, otherwise create placeholder
if [ -f "$SCRIPT_DIR/assets/NA.png" ]; then
    cp "$SCRIPT_DIR/assets/NA.png" "$INSTALL_DIR/assets/NA.png"
    ICON_PATH="$INSTALL_DIR/assets/NA.png"
elif [ -f "$SCRIPT_DIR/assets/icon.png" ]; then
    cp "$SCRIPT_DIR/assets/icon.png" "$INSTALL_DIR/assets/icon.png"
    ICON_PATH="$INSTALL_DIR/assets/icon.png"
else
    # Placeholder icon (base64 encoded 16x16 pixel)
    echo -e "${YELLOW}⚠️  Icon not found. Creating placeholder icon...${NC}"
    cat > "$INSTALL_DIR/assets/pyautodj_icon.png" << 'ICONEOF'
iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAFKSURB
VDiNpdMxahtRGMfx/2Vm9/YsO5Jty5ZtOWkcuEmDQwuFQqGQoUPHQqFDoZDhD+kQOvQPOnQs
FMpw6NChUMhQKBQKFQqFQqFQqFAoVCgUCoVCoVAoFAqFQqH8gU0iQ4f84cO99+793/u+d4QQ
QgghhBBCCCGEEEIIIYSQ/zKbzWYjwM1mszlgB7gJ3AJuAXcBN4EbQLfb/T0ajf4Gw+FwCNgG
bgDXgWvAVeAKcAG4CFwAzgNXgYvhcPi3bdt/s9lslW17yzRNB9M0HVRVtaqq6lRVNVVV1aqq
qm3btn3//v2/AwB4ngfLshAIBBAMBxUEIQgCgiDIcRwFQRBkWRYikQi2bt3i4OBgf7fb/b1t
2/+y2WyVbXvLNJ2hKAohhJC2bcuxbDtd16XrurRtm7Zt03Vduq5L13Xpui5d16XrunRdl67r
0nVduq5L13Xpui5d16XrunRdl67r0nVduq5L13Xpuu5/GQAfAgAAAP//AwDxgH4C9g==
ICONEOF
    ICON_PATH="$INSTALL_DIR/assets/pyautodj_icon.png"
fi

# 9. Create .desktop file
echo -e "${GREEN}Creating shortcut in applications menu...${NC}"

# Use absolute path for Exec and Icon
ABS_INSTALL_DIR="$(realpath "$INSTALL_DIR")"
ABS_ICON_PATH="$(realpath "$ICON_PATH")"

cat > "$DESKTOP_FILE" << DESKEOF
[Desktop Entry]
Name=pyAutoDJ
Comment=Automatically mixes songs like a DJ
Exec=$ABS_INSTALL_DIR/avvia.sh
Icon=$ABS_ICON_PATH
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Music;Utility;
Keywords=DJ;Music;Audio;Mix;Playlist;
StartupNotify=true
DesktopNames=Unity;GNOME;XFCE;KDE;
DESKEOF

# 10. Make .desktop file readable
chmod 644 "$DESKTOP_FILE"

# 11. Update application database
update-desktop-database "$LOCAL_APPS" 2>/dev/null || true
update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   Installation Complete                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${GREEN}✓ pyAutoDJ installed at:${NC} $ABS_INSTALL_DIR"
echo -e "${GREEN}✓ Shortcut created at:${NC} $DESKTOP_FILE"
echo ""
echo -e "${YELLOW}💡 To launch:${NC}"
echo "   - Via applications menu (search \"pyAutoDJ\")"
echo "   - Or execute: $ABS_INSTALL_DIR/avvia.sh"
echo ""
echo -e "${YELLOW}ℹ️  Note:${NC} Python dependencies must be installed first:"
echo "   pip install PyQt5 vlc librosa numpy mutagen soundfile pyqtgraph"
echo ""
echo -e "${GREEN}Thank you for installing pyAutoDJ! 🎧${NC}"
echo ""
