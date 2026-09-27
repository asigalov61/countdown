import html
import json
import math
import random
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


# ------------------------------------------------------------
# DATE / COUNTDOWN
# ------------------------------------------------------------

def parse_date(value: str) -> datetime:
    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


def add_months_clamped(date: datetime, months: int) -> datetime:
    month_index = date.month - 1 + months

    year = date.year + month_index // 12
    month = month_index % 12 + 1

    if month == 12:
        next_month = datetime(
            year + 1,
            1,
            1,
            tzinfo=date.tzinfo,
        )
    else:
        next_month = datetime(
            year,
            month + 1,
            1,
            tzinfo=date.tzinfo,
        )

    last_day = (next_month - timedelta(days=1)).day

    return date.replace(
        year=year,
        month=month,
        day=min(date.day, last_day),
    )


def get_countdown(now: datetime, target: datetime) -> dict:
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

    days, total_seconds = divmod(total_seconds, 86400)
    hours, total_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(total_seconds, 60)

    return {
        "months": months,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "expired": False,
    }


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def escape_xml(value) -> str:
    return html.escape(str(value), quote=True)


def validate_hex(value: str, fallback: str) -> str:
    value = str(value)

    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass

    return fallback


def label_for(unit: str, value: int) -> str:
    return LABELS[unit][0] if value == 1 else LABELS[unit][1]


def target_display(target: datetime) -> str:
    return target.strftime("%B %-d, %Y • %H:%M %Z")


# ------------------------------------------------------------
# SVG DECORATIONS
# ------------------------------------------------------------

def generate_stars(count=130, seed=61):
    """
    Deterministic star field.
    The same stars are generated on every GitHub Actions run.
    """

    rng = random.Random(seed)

    stars = []

    for _ in range(count):
        x = rng.uniform(0, 1000)
        y = rng.uniform(0, 330)

        radius = rng.choice([
            0.35,
            0.45,
            0.55,
            0.7,
            0.9,
            1.1,
        ])

        opacity = rng.uniform(0.25, 0.9)

        stars.append(
            f"""
            <circle
                cx="{x:.1f}"
                cy="{y:.1f}"
                r="{radius:.2f}"
                fill="#ffffff"
                opacity="{opacity:.2f}"
            />
            """
        )

    return "".join(stars)


def generate_music_wave(x_start, y_center, width):
    """
    Decorative MIDI/audio waveform.
    """

    bars = 31
    spacing = width / bars

    parts = []

    for i in range(bars):
        distance = abs(i - bars / 2)

        height = (
            8
            + 34 * math.exp(-(distance ** 2) / 75)
        )

        # Smooth deterministic variation
        height *= (
            0.82
            + 0.18 * math.sin(i * 1.7)
        )

        x = x_start + i * spacing

        parts.append(
            f"""
            <rect
                x="{x:.1f}"
                y="{y_center - height / 2:.1f}"
                width="2.4"
                height="{height:.1f}"
                rx="1.2"
                fill="url(#waveGradient)"
                opacity="0.9"
            />
            """
        )

    return "".join(parts)


def generate_music_notes():
    """
    Floating musical notes on the left side.
    """

    notes = [
        (65, 125, "#b84cff", 1.0),
        (105, 148, "#27a9ff", 0.9),
        (145, 112, "#5d8cff", 0.8),
        (185, 137, "#d84cff", 0.85),
        (225, 102, "#32b9ff", 0.75),
    ]

    parts = []

    for x, y, color, opacity in notes:

        parts.append(
            f"""
            <g
                transform="translate({x} {y})"
                fill="{color}"
                opacity="{opacity}"
            >
                <ellipse
                    cx="0"
                    cy="8"
                    rx="6"
                    ry="4"
                    transform="rotate(-20)"
                />

                <rect
                    x="5"
                    y="-27"
                    width="3"
                    height="35"
                    rx="1.5"
                />

                <path
                    d="M8 -27
                       C20 -32 26 -25 27 -20
                       C20 -23 14 -23 8 -21 Z"
                />
            </g>
            """
        )

    return "".join(parts)


