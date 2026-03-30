import logging
import os
import smtplib
import time
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2


def _bool_env(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def _normalize_recipients(recipients):
    """Normalize recipients input into a list of non-empty email strings."""
    if recipients is None:
        return []
    if isinstance(recipients, str):
        return [addr.strip() for addr in recipients.split(",") if addr.strip()]
    if isinstance(recipients, (list, tuple, set)):
        result = []
        for x in recipients:
            if x is None:
                continue
            sx = str(x).strip()
            if sx:
                result.append(sx)
        return result
    # Fallback: treat unknown type as a string (e.g. single email)
    sx = str(recipients).strip()
    return [sx] if sx else []


def send_email(subject, body, recipients=None):
    """Send email notification. Returns True if delivered to at least one recipient."""
    if not _bool_env("EMAIL_ENABLED", False):
        return False

    smtp_host = (os.getenv("EMAIL_SMTP_HOST") or "").strip()
    smtp_port_raw = (os.getenv("EMAIL_SMTP_PORT") or "587").strip()
    smtp_user = (os.getenv("EMAIL_SMTP_USER") or "").strip()
    smtp_password = os.getenv("EMAIL_SMTP_PASSWORD") or ""
    use_tls = _bool_env("EMAIL_USE_TLS", True)
    email_from = (os.getenv("EMAIL_FROM") or "").strip()
    subject_prefix = (os.getenv("EMAIL_SUBJECT_PREFIX") or "").strip()

    if recipients is None:
        email_to_raw = os.getenv("EMAIL_TO") or ""
        recipients = _normalize_recipients(email_to_raw)
    else:
        recipients = _normalize_recipients(recipients)

    if not recipients:
        logger.warning("Email notifications enabled, but recipients list is empty")
        return False

    if not smtp_host or not email_from:
        logger.warning("Email notifications enabled, but SMTP settings are incomplete (EMAIL_SMTP_HOST/EMAIL_FROM)")
        return False

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        logger.error("Invalid EMAIL_SMTP_PORT value: %s", smtp_port_raw)
        return False

    email_subject = f"{subject_prefix} {subject}".strip() if subject_prefix else subject
    msg = EmailMessage()
    msg["Subject"] = email_subject
    msg["From"] = email_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(body or "")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=SMTP_TIMEOUT) as server:
                if use_tls:
                    server.starttls()
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            logger.info("Email sent to %s recipient(s)", len(recipients))
            return True
        except Exception as e:
            logger.error("Email send failed attempt=%s/%s: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    logger.error("Email message was not delivered after all retries")
    return False
