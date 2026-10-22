Vristo vendor assets (licensed — not included in this repository)
=================================================================

SB Themes Vristo is a commercial ThemeForest template. There is NO official
PyPI, npm, or public GitHub package you can pip install.

Purchase (includes HTML + framework starters):
  https://themeforest.net/item/vristo-multipurpose-tailwind-css-admin-template/44221232

Documentation:
  https://vristo.sbthemes.com/documentation/installation

How to add files to Horilla
---------------------------
1. Download and unzip your licensed Vristo bundle.
2. Copy ONE of these into this folder (horilla_vristo/vendor/):

   Option A — HTML / Tailwind package (recommended for static assets):
     vendor/vristo/
       package.json
       index.html
       assets/
         css/
         js/
         images/

   Option B — Django starter (if your zip includes it):
     vendor/django/
       manage.py
       templates/
       static/   (or assets/)

3. Or set an absolute path (Docker-friendly):
     VRISTO_VENDOR_ROOT=/path/to/extracted/vristo

4. Restart Django and run:
     python manage.py vristo_status

5. Collect static in production:
     python manage.py collectstatic

Horilla will automatically:
  - Serve vendor assets under /static/vristo/ (HTML assets)
  - Load vendor Django templates if present (after DB template loader)

Horilla's own UI continues to use horilla_theme (vristo-theme.css, vristo-ui.css)
until you migrate templates to vendor partials.

Do not commit ThemeForest files to a public repository without a license.
