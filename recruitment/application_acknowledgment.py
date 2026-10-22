"""
Thank-you email sent when a candidate submits the public application form.
"""

import logging
import os

from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from base.backends import ConfiguredEmailBackend
from recruitment.models import Candidate, RecruitmentGeneralSetting

logger = logging.getLogger(__name__)


def application_acknowledgment_enabled_for(candidate: Candidate) -> bool:
    recruitment = candidate.recruitment_id
    company_id = recruitment.company_id_id if recruitment else None
    setting = RecruitmentGeneralSetting.objects.filter(
        company_id_id=company_id
    ).first()
    if setting is None:
        return True
    return setting.application_acknowledgment_email


def _job_position_label(candidate: Candidate) -> str:
    jp = candidate.job_position_id
    if jp:
        return str(getattr(jp, "job_position", jp) or jp)
    recruitment = candidate.recruitment_id
    if recruitment and recruitment.title:
        return recruitment.title
    return str(_("the position"))


def _company_name(candidate: Candidate) -> str:
    recruitment = candidate.recruitment_id
    company = getattr(recruitment, "company_id", None) if recruitment else None
    if company and getattr(company, "company", None):
        return company.company
    return str(_("our team"))


def send_application_acknowledgment_email(candidate: Candidate, request=None) -> bool:
    """
    Send a thank-you email after a public career-page application.

    Returns True if the message was handed off to the mail backend, False if
    there is no recipient email or sending failed.
    """
    to = (candidate.email or "").strip()
    if not to:
        return False
    if not application_acknowledgment_enabled_for(candidate):
        return False

    job_position = _job_position_label(candidate)
    recruitment = candidate.recruitment_id
    recruitment_title = (recruitment.title or "") if recruitment else ""
    company_name = _company_name(candidate)
    candidate_name = (candidate.name or "").strip() or to

    protocol = "https" if request and request.is_secure() else "http"
    host = request.get_host() if request else ""

    context = {
        "candidate": candidate,
        "candidate_name": candidate_name,
        "job_position": job_position,
        "recruitment_title": recruitment_title,
        "company_name": company_name,
        "protocol": protocol,
        "host": host,
    }

    html_message = render_to_string(
        "recruitment/mail_templates/application_acknowledgment.html",
        context,
        request=request,
    )

    subject = _("Thank you for applying – %(position)s") % {"position": job_position}

    recruitment_suffix = f" ({recruitment_title})" if recruitment_title else ""
    plain = _(
        "Hi %(name)s,\n\n"
        "Thank you for applying for the %(position)s role%(recruitment)s. "
        "We have received your application and will review it shortly. "
        "We will contact you about next steps.\n\n"
        "Regards,\n%(company)s"
    ) % {
        "name": candidate_name,
        "position": job_position,
        "recruitment": recruitment_suffix,
        "company": company_name,
    }

    email_backend = ConfiguredEmailBackend()
    from_email = email_backend.dynamic_from_email_with_display_name

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=from_email,
        to=[to],
        reply_to=[from_email] if from_email else None,
    )
    email.attach_alternative(html_message, "text/html")
    _attach_company_logo(email, candidate)

    try:
        email.send()
        return True
    except Exception:
        logger.exception(
            "Failed to send application acknowledgment (candidate pk=%s)",
            candidate.pk,
        )
        return False


def _attach_company_logo(email: EmailMultiAlternatives, candidate: Candidate) -> None:
    from email.mime.image import MIMEImage

    try:
        recruitment = candidate.recruitment_id
        company = recruitment.company_id if recruitment else None
        if company and company.icon and os.path.exists(company.icon.path):
            image_path = company.icon.path
        else:
            image_path = finders.find("images/ui/dsglogo.png")
        if not image_path:
            return
        with open(image_path, "rb") as image_file:
            logo = MIMEImage(image_file.read())
        logo.add_header("Content-ID", "<company_logo>")
        logo.add_header(
            "Content-Disposition",
            "inline",
            filename=os.path.basename(image_path),
        )
        email.attach(logo)
    except Exception:
        logger.exception("Company logo attach failed for application acknowledgment")
