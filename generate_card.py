from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
import requests
import json
import re
from pathlib import Path

# -----------------------------
# FILES AND FOLDERS
# -----------------------------
ROOT = Path(__file__).parent
TEMPLATE = ROOT / "template_blank.png"
OUTPUT = ROOT / "output" / "card_output.png"
OVERRIDES_FILE = ROOT / "overrides.json"
FONT_FILE = ROOT / "Inter Extra Bold 800.otf"
RECENT_GAMES_FOLDER = ROOT / "recent_games"

# -----------------------------
# CARD SIZE
# -----------------------------
CARD_WIDTH = 486
CARD_HEIGHT = 150

# -----------------------------
# TEXT POSITIONS
# First number = left/right.
# Second number = up/down.
# Nudge these if needed.
# -----------------------------
POSITIONS = {
    # Left/top
    "hours": (107, 34),
    "subtitle": (189, 45),

    # Platform row
    "psn": (123, 73),
    "steam": (162, 73),
    "retro": (203, 73),
    "android": (244, 73),
    "nintendo": (285, 73),

    # Right stat panel
    "progress": (367, 16),
    "world_rank": (444, 16),
    "games_played": (367, 41),
    "games_beaten": (443, 41),
    "achievements": (367, 66),
    "exophase_exp": (446, 66),
}

# -----------------------------
# GAME IMAGE SLOTS
# Each game image is 73 x 40
# -----------------------------
GAME_SLOTS = [
    (17, 104, 90, 144),
    (93, 104, 166, 144),
    (169, 104, 242, 144),
    (245, 104, 318, 144),
    (321, 104, 393, 144),
    (396, 104, 469, 144),
]

# -----------------------------
# FONT SIZES
# -----------------------------
FONT_HOURS = 8
FONT_SUBTITLE = 8
FONT_PLATFORM_NUMBERS = 9
FONT_RIGHT_NUMBERS = 10

# -----------------------------
# COLORS
# -----------------------------
WHITE = (255, 255, 255)
CYAN = (0, 200, 255)

# -----------------------------
# YOUR EXOPHASE PROFILE
# -----------------------------
PROFILE_URL = "https://www.exophase.com/user/AceAttorneyEric/"


def load_overrides():
    with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_font(size):
    return ImageFont.truetype(str(FONT_FILE), size=size)


