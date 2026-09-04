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
NC='\033[0m'

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
chmod +x "$INSTALL_DIR/Start.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/Start_2vlc.sh" 2>/dev/null || true

# 7. Create assets directory if it doesn't exist
mkdir -p "$INSTALL_DIR/assets"

# 8. Verify the application icon exists
if [ -f "$INSTALL_DIR/assets/icona.png" ]; then
    ICON_PATH="$INSTALL_DIR/assets/icona.png"
    echo -e "${GREEN}✓ Icon found: $ICON_PATH${NC}"
else
    echo -e "${YELLOW}⚠️  assets/icona.png not found. The shortcut will have no icon.${NC}"
    ICON_PATH=""
fi

# 9. Create .desktop file
echo -e "${GREEN}Creating shortcut in applications menu...${NC}"

ABS_INSTALL_DIR="$(realpath "$INSTALL_DIR")"

cat > "$DESKTOP_FILE" << DESKEOF
[Desktop Entry]
Name=pyAutoDJ
Comment=Automatically mixes songs like a DJ
Exec=$ABS_INSTALL_DIR/Start.sh
Icon=$ABS_INSTALL_DIR/assets/icona.png
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
echo "   - Or execute: $ABS_INSTALL_DIR/Start.sh"
echo ""
echo -e "${YELLOW}ℹ️  Note:${NC} Python dependencies must be installed first:"
echo "   pip install PyQt5 python-vlc librosa numpy mutagen soundfile pyqtgraph scipy"
echo ""
echo -e "${GREEN}Thank you for installing pyAutoDJ! 🎧${NC}"
echo ""
