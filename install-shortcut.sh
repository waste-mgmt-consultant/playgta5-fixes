#!/bin/bash
# Installs the Play GTA5 desktop shortcut for the current user on Linux.
# Creates entries on the Desktop and in the application menu, then marks them trusted.
set -eu
REPO="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$REPO/PlayGTA5.desktop"

if [ ! -f "$DESKTOP_FILE" ]; then
    echo "PlayGTA5.desktop not found next to this script."
    exit 1
fi

chmod +x "$DESKTOP_FILE"
mkdir -p "$HOME/.local/share/applications"
cp -f "$DESKTOP_FILE" "$HOME/.local/share/applications/PlayGTA5.desktop"
chmod +x "$HOME/.local/share/applications/PlayGTA5.desktop"

# Desktop path (respect XDG if set).
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
mkdir -p "$DESKTOP_DIR"
cp -f "$DESKTOP_FILE" "$DESKTOP_DIR/PlayGTA5.desktop"
chmod +x "$DESKTOP_DIR/PlayGTA5.desktop"

# Mark trusted (Cinnamon/GNOME/Nautilus) so double-click launches it.
gio set "$DESKTOP_DIR/PlayGTA5.desktop" metadata::trusted true 2>/dev/null || true

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "Installed:"
echo "  $DESKTOP_DIR/PlayGTA5.desktop"
echo "  $HOME/.local/share/applications/PlayGTA5.desktop"
echo "Double-click the icon, or find 'Play GTA5 (Local)' in the application menu."
