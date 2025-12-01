from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LEBANON = ZoneInfo("Asia/Beirut")

def fix_fraction(ts: str) -> str:
    """
    Ensure fractional seconds are always valid (6 digits).
    Accepts:
        2025-12-01T16:57:17
        2025-12-01T16:57:17.2
        2025-12-01T16:57:17.28
        2025-12-01T16:57:17.2839
        2025-12-01T16:57:17.283945
    """
    ts = ts.replace("Z", "")  # remove Z for parsing

    if "." in ts:
        main, frac = ts.split(".")
        # pad OR truncate to 6 digits
        frac = (frac + "000000")[:6]
        return f"{main}.{frac}"

    return ts  # no fractional seconds → fine


def parse_timestamp(raw, source):
    raw = raw.strip()

    # ====================
    # LBC (no timezone)
    # ====================
    if source == "LBC":
        # Example: "17-01-2023 | 10:06"
        dt = datetime.strptime(raw, "%d-%m-%Y | %H:%M")
        dt = dt.replace(tzinfo=LEBANON)             # assign Lebanon timezone
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # ====================
    # MTV (no timezone, sometimes fractional seconds)
    # ====================
    if source == "MTV":
        # Example: "2025-01-17T13:44:00" OR "2025-12-01T16:57:17.52"
        ts = fix_fraction(raw)
        dt = datetime.fromisoformat(ts).replace(tzinfo=LEBANON)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # ====================
    # 961 (has timezone offset, sometimes fractional seconds)
    # ====================
    if source == "961": 
        # Example: "2025-07-26T14:25:53+03:00" OR "2025-12-01T16:57:17.52+03:00"
        ts = fix_fraction(raw)
        dt = datetime.fromisoformat(ts)  # correctly parses +03:00
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # ====================
    # fallback
    # ====================
    return None
