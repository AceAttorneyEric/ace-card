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
# Your image is 486 x 150
# -----------------------------
CARD_WIDTH = 486
CARD_HEIGHT = 150

# -----------------------------
# TEXT POSITIONS
# If something is slightly off, nudge the numbers.
# First number = left/right.
# Second number = up/down.
# -----------------------------
POSITIONS = {
    "hours": (106, 36),
    "subtitle": (75, 42),

    "psn": (122, 73),
    "steam": (162, 73),
    "retro": (204, 73),
    "android": (243, 73),
    "nintendo": (286, 73),

    "platinums": (402, 34),
    "progress": (462, 34),
    "games_played": (402, 60),
    "games_completed": (459, 60),
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
FONT_PLATFORM_NUMBERS = 10
FONT_RIGHT_NUMBERS_BIG = 10
FONT_RIGHT_NUMBERS_MED = 10

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


def find_percent(text):
    match = re.search(r"(\d+\.\d+)%", text)
    if match:
        return match.group(1) + "%"
    return None


def find_hours(text):
    match = re.search(r"([\d,]+)\s+hours", text, re.IGNORECASE)
    if match:
        return match.group(1) + " hours"
    return None


def get_data():
    overrides = load_overrides()

    # default values
    data = {
        "hours": overrides.get("hours", "") or "",
        "subtitle": overrides.get("subtitle", "") or "",
        "psn": overrides.get("psn", "") or "",
        "steam": overrides.get("steam", "") or "",
        "retro": overrides.get("retro", "") or "",
        "android": overrides.get("android", "") or "",
        "nintendo": overrides.get("nintendo", "") or "",
        "platinums": overrides.get("platinums", "") or "",
        "progress": overrides.get("progress", "") or "",
        "games_played": overrides.get("games_played", "") or "",
        "games_completed": overrides.get("games_completed", "") or "",
    }

    try:
        text = fetch_page_text()

        scraped_hours = find_hours(text)
        if scraped_hours and not overrides.get("hours"):
            data["hours"] = scraped_hours

        scraped_psn = find_number(text, "PSN")
        if scraped_psn and not overrides.get("psn"):
            data["psn"] = scraped_psn

        scraped_steam = find_number(text, "Steam")
        if scraped_steam and not overrides.get("steam"):
            data["steam"] = scraped_steam

        scraped_retro = find_number(text, "Retro")
        if scraped_retro and not overrides.get("retro"):
            data["retro"] = scraped_retro

        # Exophase usually says GPlay, but your card label says ANDROID
        scraped_android = find_number(text, "GPlay")
        if scraped_android and not overrides.get("android"):
            data["android"] = scraped_android

        scraped_nintendo = find_number(text, "Nintendo")
        if scraped_nintendo and not overrides.get("nintendo"):
            data["nintendo"] = scraped_nintendo

        scraped_progress = find_percent(text)
        if scraped_progress and not overrides.get("progress"):
            data["progress"] = scraped_progress

    except Exception as e:
        print("Could not scrape Exophase automatically. Using fallback/manual values.")
        print("Reason:", e)

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
    right_big_font = load_font(FONT_RIGHT_NUMBERS_BIG)
    right_med_font = load_font(FONT_RIGHT_NUMBERS_MED)

    # Data
    data = get_data()

    # Draw hours
    draw_centered(draw, POSITIONS["hours"], data["hours"], hours_font, CYAN)

    # Draw subtitle
    draw.text(POSITIONS["subtitle"], str(data["subtitle"]), font=subtitle_font, fill=CYAN)

    # Draw platform numbers
    draw_centered(draw, POSITIONS["psn"], data["psn"], platform_font)
    draw_centered(draw, POSITIONS["steam"], data["steam"], platform_font)
    draw_centered(draw, POSITIONS["retro"], data["retro"], platform_font)
    draw_centered(draw, POSITIONS["android"], data["android"], platform_font)
    draw_centered(draw, POSITIONS["nintendo"], data["nintendo"], platform_font)

    # Draw right-side numbers
    draw_centered(draw, POSITIONS["platinums"], data["platinums"], right_med_font)
    draw_centered(draw, POSITIONS["progress"], data["progress"], right_med_font)
    draw_centered(draw, POSITIONS["games_played"], data["games_played"], right_big_font)
    draw_centered(draw, POSITIONS["games_completed"], data["games_completed"], right_big_font)

    # Paste recent games
    paste_recent_games(card)

    # Save
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT)

    print("Done!")
    print(f"Saved card to: {OUTPUT}")


if __name__ == "__main__":
    main()