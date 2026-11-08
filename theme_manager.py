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
SYSTEM_THEMES_DIR = Path("/usr/share/themes")
SYSTEM_ICONS_DIR = Path("/usr/share/icons")

class ThemeManager:
    def __init__(self):
        THEMES_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
        USER_ICONS_DIR.mkdir(parents=True, exist_ok=True)
        GTK3_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        GTK4_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

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

        # Check Flatpak overrides
        _, flatpak_out = self.run_cmd(["flatpak", "override", "--user", "--show"])
        flatpak_fs_synced = (
            "~/.themes:ro" in flatpak_out or "xdg-data/themes:ro" in flatpak_out
        ) and (
            "~/.icons:ro" in flatpak_out or "xdg-data/icons:ro" in flatpak_out
        ) and (
            "xdg-config/gtk-4.0:ro" in flatpak_out
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

        gtk3_ini_content = (
            f"[Settings]\n"
            f"gtk-theme-name = {gtk_theme}\n"
            f"gtk-icon-theme-name = {icon_theme}\n"
            f"gtk-cursor-theme-name = {cursor_theme}\n"
            f"gtk-cursor-theme-size = {cursor_size}\n"
            f"gtk-decoration-layout = {button_layout}\n"
            f"gtk-application-prefer-dark-theme = {'1' if mode == 'dark' else '0'}\n"
            f"gtk-font-name = Ubuntu 10\n"
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
        )
        (GTK4_CONFIG_DIR / "settings.ini").write_text(gtk4_ini_content)
        log("Updated GTK 3.0 and GTK 4.0 settings.ini with decoration layout and cursor settings.")

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

    def _apply_gtk4_override(self, gtk_theme: str, mode: str, log: Callable[[str], None]):
        """Symlink GTK 4 CSS from the active theme to ~/.config/gtk-4.0 so Libadwaita inherits it."""
        theme_path = self.find_theme_path(gtk_theme)
        gtk4_css_src = None

        if theme_path:
            gtk4_dir = theme_path / "gtk-4.0"
            if gtk4_dir.exists() and (gtk4_dir / "gtk.css").exists():
                gtk4_css_src = gtk4_dir

        target_css = GTK4_CONFIG_DIR / "gtk.css"
        target_dark_css = GTK4_CONFIG_DIR / "gtk-dark.css"
        target_assets = GTK4_CONFIG_DIR / "assets"

        # Remove existing symlinks
        for link in [target_css, target_dark_css, target_assets]:
            if link.is_symlink():
                link.unlink()
            elif link.is_dir() and link.name == "assets":
                shutil.rmtree(link)

        if gtk4_css_src:
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
            log("No custom GTK 4 CSS in theme; default Adwaita engine active.")

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

        # Sync GTK 3 & GTK 4 settings.ini so sandboxed apps read the current cursor & theme
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
        )
        (GTK4_CONFIG_DIR / "settings.ini").write_text(gtk4_ini_content)
        log("Synchronized ~/.config/gtk-3.0/settings.ini and gtk-4.0/settings.ini.")

        # Filesystem permissions
        fs_rules = [
            "xdg-data/themes:ro",
            "xdg-data/icons:ro",
            "~/.themes:ro",
            "~/.icons:ro",
            "xdg-config/gtk-3.0:ro",
            "xdg-config/gtk-4.0:ro"
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
            "--env=QT_QPA_PLATFORMTHEME=qt5ct"
        ])

        code, out = self.run_cmd(cmd)
        if code == 0:
            log("Flatpak user overrides configured successfully.")
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

        # 3. Clean GTK 4 symlinks so Libadwaita reverts to pure default
        for link in [GTK4_CONFIG_DIR / "gtk.css", GTK4_CONFIG_DIR / "gtk-dark.css", GTK4_CONFIG_DIR / "assets"]:
            if link.is_symlink():
                link.unlink()

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
