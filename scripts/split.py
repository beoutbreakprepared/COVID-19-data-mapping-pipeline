def normalize_date(date):
    date = date.replace("-", ".")
    if len(date) == len("D.MM.YYYY"):
        # Single day digit
        date = date.zfill(len("DD.MM.YYYY"))
    # Reverse DD.MM.YYYY into YYYY.MM.DD so that alphabetical order is the
    # same as chronological.
    date_parts = date.split(".")
    if len(date_parts[0]) != 4:
        date_parts.reverse()
    return ".".join(date_parts)
