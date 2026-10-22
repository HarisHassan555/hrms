TailAdmin free template (MIT) — optional vendor assets
======================================================

Official repository:
  git clone https://github.com/TailAdmin/tailadmin-free-tailwind-dashboard-template.git

Place the clone here, for example:
  horilla_tailadmin/vendor/tailadmin-free-tailwind-dashboard-template/

Or set:
  TAILADMIN_VENDOR_ROOT=/absolute/path/to/repo

Then rebuild theme static (required after vendor updates):
  python manage.py build_tailadmin

Check mount:
  python manage.py tailadmin_status

Production:
  python manage.py collectstatic

Horilla loads the compiled TailAdmin CSS from:
  horilla_theme/static/horilla_theme/assets/tailadmin/build/style.css
Shell behavior: horilla-tailadmin-shell.js + templates/horilla_theme/components/tailadmin/
