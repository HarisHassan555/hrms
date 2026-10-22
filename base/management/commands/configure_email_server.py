"""
Upsert primary application SMTP settings (DynamicEmailConfiguration).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from base.models import DynamicEmailConfiguration, Company


class Command(BaseCommand):
    help = (
        "Create or update the primary mail server in Settings → Email Configuration. "
        "Pass secrets via flags or environment variables "
        "(EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, "
        "DEFAULT_FROM_EMAIL, EMAIL_DISPLAY_NAME)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--host", default=None)
        parser.add_argument("--port", type=int, default=None)
        parser.add_argument("--username", default=None)
        parser.add_argument("--password", default=None)
        parser.add_argument("--from-email", dest="from_email", default=None)
        parser.add_argument("--display-name", dest="display_name", default=None)
        parser.add_argument(
            "--company-id",
            type=int,
            default=None,
            help="Optional company id for per-company SMTP (otherwise primary/global).",
        )
        parser.add_argument(
            "--primary",
            action="store_true",
            default=True,
            help="Mark as primary mail server (default: true).",
        )
        parser.add_argument(
            "--no-primary",
            action="store_false",
            dest="primary",
            help="Do not set as primary.",
        )
        parser.add_argument(
            "--use-tls",
            action="store_true",
            default=True,
            help="Use STARTTLS (default for port 587).",
        )
        parser.add_argument(
            "--no-tls",
            action="store_false",
            dest="use_tls",
        )
        parser.add_argument(
            "--use-ssl",
            action="store_true",
            default=False,
        )

    @transaction.atomic
    def handle(self, *args, **options):
        import os

        host = options["host"] or os.environ.get("EMAIL_HOST")
        port = options["port"]
        if port is None:
            port = int(os.environ.get("EMAIL_PORT", "587") or "587")
        username = options["username"] or os.environ.get("EMAIL_HOST_USER")
        password = options["password"] or os.environ.get("EMAIL_HOST_PASSWORD")
        from_email = (
            options["from_email"]
            or os.environ.get("DEFAULT_FROM_EMAIL")
            or username
        )
        display_name = (
            options["display_name"]
            or os.environ.get("EMAIL_DISPLAY_NAME")
            or "HRMS"
        )

        missing = [
            name
            for name, val in [
                ("host", host),
                ("username", username),
                ("password", password),
                ("from_email", from_email),
            ]
            if not val
        ]
        if missing:
            raise CommandError(
                "Missing required mail settings: "
                + ", ".join(missing)
                + ". Use flags or EMAIL_* environment variables."
            )

        company = None
        if options["company_id"]:
            company = Company.objects.filter(pk=options["company_id"]).first()
            if not company:
                raise CommandError(f"Company id {options['company_id']} not found.")

        is_primary = options["primary"] and company is None
        use_tls = options["use_tls"]
        use_ssl = options["use_ssl"]
        if use_tls and use_ssl:
            raise CommandError("use_tls and use_ssl cannot both be enabled.")

        if company:
            config, created = DynamicEmailConfiguration.objects.get_or_create(
                company_id=company,
                defaults={
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,
                    "from_email": from_email,
                    "display_name": display_name,
                    "use_tls": use_tls,
                    "use_ssl": use_ssl,
                    "is_primary": False,
                    "fail_silently": False,
                },
            )
        else:
            config = DynamicEmailConfiguration.objects.filter(is_primary=True).first()
            created = config is None
            if created:
                config = DynamicEmailConfiguration(is_primary=is_primary)

        config.host = host
        config.port = port
        config.username = username
        config.password = password
        config.from_email = from_email
        config.display_name = display_name
        config.use_tls = use_tls
        config.use_ssl = use_ssl
        config.fail_silently = False
        if is_primary:
            config.is_primary = True
        config.save()

        action = "Created" if created else "Updated"
        scope = f"company {company}" if company else "primary"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} DynamicEmailConfiguration ({scope}): "
                f"{username} @ {host}:{port} TLS={use_tls}"
            )
        )
