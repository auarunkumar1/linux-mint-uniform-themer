#!/usr/bin/env bash
# Linux Mint Uniform Themer - Installation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

echo "=================================================="
echo "  Installing Linux Mint Uniform Themer"
echo "=================================================="

mkdir -p "$BIN_DIR" "$APP_DIR"

# Ensure execution rights
chmod +x "$SCRIPT_DIR/cinna_theme.py"

# Symlink executable
ln -sf "$SCRIPT_DIR/cinna_theme.py" "$BIN_DIR/cinna-theme"
echo "✓ Symlinked executable to $BIN_DIR/cinna-theme"

# Install desktop entry
cat << 'EOF' > "$APP_DIR/cinnamon-theme-sync.desktop"
[Desktop Entry]
Name=Cinnamon Theme Sync
Comment=Uniform theming manager for GTK 3, Libadwaita, Cinnamon & Flatpaks
Exec=x-terminal-emulator -e cinna-theme
Icon=preferences-desktop-theme
Terminal=false
Type=Application
Categories=Settings;DesktopSettings;GTK;
Keywords=theme;cinnamon;gtk;flatpak;libadwaita;nordic;catppuccin;whitesur;gruvbox;
StartupNotify=true
EOF

chmod +x "$APP_DIR/cinnamon-theme-sync.desktop"
echo "✓ Installed desktop launcher to $APP_DIR/cinnamon-theme-sync.desktop"

echo ""
echo "Installation complete!"
echo "Run 'cinna-theme' in any terminal or launch 'Cinnamon Theme Sync' from your Cinnamon application menu."
echo "=================================================="
