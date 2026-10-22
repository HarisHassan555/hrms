"""
Fixed Vristo chrome palette.

The Color Theme settings page (`/theme/color-theme-view/`) stores a
`CompanyTheme`, but the application chrome must stay on the Vristo layer
(`html.vristo-theme`) rather than Coral / Amber / Sunset presets. Those
presets paint `bg-primary-50` / `bg-primary-100` as peach or yellow.

Template tags `get_company` and `get_def_theme` return this object so
inline CSS and Tailwind JIT utilities stay on Vristo indigo.
"""


class VristoPalette:
    name = "Vristo"
    description = "Vristo indigo chrome"
    is_default = True

    # Brand (matches --vristo-primary in vristo-theme.css)
    primary_50 = "#f5f7fb"
    primary_100 = "#eaf1ff"
    primary_200 = "#d9e5ff"
    primary_300 = "#c4d7ff"
    primary_400 = "#a8c0ff"
    primary_500 = "#6b8cff"
    primary_600 = "#4361ee"
    primary_700 = "#3a4ecc"
    primary_800 = "#2f3eb8"
    primary_900 = "#1e2a80"

    dark_50 = "#E6E6E6"
    dark_100 = "#A8A8A8"
    dark_200 = "#515151"
    dark_300 = "#3b3f5c"
    dark_400 = "#64748B"
    dark_500 = "#0e1726"
    dark_600 = "#000000"

    secondary_50 = "#f8fafc"
    secondary_100 = "#f1f5f9"
    secondary_200 = "#e2e8f0"
    secondary_300 = "#cbd5e1"
    secondary_400 = "#a8c0ff"
    secondary_500 = "#6b8cff"
    secondary_600 = "#4361ee"
    secondary_700 = "#334155"
    secondary_800 = "#1e293b"
    secondary_900 = "#0f172a"


VRISTO_THEME = VristoPalette()
