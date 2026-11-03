"""
Fixed DSG / Vristo chrome palette.

The Color Theme settings page (`/theme/color-theme-view/`) stores a
`CompanyTheme`, but the application chrome stays on this indigo layer
rather than Coral / Amber / Sunset presets. Those presets paint
`bg-primary-50` / `bg-primary-100` as peach or yellow.

Template tags `get_company` and `get_def_theme` return this object so
inline CSS and Tailwind JIT utilities stay on the DSG indigo brand.
"""


class VristoPalette:
    name = "DSG Indigo"
    description = "DSG enterprise indigo chrome"
    is_default = True

    # Brand (matches AGENTS.md / SaaS design tokens)
    primary_50 = "#F8FAFC"
    primary_100 = "#EEF2FF"
    primary_200 = "#E0E7FF"
    primary_300 = "#C7D2FE"
    primary_400 = "#A5B4FC"
    primary_500 = "#818CF8"
    primary_600 = "#4F46E5"
    primary_700 = "#4338CA"
    primary_800 = "#3730A3"
    primary_900 = "#312E81"

    dark_50 = "#E6E6E6"
    dark_100 = "#A8A8A8"
    dark_200 = "#515151"
    dark_300 = "#334155"
    dark_400 = "#64748B"
    dark_500 = "#0F172A"
    dark_600 = "#000000"

    secondary_50 = "#F8FAFC"
    secondary_100 = "#F1F5F9"
    secondary_200 = "#E2E8F0"
    secondary_300 = "#CBD5E1"
    secondary_400 = "#A5B4FC"
    secondary_500 = "#818CF8"
    secondary_600 = "#4F46E5"
    secondary_700 = "#334155"
    secondary_800 = "#1E293B"
    secondary_900 = "#0F172A"


VRISTO_THEME = VristoPalette()
