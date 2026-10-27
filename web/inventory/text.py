def repair_arabic_encoding(value):
    """Recover UTF-8 Arabic decoded as Windows-1252, leaving other text alone."""
    original = value
    for _ in range(3):
        if not any(c in value for c in ("\u00d8", "\u00d9")):
            break
        try:
            raw = b"".join(
                bytes([ord(c)]) if ord(c) < 256 else c.encode("cp1252")
                for c in value
            )
            repaired = raw.decode("utf-8")
        except (UnicodeError, ValueError):
            break
        if not any("\u0600" <= c <= "\u06ff" for c in repaired):
            break
        value = repaired
    return value or original
