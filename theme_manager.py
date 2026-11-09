"""Theme, Cursor, and Flatpak synchronization engine for Cinnamon Desktop."""

import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from theme_data import PRESETS, ICON_PACKS, ThemePreset

HOME = Path.home()
THEMES_DIR = HOME / ".themes"
ICONS_DIR = HOME / ".local" / "share" / "icons"
USER_ICONS_DIR = HOME / ".icons"
GTK3_CONFIG_DIR = HOME / ".config" / "gtk-3.0"
GTK4_CONFIG_DIR = HOME / ".config" / "gtk-4.0"
FONTCONFIG_DIR = HOME / ".config" / "fontconfig"
FONTCONFIG_FILE = FONTCONFIG_DIR / "fonts.conf"
SYSTEM_THEMES_DIR = Path("/usr/share/themes")
SYSTEM_ICONS_DIR = Path("/usr/share/icons")

class ThemeManager:
    def __init__(self):
        THEMES_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
        USER_ICONS_DIR.mkdir(parents=True, exist_ok=True)
        GTK3_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        GTK4_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        FONTCONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def run_cmd(self, cmd: List[str], check: bool = False, env_extra: Optional[Dict[str, str]] = None, input_text: Optional[str] = None) -> Tuple[int, str]:
        """Execute a shell command with proper user-bin paths and return exit code and stripped output."""
        try:
            env = os.environ.copy()
            env["PATH"] = f"{HOME}/.local/bin:{env.get('PATH', '')}"
            env["LD_LIBRARY_PATH"] = f"{HOME}/.local/lib:{env.get('LD_LIBRARY_PATH', '')}"
            if env_extra:
                env.update(env_extra)
            res = subprocess.run(
                cmd,
                input=input_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=check,
                env=env
            )
            return res.returncode, res.stdout.strip()
        except Exception as e:
            return -1, str(e)

    def ensure_cursor_in_user_space(self, cursor_name: str, log: Callable[[str], None] = lambda m: None) -> bool:
        """Ensure the cursor theme is available in ~/.icons so Flatpak sandboxes can access it."""
        if not cursor_name:
            return False

        target_dir = USER_ICONS_DIR / cursor_name
        if target_dir.exists() and (target_dir / "cursors").exists():
            return True

        candidates = [
            ICONS_DIR / cursor_name,
            SYSTEM_ICONS_DIR / cursor_name
        ]

        for cand in candidates:
            if cand.exists() and (cand / "cursors").exists():
                log(f"Shadowing cursor theme '{cursor_name}' from {cand} to ~/.icons for Flatpak access...")
                try:
                    if target_dir.exists():
                        shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.copytree(cand, target_dir, symlinks=True)
                    log(f"Cursor '{cursor_name}' successfully copied to ~/.icons.")
                    return True
                except Exception as e:
                    log(f"Warning: Failed to copy cursor '{cursor_name}' to ~/.icons: {e}")
                    return False

        return False

    def ensure_theme_in_user_space(self, theme_name: str, log: Callable[[str], None] = lambda m: None) -> bool:
        """Ensure the GTK theme is available in ~/.themes so Flatpak sandboxes can access it."""
        if not theme_name:
            return False

        target_dir = THEMES_DIR / theme_name
        if target_dir.exists() and (target_dir / "gtk-3.0").exists():
            return True

        candidates = [
            HOME / ".local" / "share" / "themes" / theme_name,
            SYSTEM_THEMES_DIR / theme_name
        ]

        for cand in candidates:
            if cand.exists() and ((cand / "gtk-3.0").exists() or (cand / "cinnamon").exists()):
                log(f"Shadowing system theme '{theme_name}' from {cand} to ~/.themes for Flatpak access...")
                try:
                    if target_dir.exists():
                        shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.copytree(cand, target_dir, symlinks=True)
                    log(f"Theme '{theme_name}' successfully copied to ~/.themes.")
                    return True
                except Exception as e:
                    log(f"Warning: Failed to copy theme '{theme_name}' to ~/.themes: {e}")
                    return False

        return False

    def update_xresources_cursor(self, cursor_theme: str, cursor_size: int, log: Callable[[str], None] = lambda m: None):
        """Update xrdb and ~/.Xresources with active Xcursor settings for X11 & Flatpak compatibility."""
        if not cursor_theme:
            return
        xres_content = f"Xcursor.theme: {cursor_theme}\nXcursor.size: {cursor_size}\n"
        code, out = self.run_cmd(["xrdb", "-merge"], input_text=xres_content)
        if code == 0:
            log("Merged Xcursor settings into active X server via xrdb.")
        else:
            log(f"xrdb note: {out}")

        xres_file = HOME / ".Xresources"
        try:
            lines = []
            if xres_file.exists():
                for line in xres_file.read_text().splitlines():
                    if not line.strip().startswith(("Xcursor.theme:", "Xcursor.size:")):
                        lines.append(line)
            lines.append(f"Xcursor.theme: {cursor_theme}")
            lines.append(f"Xcursor.size: {cursor_size}")
            xres_file.write_text("\n".join(lines) + "\n")
            log("Updated ~/.Xresources with Xcursor settings.")
        except Exception as e:
            log(f"Could not update ~/.Xresources: {e}")

    def get_font_dpi_and_scale(self) -> Tuple[int, float, int]:
        """Detect active Cinnamon text-scaling-factor and DPI for crisp font rendering."""
        scale_val = 1.0
        try:
            scale_str = self.get_gsetting("org.cinnamon.desktop.interface", "text-scaling-factor")
            if scale_str:
                scale_val = float(scale_str)
        except Exception:
            scale_val = 1.0

        dpi = int(round(96 * scale_val))
        try:
            code, out = self.run_cmd(["xrdb", "-query"])
            if code == 0:
                for line in out.splitlines():
                    if line.startswith("Xft.dpi:"):
                        val = line.split(":", 1)[1].strip()
                        dpi = int(val)
                        break
        except Exception:
            pass

        gtk_xft_dpi = dpi * 1024
        return dpi, scale_val, gtk_xft_dpi

    def ensure_subpixel_fontconfig(self, log: Callable[[str], None] = lambda m: None):
        """Enforce subpixel RGB antialiasing, LCD default filtering and full hinting across host & Flatpak."""
        FONTCONFIG_DIR.mkdir(parents=True, exist_ok=True)
        fonts_conf_content = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- Enforce Subpixel RGB Antialiasing and Full Hinting for razor-sharp text -->
  <match target="font">
    <edit mode="assign" name="antialias"><bool>true</bool></edit>
    <edit mode="assign" name="hinting"><bool>true</bool></edit>
    <edit mode="assign" name="hintstyle"><const>hintfull</const></edit>
    <edit mode="assign" name="rgba"><const>rgb</const></edit>
    <edit mode="assign" name="lcdfilter"><const>lcddefault</const></edit>
  </match>
