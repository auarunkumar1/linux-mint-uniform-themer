"""Theme definitions and repository metadata for Cinnamon Theme Sync."""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ThemePreset:
    id: str
    name: str
    description: str
    mode: str  # 'dark' or 'light'
    gtk_theme_name: str
    cinnamon_theme_name: str
    icon_theme_name: str
    cursor_theme_name: str
    provider_name: str
    install_type: str  # 'git_installer', 'archive', 'system_apt'
    repo_url: str
    download_url: Optional[str] = None
    install_args: Optional[List[str]] = None
    cursor_download_url: Optional[str] = None
    icon_download_url: Optional[str] = None

# Curated list of high-uniformity theme presets with known Libadwaita & Cinnamon support
PRESETS = [
    ThemePreset(
        id="mint-default",
        name="[FALLBACK] Linux Mint Default",
        description="Emergency safety fallback: stock Mint-Y-Dark, standard icons & pure default Adwaita",
        mode="dark",
        gtk_theme_name="Mint-Y-Dark",
        cinnamon_theme_name="Mint-Y-Dark",
        icon_theme_name="Mint-Y",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="Linux Mint (Pre-installed)",
        install_type="system_apt",
        repo_url=""
    ),
    ThemePreset(
        id="nordic-dark",
        name="Nordic (Dark Arctic)",
        description="Cold northern blue-grey tones with matching Nordzy-dark icons & Bibata cursor",
        mode="dark",
        gtk_theme_name="Nordic",
        cinnamon_theme_name="Nordic",
        icon_theme_name="Nordzy-dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="EliverLara & MolassesLover",
        install_type="archive",
        repo_url="https://github.com/EliverLara/Nordic",
        download_url="https://github.com/EliverLara/Nordic/releases/download/v2.2.0/Nordic-v40.tar.xz",
        icon_download_url="https://github.com/MolassesLover/Nordzy-icon/releases/download/1.8.7/Nordzy-dark.tar.gz"
    ),
    ThemePreset(
        id="nordic-polar",
        name="Nordic Polar (Light Arctic)",
        description="Crisp icy white and pastel blue light theme with matching Nordzy icons & Bibata Ice cursor",
        mode="light",
        gtk_theme_name="Nordic-Polar",
        cinnamon_theme_name="Nordic-Polar",
        icon_theme_name="Nordzy",
        cursor_theme_name="Bibata-Modern-Ice",
        provider_name="EliverLara & MolassesLover",
        install_type="archive",
        repo_url="https://github.com/EliverLara/Nordic",
        download_url="https://github.com/EliverLara/Nordic/releases/download/v2.2.0/Nordic-Polar-v40.tar.xz",
        icon_download_url="https://github.com/MolassesLover/Nordzy-icon/releases/download/1.8.7/Nordzy.tar.gz"
    ),
    ThemePreset(
        id="gruvbox-dark",
        name="Gruvbox Retro (Dark)",
        description="Warm earthy retro-groove palette with native Cinnamon panel and Libadwaita styling",
        mode="dark",
        gtk_theme_name="Colloid-Dark-Gruvbox",
        cinnamon_theme_name="Colloid-Dark-Gruvbox",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="vinceliuice (Colloid)",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Colloid-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "--tweaks", "gruvbox", "-c", "dark"]
    ),
    ThemePreset(
        id="everforest-dark",
        name="Everforest Nature (Dark)",
        description="Comforting nature-inspired green-grey tones with Libadwaita & Cinnamon assets",
        mode="dark",
        gtk_theme_name="Colloid-Dark-Everforest",
        cinnamon_theme_name="Colloid-Dark-Everforest",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="vinceliuice (Colloid)",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Colloid-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "--tweaks", "everforest", "-c", "dark"]
    ),
    ThemePreset(
        id="graphite-dark",
        name="Graphite Minimal (Dark)",
        description="Refined monochrome minimalist dark design with full Libadwaita & Cinnamon panel styling",
        mode="dark",
        gtk_theme_name="Graphite-Dark",
        cinnamon_theme_name="Graphite-Dark",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="vinceliuice (GitHub)",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Graphite-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "-c", "dark"]
    ),
    ThemePreset(
        id="sweet-dark",
        name="Sweet Cyberpunk (Dark)",
        description="Vibrant neon gradient dark aesthetic by EliverLara with Cinnamon & GTK4 support",
        mode="dark",
        gtk_theme_name="Sweet-Dark",
        cinnamon_theme_name="Sweet-Dark",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="EliverLara (GitHub)",
        install_type="archive",
        repo_url="https://github.com/EliverLara/Sweet",
        download_url="https://github.com/EliverLara/Sweet/releases/download/v6.0/Sweet-Dark-v40.tar.xz"
    ),
    ThemePreset(
        id="dracula",
        name="Dracula Official (Dark)",
        description="High-contrast dark gothic palette with vibrant neon accents & Dracula cursors",
        mode="dark",
        gtk_theme_name="Dracula",
        cinnamon_theme_name="Dracula",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Dracula-cursors",
        provider_name="dracula (GitHub)",
        install_type="archive",
        repo_url="https://github.com/dracula/gtk",
        download_url="https://github.com/dracula/gtk/releases/download/v4.0.0/Dracula.tar.xz",
        cursor_download_url="https://github.com/dracula/gtk/releases/download/v4.0.0/Dracula-cursors.tar.xz"
    ),
    ThemePreset(
        id="tokyo-night-dark",
        name="Tokyo Night (Dark)",
        description="Dark neon aesthetic celebrating the lights of downtown Tokyo with Bibata cursor",
        mode="dark",
        gtk_theme_name="Tokyonight-Dark",
        cinnamon_theme_name="Tokyonight-Dark",
        icon_theme_name="Tokyonight-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="Fausto-Korpsvart (GitHub)",
        install_type="git_installer",
        repo_url="https://github.com/Fausto-Korpsvart/Tokyo-Night-GTK-Theme.git",
        install_args=["-d", "{themes_dir}", "-c", "dark"]
    ),
    ThemePreset(
        id="tokyo-night-light",
        name="Tokyo Night (Light)",
        description="Tokyo Night daylight variant with balanced contrast & Bibata Ice cursor",
        mode="light",
        gtk_theme_name="Tokyonight-Light",
        cinnamon_theme_name="Tokyonight-Light",
        icon_theme_name="Tokyonight-Light",
        cursor_theme_name="Bibata-Modern-Ice",
        provider_name="Fausto-Korpsvart (GitHub)",
        install_type="git_installer",
        repo_url="https://github.com/Fausto-Korpsvart/Tokyo-Night-GTK-Theme.git",
        install_args=["-d", "{themes_dir}", "-c", "light"]
    ),
    ThemePreset(
        id="whitesur-dark",
        name="macOS WhiteSur (Dark)",
        description="Apple macOS Big Sur / Sonoma dark aesthetics with Libadwaita, Cinnamon & macOS cursor",
        mode="dark",
        gtk_theme_name="WhiteSur-Dark",
        cinnamon_theme_name="WhiteSur-Dark",
        icon_theme_name="WhiteSur-dark",
        cursor_theme_name="macOS",
        provider_name="vinceliuice & ful1e5",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/WhiteSur-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "-c", "dark", "-a", "normal", "-N", "stable"],
        cursor_download_url="https://github.com/ful1e5/apple_cursor/releases/download/v2.0.1/macOS.tar.xz"
    ),
    ThemePreset(
        id="whitesur-light",
        name="macOS WhiteSur (Light)",
        description="Apple macOS light design with frosted borders, Libadwaita alignment & white macOS cursor",
        mode="light",
        gtk_theme_name="WhiteSur-Light",
        cinnamon_theme_name="WhiteSur-Light",
        icon_theme_name="WhiteSur",
        cursor_theme_name="macOS-White",
        provider_name="vinceliuice & ful1e5",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/WhiteSur-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "-c", "light", "-a", "normal", "-N", "stable"],
        cursor_download_url="https://github.com/ful1e5/apple_cursor/releases/download/v2.0.1/macOS-White.tar.xz"
    ),
    ThemePreset(
        id="catppuccin-mocha",
        name="Catppuccin Mocha (Dark)",
        description="Soothing pastel dark palette with deep blue accents, Libadwaita & Catppuccin cursor",
        mode="dark",
        gtk_theme_name="Colloid-Dark-Catppuccin",
        cinnamon_theme_name="Colloid-Dark-Catppuccin",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="catppuccin-mocha-dark-cursors",
        provider_name="vinceliuice & Catppuccin",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Colloid-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "--tweaks", "catppuccin", "-c", "dark"],
        cursor_download_url="https://github.com/catppuccin/cursors/releases/download/v1.0.2/catppuccin-mocha-dark-cursors.zip"
    ),
    ThemePreset(
        id="catppuccin-latte",
        name="Catppuccin Latte (Light)",
        description="Warm, comforting pastel light theme with soft contrast, Libadwaita & Catppuccin cursor",
        mode="light",
        gtk_theme_name="Colloid-Light-Catppuccin",
        cinnamon_theme_name="Colloid-Light-Catppuccin",
        icon_theme_name="Papirus-Light",
        cursor_theme_name="catppuccin-latte-light-cursors",
        provider_name="vinceliuice & Catppuccin",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Colloid-gtk-theme.git",
        install_args=["-d", "{themes_dir}", "--tweaks", "catppuccin", "-c", "light"],
        cursor_download_url="https://github.com/catppuccin/cursors/releases/download/v1.0.2/catppuccin-latte-light-cursors.zip"
    ),
    ThemePreset(
        id="orchis-dark",
        name="Orchis Modern (Dark)",
        description="Material-inspired rounded design with fluid Cinnamon panel & Bibata cursor",
        mode="dark",
        gtk_theme_name="Orchis-Dark",
        cinnamon_theme_name="Orchis-Dark",
        icon_theme_name="Papirus-Dark",
        cursor_theme_name="Bibata-Modern-Classic",
        provider_name="vinceliuice (GitHub)",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Orchis-theme.git",
        install_args=["-d", "{themes_dir}", "-c", "dark"]
    ),
    ThemePreset(
        id="orchis-light",
        name="Orchis Modern (Light)",
        description="Material-inspired clean light theme with subtle elevations & Bibata Ice cursor",
        mode="light",
        gtk_theme_name="Orchis-Light",
        cinnamon_theme_name="Orchis-Light",
        icon_theme_name="Papirus-Light",
        cursor_theme_name="Bibata-Modern-Ice",
        provider_name="vinceliuice (GitHub)",
        install_type="git_installer",
        repo_url="https://github.com/vinceliuice/Orchis-theme.git",
        install_args=["-d", "{themes_dir}", "-c", "light"]
    )
]

