def dated_subject(title, date_text):
    """Build report email subject with guaranteed ASCII space before 'за'."""
    title = " ".join(str(title or "").split())
    date_text = str(date_text or "").strip()
    return f"{title} за {date_text}"


def stock_monitor_subject(report_date):
    """Full Stock Monitor subject passed to send_email (without EMAIL_SUBJECT_PREFIX)."""
    return dated_subject("Проверка остатков", report_date)


def compose_email_subject(subject_prefix, subject):
    """Join EMAIL_SUBJECT_PREFIX and subject with exactly one space (never glue 'остатков'+'за')."""
    parts = []
    for part in (subject_prefix, subject):
        text = str(part or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)
