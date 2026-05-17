def dated_subject(title, date_text):
    """Build report email subject with guaranteed space before 'за'."""
    title = " ".join(str(title or "").split())
    date_text = str(date_text or "").strip()
    return f"{title} за {date_text}"