# Curated icon providers for separate or bundled installation
ICON_PACKS = [
    {
        "id": "nordzy-icons",
        "name": "Nordzy (Nordic Icons)",
        "variants": ["Nordzy-dark", "Nordzy"],
        "repo_url": "https://github.com/MolassesLover/Nordzy-icon",
        "install_type": "archive",
        "download_url": "https://github.com/MolassesLover/Nordzy-icon/releases/download/1.8.7/Nordzy-dark.tar.gz"
    },
    {
        "id": "whitesur-icons",
        "name": "WhiteSur Icons",
        "variants": ["WhiteSur-dark", "WhiteSur"],
        "repo_url": "https://github.com/vinceliuice/WhiteSur-icon-theme.git",
        "install_type": "git_installer",
        "install_args": ["-d", "{icons_dir}"]
    },
    {
        "id": "tela-circle-icons",
        "name": "Tela Circle Icons",
        "variants": ["Tela-circle-dark", "Tela-circle"],
        "repo_url": "https://github.com/vinceliuice/Tela-circle-icon-theme.git",
        "install_type": "git_installer",
        "install_args": ["-d", "{icons_dir}"]
    },
    {
        "id": "papirus-icons",
        "name": "Papirus Icons",
        "variants": ["Papirus-Dark", "Papirus-Light", "Papirus"],
        "repo_url": "https://github.com/PapirusDevelopmentTeam/papirus-icon-theme",
        "install_type": "preinstalled",
        "install_args": []
    }
]
