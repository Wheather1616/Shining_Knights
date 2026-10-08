"""ShiningKnights design tokens and lightweight QSS token rendering."""

from __future__ import annotations

from pathlib import Path

TOKENS: dict[str, str] = {
    # Typography
    "font_regular": '"Idiqlat", "Helvetica Neue", Arial, sans-serif',
    "font_body": '"Helvetica Neue", "Segoe UI", Arial, sans-serif',
    "font_light": '"Idiqlat ExtraLight", "Idiqlat Light", "Helvetica Neue", Arial, sans-serif',
    # Brand palette
    "canvas": "#fbf8f5",
    "surface": "#fffdfb",
    "surface_alt": "#fffaf7",
    "surface_soft": "#f8f3ef",
    "text": "#302a30",
    "text_muted": "#6b6267",
    "text_subtle": "#8a8185",
    "border": "#e5dad3",
    "border_strong": "#d7d0c8",
    "bordeaux": "#52050a",
    "bordeaux_mid": "#6d0813",
    "bordeaux_dark": "#430408",
    "amethyst": "#a846a0",
    "cyan": "#258ea6",
    "coral": "#f87666",
    "white": "#ffffff",
    # Soft semantic fills
    "cyan_soft": "#eef8fa",
    "cyan_border": "#c6e5eb",
    "amethyst_soft": "#faf2fb",
    "amethyst_border": "#e7cce5",
    "coral_soft": "#fff2ef",
    "coral_border": "#f3c5be",
    "green_soft": "#eef9f1",
    "green": "#2d7650",
    "green_border": "#c8e8d2",
    # Standard geometry
    "radius_control": "12px",
    "radius_card": "18px",
    "radius_large": "20px",
}


# Paths are resolved at runtime, including inside a PyInstaller bundle.
_THEME_ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'theme'
for key, filename in [('icon_tick','check.svg'), ('icon_down','chevron-down.svg'),
                      ('icon_right','chevron-right.svg'), ('icon_partial','partial.svg'),
                      ('icon_down_white','chevron-down-white.svg')]:
    path = (_THEME_ASSETS / filename).as_posix().replace('"', '\\"')
    TOKENS[key] = f'url("{path}")'

def themed(source: str) -> str:
    """Replace ``@token@`` markers in a QSS fragment with design tokens."""
    rendered = source
    for key, value in TOKENS.items():
        rendered = rendered.replace(f"@{key}@", value)
    return rendered
