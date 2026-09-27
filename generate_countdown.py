import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


CONFIG_FILE = Path("countdown.json")
OUTPUT_FILE = Path("site/countdown.svg")

ALLOWED_UNITS = ("months", "days", "hours", "minutes", "seconds")

LABELS = {
    "months": ("MONTH", "MONTHS"),
    "days": ("DAY", "DAYS"),
    "hours": ("HOUR", "HOURS"),
    "minutes": ("MINUTE", "MINUTES"),
    "seconds": ("SECOND", "SECONDS"),
}


def parse_date(value: str) -> datetime:
    """Parse an ISO-8601 date and ensure it has a timezone."""
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


def add_months_clamped(date: datetime, months: int) -> datetime:
    """Add calendar months without overflowing short target months."""
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1

    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=date.tzinfo)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=date.tzinfo)

    last_day = (next_month - timedelta(days=1)).day

    return date.replace(
        year=year,
        month=month,
        day=min(date.day, last_day),
    )


def get_countdown(now: datetime, target: datetime) -> dict:
    """Return calendar-aware months plus remaining days/time."""
    if target <= now:
        return {
            "months": 0,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
            "expired": True,
        }

    months = (
        (target.year - now.year) * 12
        + (target.month - now.month)
    )

    cursor = add_months_clamped(now, months)

    if cursor > target:
        months -= 1
        cursor = add_months_clamped(now, months)

    remaining = target - cursor
    total_seconds = int(remaining.total_seconds())

    days, total_seconds = divmod(total_seconds, 86_400)
    hours, total_seconds = divmod(total_seconds, 3_600)
    minutes, seconds = divmod(total_seconds, 60)

    return {
        "months": months,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "expired": False,
    }


def escape_xml(value) -> str:
    return html.escape(str(value), quote=True)


def label_for(unit: str, value: int) -> str:
    return LABELS[unit][0] if value == 1 else LABELS[unit][1]


def validate_hex(value: str, fallback: str) -> str:
    value = str(value)
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass
    return fallback


def target_display(target: datetime) -> str:
    # GitHub-hosted runners use Linux, so this is safe there.
    return target.strftime("%B %-d, %Y • %H:%M %Z")


def generate_svg(config: dict, values: dict) -> str:
    width = 1000
    height = 300
    padding = 38
    gap = 14
    box_y = 125
    box_height = 105

    title = config.get("title", "Countdown")
    description = config.get("description", "Time remaining")
    units = config.get(
        "units",
        ["months", "days", "hours", "minutes"],
    )

    units = [unit for unit in units if unit in ALLOWED_UNITS]
    if not units:
        units = ["months", "days", "hours", "minutes"]

    background = validate_hex(config.get("background", "#050816"), "#050816")
    card = validate_hex(config.get("card", "#0c1430"), "#0c1430")
    text = validate_hex(config.get("text", "#ffffff"), "#ffffff")
    muted = validate_hex(config.get("muted", "#9ca9c7"), "#9ca9c7")
    accent = validate_hex(config.get("accent", "#d94cff"), "#d94cff")
    border = validate_hex(config.get("border", "#26396d"), "#26396d")

    if values["expired"]:
        description = config.get(
            "expired_description",
            "The countdown has reached its target! 🎉",
        )

    usable_width = width - padding * 2
    box_width = (
        usable_width - gap * (len(units) - 1)
    ) / len(units)

    parts = [
        f"""<rect width="{width}" height="{height}" rx="28" fill="{escape_xml(background)}"/>""",
        f"""
        <defs>
          <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="{escape_xml(background)}"/>
            <stop offset="100%" stop-color="{escape_xml(card)}"/>
          </linearGradient>
          <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="{escape_xml(accent)}"/>
            <stop offset="100%" stop-color="{escape_xml(accent)}" stop-opacity="0.25"/>
          </linearGradient>
        </defs>
        <rect width="{width}" height="{height}" rx="28" fill="url(#bg)"/>
        """,
        f"""<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="27"
                    fill="none" stroke="{escape_xml(border)}" stroke-width="2"/>""",
        f"""<rect x="{padding}" y="27" width="90" height="5" rx="2.5" fill="url(#accent)"/>""",
        f"""<text x="{padding}" y="70" fill="{escape_xml(text)}"
                    font-family="Arial, Helvetica, sans-serif" font-size="30"
                    font-weight="700">{escape_xml(title)}</text>""",
        f"""<text x="{padding}" y="99" fill="{escape_xml(muted)}"
                    font-family="Arial, Helvetica, sans-serif" font-size="15">{escape_xml(description)}</text>""",
    ]

    for index, unit in enumerate(units):
        value = values[unit]
        x = padding + index * (box_width + gap)

        parts.append(
            f"""
            <rect x="{x:.1f}" y="{box_y}" width="{box_width:.1f}" height="{box_height}"
                  rx="20" fill="{escape_xml(card)}"
                  stroke="{escape_xml(border)}" stroke-width="1"/>

            <text x="{x + box_width / 2:.1f}" y="{box_y + 57}"
                  text-anchor="middle" fill="{escape_xml(text)}"
                  font-family="Arial, Helvetica, sans-serif" font-size="38"
                  font-weight="700">{value}</text>

            <text x="{x + box_width / 2:.1f}" y="{box_y + 83}"
                  text-anchor="middle" fill="{escape_xml(muted)}"
                  font-family="Arial, Helvetica, sans-serif" font-size="11"
                  font-weight="700" letter-spacing="1.8">{label_for(unit, value)}</text>
            """
        )

    target = parse_date(config["target"])
    parts.append(
        f"""
        <text x="{width - padding}" y="{height - 20}" text-anchor="end"
              fill="{escape_xml(muted)}"
              font-family="Arial, Helvetica, sans-serif" font-size="11">
          TARGET • {escape_xml(target_display(target))}
        </text>
        """
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     role="img" aria-label="{escape_xml(title)} countdown">
  {''.join(parts)}
</svg>
"""


def main() -> None:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    if "target" not in config:
        raise ValueError("countdown.json must contain a 'target' field.")

    target = parse_date(config["target"])
    now = datetime.now(target.tzinfo)

    values = get_countdown(now, target)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        generate_svg(config, values),
        encoding="utf-8",
    )

    print(f"Generated {OUTPUT_FILE}")
    print(
        f"Target: {target.isoformat()} | "
        f"Remaining: {values['months']} months, "
        f"{values['days']} days, "
        f"{values['hours']} hours, "
        f"{values['minutes']} minutes, "
        f"{values['seconds']} seconds"
    )


if __name__ == "__main__":
    main()