def fetch_page_text():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(PROFILE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    return text


def find_number(text, label):
    """
    Tries both:
    8,089 PSN
    PSN 8,089
    """
    patterns = [
        rf"([\d,]+)\s+{re.escape(label)}",
        rf"{re.escape(label)}\s+([\d,]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def find_overall_stats(text):
    """
    Exophase's overall top profile stats usually appear like this:

    AceAttorneyEric
    98.26%
    11,171
    7,172 hours
    11,339
    286
    266
    1,216,143

    This pulls:
    - progress
    - world rank
    - hours
    - achievements
    - games played
    - games beaten/completed
    - Exophase EXP
    """
    pattern = (
        r"AceAttorneyEric\s+"
        r"(?P<progress>\d+\.\d+)%\s+"
        r"(?P<world_rank>[\d,]+)\s+"
        r"(?P<hours>[\d,]+)\s+hours\s+"
        r"(?P<achievements>[\d,]+)\s+"
        r"(?P<games_played>[\d,]+)\s+"
        r"(?P<games_beaten>[\d,]+)\s+"
        r"(?P<exophase_exp>[\d,]+)"
    )

    match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        return {}

    stats = match.groupdict()
    stats["hours"] = stats["hours"] + " hours"

    # Keep the percent sign removed.
    stats["progress"] = stats["progress"]

    return stats


def get_data():
    overrides = load_overrides()

    data = {
        "hours": overrides.get("hours", "") or "",
        "subtitle": overrides.get("subtitle", "") or "",
        "psn": overrides.get("psn", "") or "",
        "steam": overrides.get("steam", "") or "",
        "retro": overrides.get("retro", "") or "",
        "android": overrides.get("android", "") or "",
        "nintendo": overrides.get("nintendo", "") or "",
        "progress": overrides.get("progress", "") or "",
        "world_rank": overrides.get("world_rank", "") or "",
        "games_played": overrides.get("games_played", "") or "",
        "games_beaten": overrides.get("games_beaten", "") or "",
        "achievements": overrides.get("achievements", "") or "",
        "exophase_exp": overrides.get("exophase_exp", "") or "",
    }

    sources = {
        key: "override" if overrides.get(key) else "blank"
        for key in data.keys()
    }

    try:
        text = fetch_page_text()

        overall_stats = find_overall_stats(text)

        for key in [
            "hours",
            "progress",
            "world_rank",
            "games_played",
            "games_beaten",
            "achievements",
            "exophase_exp",
        ]:
            if overall_stats.get(key) and not overrides.get(key):
                data[key] = overall_stats[key]
                sources[key] = "Exophase"

        scraped_psn = find_number(text, "PSN")
        if scraped_psn and not overrides.get("psn"):
            data["psn"] = scraped_psn
            sources["psn"] = "Exophase"

        scraped_steam = find_number(text, "Steam")
        if scraped_steam and not overrides.get("steam"):
            data["steam"] = scraped_steam
            sources["steam"] = "Exophase"

        scraped_retro = find_number(text, "Retro")
        if scraped_retro and not overrides.get("retro"):
            data["retro"] = scraped_retro
            sources["retro"] = "Exophase"

        # Exophase says GPlay, but your card label says ANDROID.
        scraped_android = find_number(text, "GPlay")
        if scraped_android and not overrides.get("android"):
            data["android"] = scraped_android
            sources["android"] = "Exophase"

        scraped_nintendo = find_number(text, "Nintendo")
        if scraped_nintendo and not overrides.get("nintendo"):
            data["nintendo"] = scraped_nintendo
            sources["nintendo"] = "Exophase"

    except Exception as e:
        print("Could not scrape Exophase automatically. Using fallback/manual values.")
        print("Reason:", e)

    print()
    print("Data sources:")
    for key in [
        "hours",
        "subtitle",
        "psn",
        "steam",
        "retro",
        "android",
        "nintendo",
        "progress",
        "world_rank",
        "games_played",
        "games_beaten",
        "achievements",
        "exophase_exp",
    ]:
        print(f"  {key}: {data[key]} ({sources[key]})")
    print()

    return data


def draw_centered(draw, position, text, font, color=WHITE):
    draw.text(position, str(text), font=font, fill=color, anchor="mm")


def paste_recent_games(card):
    """
    Put 6 images into the 6 recent-game slots.
    Name them:
    1.png, 2.png, 3.png, 4.png, 5.png, 6.png
    inside the recent_games folder.
    """
    for i, slot in enumerate(GAME_SLOTS, start=1):
        x1, y1, x2, y2 = slot
        width = x2 - x1
        height = y2 - y1

        possible_files = [
            RECENT_GAMES_FOLDER / f"{i}.png",
            RECENT_GAMES_FOLDER / f"{i}.jpg",
            RECENT_GAMES_FOLDER / f"{i}.jpeg",
            RECENT_GAMES_FOLDER / f"{i}.webp",
        ]

        image_file = None

        for file in possible_files:
            if file.exists():
                image_file = file
                break

        if image_file is None:
            continue

        game = Image.open(image_file).convert("RGBA")
        game = game.resize((width, height), Image.LANCZOS)
        card.paste(game, (x1, y1))


def main():
    # Load template
    card = Image.open(TEMPLATE).convert("RGBA")
    draw = ImageDraw.Draw(card)

    # Fonts
    hours_font = load_font(FONT_HOURS)
    subtitle_font = load_font(FONT_SUBTITLE)
    platform_font = load_font(FONT_PLATFORM_NUMBERS)
    right_font = load_font(FONT_RIGHT_NUMBERS)

    # Data
    data = get_data()

    # Draw hours
    draw_centered(draw, POSITIONS["hours"], data["hours"], hours_font, CYAN)

    # Draw subtitle
    draw_centered(draw, POSITIONS["subtitle"], data["subtitle"], subtitle_font, CYAN)

    # Draw platform numbers
    draw_centered(draw, POSITIONS["psn"], data["psn"], platform_font)
    draw_centered(draw, POSITIONS["steam"], data["steam"], platform_font)
    draw_centered(draw, POSITIONS["retro"], data["retro"], platform_font)
    draw_centered(draw, POSITIONS["android"], data["android"], platform_font)
    draw_centered(draw, POSITIONS["nintendo"], data["nintendo"], platform_font)

    # Draw right-side numbers
    draw_centered(draw, POSITIONS["progress"], data["progress"], right_font)
    draw_centered(draw, POSITIONS["world_rank"], data["world_rank"], right_font)
    draw_centered(draw, POSITIONS["games_played"], data["games_played"], right_font)
    draw_centered(draw, POSITIONS["games_beaten"], data["games_beaten"], right_font)
    draw_centered(draw, POSITIONS["achievements"], data["achievements"], right_font)
    draw_centered(draw, POSITIONS["exophase_exp"], data["exophase_exp"], right_font)

    # Paste recent games
    paste_recent_games(card)

    # Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT)

    print("Done!")
    print(f"Saved card to: {OUTPUT}")


if __name__ == "__main__":
    main()