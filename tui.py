"""Interactive Curses TUI for Cinnamon Desktop, Cursors and Flatpak Uniform Theming."""

import curses
import os
import sys
import time
from typing import List, Optional

from theme_data import PRESETS, ICON_PACKS, ThemePreset
from theme_manager import ThemeManager

class CinnamonThemeTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.manager = ThemeManager()
        self.current_tab = 0  # 0: Presets, 1: Custom, 2: Flatpak & Libadwaita, 3: Help
        self.tabs = ["Curated Suites", "Custom Components", "Flatpak & Libadwaita", "Help & Info"]
        self.preset_index = 0
        self.preset_scroll_offset = 0
        self.custom_focus = 0  # 0: GTK, 1: Shell, 2: Icons, 3: Cursors, 4: Mode, 5: Apply
        self.custom_gtk_idx = 0
        self.custom_shell_idx = 0
        self.custom_icon_idx = 0
        self.custom_cursor_idx = 0
        self.custom_mode = "dark"
        self.logs: List[str] = []
        self.status = {}
        self.flatpak_apps = []

        try:
            curses.curs_set(0)
        except curses.error:
            pass

        self.init_colors()
        self.refresh_status()

    def init_colors(self):
        if not curses.has_colors():
            return
        try:
            curses.start_color()
        except Exception:
            return

        use_default = False
        try:
            curses.use_default_colors()
            use_default = True
        except Exception:
            use_default = False

        bg = -1 if use_default else curses.COLOR_BLACK

        try:
            curses.init_pair(1, curses.COLOR_CYAN, bg)     # Header / Title
            curses.init_pair(2, curses.COLOR_GREEN, bg)    # Success / Active
            curses.init_pair(3, curses.COLOR_YELLOW, bg)   # Warning / Accent
            curses.init_pair(4, curses.COLOR_RED, bg)      # Error / Inactive
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Selected Item
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Highlight / Tab
            curses.init_pair(7, curses.COLOR_MAGENTA, bg)  # Badges
            curses.init_pair(8, curses.COLOR_BLUE, bg)     # Info / Muted
        except Exception:
            pass

    def safe_addstr(self, y: int, x: int, text: str, attr: int = 0):
        """Safely write string without raising curses ERR on boundaries or bottom-right corner."""
        try:
            max_y, max_x = self.stdscr.getmaxyx()
            if y < 0 or y >= max_y or x < 0 or x >= max_x:
                return
            avail = max_x - x
            if y == max_y - 1:
                avail = max(0, avail - 1)
            sub = str(text)[:avail]
            if not sub:
                return
            if attr:
                self.stdscr.addstr(y, x, sub, attr)
            else:
                self.stdscr.addstr(y, x, sub)
        except curses.error:
            pass

    def refresh_status(self):
        self.status = self.manager.get_status()
        self.installed_themes = self.status.get("installed_themes", [])
        self.installed_icons = self.status.get("installed_icons", [])
        self.installed_cursors = self.status.get("installed_cursors", [])

        # Cache installed flatpak apps for the diagnostic tab
        _, out = self.manager.run_cmd(["flatpak", "list", "--app", "--columns=name,application"])
        self.flatpak_apps = [line.strip() for line in out.splitlines() if line.strip()]

        # Set default custom indices if available
        if self.status.get("gtk_theme") in self.installed_themes:
            self.custom_gtk_idx = self.installed_themes.index(self.status["gtk_theme"])
        if self.status.get("cinnamon_theme") in self.installed_themes:
            self.custom_shell_idx = self.installed_themes.index(self.status["cinnamon_theme"])
        if self.status.get("icon_theme") in self.installed_icons:
            self.custom_icon_idx = self.installed_icons.index(self.status["icon_theme"])
        if self.status.get("cursor_theme") in self.installed_cursors:
            self.custom_cursor_idx = self.installed_cursors.index(self.status["cursor_theme"])
        self.custom_mode = "dark" if "dark" in self.status.get("color_scheme", "").lower() else "light"

    def log_message(self, msg: str):
        self.logs.append(msg)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def draw_header(self, max_y: int, max_x: int):
        title = " Cinnamon Uniform Theming, Cursors & Flatpak Sync "
        self.safe_addstr(0, 0, title.center(max_x), curses.color_pair(6) | curses.A_BOLD)

        # Tab bar
        tab_str = "  "
        for idx, tab_name in enumerate(self.tabs):
            if idx == self.current_tab:
                tab_str += f"[ {idx + 1}. {tab_name} ]  "
            else:
                tab_str += f"  {idx + 1}. {tab_name}    "

        self.safe_addstr(1, 0, tab_str, curses.color_pair(1) | curses.A_BOLD)
        self.safe_addstr(2, 0, "─" * max_x)

        # Live status pill row
        gtk_str = f"GTK: {self.status.get('gtk_theme', 'Unknown')}"
        shell_str = f"Shell: {self.status.get('cinnamon_theme', 'Unknown')}"
        icon_str = f"Icons: {self.status.get('icon_theme', 'Unknown')}"
        cursor_str = f"Cursor: {self.status.get('cursor_theme', 'Unknown')}"
        mode_str = f"Mode: {self.status.get('color_scheme', 'Unknown')}"
        libadw_str = "Libadwaita: Synced" if self.status.get("gtk4_active") else "Libadwaita: Default"
        fp_str = "Flatpak: Synced" if self.status.get("flatpak_fs_synced") else "Flatpak: Untuned"

        status_line = f" {gtk_str} | {shell_str} | {icon_str} | {cursor_str} | {mode_str} | "
        self.safe_addstr(3, 0, status_line)
        offset = len(status_line)

        # Color badge for Libadwaita
        adw_color = curses.color_pair(2) if self.status.get("gtk4_active") else curses.color_pair(3)
        self.safe_addstr(3, min(offset, max_x - 1), f"[{libadw_str}] ", adw_color | curses.A_BOLD)
        offset += len(libadw_str) + 3

        # Color badge for Flatpak
        fp_color = curses.color_pair(2) if self.status.get("flatpak_fs_synced") else curses.color_pair(4)
        if offset < max_x - 15:
            self.safe_addstr(3, offset, f"[{fp_str}]", fp_color | curses.A_BOLD)

        self.safe_addstr(4, 0, "─" * max_x)

    def draw_footer(self, max_y: int, max_x: int):
        help_text = " [↑/↓] Navigate  [Tab] Switch Tab  [Enter] Apply  [b] Fallback (Mint-Y-Dark)  [s] Sync  [r] Refresh  [q] Quit"
        self.safe_addstr(max_y - 1, 0, help_text.ljust(max_x - 1), curses.color_pair(5))

    def render_presets_tab(self, start_y: int, max_y: int, max_x: int):
        total_presets = len(PRESETS)
        list_y = start_y + 2
        avail_height = (max_y - 6) - list_y
        items_per_page = max(1, avail_height // 2)

        # Update scroll offset so preset_index is always in the visible window
        if self.preset_index < self.preset_scroll_offset:
            self.preset_scroll_offset = self.preset_index
        elif self.preset_index >= self.preset_scroll_offset + items_per_page:
            self.preset_scroll_offset = self.preset_index - items_per_page + 1

        # Bounds check scroll offset
        max_possible_offset = max(0, total_presets - items_per_page)
        self.preset_scroll_offset = max(0, min(self.preset_scroll_offset, max_possible_offset))

        # Title & Scroll Indicators
        end_idx = min(total_presets, self.preset_scroll_offset + items_per_page)
        header_text = f"Select a curated suite (showing {self.preset_scroll_offset + 1}-{end_idx} of {total_presets}):"
        self.safe_addstr(start_y, 2, header_text, curses.color_pair(1) | curses.A_BOLD)

        # Scroll indicator flags
        more_up = self.preset_scroll_offset > 0
        more_down = end_idx < total_presets
        scroll_indicator = ""
        if more_up and more_down:
            scroll_indicator = f"▲ ({self.preset_scroll_offset} above) | ▼ ({total_presets - end_idx} below)"
        elif more_up:
            scroll_indicator = f"▲ ({self.preset_scroll_offset} more above)"
        elif more_down:
            scroll_indicator = f"▼ ({total_presets - end_idx} more below - scroll with ↓)"

        if scroll_indicator:
            ind_x = max(len(header_text) + 5, max_x - len(scroll_indicator) - 4)
            self.safe_addstr(start_y, ind_x, scroll_indicator, curses.color_pair(3) | curses.A_BOLD)

        visible_presets = PRESETS[self.preset_scroll_offset : self.preset_scroll_offset + items_per_page]

        for i, preset in enumerate(visible_presets):
            actual_idx = self.preset_scroll_offset + i
            y = list_y + i * 2
            if y >= max_y - 6:
                break

            is_selected = (actual_idx == self.preset_index)
            is_installed = self.manager.is_preset_installed(preset)
            is_active = (self.status.get("gtk_theme") == preset.gtk_theme_name)

            # Status tag
            if is_active:
                tag = " [ACTIVE] "
                tag_color = curses.color_pair(2) | curses.A_BOLD
            elif is_installed:
                tag = " [INSTALLED] "
                tag_color = curses.color_pair(3)
            else:
                tag = " [DOWNLOAD & APPLY] "
                tag_color = curses.color_pair(7)

            prefix = " ❯ " if is_selected else "   "
            item_text = f"{prefix}{preset.name:<32} {tag}"

            if is_selected:
                self.safe_addstr(y, 2, item_text, curses.color_pair(5) | curses.A_BOLD)
            else:
                self.safe_addstr(y, 2, prefix + f"{preset.name:<32}")
                self.safe_addstr(y, 37, tag, tag_color)

            # Details description line
            desc = f"    └─ {preset.description} (Cursor: {preset.cursor_theme_name})"
            self.safe_addstr(y + 1, 2, desc, curses.color_pair(8))

        # Bottom Log / Notice Area
        log_y = max_y - 5
        self.safe_addstr(log_y, 0, "─" * max_x)
        last_log = self.logs[-1] if self.logs else "Ready. Press [Enter] to install & apply, [↑/↓/PgUp/PgDn] to scroll."
        self.safe_addstr(log_y + 1, 2, f"Status: {last_log}", curses.color_pair(3))

    def render_custom_tab(self, start_y: int, max_y: int, max_x: int):
        self.safe_addstr(start_y, 2, "Configure components individually from installed packages:", curses.color_pair(1) | curses.A_BOLD)

        y = start_y + 2
        fields = [
            ("GTK Application Theme", self.installed_themes, self.custom_gtk_idx),
            ("Cinnamon Desktop Shell", self.installed_themes, self.custom_shell_idx),
            ("Icon Pack", self.installed_icons, self.custom_icon_idx),
            ("Cursor Theme", self.installed_cursors, self.custom_cursor_idx),
            ("Color Scheme Preference", ["dark", "light"], 0 if self.custom_mode == "dark" else 1),
            ("Apply Uniform Theming Now", [], 0)
        ]

        for idx, (label, options, curr_idx) in enumerate(fields):
            is_focus = (idx == self.custom_focus)
            prefix = " ❯ " if is_focus else "   "

            if idx == 5:
                # Apply button
                btn_text = f"{prefix}[ APPLY & SYNC FLATPAK / GTK4 / CURSORS NOW ]"
                btn_color = curses.color_pair(5) | curses.A_BOLD if is_focus else curses.color_pair(2) | curses.A_BOLD
                self.safe_addstr(y + 1, 4, btn_text, btn_color)
                break

            val = options[curr_idx] if options else "None installed"
            field_text = f"{prefix}{label:<28} : ◀ {val} ▶"
            field_color = curses.color_pair(5) | curses.A_BOLD if is_focus else 0
            self.safe_addstr(y, 4, field_text, field_color)

            y += 2

        # Log info
        log_y = max_y - 5
        self.safe_addstr(log_y, 0, "─" * max_x)
        last_log = self.logs[-1] if self.logs else "Use [←/→] to cycle values, [Enter] on Apply to execute."
        self.safe_addstr(log_y + 1, 2, f"Status: {last_log}", curses.color_pair(3))

    def render_flatpak_tab(self, start_y: int, max_y: int, max_x: int):
        self.safe_addstr(start_y, 2, "Flatpak Sandboxing & GTK 4 / Libadwaita Integration Status:", curses.color_pair(1) | curses.A_BOLD)

        y = start_y + 2
        fs_synced = self.status.get("flatpak_fs_synced", False)
        adw_synced = self.status.get("gtk4_active", False)

        # Flatpak filesystem access
        self.safe_addstr(y, 4, "Flatpak Read Access to ~/.themes, ~/.icons : ")
        if fs_synced:
            self.safe_addstr(y, 52, "GRANTED (Configured)", curses.color_pair(2) | curses.A_BOLD)
        else:
            self.safe_addstr(y, 52, "RESTRICTED (Flatpaks cannot see host themes)", curses.color_pair(4) | curses.A_BOLD)

        # GTK4 Link
        y += 2
        self.safe_addstr(y, 4, "Libadwaita / GTK 4 User Stylesheet (~/.config/gtk-4.0) : ")
        if adw_synced:
            self.safe_addstr(y, 60, "ACTIVE (Linked to current theme)", curses.color_pair(2) | curses.A_BOLD)
        else:
            self.safe_addstr(y, 60, "DEFAULT GNOME ADWAITA", curses.color_pair(3))

        y += 2
        self.safe_addstr(y, 4, "Detected Installed Flatpak Applications:", curses.color_pair(1))

        y += 1
        for app in self.flatpak_apps[:max_y - y - 6]:
            self.safe_addstr(y, 6, f"• {app}", curses.color_pair(8))
            y += 1

        # Quick Actions
        action_y = max_y - 4
        self.safe_addstr(action_y, 0, "─" * max_x)
        self.safe_addstr(action_y + 1, 4, " Press [s] to forcefully re-sync Flatpak overrides now ", curses.color_pair(6))

    def render_help_tab(self, start_y: int, max_y: int, max_x: int):
        self.safe_addstr(start_y, 2, "How Uniform Theming & Cursors Work on Linux Mint / Cinnamon:", curses.color_pair(1) | curses.A_BOLD)

        help_paragraphs = [
            ("1. Cursor Synchronization",
             "Cursor themes are synchronized across Cinnamon GSettings, GNOME XDG Portals,\n"
             "~/.config/gtk-3.0/settings.ini, ~/.icons/default/index.theme (root X11 window),\n"
             "and injected into Flatpak sandboxes via XCURSOR_THEME & XCURSOR_SIZE."),

            ("2. The GTK3 vs Libadwaita Divide",
             "Modern GNOME apps built with GTK4 / Libadwaita ignore traditional GTK themes by design.\n"
             "This tool solves that by synchronizing your selected theme's GTK 4 CSS rules into\n"
             "~/.config/gtk-4.0/gtk.css and setting the desktop portal color-scheme flag."),

            ("3. Flatpak Sandboxing Resolution",
             "Flatpaks cannot access ~/.themes or ~/.icons unless explicitly permitted.\n"
             "This tool sets global user overrides granting read-only access to host theme dirs,\n"
             "synchronizes window button layouts and cursors, and aligns Libadwaita stylesheets.")
        ]

        y = start_y + 2
        for title, body in help_paragraphs:
            if y >= max_y - 4:
                break
            self.safe_addstr(y, 4, title, curses.color_pair(3) | curses.A_BOLD)
            y += 1
            for line in body.splitlines():
                if y >= max_y - 4:
                    break
                self.safe_addstr(y, 6, line)
                y += 1
            y += 1

    def run_preset_action(self, preset: ThemePreset):
        def log(msg):
            self.log_message(msg)
            self.draw()

        # Handle restore default
        if preset.id == "mint-default":
            self.manager.reset_to_defaults(log)
            self.refresh_status()
            return

        # 1. Download/Install theme if needed
        success = self.manager.install_theme_preset(preset, log)
        if not success:
            log(f"Failed to install {preset.name}. Safely falling back to Mint-Y-Dark...")
            self.manager.fallback_to_default(log)
            self.refresh_status()
            return

        # 2. Check icon pack
        if preset.id.startswith("whitesur"):
            self.manager.install_icon_pack("whitesur-icons", log)
        elif preset.icon_download_url:
            self.manager.install_icon_archive(preset.icon_theme_name, preset.icon_download_url, log)

        # 3. Check cursor pack
        if preset.cursor_download_url:
            self.manager.install_cursor_theme(preset.cursor_theme_name, preset.cursor_download_url, log)

        # 4. Apply uniform settings
        self.manager.apply_uniform_theming(
            gtk_theme=preset.gtk_theme_name,
            cinnamon_theme=preset.cinnamon_theme_name,
            icon_theme=preset.icon_theme_name,
            cursor_theme=preset.cursor_theme_name,
            mode=preset.mode,
            log=log
        )
        self.refresh_status()

    def draw(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        if max_y < 15 or max_x < 60:
            self.safe_addstr(0, 0, "Terminal window too small! Please enlarge.")
            self.stdscr.refresh()
            return

        self.draw_header(max_y, max_x)

        start_y = 5
        if self.current_tab == 0:
            self.render_presets_tab(start_y, max_y, max_x)
        elif self.current_tab == 1:
            self.render_custom_tab(start_y, max_y, max_x)
        elif self.current_tab == 2:
            self.render_flatpak_tab(start_y, max_y, max_x)
        elif self.current_tab == 3:
            self.render_help_tab(start_y, max_y, max_x)

        self.draw_footer(max_y, max_x)
        self.stdscr.refresh()

    def handle_input(self):
        key = self.stdscr.getch()

        if key in [ord('q'), ord('Q'), 27]:  # 27 is ESC
            return False

        elif key in [curses.KEY_LEFT, ord('h'), ord('\t')]:
            self.current_tab = (self.current_tab + 1) % len(self.tabs)

        elif key in [curses.KEY_RIGHT, ord('l')]:
            self.current_tab = (self.current_tab - 1) % len(self.tabs)

        elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:
            self.current_tab = key - ord('1')

        elif key in [ord('r'), ord('R')]:
            self.refresh_status()
            self.log_message("Status refreshed.")

        elif key in [ord('s'), ord('S')]:
            def log(msg):
                self.log_message(msg)
                self.draw()
            self.manager.sync_flatpak_overrides(
                self.status.get("gtk_theme", "Mint-Y-Dark"),
                self.status.get("icon_theme", "Mint-Y"),
                self.status.get("cursor_theme", "Bibata-Modern-Classic"),
                24,
                log
            )
            self.refresh_status()

        elif key in [ord('b'), ord('B')]:
            def log(msg):
                self.log_message(msg)
                self.draw()
            self.manager.fallback_to_default(log)
            self.refresh_status()
            self.log_message("Safety fallback activated: Mint-Y-Dark active.")

        # Tab specific controls
        elif self.current_tab == 0:
            # Presets tab
            if key in [curses.KEY_UP, ord('k')]:
                self.preset_index = (self.preset_index - 1) % len(PRESETS)
            elif key in [curses.KEY_DOWN, ord('j')]:
                self.preset_index = (self.preset_index + 1) % len(PRESETS)
            elif key in [curses.KEY_PPAGE]:  # Page Up
                self.preset_index = max(0, self.preset_index - 4)
            elif key in [curses.KEY_NPAGE]:  # Page Down
                self.preset_index = min(len(PRESETS) - 1, self.preset_index + 4)
            elif key in [curses.KEY_HOME]:
                self.preset_index = 0
            elif key in [curses.KEY_END]:
                self.preset_index = len(PRESETS) - 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                chosen = PRESETS[self.preset_index]
                self.run_preset_action(chosen)

        elif self.current_tab == 1:
            # Custom tab
            if key in [curses.KEY_UP, ord('k')]:
                self.custom_focus = (self.custom_focus - 1) % 6
            elif key in [curses.KEY_DOWN, ord('j')]:
                self.custom_focus = (self.custom_focus + 1) % 6
            elif key in [curses.KEY_LEFT, ord('h')]:
                if self.custom_focus == 0 and self.installed_themes:
                    self.custom_gtk_idx = (self.custom_gtk_idx - 1) % len(self.installed_themes)
                elif self.custom_focus == 1 and self.installed_themes:
                    self.custom_shell_idx = (self.custom_shell_idx - 1) % len(self.installed_themes)
                elif self.custom_focus == 2 and self.installed_icons:
                    self.custom_icon_idx = (self.custom_icon_idx - 1) % len(self.installed_icons)
                elif self.custom_focus == 3 and self.installed_cursors:
                    self.custom_cursor_idx = (self.custom_cursor_idx - 1) % len(self.installed_cursors)
                elif self.custom_focus == 4:
                    self.custom_mode = "light" if self.custom_mode == "dark" else "dark"
            elif key in [curses.KEY_RIGHT, ord('l')]:
                if self.custom_focus == 0 and self.installed_themes:
                    self.custom_gtk_idx = (self.custom_gtk_idx + 1) % len(self.installed_themes)
                elif self.custom_focus == 1 and self.installed_themes:
                    self.custom_shell_idx = (self.custom_shell_idx + 1) % len(self.installed_themes)
                elif self.custom_focus == 2 and self.installed_icons:
                    self.custom_icon_idx = (self.custom_icon_idx + 1) % len(self.installed_icons)
                elif self.custom_focus == 3 and self.installed_cursors:
                    self.custom_cursor_idx = (self.custom_cursor_idx + 1) % len(self.installed_cursors)
                elif self.custom_focus == 4:
                    self.custom_mode = "light" if self.custom_mode == "dark" else "dark"
            elif key in [curses.KEY_ENTER, 10, 13]:
                if self.custom_focus == 5:
                    def log(msg):
                        self.log_message(msg)
                        self.draw()
                    gtk_name = self.installed_themes[self.custom_gtk_idx]
                    shell_name = self.installed_themes[self.custom_shell_idx]
                    icon_name = self.installed_icons[self.custom_icon_idx]
                    cursor_name = self.installed_cursors[self.custom_cursor_idx] if self.installed_cursors else ""
                    self.manager.apply_uniform_theming(
                        gtk_name, shell_name, icon_name, cursor_name, self.custom_mode, 24, log
                    )
                    self.refresh_status()

        return True

    def main_loop(self):
        while True:
            self.draw()
            if not self.handle_input():
                break

def launch():
    curses.wrapper(lambda scr: CinnamonThemeTUI(scr).main_loop())

if __name__ == "__main__":
    launch()
