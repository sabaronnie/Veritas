from datetime import datetime

# 2025-01-17T13:44:00Z
def parse_timestamp(raw, source):
    raw = raw.strip()

    if source == "LBC":
        # Example: "17-01-2023 | 10:06"
        return datetime.strptime(raw, "%d-%m-%Y | %H:%M").isoformat() + "Z"

    if source == "MTV":
        # MTV is already ISO format
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S").isoformat() + "Z"

    if source == "NNA":
        # Example: "Fri, 17 Jan 2025 13:44:00 GMT"
        return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S GMT").isoformat() + "Z"

    if source == "ANNAHAR":
        # Example: "January 17, 2023 10:06 AM"
        return datetime.strptime(raw, "%B %d, %Y %I:%M %p").isoformat() + "Z"

    # fallback
    return None