</fontconfig>
"""
        try:
            if not FONTCONFIG_FILE.exists() or "lcdfilter" not in FONTCONFIG_FILE.read_text():
                FONTCONFIG_FILE.write_text(fonts_conf_content)
                log("Configured subpixel RGB antialiasing & LCD filter in ~/.config/fontconfig/fonts.conf.")
        except Exception as e:
            log(f"Notice: Could not write fontconfig file: {e}")

    def sync_electron_and_chromium_anti_blur(self, log: Callable[[str], None] = lambda m: None):
        """Configure crisp subpixel font rendering and native Wayland/X11 flags for Chromium and Electron Flatpaks."""
        var_app = HOME / ".var" / "app"
        if not var_app.exists():
            return

        flags_content = (
            "--enable-font-antialiasing\n"
            "--font-render-hinting=medium\n"
            "--ozone-platform-hint=auto\n"
        )

        app_flag_files = {
            "com.brave.Browser": "brave-flags.conf",
            "com.google.Chrome": "chrome-flags.conf",
            "org.chromium.Chromium": "chromium-flags.conf",
            "com.vscodium.codium": "codium-flags.conf",
            "com.visualstudio.code": "code-flags.conf",
            "com.discordapp.Discord": "discord-flags.conf",
            "com.spotify.Client": "spotify-flags.conf",
            "com.slack.Slack": "slack-flags.conf",
            "md.obsidian.Obsidian": "obsidian-flags.conf",
        }

        for app_dir in var_app.iterdir():
            if not app_dir.is_dir():
                continue
            app_id = app_dir.name
            config_dir = app_dir / "config"
            if not config_dir.exists():
                continue

            target_filename = app_flag_files.get(app_id, "electron-flags.conf")
            flag_file = config_dir / target_filename
            try:
                if not flag_file.exists():
                    flag_file.write_text(flags_content)
                    log(f"Configured crisp font & Ozone flags for {app_id} ({target_filename}).")
                else:
                    curr = flag_file.read_text()
                    if "--enable-font-antialiasing" not in curr:
                        flag_file.write_text(curr.rstrip() + "\n" + flags_content)
                        log(f"Updated crisp font flags for {app_id}.")
            except Exception as e:
                log(f"Notice: Could not write flags for {app_id}: {e}")

    def get_gsetting(self, schema: str, key: str) -> str:
        code, out = self.run_cmd(["gsettings", "get", schema, key])
        if code == 0:
            return out.strip("'\"")
        return ""

    def set_gsetting(self, schema: str, key: str, value: str) -> bool:
        code, _ = self.run_cmd(["gsettings", "set", schema, key, value])
        return code == 0

    def get_status(self) -> Dict[str, any]:
        """Return comprehensive status of current desktop, GTK, Libadwaita, cursor and Flatpak theming."""
        gtk_theme = self.get_gsetting("org.cinnamon.desktop.interface", "gtk-theme")
        cinnamon_theme = self.get_gsetting("org.cinnamon.theme", "name")
        icon_theme = self.get_gsetting("org.cinnamon.desktop.interface", "icon-theme")
        cursor_theme = self.get_gsetting("org.cinnamon.desktop.interface", "cursor-theme") or "Bibata-Modern-Classic"
        cursor_size = self.get_gsetting("org.cinnamon.desktop.interface", "cursor-size") or "24"
        color_scheme = self.get_gsetting("org.cinnamon.desktop.interface", "color-scheme")
        if not color_scheme:
            color_scheme = self.get_gsetting("org.gnome.desktop.interface", "color-scheme") or "default"

        # Check GTK 4 override status
        gtk4_css = GTK4_CONFIG_DIR / "gtk.css"
        gtk4_active = False
        gtk4_target = ""
        if gtk4_css.is_symlink():
            gtk4_active = True
            try:
                gtk4_target = str(gtk4_css.resolve())
            except Exception:
                gtk4_target = "Broken link"
        elif gtk4_css.is_file():
            gtk4_active = True
            gtk4_target = "Custom user CSS file"

        # Check Flatpak overrides & subpixel fontconfig sync
        fontconfig_synced = FONTCONFIG_FILE.exists() and "lcdfilter" in FONTCONFIG_FILE.read_text()
        _, flatpak_out = self.run_cmd(["flatpak", "override", "--user", "--show"])
        flatpak_fs_synced = (
            ("~/.themes:ro" in flatpak_out or "xdg-data/themes:ro" in flatpak_out) and
            ("~/.icons:ro" in flatpak_out or "xdg-data/icons:ro" in flatpak_out) and
            ("xdg-config/gtk-4.0:ro" in flatpak_out) and
            ("xdg-config/fontconfig:ro" in flatpak_out)
        )
        flatpak_env_synced = (
            f"XCURSOR_THEME={cursor_theme}" in flatpak_out and
            "GTK_THEME=" not in flatpak_out
        )

        # List installed components
        installed_themes = self.get_installed_themes()
        installed_icons = self.get_installed_icons()
        installed_cursors = self.get_installed_cursors()

        return {
            "gtk_theme": gtk_theme,
            "cinnamon_theme": cinnamon_theme,
            "icon_theme": icon_theme,
            "cursor_theme": cursor_theme,
            "cursor_size": cursor_size,
            "color_scheme": color_scheme,
            "gtk4_active": gtk4_active,
            "gtk4_target": gtk4_target,
            "fontconfig_synced": fontconfig_synced,
            "flatpak_fs_synced": flatpak_fs_synced,
            "flatpak_env_synced": flatpak_env_synced,
            "flatpak_raw_overrides": flatpak_out,
            "installed_themes": installed_themes,
            "installed_icons": installed_icons,
            "installed_cursors": installed_cursors
        }

    def get_installed_themes(self) -> List[str]:
        themes = set()
        for directory in [THEMES_DIR, HOME / ".local" / "share" / "themes", SYSTEM_THEMES_DIR]:
            if directory.exists():
                for item in directory.iterdir():
                    if item.is_dir() and (item / "gtk-3.0").exists() or (item / "cinnamon").exists():
                        themes.add(item.name)
        return sorted(list(themes))

    def get_installed_icons(self) -> List[str]:
        icons = set()
        for directory in [ICONS_DIR, USER_ICONS_DIR, SYSTEM_ICONS_DIR]:
            if directory.exists():
                for item in directory.iterdir():
                    if item.is_dir() and (item / "index.theme").exists() and not (item / "cursors").exists():
                        icons.add(item.name)
        return sorted(list(icons))

    def get_installed_cursors(self) -> List[str]:
        cursors = set()
        for directory in [USER_ICONS_DIR, ICONS_DIR, SYSTEM_ICONS_DIR]:
            if directory.exists():
                for item in directory.iterdir():
                    if item.is_dir() and (item / "cursors").exists():
                        cursors.add(item.name)
        return sorted(list(cursors))

    def find_theme_path(self, theme_name: str) -> Optional[Path]:
        """Locate theme directory on filesystem."""
        candidates = [
            THEMES_DIR / theme_name,
            HOME / ".local" / "share" / "themes" / theme_name,
            SYSTEM_THEMES_DIR / theme_name
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c
        return None

    def is_preset_installed(self, preset: ThemePreset) -> bool:
        if preset.install_type == "system_apt":
            return bool(self.find_theme_path(preset.gtk_theme_name))
        return bool(self.find_theme_path(preset.gtk_theme_name))

    def is_icon_installed(self, icon_name: str) -> bool:
        candidates = [
            ICONS_DIR / icon_name,
            USER_ICONS_DIR / icon_name,
            SYSTEM_ICONS_DIR / icon_name
        ]
        return any(c.exists() for c in candidates)

    def is_cursor_installed(self, cursor_name: str) -> bool:
        candidates = [
            USER_ICONS_DIR / cursor_name,
            ICONS_DIR / cursor_name,
            SYSTEM_ICONS_DIR / cursor_name
        ]
        return any((c / "cursors").exists() for c in candidates if c.exists())

    def install_theme_preset(self, preset: ThemePreset, log: Callable[[str], None]) -> bool:
        """Download and install theme files from official source."""
        if self.is_preset_installed(preset):
            log(f"Theme '{preset.gtk_theme_name}' is already installed.")
            return True

        log(f"Downloading {preset.name} from {preset.provider_name}...")

        if preset.install_type == "git_installer":
            # Remove any stale lock files from previous runs
            for lock in Path("/tmp").glob("whitesur*"):
                try:
                    if lock.is_file():
                        lock.unlink()
                except Exception:
                    pass

            temp_dir = Path(f"/tmp/cinna_theme_{preset.id}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

            log("Cloning repository (shallow)...")
            code, out = self.run_cmd(["git", "clone", "--depth=1", preset.repo_url, str(temp_dir)])
            if code != 0:
                log(f"Git clone failed: {out}")
                return False

            install_script = temp_dir / "install.sh"
            if not install_script.exists():
                install_script = temp_dir / "themes" / "install.sh"

            if not install_script.exists():
                log("Error: install.sh not found in repository.")
                return False

            args = []
            if preset.install_args:
                for a in preset.install_args:
                    args.append(a.replace("{themes_dir}", str(THEMES_DIR)))

            log(f"Executing installer: ./install.sh {' '.join(args)}...")
            os.chmod(install_script, 0o755)
            code, out = self.run_cmd([str(install_script)] + args)
            log(f"Installer output:\n{out[:400]}...")

            # If the repository includes bundled icons (such as Tokyo Night), copy them to ~/.local/share/icons
            icons_source = temp_dir / "icons"
            if icons_source.exists():
                log("Installing bundled icons from repository...")
                for item in icons_source.iterdir():
                    if item.is_dir() and (item / "index.theme").exists():
                        dest = ICONS_DIR / item.name
                        if not dest.exists():
                            try:
                                shutil.copytree(item, dest)
                            except Exception:
                                pass

            # Clean up temp files
            shutil.rmtree(temp_dir, ignore_errors=True)
            return self.is_preset_installed(preset)

        elif preset.install_type == "archive" and preset.download_url:
            archive_path = Path(f"/tmp/{preset.id}.tar.xz")
            log(f"Downloading release archive {preset.download_url}...")
            try:
                urllib.request.urlretrieve(preset.download_url, str(archive_path))
                log("Extracting into ~/.themes...")
                with tarfile.open(archive_path, "r:*") as tar:
                    tar.extractall(path=THEMES_DIR)
                if archive_path.exists():
                    archive_path.unlink()

                # Handle extracted folder variants (e.g. Nordic-v40 -> Nordic)
                for variant_suffix in ["-v40", "-master", "-main"]:
                    v_dir = THEMES_DIR / f"{preset.gtk_theme_name}{variant_suffix}"
                    target_dir = THEMES_DIR / preset.gtk_theme_name
                    if v_dir.exists() and not target_dir.exists():
                        target_dir.symlink_to(v_dir)

                return self.is_preset_installed(preset)
            except Exception as e:
                log(f"Archive extraction failed: {e}")
                return False

        elif preset.install_type == "system_apt":
            log(f"System theme {preset.name} ready.")
            return True

        return False

    def install_cursor_theme(self, cursor_name: str, download_url: Optional[str], log: Callable[[str], None]) -> bool:
        """Download and install cursor theme if not already present."""
        if self.is_cursor_installed(cursor_name):
            log(f"Cursor '{cursor_name}' is already installed.")
            return True

        if not download_url:
            log(f"Cursor '{cursor_name}' has no download URL; checking system fallback...")
            return self.is_cursor_installed(cursor_name)

        log(f"Downloading cursor pack '{cursor_name}'...")
        temp_file = Path(f"/tmp/cursor_{cursor_name}")

        try:
            if download_url.endswith(".zip"):
                zip_path = Path(f"/tmp/cursor_{cursor_name}.zip")
                urllib.request.urlretrieve(download_url, str(zip_path))
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(path=USER_ICONS_DIR)
                if zip_path.exists():
                    zip_path.unlink()
            else:
                tar_path = Path(f"/tmp/cursor_{cursor_name}.tar.xz")
                urllib.request.urlretrieve(download_url, str(tar_path))
                with tarfile.open(tar_path, "r:*") as tar:
                    tar.extractall(path=USER_ICONS_DIR)
                if tar_path.exists():
                    tar_path.unlink()

            log(f"Cursor theme '{cursor_name}' installed to ~/.icons.")
            return self.is_cursor_installed(cursor_name)
        except Exception as e:
            log(f"Cursor download failed: {e}")
            return False

    def install_icon_archive(self, icon_name: str, download_url: Optional[str], log: Callable[[str], None]) -> bool:
        """Download and extract icon archive if not present."""
        if self.is_icon_installed(icon_name):
            log(f"Icons '{icon_name}' already installed.")
            return True

        if not download_url:
            return self.is_icon_installed(icon_name)

        log(f"Downloading icon pack '{icon_name}'...")
        temp_path = Path(f"/tmp/icon_{icon_name}.tar.gz")
        try:
            urllib.request.urlretrieve(download_url, str(temp_path))
            with tarfile.open(temp_path, "r:*") as tar:
                tar.extractall(path=ICONS_DIR)
            if temp_path.exists():
                temp_path.unlink()
            log(f"Icons '{icon_name}' installed to ~/.local/share/icons.")
            return self.is_icon_installed(icon_name)
        except Exception as e:
            log(f"Icon archive extraction failed: {e}")
            return False

    def install_icon_pack(self, pack_id: str, log: Callable[[str], None]) -> bool:
        """Download and install icon pack."""
        pack = next((p for p in ICON_PACKS if p["id"] == pack_id), None)
        if not pack:
            return False

        first_variant = pack["variants"][0]
        if self.is_icon_installed(first_variant):
            log(f"Icons '{pack['name']}' already installed.")
            return True

        if pack["install_type"] == "git_installer":
            temp_dir = Path(f"/tmp/cinna_icon_{pack_id}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

            log(f"Cloning icon pack {pack['name']}...")
            code, out = self.run_cmd(["git", "clone", "--depth=1", pack["repo_url"], str(temp_dir)])
            if code != 0:
                log(f"Clone failed: {out}")
                return False

            install_script = temp_dir / "install.sh"
            if install_script.exists():
                args = [a.replace("{icons_dir}", str(ICONS_DIR)) for a in pack.get("install_args", [])]
                os.chmod(install_script, 0o755)
                log(f"Running icon installer...")
                self.run_cmd([str(install_script)] + args)
            else:
                # Direct folder copy if no installer script
                for item in temp_dir.iterdir():
                    if item.is_dir() and (item / "index.theme").exists():
                        dest = ICONS_DIR / item.name
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)

            shutil.rmtree(temp_dir, ignore_errors=True)
            return self.is_icon_installed(first_variant)

        elif pack["install_type"] == "preinstalled":
            log("Icons are system pre-installed.")
            return True

        return False

    def apply_uniform_theming(
        self,
        gtk_theme: str,
        cinnamon_theme: str,
        icon_theme: str,
        cursor_theme: str,
        mode: str,  # 'dark' or 'light'
        cursor_size: int = 24,
        log: Callable[[str], None] = lambda m: None
    ) -> bool:
        """Apply uniform settings across GTK3, GTK4/Libadwaita, Cinnamon Shell, Cursors and Flatpak."""
        log(f"Applying uniform theme: {gtk_theme} (cursor={cursor_theme}, mode={mode})...")

        # 1. Cinnamon Desktop Settings
        self.set_gsetting("org.cinnamon.desktop.interface", "gtk-theme", gtk_theme)
        self.set_gsetting("org.cinnamon.desktop.interface", "icon-theme", icon_theme)
        if cursor_theme:
            self.set_gsetting("org.cinnamon.desktop.interface", "cursor-theme", cursor_theme)
            self.set_gsetting("org.cinnamon.desktop.interface", "cursor-size", str(cursor_size))
        
        # Check if cinnamon theme directory exists; fallback to gtk_theme
        theme_path = self.find_theme_path(cinnamon_theme)
        if theme_path and (theme_path / "cinnamon").exists():
            self.set_gsetting("org.cinnamon.theme", "name", cinnamon_theme)
        elif self.find_theme_path(gtk_theme) and (self.find_theme_path(gtk_theme) / "cinnamon").exists():
            self.set_gsetting("org.cinnamon.theme", "name", gtk_theme)
        else:
            log(f"Note: '{cinnamon_theme}' does not have a Cinnamon shell theme; retaining active shell.")

        # Window Manager Borders (SSD) Synchronization
        if theme_path and (theme_path / "metacity-1").exists():
            self.set_gsetting("org.cinnamon.desktop.wm.preferences", "theme", cinnamon_theme)
        elif self.find_theme_path(gtk_theme) and (self.find_theme_path(gtk_theme) / "metacity-1").exists():
            self.set_gsetting("org.cinnamon.desktop.wm.preferences", "theme", gtk_theme)

        # 2. GNOME / Portal Desktop Settings
        color_scheme_val = "prefer-dark" if mode == "dark" else "prefer-light"
        self.set_gsetting("org.cinnamon.desktop.interface", "color-scheme", color_scheme_val)
        self.set_gsetting("org.gnome.desktop.interface", "gtk-theme", gtk_theme)
        self.set_gsetting("org.gnome.desktop.interface", "icon-theme", icon_theme)
        self.set_gsetting("org.gnome.desktop.interface", "color-scheme", color_scheme_val)
        if cursor_theme:
            self.set_gsetting("org.gnome.desktop.interface", "cursor-theme", cursor_theme)
            self.set_gsetting("org.gnome.desktop.interface", "cursor-size", str(cursor_size))

        # 3. GTK 3 & GTK 4 User Configuration (~/.config/gtk-3.0/settings.ini & gtk-4.0/settings.ini)
        self.ensure_theme_in_user_space(gtk_theme, log)
        button_layout = self.get_gsetting("org.cinnamon.desktop.wm.preferences", "button-layout") or ":minimize,maximize,close"

        dpi, scale_val, gtk_xft_dpi = self.get_font_dpi_and_scale()
        self.ensure_subpixel_fontconfig(log)
        self.sync_electron_and_chromium_anti_blur(log)

        gtk3_ini_content = (
            f"[Settings]\n"
            f"gtk-theme-name = {gtk_theme}\n"
            f"gtk-icon-theme-name = {icon_theme}\n"
            f"gtk-cursor-theme-name = {cursor_theme}\n"
            f"gtk-cursor-theme-size = {cursor_size}\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = {'1' if mode == 'dark' else '0'}\n"
            f"gtk-font-name = Ubuntu 10\n"
            f"gtk-xft-antialias = 1\n"
            f"gtk-xft-hinting = 1\n"
            f"gtk-xft-hintstyle = hintfull\n"
            f"gtk-xft-rgba = rgb\n"
            f"gtk-xft-dpi = {gtk_xft_dpi}\n"
        )
        (GTK3_CONFIG_DIR / "settings.ini").write_text(gtk3_ini_content)

        # For GTK 4 / Libadwaita: only set cursor, icons, and decoration layout in settings.ini.
        # Custom theming is loaded via ~/.config/gtk-4.0/gtk.css. Setting gtk-theme-name to a
        # legacy GTK3 theme breaks Libadwaita window headerbars and strips button CSS.
        gtk4_ini_content = (
            f"[Settings]\n"
            f"gtk-icon-theme-name = {icon_theme}\n"
            f"gtk-cursor-theme-name = {cursor_theme}\n"
            f"gtk-cursor-theme-size = {cursor_size}\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = {'1' if mode == 'dark' else '0'}\n"
            f"gtk-font-name = Ubuntu 10\n"
            f"gtk-xft-antialias = 1\n"
            f"gtk-xft-hinting = 1\n"
            f"gtk-xft-hintstyle = hintfull\n"
            f"gtk-xft-rgba = rgb\n"
            f"gtk-xft-dpi = {gtk_xft_dpi}\n"
        )
        (GTK4_CONFIG_DIR / "settings.ini").write_text(gtk4_ini_content)
        log("Updated GTK 3.0 and GTK 4.0 settings.ini with decoration layout, cursor, and subpixel font settings.")

        # 4. Shadow cursor to ~/.icons for Flatpaks, write default index.theme & update xrdb
        if cursor_theme:
            self.ensure_cursor_in_user_space(cursor_theme, log)
            default_cursor_dir = USER_ICONS_DIR / "default"
            default_cursor_dir.mkdir(parents=True, exist_ok=True)
            default_index = default_cursor_dir / "index.theme"
            default_index.write_text(f"[icon theme]\nInherits={cursor_theme}\n")
            log("Updated ~/.icons/default/index.theme")
            self.update_xresources_cursor(cursor_theme, cursor_size, log)

        # 5. GTK 4 / Libadwaita Uniformity Override
        self._apply_gtk4_override(gtk_theme, mode, log)

        # 6. Flatpak Sandbox Uniformity Overrides (including XCURSOR_THEME)
        self.sync_flatpak_overrides(gtk_theme, icon_theme, cursor_theme, cursor_size, log)

        log("Uniform theming & cursors applied successfully!")
        return True

    def get_libadwaita_palette(self, theme_name: str, mode: str = "dark", css_content: str = "") -> str:
        """Generate Libadwaita color definitions for themes lacking modern @define-color window_bg_color."""
        normalized = theme_name.lower().replace("-v40", "").replace("-v42", "")

        palettes = {
            "nordic": {
                "accent_bg_color": "#88c0d0",
                "accent_fg_color": "#2e3440",
                "accent_color": "#88c0d0",
                "destructive_bg_color": "#bf616a",
                "destructive_fg_color": "#eceff4",
                "destructive_color": "#bf616a",
                "success_bg_color": "#a3be8c",
                "success_fg_color": "#2e3440",
                "success_color": "#a3be8c",
                "warning_bg_color": "#ebcb8b",
                "warning_fg_color": "#2e3440",
                "warning_color": "#ebcb8b",
                "error_bg_color": "#bf616a",
                "error_fg_color": "#eceff4",
                "error_color": "#bf616a",
                "window_bg_color": "#2e3440",
                "window_fg_color": "#eceff4",
                "view_bg_color": "#242933",
                "view_fg_color": "#eceff4",
                "headerbar_bg_color": "#2e3440",
                "headerbar_fg_color": "#eceff4",
                "headerbar_border_color": "rgba(236, 239, 244, 0.12)",
                "headerbar_backdrop_color": "#2e3440",
                "card_bg_color": "#3b4252",
                "card_fg_color": "#eceff4",
                "dialog_bg_color": "#2e3440",
                "dialog_fg_color": "#eceff4",
                "popover_bg_color": "#353c4a",
                "popover_fg_color": "#eceff4",
                "shade_color": "rgba(0, 0, 0, 0.25)",
                "scrollbar_outline_color": "rgba(216, 222, 233, 0.15)",
            },
            "nordic-polar": {
                "accent_bg_color": "#5e81ac",
                "accent_fg_color": "#ffffff",
                "accent_color": "#5e81ac",
                "destructive_bg_color": "#bf616a",
                "destructive_fg_color": "#ffffff",
                "destructive_color": "#bf616a",
                "success_bg_color": "#a3be8c",
                "success_fg_color": "#ffffff",
                "success_color": "#a3be8c",
                "warning_bg_color": "#ebcb8b",
                "warning_fg_color": "#2e3440",
                "warning_color": "#ebcb8b",
                "error_bg_color": "#bf616a",
                "error_fg_color": "#ffffff",
                "error_color": "#bf616a",
                "window_bg_color": "#e5e9f0",
                "window_fg_color": "#2e3440",
                "view_bg_color": "#eceff4",
                "view_fg_color": "#2e3440",
                "headerbar_bg_color": "#d8dee9",
                "headerbar_fg_color": "#2e3440",
                "headerbar_border_color": "rgba(46, 52, 64, 0.12)",
                "headerbar_backdrop_color": "#d8dee9",
                "card_bg_color": "#d8dee9",
                "card_fg_color": "#2e3440",
                "dialog_bg_color": "#e5e9f0",
                "dialog_fg_color": "#2e3440",
                "popover_bg_color": "#d8dee9",
                "popover_fg_color": "#2e3440",
                "shade_color": "rgba(0, 0, 0, 0.08)",
                "scrollbar_outline_color": "rgba(46, 52, 64, 0.15)",
            },
            "dracula": {
                "accent_bg_color": "#bd93f9",
                "accent_fg_color": "#282a36",
                "accent_color": "#bd93f9",
                "destructive_bg_color": "#ff5555",
                "destructive_fg_color": "#f8f8f2",
                "destructive_color": "#ff5555",
                "success_bg_color": "#50fa7b",
                "success_fg_color": "#282a36",
                "success_color": "#50fa7b",
                "warning_bg_color": "#ffb86c",
                "warning_fg_color": "#282a36",
                "warning_color": "#ffb86c",
                "error_bg_color": "#ff5555",
                "error_fg_color": "#f8f8f2",
                "error_color": "#ff5555",
                "window_bg_color": "#282a36",
                "window_fg_color": "#f8f8f2",
                "view_bg_color": "#21222c",
                "view_fg_color": "#f8f8f2",
                "headerbar_bg_color": "#282a36",
                "headerbar_fg_color": "#f8f8f2",
                "headerbar_border_color": "rgba(248, 248, 242, 0.12)",
                "headerbar_backdrop_color": "#282a36",
                "card_bg_color": "#343746",
                "card_fg_color": "#f8f8f2",
                "dialog_bg_color": "#282a36",
                "dialog_fg_color": "#f8f8f2",
                "popover_bg_color": "#343746",
                "popover_fg_color": "#f8f8f2",
                "shade_color": "rgba(0, 0, 0, 0.35)",
                "scrollbar_outline_color": "rgba(248, 248, 242, 0.12)",
            },
            "sweet-dark": {
                "accent_bg_color": "#00e8c6",
                "accent_fg_color": "#161925",
                "accent_color": "#00e8c6",
                "destructive_bg_color": "#f92672",
                "destructive_fg_color": "#ffffff",
                "destructive_color": "#f92672",
                "success_bg_color": "#00e8c6",
                "success_fg_color": "#161925",
                "success_color": "#00e8c6",
                "warning_bg_color": "#f39c12",
                "warning_fg_color": "#161925",
                "warning_color": "#f39c12",
                "error_bg_color": "#f92672",
                "error_fg_color": "#ffffff",
                "error_color": "#f92672",
                "window_bg_color": "#161925",
                "window_fg_color": "#fcfcfc",
                "view_bg_color": "#11121d",
                "view_fg_color": "#fcfcfc",
                "headerbar_bg_color": "#161925",
                "headerbar_fg_color": "#fcfcfc",
                "headerbar_border_color": "rgba(252, 252, 252, 0.12)",
                "headerbar_backdrop_color": "#161925",
                "card_bg_color": "#1e2233",
                "card_fg_color": "#fcfcfc",
                "dialog_bg_color": "#161925",
                "dialog_fg_color": "#fcfcfc",
                "popover_bg_color": "#1e2233",
                "popover_fg_color": "#fcfcfc",
                "shade_color": "rgba(0, 0, 0, 0.35)",
                "scrollbar_outline_color": "rgba(252, 252, 252, 0.15)",
            },
            "mint-y-dark": {
                "accent_bg_color": "#35a854",
                "accent_fg_color": "#ffffff",
                "accent_color": "#35a854",
                "destructive_bg_color": "#c6262e",
                "destructive_fg_color": "#ffffff",
                "destructive_color": "#c6262e",
                "success_bg_color": "#35a854",
                "success_fg_color": "#ffffff",
                "success_color": "#35a854",
                "warning_bg_color": "#f37329",
                "warning_fg_color": "#ffffff",
                "warning_color": "#f37329",
                "error_bg_color": "#c6262e",
                "error_fg_color": "#ffffff",
                "error_color": "#c6262e",
                "window_bg_color": "#2f2f2f",
                "window_fg_color": "#ffffff",
                "view_bg_color": "#252525",
                "view_fg_color": "#ffffff",
                "headerbar_bg_color": "#2f2f2f",
                "headerbar_fg_color": "#ffffff",
                "headerbar_border_color": "rgba(255, 255, 255, 0.1)",
                "headerbar_backdrop_color": "#2f2f2f",
                "card_bg_color": "#383838",
                "card_fg_color": "#ffffff",
                "dialog_bg_color": "#2f2f2f",
                "dialog_fg_color": "#ffffff",
                "popover_bg_color": "#383838",
                "popover_fg_color": "#ffffff",
                "shade_color": "rgba(0, 0, 0, 0.25)",
                "scrollbar_outline_color": "rgba(255, 255, 255, 0.15)",
            },
            "mint-y": {
                "accent_bg_color": "#35a854",
                "accent_fg_color": "#ffffff",
                "accent_color": "#35a854",
                "destructive_bg_color": "#c6262e",
                "destructive_fg_color": "#ffffff",
                "destructive_color": "#c6262e",
                "success_bg_color": "#35a854",
                "success_fg_color": "#ffffff",
                "success_color": "#35a854",
                "warning_bg_color": "#f37329",
                "warning_fg_color": "#ffffff",
                "warning_color": "#f37329",
                "error_bg_color": "#c6262e",
                "error_fg_color": "#ffffff",
                "error_color": "#c6262e",
                "window_bg_color": "#f8f8f8",
                "window_fg_color": "#2f2f2f",
                "view_bg_color": "#ffffff",
                "view_fg_color": "#2f2f2f",
                "headerbar_bg_color": "#f0f0f0",
                "headerbar_fg_color": "#2f2f2f",
                "headerbar_border_color": "rgba(0, 0, 0, 0.1)",
                "headerbar_backdrop_color": "#f0f0f0",
                "card_bg_color": "#ffffff",
                "card_fg_color": "#2f2f2f",
                "dialog_bg_color": "#f8f8f8",
                "dialog_fg_color": "#2f2f2f",
                "popover_bg_color": "#ffffff",
                "popover_fg_color": "#2f2f2f",
                "shade_color": "rgba(0, 0, 0, 0.08)",
                "scrollbar_outline_color": "rgba(0, 0, 0, 0.15)",
            }
        }

        # Check curated palette match
        matched_palette = None
        for key, p in palettes.items():
            if key in normalized:
                matched_palette = p
                break

        if not matched_palette:
            import re
            def extract(pattern, default):
                m = re.search(pattern, css_content)
                return m.group(1).strip() if m else default

            is_dark = (mode == "dark")
            win_bg = extract(r"@define-color\s+(?:theme_)?bg_color\s+([^;]+);", "#2f2f2f" if is_dark else "#f8f8f8")
            win_fg = extract(r"@define-color\s+(?:theme_)?fg_color\s+([^;]+);", "#ffffff" if is_dark else "#2e3440")
            accent = extract(r"@define-color\s+(?:theme_)?selected_bg_color\s+([^;]+);", "#3584e4")
            view_bg = extract(r"@define-color\s+(?:theme_)?base_color\s+([^;]+);", "#242424" if is_dark else "#ffffff")

            matched_palette = {
                "accent_bg_color": accent,
                "accent_fg_color": "#ffffff" if is_dark else "#2e3440",
                "accent_color": accent,
                "destructive_bg_color": "#c6262e",
                "destructive_fg_color": "#ffffff",
                "destructive_color": "#c6262e",
                "success_bg_color": "#35a854",
                "success_fg_color": "#ffffff",
                "success_color": "#35a854",
                "warning_bg_color": "#f37329",
                "warning_fg_color": "#ffffff",
                "warning_color": "#f37329",
                "error_bg_color": "#c6262e",
                "error_fg_color": "#ffffff",
                "error_color": "#c6262e",
                "window_bg_color": win_bg,
                "window_fg_color": win_fg,
                "view_bg_color": view_bg,
                "view_fg_color": win_fg,
                "headerbar_bg_color": win_bg,
                "headerbar_fg_color": win_fg,
                "headerbar_border_color": "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.1)",
                "headerbar_backdrop_color": win_bg,
                "card_bg_color": view_bg,
                "card_fg_color": win_fg,
                "dialog_bg_color": win_bg,
                "dialog_fg_color": win_fg,
                "popover_bg_color": view_bg,
                "popover_fg_color": win_fg,
                "shade_color": "rgba(0, 0, 0, 0.25)" if is_dark else "rgba(0, 0, 0, 0.08)",
                "scrollbar_outline_color": "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)",
            }

        lines = ["\n/* === Libadwaita Compatibility Palette (Generated by cinna-theme) === */"]
        for k, v in matched_palette.items():
            lines.append(f"@define-color {k} {v};")

        # Window Controls Visibility & Styling for GTK 4 / Libadwaita Flatpaks
        lines.append("""
