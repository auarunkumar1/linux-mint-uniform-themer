#!/usr/bin/env python3
"""Unified Cinnamon Uniform Theming, Cursors & Flatpak Manager CLI and TUI launcher."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from theme_data import PRESETS, ICON_PACKS
from theme_manager import ThemeManager

def print_status(manager: ThemeManager):
    status = manager.get_status()
    print("=" * 64)
    print("  Cinnamon Desktop & Flatpak Uniform Theming Status")
    print("=" * 64)
    print(f" GTK Application Theme       : {status['gtk_theme']}")
    print(f" Cinnamon Shell Theme        : {status['cinnamon_theme']}")
    print(f" Icon Pack                   : {status['icon_theme']}")
    print(f" Cursor Theme                : {status['cursor_theme']} (Size: {status['cursor_size']})")
    print(f" Color Scheme Preference     : {status['color_scheme']}")
    
    adw_status = "ENABLED (Linked)" if status['gtk4_active'] else "DEFAULT (Unlinked)"
    print(f" GTK 4 / Libadwaita Sync     : {adw_status}")
    if status['gtk4_active']:
        print(f"   Target                    : {status['gtk4_target']}")

    fp_status = "SYNCHRONIZED (Filesystem + Env)" if status['flatpak_fs_synced'] else "UNCONFIGURED (Sandboxed)"
    print(f" Flatpak Sandbox Overrides   : {fp_status}")

    fc_status = "SYNCHRONIZED (Subpixel RGB + HintFull)" if status.get('fontconfig_synced') else "UNCONFIGURED (Grayscale blur)"
    print(f" Subpixel Anti-Blur (LCD)    : {fc_status}")
    if not status.get('fontconfig_synced'):
        print("-" * 64)
        print(" ⚠️  NOTICE: Flatpak text blurriness detected (Grayscale fallback).")
        print("    Run 'cinna-theme --fix-blur' or press [F] in TUI to enable anti-blur.")
    print("=" * 64)

def print_presets(manager: ThemeManager):
    print(f"{'ID':<18} {'Name':<24} {'Cursor':<24} {'Status'}")
    print("-" * 78)
    for p in PRESETS:
        installed = "Installed" if manager.is_preset_installed(p) else "Available for Download"
        print(f"{p.id:<18} {p.name:<24} {p.cursor_theme_name:<24} {installed}")

def cli_apply_preset(manager: ThemeManager, preset_id: str):
    preset = next((p for p in PRESETS if p.id.lower() == preset_id.lower()), None)
    if not preset:
        print(f"Error: Unknown preset '{preset_id}'. Run --list to see available options.")
        sys.exit(1)

    print(f"Applying suite '{preset.name}'...")
    if preset.id == "mint-default":
        manager.reset_to_defaults(print)
        print("Restored to Linux Mint defaults.")
        return

    success = manager.install_theme_preset(preset, print)
    if not success:
        print(f"Installation failed. Safely falling back to Linux Mint defaults (Mint-Y-Dark)...")
        manager.fallback_to_default(print)
        sys.exit(1)

    if preset.id.startswith("whitesur"):
        manager.install_icon_pack("whitesur-icons", print)
    elif preset.icon_download_url:
        manager.install_icon_archive(preset.icon_theme_name, preset.icon_download_url, print)

    if preset.cursor_download_url:
        manager.install_cursor_theme(preset.cursor_theme_name, preset.cursor_download_url, print)

    manager.apply_uniform_theming(
        gtk_theme=preset.gtk_theme_name,
        cinnamon_theme=preset.cinnamon_theme_name,
        icon_theme=preset.icon_theme_name,
        cursor_theme=preset.cursor_theme_name,
        mode=preset.mode,
        cursor_size=24,
        log=print
    )
    print("Finished.")

def main():
    parser = argparse.ArgumentParser(
        description="Unified Cinnamon Desktop, Libadwaita, Cursor & Flatpak Theme Synchronization Tool"
    )
    parser.add_argument("--status", action="store_true", help="Show current theming, cursor and sandbox status")
    parser.add_argument("--list", action="store_true", help="List available curated theme presets")
    parser.add_argument("--apply", metavar="PRESET_ID", help="Apply a theme preset directly without TUI")
    parser.add_argument("--sync-flatpak", action="store_true", help="Force sync host themes, icons & cursors to Flatpak")
    parser.add_argument("--fix-blur", action="store_true", help="Fix Flatpak text blurriness (Enforce subpixel RGB & High-DPI fontconfig)")
    parser.add_argument("--toggle-antiblur", action="store_true", help="Toggle subpixel font anti-blur and Flatpak overrides on/off")
    parser.add_argument("--fallback", action="store_true", help="Safety fallback: instantly restore Mint-Y-Dark system-wide")
    parser.add_argument("--reset", action="store_true", help="Restore system defaults (Mint-Y-Dark, default Bibata cursor & pure Adwaita)")
    parser.add_argument("--tui", action="store_true", help="Launch interactive TUI (default when no args provided)")

    args = parser.parse_args()
    manager = ThemeManager()

    if args.status:
        print_status(manager)
    elif args.list:
        print_presets(manager)
    elif args.fix_blur:
        manager.enable_antiblur(print)
    elif args.toggle_antiblur:
        manager.toggle_antiblur(print)
    elif args.sync_flatpak:
        status = manager.get_status()
        manager.sync_flatpak_overrides(
            status.get("gtk_theme", "Mint-Y-Dark"),
            status.get("icon_theme", "Mint-Y"),
            status.get("cursor_theme", "Bibata-Modern-Classic"),
            int(status.get("cursor_size") or 24),
            print
        )
    elif args.fallback or args.reset:
        manager.fallback_to_default(print)
    elif args.apply:
        cli_apply_preset(manager, args.apply)
    else:
        # Default: Launch TUI
        try:
            from tui import launch
            launch()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