def generate_planet():
    """
    Small stylized planet in the upper-left corner.
    """

    return """
    <g opacity="0.75">

        <defs>
            <radialGradient id="planetGradient"
                            cx="35%" cy="30%" r="70%">
                <stop offset="0%" stop-color="#78d9ff"/>
                <stop offset="45%" stop-color="#2457d6"/>
                <stop offset="100%" stop-color="#090d38"/>
            </radialGradient>
        </defs>

        <circle
            cx="34"
            cy="42"
            r="37"
            fill="url(#planetGradient)"
        />

        <ellipse
            cx="34"
            cy="42"
            rx="54"
            ry="12"
            fill="none"
            stroke="#4b8cff"
            stroke-width="3"
            opacity="0.65"
            transform="rotate(-15 34 42)"
        />

        <ellipse
            cx="34"
            cy="42"
            rx="54"
            ry="12"
            fill="none"
            stroke="#c34cff"
            stroke-width="1"
            opacity="0.4"
            transform="rotate(-15 34 42)"
        />

    </g>
    """


def generate_nebula():
    """
    Soft abstract galactic glow using SVG radial gradients.
    """

    return """
    <circle
        cx="870"
        cy="75"
        r="135"
        fill="url(#nebulaPurple)"
        opacity="0.35"
    />

    <circle
        cx="760"
        cy="50"
        r="115"
        fill="url(#nebulaBlue)"
        opacity="0.25"
    />

    <circle
        cx="520"
        cy="320"
        r="150"
        fill="url(#nebulaPink)"
        opacity="0.12"
    />
    """


# ------------------------------------------------------------
# COUNTDOWN CARDS
# ------------------------------------------------------------

def generate_card(
    x,
    y,
    width,
    height,
    value,
    unit,
    index,
):
    gradients = [
        "cardPurple",
        "cardBlue",
        "cardPurple",
        "cardBlue",
        "cardPink",
    ]

    gradient = gradients[index % len(gradients)]

    label = label_for(unit, value)

    return f"""
    <g>

        <!-- Card glow -->
        <rect
            x="{x:.1f}"
            y="{y:.1f}"
            width="{width:.1f}"
            height="{height:.1f}"
            rx="19"
            fill="none"
            stroke="url(#{gradient})"
            stroke-width="5"
            opacity="0.12"
            filter="url(#glow)"
        />

        <!-- Card -->
        <rect
            x="{x:.1f}"
            y="{y:.1f}"
            width="{width:.1f}"
            height="{height:.1f}"
            rx="19"
            fill="url(#{gradient})"
            stroke="url(#{gradient})"
            stroke-width="1.5"
        />

        <!-- Inner glass -->
        <rect
            x="{x + 2:.1f}"
            y="{y + 2:.1f}"
            width="{width - 4:.1f}"
            height="{height - 4:.1f}"
            rx="17"
            fill="#05091f"
            fill-opacity="0.72"
        />

        <!-- Small top glow -->
        <rect
            x="{x + 22:.1f}"
            y="{y + 14:.1f}"
            width="{width - 44:.1f}"
            height="2"
            rx="1"
            fill="url(#{gradient})"
            opacity="0.75"
        />

        <!-- Number -->
        <text
            x="{x + width / 2:.1f}"
            y="{y + 75:.1f}"
            text-anchor="middle"
            fill="#ffffff"
            font-family="Arial, Helvetica, sans-serif"
            font-size="42"
            font-weight="700"
            letter-spacing="-1"
        >{value}</text>

        <!-- Label -->
        <text
            x="{x + width / 2:.1f}"
            y="{y + 101:.1f}"
            text-anchor="middle"
            fill="#aebfff"
            font-family="Arial, Helvetica, sans-serif"
            font-size="10"
            font-weight="700"
            letter-spacing="2.2"
        >{label}</text>

    </g>
    """


# ------------------------------------------------------------
# MAIN SVG
# ------------------------------------------------------------