/* === Perfect 1:1 Circular Window Controls (Traffic Lights) === */
headerbar windowcontrols,
windowcontrols {
  border-spacing: 6px;
}

headerbar windowcontrols button,
windowcontrols button,
headerbar windowcontrols button.close,
windowcontrols button.close,
headerbar windowcontrols button.maximize,
windowcontrols button.maximize,
headerbar windowcontrols button.minimize,
windowcontrols button.minimize {
  background-color: transparent;
  background-image: none;
  box-shadow: none;
  border: none;
  padding: 0;
  margin: 0 2px;
  min-width: 14px;
  min-height: 14px;
}

headerbar windowcontrols button > image,
windowcontrols button > image {
  background-color: transparent;
  background-image: none;
  border-radius: 9999px;
  min-width: 14px;
  min-height: 14px;
  padding: 0;
  margin: 0;
  border: 1px solid alpha(currentColor, 0.15);
  color: transparent;
  -gtk-icon-size: 10px;
  transition: all 120ms ease-in-out;
}

headerbar windowcontrols button.close > image,
windowcontrols button.close > image {
  background-color: @destructive_bg_color;
}

headerbar windowcontrols button.maximize > image,
windowcontrols button.maximize > image {
  background-color: @success_bg_color;
}

headerbar windowcontrols button.minimize > image,
windowcontrols button.minimize > image {
  background-color: @warning_bg_color;
}

