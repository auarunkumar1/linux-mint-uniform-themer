# Linux Mint Uniform Themer (`cinna-theme`)

[![Platform](https://img.shields.io/badge/Platform-Linux%20Mint%20%7C%20Cinnamon-darkgreen?logo=linuxmint)](https://linuxmint.com/)
[![GTK Support](https://img.shields.io/badge/GTK-3.0%20%7C%204.0%20%28Libadwaita%29-blue)](https://gtk.org/)
[![Flatpak](https://img.shields.io/badge/Flatpak-Sandbox%20Synced-2f54eb?logo=flatpak)](https://flatpak.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B%20%28Zero%20Dependencies%29-yellow?logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A lightweight, zero-dependency Terminal User Interface (TUI) and automation engine designed to solve desktop theming fragmentation across **Cinnamon Shell**, **GTK 3**, **GTK 4 / Libadwaita**, **Cursor Themes**, and **Flatpak applications**.

---

## The Theming Fragmentation Problem

Modern Linux desktops — particularly Linux Mint Cinnamon running a mixture of native and sandboxed Flatpak apps — suffer from four distinct layers of theming isolation:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Cinnamon Desktop Shell                          │
│          (Panel, Start Menu, Workspace Switcher, Applets)              │
├───────────────────────────────────┬────────────────────────────────────┤
│         GTK 3 Applications        │        GTK 4 / Libadwaita Apps     │
│   (Nemo, Xed, Celluloid, etc.)    │  (Easy Effects, TubeConverter,     │
│  Reads: org.cinnamon.desktop.gtk  │   Flatseal, modern GNOME apps)     │
│  and ~/.config/gtk-3.0/           │  Ignores classic GTK themes;      │
│                                   │  requires ~/.config/gtk-4.0/ CSS   │
├───────────────────────────────────┴────────────────────────────────────┤
│                       Flatpak Container Sandboxes                      │
│   (Cannot see ~/.themes, ~/.icons, or GTK configs unless permitted;    │
│    often fall back to default white/black cursors and Adwaita styles)  │
├────────────────────────────────────────────────────────────────────────┤
│                         Cursor Synchronization                         │
│   (Root X11 window reads ~/.icons/default/index.theme;                 │
│    Flatpaks require XCURSOR_THEME & XCURSOR_SIZE environment vars)     │
└────────────────────────────────────────────────────────────────────────┘
```

**Linux Mint Uniform Themer** bridges all these layers simultaneously in a single keystroke.

---

## Key Features

- **Zero Pip Dependencies**: Built strictly using Python's standard library (`curses`, `subprocess`, `urllib`, `tarfile`, `zipfile`). Runs natively on stock Linux Mint without setting up virtual environments or installing pip packages.
- **Dynamic Virtual Scrolling**: Effortlessly browses long lists of theme suites with automatic viewport scrolling, position indicators, and support for `↑`/`↓`, `Page Up`, `Page Down`, `Home`, and `End`.
- **Complete Libadwaita Alignment**: Automatically symlinks theme `gtk-4.0` stylesheets and synchronizes desktop portal `color-scheme` preferences (`prefer-dark` / `prefer-light`).
- **Comprehensive Flatpak Overrides**: Automatically grants read-only container access to host themes (`xdg-data/themes`, `~/.themes`, `~/.icons`, `xdg-config/gtk-3.0`, `xdg-config/gtk-4.0`), exports `XCURSOR_THEME`, `XCURSOR_SIZE`, and `QT_QPA_PLATFORMTHEME`, and safely prevents `GTK_THEME` environment collisions that break modern Libadwaita apps.
- **Window Controls & Layout Alignment**: Automatically propagates Cinnamon's window titlebar button layout (`:minimize,maximize,close`) into both GTK 3 and GTK 4 `settings.ini` so sandboxed Flatpak apps never lose their headerbars, minimize, maximize, or close buttons.
- **System-Wide Cursor Synchronization**: Keeps cursor themes uniform across Cinnamon GSettings, GNOME GSettings, GTK3 INI, X11 root window, and Flatpaks.
- **Instant Safety Fallback (`[b]`)**: Press `b` at any time to instantly restore stock `Mint-Y-Dark`, default `Mint-Y` icons, and `Bibata-Modern-Classic` cursors while safely clearing any active overrides.
- **Automated Error Recovery**: If any upstream theme download or compilation fails, the system automatically catches the failure and reverts safely to `Mint-Y-Dark` so the desktop is never left in a broken state.

---

## Curated Theme Suites

Only themes with proven upstream support for GTK 3, GTK 4, Cinnamon, and high-DPI icon integration are included:

| Suite | Style / Mode | Upstream Provider | Included Assets |
| :--- | :--- | :--- | :--- |
| **Linux Mint Default** | Dark | Linux Mint | **[SAFETY FALLBACK]** Stock Mint-Y-Dark, Mint-Y icons & pure Adwaita |
| **Nordic** | Dark & Polar (Light) | [EliverLara](https://github.com/EliverLara/Nordic) | Nordic arctic palette with matching **Nordzy** icon packs & Bibata cursor |
| **Gruvbox Retro** | Dark | [vinceliuice (Colloid)](https://github.com/vinceliuice/Colloid-gtk-theme) | Warm earthy retro-groove theme with Cinnamon panel & Libadwaita styling |
| **Everforest Nature** | Dark | [vinceliuice (Colloid)](https://github.com/vinceliuice/Colloid-gtk-theme) | Nature-inspired green-grey tones with Libadwaita stylesheet & Cinnamon assets |
| **Graphite Minimal** | Dark | [vinceliuice](https://github.com/vinceliuice/Graphite-gtk-theme) | Refined monochrome minimalist dark design with Cinnamon shell & GTK4 styling |
| **Sweet Cyberpunk** | Dark | [EliverLara](https://github.com/EliverLara/Sweet) | Vibrant neon gradient dark aesthetic with Cinnamon & GTK4 window assets |
| **Dracula Official** | Dark | [dracula](https://github.com/dracula/gtk) | Iconic high-contrast dark gothic theme with official Dracula cursors |
| **Tokyo Night** | Dark & Light | [Fausto-Korpsvart](https://github.com/Fausto-Korpsvart/Tokyo-Night-GTK-Theme) | Downtown Tokyo aesthetic with bundled Tokyonight icon sets & Libadwaita |
| **macOS WhiteSur** | Dark & Light | [vinceliuice](https://github.com/vinceliuice/WhiteSur-gtk-theme) | macOS Big Sur/Sonoma styling + WhiteSur icons & [ful1e5](https://github.com/ful1e5/apple_cursor) macOS cursor |
| **Catppuccin** | Mocha & Latte | vinceliuice & [catppuccin](https://github.com/catppuccin/cursors) | Soothing pastel dark & light palettes with Catppuccin cursors |
| **Orchis Modern** | Dark & Light | [vinceliuice](https://github.com/vinceliuice/Orchis-theme) | Material-inspired rounded design with Cinnamon shell integration |

---

## Installation

### Clone & Install
```bash
git clone https://github.com/auarunkumar1/linux-mint-uniform-themer.git ~/Documents/pyscripts/cinna-theme
cd ~/Documents/pyscripts/cinna-theme
./install.sh
```

The installer:
1. Links the executable to `~/.local/bin/cinna-theme`.
2. Installs the desktop entry into `~/.local/share/applications/` so you can launch **Cinnamon Theme Sync** directly from your Cinnamon application menu.

---

## Usage

### 1. Interactive TUI (Recommended)
Launch the TUI from any terminal:
```bash
cinna-theme
```

#### Keyboard Shortcuts:
| Key | Action |
| :--- | :--- |
| `↑` / `↓` or `k` / `j` | Navigate items and scroll smoothly through the suite list |
| `Page Up` / `Page Down` | Jump 4 items up or down |
| `Home` / `End` | Jump directly to the top or bottom of the preset list |
| `Tab` or `←` / `→` | Switch tabs (*Curated Suites*, *Custom Components*, *Flatpak & Libadwaita*, *Help*) |
| `Enter` | 1-Click download (if needed) and apply system-wide |
| `b` | **Emergency Safety Fallback**: Instantly restores `Mint-Y-Dark` system-wide |
| `s` | Force re-sync Flatpak sandboxes to active host theme |
| `r` | Refresh live desktop & sandbox status |
| `q` / `Esc` | Quit the application |

---

### 2. CLI Mode (For Scripts & Quick Actions)

```bash
# Check current system-wide theme, cursor, and Flatpak status
cinna-theme --status

# List all available presets with installation status
cinna-theme --list

# Apply any preset headless
cinna-theme --apply nordic-dark
cinna-theme --apply gruvbox-dark
cinna-theme --apply everforest-dark
cinna-theme --apply sweet-dark
cinna-theme --apply graphite-dark
cinna-theme --apply dracula
cinna-theme --apply tokyo-night-dark
cinna-theme --apply whitesur-dark

# Force re-sync Flatpaks to your active desktop theme
cinna-theme --sync-flatpak

# Instant safety fallback to Linux Mint defaults (Mint-Y-Dark)
cinna-theme --fallback
# or
cinna-theme --reset
```

---

## Under the Hood: What Gets Changed

When you apply a theme, `cinna-theme` automates the following steps:

1. **Cinnamon Shell & GTK3**:
   - `gsettings set org.cinnamon.desktop.interface gtk-theme <theme>`
   - `gsettings set org.cinnamon.desktop.interface icon-theme <icons>`
   - `gsettings set org.cinnamon.desktop.interface cursor-theme <cursor>`
   - `gsettings set org.cinnamon.theme name <theme>`
2. **XDG Desktop Portal & Libadwaita**:
   - `gsettings set org.cinnamon.desktop.interface color-scheme "prefer-dark"` (or `"prefer-light"`)
   - `gsettings set org.gnome.desktop.interface color-scheme "prefer-dark"`
   - Links `<theme_path>/gtk-4.0/gtk.css` and `assets` to `~/.config/gtk-4.0/`.
3. **GTK 3 & GTK 4 Settings Files**:
   - Generates and synchronizes both `~/.config/gtk-3.0/settings.ini` and `~/.config/gtk-4.0/settings.ini` with cursor definitions (`gtk-cursor-theme-name`, `gtk-cursor-theme-size`) and window controls layout (`gtk-decoration-layout = :minimize,maximize,close`).
   - Keeps `gtk-theme-name` for GTK 3 while ensuring GTK 4 / Libadwaita retains its native stylesheet engine (styling customized cleanly via `gtk.css`), avoiding stripped buttons and corrupted headerbars.
4. **User-Space Cursor Shadowing & X11 Sync**:
   - **User-Space Shadowing**: Flatpak sandboxes cannot access `/usr/share/icons/` from the host. `cinna-theme` automatically detects and shadows host system cursor themes into `~/.icons/<theme>` so sandboxed apps have direct read access.
   - **X11 Resources (`xrdb`)**: Merges `Xcursor.theme` and `Xcursor.size` dynamically into the active X11 server via `xrdb -merge` and updates `~/.Xresources`.
   - **Root Window**: Updates `~/.icons/default/index.theme` so legacy, root-level, and desktop boundary windows inherit the cursor.
5. **Flatpak Sandbox Overrides**:
   - Grants read-only filesystem permissions for themes, icons, and GTK 3/4 configurations (`xdg-data/themes`, `xdg-data/icons`, `~/.themes`, `~/.icons`, `xdg-config/gtk-3.0`, `xdg-config/gtk-4.0`).
   - Explicitly avoids global `GTK_THEME` environment injection (which crashes Libadwaita's style engine into bare unstyled text), while setting `XCURSOR_THEME`, `XCURSOR_SIZE`, and `QT_QPA_PLATFORMTHEME=qt5ct`.

---

## Upstream Credits

Huge thanks to the upstream designers and maintainers whose work makes desktop customization on Linux beautiful:
- [EliverLara](https://github.com/EliverLara) (Nordic, Sweet)
- [vinceliuice](https://github.com/vinceliuice) (WhiteSur, Colloid, Orchis, Graphite, Tela Icons)
- [MolassesLover](https://github.com/MolassesLover) (Nordzy Icon Theme)
- [Fausto-Korpsvart](https://github.com/Fausto-Korpsvart) (Tokyo Night GTK)
- [dracula](https://github.com/dracula) (Dracula Theme Organization)
- [ful1e5](https://github.com/ful1e5) (Apple Cursor)
- [Papirus Development Team](https://github.com/PapirusDevelopmentTeam) (Papirus Icons)

---

## License

Distributed under the [MIT License](LICENSE).
