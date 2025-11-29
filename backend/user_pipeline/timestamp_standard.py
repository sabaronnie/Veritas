from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LEBANON = ZoneInfo("Asia/Beirut")

def parse_timestamp(raw, source):
    raw = raw.strip()

    # ====================
    # LBC (no timezone)
    # ====================
    if source == "LBC":
        # Example: "17-01-2023 | 10:06"
        dt = datetime.strptime(raw, "%d-%m-%Y | %H:%M")
        dt = dt.replace(tzinfo=LEBANON)             # assign Lebanon timezone
        dt_utc = dt.astimezone(timezone.utc)        # convert to UTC
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # ====================
    # MTV (no timezone)
    # ====================
    if source == "MTV":
        # Example: "2025-01-17T13:44:00"
        dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=LEBANON)     
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # ====================
    # 961 (has timezone offset)
    # ====================
    if source == "961": 
        # Example: "2025-07-26T14:25:53+03:00"
        dt = datetime.fromisoformat(raw)       # parses +03:00 automatically
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # fallback
    return None