def generate_svg(config: dict, values: dict) -> str:

    width = 1200
    height = 390

    padding = 34
    card_y = 205
    card_height = 130

    gap = 14

    # Five cards look much more like the professional reference design.
    units = config.get(
        "units",
        [
            "months",
            "days",
            "hours",
            "minutes",
            "seconds",
        ],
    )

    units = [
        unit
        for unit in units
        if unit in ALLOWED_UNITS
    ]

    if not units:
        units = [
            "months",
            "days",
            "hours",
            "minutes",
        ]

    # Configuration
    title = config.get(
        "title",
        "Galaxy MIDI Dataset",
    )

    subtitle = config.get(
        "subtitle",
        "THE UNIVERSE OF MUSIC",
    )

    description = config.get(
        "description",
        "Coming January 1, 2027",
    )

    background = validate_hex(
        config.get("background", "#03061a"),
        "#03061a",
    )

    card = validate_hex(
        config.get("card", "#070d2b"),
        "#070d2b",
    )

    text = validate_hex(
        config.get("text", "#ffffff"),
        "#ffffff",
    )

    muted = validate_hex(
        config.get("muted", "#aebfff"),
        "#aebfff",
    )

    accent = validate_hex(
        config.get("accent", "#a94cff"),
        "#a94cff",
    )

    border = validate_hex(
        config.get("border", "#3157a5"),
        "#3157a5",
    )

    # --------------------------------------------------------
    # CARD GEOMETRY
    # --------------------------------------------------------

    usable_width = width - padding * 2

    card_width = (
        usable_width
        - gap * (len(units) - 1)
    ) / len(units)

    # --------------------------------------------------------
    # SVG
    # --------------------------------------------------------

    parts = []

    parts.append(
        f"""
        <defs>

            <!-- Background -->
            <linearGradient
                id="backgroundGradient"
                x1="0"
                y1="0"
                x2="1"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="{background}"
                />

                <stop
                    offset="45%"
                    stop-color="#060b29"
                />

                <stop
                    offset="100%"
                    stop-color="#10051e"
                />
            </linearGradient>

            <!-- Purple nebula -->
            <radialGradient
                id="nebulaPurple"
                cx="50%"
                cy="50%"
                r="50%"
            >
                <stop
                    offset="0%"
                    stop-color="#b92cff"
                    stop-opacity="0.9"
                />

                <stop
                    offset="100%"
                    stop-color="#7b2cff"
                    stop-opacity="0"
                />
            </radialGradient>

            <!-- Blue nebula -->
            <radialGradient
                id="nebulaBlue"
                cx="50%"
                cy="50%"
                r="50%"
            >
                <stop
                    offset="0%"
                    stop-color="#258cff"
                    stop-opacity="0.8"
                />

                <stop
                    offset="100%"
                    stop-color="#258cff"
                    stop-opacity="0"
                />
            </radialGradient>

            <!-- Pink nebula -->
            <radialGradient
                id="nebulaPink"
                cx="50%"
                cy="50%"
                r="50%"
            >
                <stop
                    offset="0%"
                    stop-color="#ff3bbf"
                    stop-opacity="0.7"
                />

                <stop
                    offset="100%"
                    stop-color="#ff3bbf"
                    stop-opacity="0"
                />
            </radialGradient>

            <!-- Cards -->
            <linearGradient
                id="cardPurple"
                x1="0"
                y1="0"
                x2="1"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="#b735ff"
                />

                <stop
                    offset="100%"
                    stop-color="#533cff"
                />
            </linearGradient>

            <linearGradient
                id="cardBlue"
                x1="0"
                y1="0"
                x2="1"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="#20b8ff"
                />

                <stop
                    offset="100%"
                    stop-color="#2860ff"
                />
            </linearGradient>

            <linearGradient
                id="cardPink"
                x1="0"
                y1="0"
                x2="1"
                y2="1"
            >
                <stop
                    offset="0%"
                    stop-color="#ff49dc"
                />

                <stop
                    offset="100%"
                    stop-color="#9a39ff"
                />
            </linearGradient>

            <!-- Accent -->
            <linearGradient
                id="accentGradient"
                x1="0"
                y1="0"
                x2="1"
                y2="0"
            >
                <stop
                    offset="0%"
                    stop-color="#27aaff"
                />

                <stop
                    offset="50%"
                    stop-color="#b83cff"
                />

                <stop
                    offset="100%"
                    stop-color="#ff42cf"
                />
            </linearGradient>

            <linearGradient
                id="waveGradient"
                x1="0"
                y1="0"
                x2="1"
                y2="0"
            >
                <stop
                    offset="0%"
                    stop-color="#22b8ff"
                />

                <stop
                    offset="50%"
                    stop-color="#a63cff"
                />

                <stop
                    offset="100%"
                    stop-color="#ff42d1"
                />
            </linearGradient>

            <!-- Soft glow -->
            <filter
                id="glow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
            >
                <feGaussianBlur
                    stdDeviation="7"
                    result="blur"
                />

                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>

            <!-- Strong glow -->
            <filter
                id="strongGlow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
            >
                <feGaussianBlur
                    stdDeviation="12"
                    result="blur"
                />

                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>

        </defs>
        """
    )

    # Background
    parts.append(
        f"""
        <rect
            width="{width}"
            height="{height}"
            rx="28"
            fill="url(#backgroundGradient)"
        />
        """
    )

    # Nebula
    parts.append(generate_nebula())

    # Stars
    parts.append(generate_stars())

    # Planet
    parts.append(generate_planet())

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    parts.append(
        f"""
        <!-- Header accent line -->
        <rect
            x="65"
            y="30"
            width="82"
            height="4"
            rx="2"
            fill="url(#accentGradient)"
        />

        <rect
            x="{width - 147}"
            y="30"
            width="82"
            height="4"
            rx="2"
            fill="url(#accentGradient)"
        />

        <!-- Subtitle -->
        <text
            x="{width / 2}"
            y="40"
            text-anchor="middle"
            fill="#a9c8ff"
            font-family="Arial, Helvetica, sans-serif"
            font-size="13"
            font-weight="600"
            letter-spacing="5"
        >
            {escape_xml(subtitle)}
        </text>

        <!-- Main title -->
        <text
            x="{width / 2}"
            y="92"
            text-anchor="middle"
            fill="{escape_xml(text)}"
            font-family="Arial, Helvetica, sans-serif"
            font-size="46"
            font-weight="700"
            letter-spacing="-1"
        >
            {escape_xml(title)}
        </text>

        <!-- Title glow -->
        <text
            x="{width / 2}"
            y="92"
            text-anchor="middle"
            fill="none"
            stroke="#9c4cff"
            stroke-width="1"
            opacity="0.22"
            font-family="Arial, Helvetica, sans-serif"
            font-size="46"
            font-weight="700"
        >
            {escape_xml(title)}
        </text>

        <!-- Release date -->
        <text
            x="{width / 2}"
            y="123"
            text-anchor="middle"
            fill="{escape_xml(muted)}"
            font-family="Arial, Helvetica, sans-serif"
            font-size="16"
            font-weight="600"
            letter-spacing="3"
        >
            {escape_xml(description).upper()}
        </text>
        """
    )

    # Music notes
    parts.append(generate_music_notes())

    # --------------------------------------------------------
    # COUNTDOWN CARDS
    # --------------------------------------------------------

    for index, unit in enumerate(units):

        value = values[unit]

        x = (
            padding
            + index * (card_width + gap)
        )

        parts.append(
            generate_card(
                x=x,
                y=card_y,
                width=card_width,
                height=card_height,
                value=value,
                unit=unit,
                index=index,
            )
        )

    # --------------------------------------------------------
    # BOTTOM AUDIO WAVE
    # --------------------------------------------------------

    wave_width = 230
    wave_x = (
        width / 2
        - wave_width / 2
    )

    parts.append(
        f"""
        <line
            x1="{wave_x - 95}"
            y1="365"
            x2="{wave_x - 15}"
            y2="365"
            stroke="url(#accentGradient)"
            stroke-width="2"
        />

        <line
            x1="{wave_x + wave_width + 15}"
            y1="365"
            x2="{wave_x + wave_width + 95}"
            y2="365"
            stroke="url(#accentGradient)"
            stroke-width="2"
        />

        {generate_music_wave(
            wave_x,
            365,
            wave_width
        )}
        """
    )

    # Target
    target = parse_date(config["target"])

    parts.append(
        f"""
        <text
            x="{width - padding}"
            y="372"
            text-anchor="end"
            fill="{escape_xml(muted)}"
            font-family="Arial, Helvetica, sans-serif"
            font-size="10"
            letter-spacing="1.2"
        >
            TARGET • {escape_xml(target_display(target))}
        </text>
        """
    )

    # Border
    parts.append(
        f"""
        <rect
            x="1"
            y="1"
            width="{width - 2}"
            height="{height - 2}"
            rx="27"
            fill="none"
            stroke="{escape_xml(border)}"
            stroke-width="2"
        />
        """
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>

<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
    role="img"
    aria-label="{escape_xml(title)} countdown"
>

{''.join(parts)}

</svg>
"""


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main() -> None:

    config = json.loads(
        CONFIG_FILE.read_text(
            encoding="utf-8"
        )
    )

    if "target" not in config:
        raise ValueError(
            "countdown.json must contain a 'target' field."
        )

    target = parse_date(config["target"])

    now = datetime.now(
        target.tzinfo
    )

    values = get_countdown(
        now,
        target,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        generate_svg(
            config,
            values,
        ),
        encoding="utf-8",
    )

    print(
        f"Generated {OUTPUT_FILE}"
    )

    print(
        f"Target: {target.isoformat()} | "
        f"Remaining: "
        f"{values['months']} months, "
        f"{values['days']} days, "
        f"{values['hours']} hours, "
        f"{values['minutes']} minutes, "
        f"{values['seconds']} seconds"
    )


if __name__ == "__main__":
    main()