headerbar windowcontrols button:hover > image,
windowcontrols button:hover > image {
  color: alpha(@window_bg_color, 0.95);
  filter: brightness(1.15);
}

headerbar windowcontrols button:active > image,
windowcontrols button:active > image {
  filter: brightness(0.85);
}

headerbar windowcontrols button:backdrop > image,
windowcontrols button:backdrop > image {
  opacity: 0.55;
  filter: grayscale(0.4);
}
""")
        return "\n".join(lines) + "\n"

    def _apply_gtk4_override(self, gtk_theme: str, mode: str, log: Callable[[str], None]):
        """Symlink GTK 4 CSS from the active theme to ~/.config/gtk-4.0 with Libadwaita variable injection."""
        self.ensure_theme_in_user_space(gtk_theme, log)
        theme_path = self.find_theme_path(gtk_theme)
        gtk4_css_src = None

        if theme_path:
            gtk4_dir = theme_path / "gtk-4.0"
            if gtk4_dir.exists() and (gtk4_dir / "gtk.css").exists():
                gtk4_css_src = gtk4_dir

        target_css = GTK4_CONFIG_DIR / "gtk.css"
        target_dark_css = GTK4_CONFIG_DIR / "gtk-dark.css"
        target_assets = GTK4_CONFIG_DIR / "assets"

        # Remove existing symlinks or files
        for link in [target_css, target_dark_css, target_assets]:
            if link.is_symlink() or link.is_file():
                link.unlink()
            elif link.is_dir() and link.name == "assets":
                shutil.rmtree(link)

        if gtk4_css_src:
            # Check if Libadwaita color variables or windowcontrols fixes are present
            css_sample = (gtk4_css_src / "gtk.css").read_text()
            marker = "/* === Libadwaita Compatibility Palette"
            palette_block = self.get_libadwaita_palette(gtk_theme, mode, css_sample)
            for f_name in ["gtk.css", "gtk-dark.css"]:
                target_file = gtk4_css_src / f_name
                if target_file.exists():
                    try:
                        content = target_file.read_text()
                        if marker in content:
                            base_content = content.split(marker)[0].rstrip()
                            target_file.write_text((base_content + "\n\n" if base_content else "") + palette_block)
                        elif "window_bg_color" not in content or "Perfect 1:1 Circular Window Controls" not in content:
                            target_file.write_text(content.rstrip() + "\n\n" + palette_block)
                    except Exception as e:
                        log(f"Note: Could not patch {f_name}: {e}")

            log(f"Linking GTK 4 stylesheet from {gtk4_css_src} for Libadwaita consistency...")
            try:
                target_css.symlink_to(gtk4_css_src / "gtk.css")
                if (gtk4_css_src / "gtk-dark.css").exists():
                    target_dark_css.symlink_to(gtk4_css_src / "gtk-dark.css")
                if (gtk4_css_src / "assets").exists():
                    target_assets.symlink_to(gtk4_css_src / "assets")
                log("GTK 4 / Libadwaita linked successfully.")
            except Exception as e:
                log(f"Warning: could not link GTK 4 files: {e}")
        else:
            log(f"Generating fallback Libadwaita palette for '{gtk_theme}'...")
            palette_block = self.get_libadwaita_palette(gtk_theme, mode, "")
            target_css.write_text(palette_block)
            target_dark_css.write_text(palette_block)
            log("Libadwaita color palette created at ~/.config/gtk-4.0/gtk.css.")

    def sync_flatpak_overrides(
        self,
        gtk_theme: str,
        icon_theme: str,
        cursor_theme: str = "Bibata-Modern-Classic",
        cursor_size: int = 24,
        log: Callable[[str], None] = lambda m: None
    ):
        """Grant Flatpaks filesystem access to themes and set environment variables including cursors."""
        log("Configuring Flatpak sandbox permissions and environment (including cursor theme)...")
        
        # Ensure cursor and theme are in user space and xrdb is refreshed
        if gtk_theme:
            self.ensure_theme_in_user_space(gtk_theme, log)
        if cursor_theme:
            self.ensure_cursor_in_user_space(cursor_theme, log)
            self.update_xresources_cursor(cursor_theme, cursor_size, log)

        dpi, scale_val, gtk_xft_dpi = self.get_font_dpi_and_scale()
        self.ensure_subpixel_fontconfig(log)
        self.sync_electron_and_chromium_anti_blur(log)

        # Sync GTK 3 & GTK 4 settings.ini so sandboxed apps read the current cursor, theme & subpixel fonts
        button_layout = self.get_gsetting("org.cinnamon.desktop.wm.preferences", "button-layout") or ":minimize,maximize,close"
        gtk3_ini_content = (
            f"[Settings]\n"
            f"gtk-theme-name = {gtk_theme}\n"
            f"gtk-icon-theme-name = {icon_theme}\n"
            f"gtk-cursor-theme-name = {cursor_theme}\n"
            f"gtk-cursor-theme-size = {cursor_size}\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = 1\n"
            f"gtk-font-name = Ubuntu 10\n"
            f"gtk-xft-antialias = 1\n"
            f"gtk-xft-hinting = 1\n"
            f"gtk-xft-hintstyle = hintfull\n"
            f"gtk-xft-rgba = rgb\n"
            f"gtk-xft-dpi = {gtk_xft_dpi}\n"
        )
        (GTK3_CONFIG_DIR / "settings.ini").write_text(gtk3_ini_content)

        # For GTK 4 / Libadwaita: only set cursor, icons, and decoration layout in settings.ini.
        # Setting gtk-theme-name to a GTK3 theme strips Libadwaita button styling and breaks headerbars.
        gtk4_ini_content = (
            f"[Settings]\n"
            f"gtk-icon-theme-name = {icon_theme}\n"
            f"gtk-cursor-theme-name = {cursor_theme}\n"
            f"gtk-cursor-theme-size = {cursor_size}\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = 1\n"
            f"gtk-font-name = Ubuntu 10\n"
            f"gtk-xft-antialias = 1\n"
            f"gtk-xft-hinting = 1\n"
            f"gtk-xft-hintstyle = hintfull\n"
            f"gtk-xft-rgba = rgb\n"
            f"gtk-xft-dpi = {gtk_xft_dpi}\n"
        )
        (GTK4_CONFIG_DIR / "settings.ini").write_text(gtk4_ini_content)
        log("Synchronized ~/.config/gtk-3.0/settings.ini and gtk-4.0/settings.ini with subpixel font rendering.")

        # Filesystem permissions
        fs_rules = [
            "xdg-data/themes:ro",
            "xdg-data/icons:ro",
            "~/.themes:ro",
            "~/.icons:ro",
            "xdg-config/gtk-3.0:ro",
            "xdg-config/gtk-4.0:ro",
            "xdg-config/fontconfig:ro",
            "xdg-data/fonts:ro",
            "~/.fonts:ro"
        ]
        cmd = ["flatpak", "override", "--user"]
        for rule in fs_rules:
            cmd.append(f"--filesystem={rule}")

        # Explicitly unset dangerous GTK_THEME and ICON_THEME environment variables.
        # Exporting GTK_THEME globally breaks Libadwaita/GTK4 Flatpaks (stripping button styling
        # and destroying window headerbars). GTK3 themes are read from settings.ini and GTK4 from gtk.css.
        cmd.extend([
            "--unset-env=GTK_THEME",
            "--unset-env=ICON_THEME",
            f"--env=XCURSOR_THEME={cursor_theme}",
            f"--env=XCURSOR_SIZE={cursor_size}",
            "--env=QT_QPA_PLATFORMTHEME=qt5ct",
            "--env=QT_AUTO_SCREEN_SCALE_FACTOR=1",
            "--env=QT_ENABLE_HIGHDPI_SCALING=1",
            f"--env=GDK_DPI_SCALE={round(scale_val, 2)}",
            "--env=ELECTRON_OZONE_PLATFORM_HINT=auto"
        ])

        code, out = self.run_cmd(cmd)
        if code == 0:
            log("Flatpak user overrides configured successfully (themes, cursors, subpixel fontconfig & Ozone).")
        else:
            log(f"Flatpak override notice: {out}")

        # Clean any empty GTK_THEME= / ICON_THEME= lines from the flatpak override file
        override_file = HOME / ".local" / "share" / "flatpak" / "overrides" / "global"
        if override_file.exists():
            try:
                lines = [l for l in override_file.read_text().splitlines() if not l.startswith(("GTK_THEME=", "ICON_THEME="))]
                override_file.write_text("\n".join(lines) + "\n")
            except Exception:
                pass

    def fallback_to_default(self, log: Callable[[str], None] = lambda m: None) -> bool:
        """Trigger safe fallback to default Linux Mint theming (Mint-Y-Dark)."""
        log("Activating safety fallback to Linux Mint default theme (Mint-Y-Dark)...")
        return self.reset_to_defaults(log)

    def reset_to_defaults(self, log: Callable[[str], None]) -> bool:
        """Reset all theming and cursors to Linux Mint defaults and clean overrides."""
        log("Restoring desktop to Linux Mint defaults (Mint-Y-Dark)...")

        default_theme = "Mint-Y-Dark"
        default_icon = "Mint-Y"
        default_cursor = "Bibata-Modern-Classic"

        # 1. Restore GSettings for Cinnamon & GNOME
        self.set_gsetting("org.cinnamon.desktop.interface", "gtk-theme", default_theme)
        self.set_gsetting("org.cinnamon.theme", "name", default_theme)
        self.set_gsetting("org.cinnamon.desktop.wm.preferences", "theme", default_theme)
        self.set_gsetting("org.cinnamon.desktop.interface", "icon-theme", default_icon)
        self.set_gsetting("org.cinnamon.desktop.interface", "cursor-theme", default_cursor)
        self.set_gsetting("org.cinnamon.desktop.interface", "cursor-size", "24")
        self.set_gsetting("org.cinnamon.desktop.interface", "color-scheme", "prefer-dark")

        self.set_gsetting("org.gnome.desktop.interface", "gtk-theme", default_theme)
        self.set_gsetting("org.gnome.desktop.interface", "icon-theme", default_icon)
        self.set_gsetting("org.gnome.desktop.interface", "cursor-theme", default_cursor)
        self.set_gsetting("org.gnome.desktop.interface", "cursor-size", "24")
        self.set_gsetting("org.gnome.desktop.interface", "color-scheme", "prefer-dark")

        # 2. Reset ~/.config/gtk-3.0/settings.ini & gtk-4.0/settings.ini
        button_layout = self.get_gsetting("org.cinnamon.desktop.wm.preferences", "button-layout") or ":minimize,maximize,close"
        gtk3_content = (
            f"[Settings]\n"
            f"gtk-theme-name = {default_theme}\n"
            f"gtk-icon-theme-name = {default_icon}\n"
            f"gtk-cursor-theme-name = {default_cursor}\n"
            f"gtk-cursor-theme-size = 24\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = 1\n"
            f"gtk-font-name = Ubuntu 10\n"
        )
        (GTK3_CONFIG_DIR / "settings.ini").write_text(gtk3_content)

        gtk4_content = (
            f"[Settings]\n"
            f"gtk-icon-theme-name = {default_icon}\n"
            f"gtk-cursor-theme-name = {default_cursor}\n"
            f"gtk-cursor-theme-size = 24\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = 1\n"
            f"gtk-font-name = Ubuntu 10\n"
        )
        (GTK4_CONFIG_DIR / "settings.ini").write_text(gtk4_content)

        # 3. Clean GTK 4 symlinks and configs so Libadwaita reverts to pure default
        for link in [GTK4_CONFIG_DIR / "gtk.css", GTK4_CONFIG_DIR / "gtk-dark.css", GTK4_CONFIG_DIR / "assets"]:
            if link.is_symlink() or link.is_file():
                link.unlink()
            elif link.is_dir() and link.name == "assets":
                shutil.rmtree(link)

        # 4. Clean root cursor index.theme & ensure default cursor and theme are in user space
        self.ensure_theme_in_user_space(default_theme, log)
        self.ensure_cursor_in_user_space(default_cursor, log)
        default_index = USER_ICONS_DIR / "default" / "index.theme"
        if default_index.parent.exists():
            default_index.write_text(f"[icon theme]\nInherits={default_cursor}\n")
        self.update_xresources_cursor(default_cursor, 24, log)

        # 5. Clean Flatpak overrides
        log("Resetting Flatpak user overrides...")
        self.run_cmd(["flatpak", "override", "--user", "--reset"])

        # Re-apply safe default for Mint-Y
        self.sync_flatpak_overrides(default_theme, default_icon, default_cursor, 24, log)
        log("System restored to Linux Mint defaults!")
        return True
