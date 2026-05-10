from pathlib import Path
from urllib.parse import urljoin
from PIL import Image
from playwright.sync_api import sync_playwright
import requests
import re
from io import BytesIO

# -----------------------------
# SETTINGS
# -----------------------------
PROFILE_URL = "https://www.exophase.com/user/AceAttorneyEric/"

ROOT = Path(__file__).parent
RECENT_GAMES_FOLDER = ROOT / "recent_games"

# Number of recent games to download
MAX_RECENT_GAMES = 6

# Since your first 6 candidates were correct, leave this at 0.
# If Exophase ever changes and the first useful image becomes #2 or #3,
# you can change this later.
SKIP_FIRST = 0

# Your card uses 73 x 40 recent-game images
FINAL_WIDTH = 73
FINAL_HEIGHT = 40


def fetch_image(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": PROFILE_URL,
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return Image.open(BytesIO(response.content)).convert("RGBA")


def find_candidate_images():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1400, "height": 2000},
            user_agent="Mozilla/5.0"
        )

        page.goto(PROFILE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        images = page.evaluate(
            """
            () => Array.from(document.images).map((img, index) => {
                const rect = img.getBoundingClientRect();

                const src =
                    img.currentSrc ||
                    img.src ||
                    img.getAttribute("data-src") ||
                    img.getAttribute("data-lazy-src") ||
                    "";

                return {
                    index: index,
                    src: src,
                    alt: img.alt || "",
                    title: img.title || "",
                    naturalWidth: img.naturalWidth || 0,
                    naturalHeight: img.naturalHeight || 0,
                    displayWidth: rect.width || 0,
                    displayHeight: rect.height || 0,
                    x: rect.x || 0,
                    y: rect.y || 0,
                    visible:
                        rect.width > 20 &&
                        rect.height > 20 &&
                        window.getComputedStyle(img).visibility !== "hidden" &&
                        window.getComputedStyle(img).display !== "none"
                };
            })
            """
        )

        browser.close()

    candidates = []

    bad_words = [
        "avatar",
        "profile",
        "badge",
        "logo",
        "icon",
        "sprite",
        "platform",
        "user",
        "flags",
        "blank",
        "transparent",
    ]

    for img in images:
        src = img.get("src", "")
        alt = img.get("alt", "")
        title = img.get("title", "")

        if not img.get("visible"):
            continue

        if not src:
            continue

        if src.startswith("data:"):
            continue

        full_src = urljoin(PROFILE_URL, src)

        combined = f"{full_src} {alt} {title}".lower()

        if any(word in combined for word in bad_words):
            continue

        natural_w = img.get("naturalWidth", 0)
        natural_h = img.get("naturalHeight", 0)

        if natural_w <= 0 or natural_h <= 0:
            continue

        aspect = natural_w / natural_h

        # Your final thumbnail shape is 73x40.
        # 73 / 40 = 1.825.
        # This range keeps wide game thumbnails and rejects square icons.
        if not (1.35 <= aspect <= 2.45):
            continue

        # Ignore tiny UI icons.
        if natural_w < 45 or natural_h < 25:
            continue

        # Ignore huge banners/backgrounds.
        if natural_w > 1000 or natural_h > 600:
            continue

        candidates.append(
            {
                "url": full_src,
                "alt": alt or title or f"candidate_{img.get('index')}",
                "x": img.get("x", 0),
                "y": img.get("y", 0),
                "naturalWidth": natural_w,
                "naturalHeight": natural_h,
            }
        )

    # Sort by where the images appear on the Exophase page:
    # top-to-bottom, then left-to-right.
    candidates.sort(key=lambda item: (item["y"], item["x"]))

    return candidates


def main():
    RECENT_GAMES_FOLDER.mkdir(parents=True, exist_ok=True)

    candidates = find_candidate_images()

    print()
    print(f"Found {len(candidates)} candidate images.")
    print("Downloading only the first 6 candidates.")
    print()

    selected_candidates = candidates[SKIP_FIRST:SKIP_FIRST + MAX_RECENT_GAMES]

    if len(selected_candidates) < MAX_RECENT_GAMES:
        print()
        print("WARNING: Did not find enough candidate images.")
        print(f"Only found {len(selected_candidates)} after SKIP_FIRST = {SKIP_FIRST}.")
        print()

    for i, candidate in enumerate(selected_candidates, start=1):
        try:
            img = fetch_image(candidate["url"])
            img = img.resize((FINAL_WIDTH, FINAL_HEIGHT), Image.LANCZOS)
            img.save(RECENT_GAMES_FOLDER / f"{i}.png")

            print(f"Saved recent_games\\{i}.png")
            print(f"  {candidate['alt']}")
            print(f"  Original size: {candidate['naturalWidth']}x{candidate['naturalHeight']}")

        except Exception as e:
            print(f"Could not download recent game {i}: {candidate['url']}")
            print(f"Reason: {e}")

    print()
    print("Done!")
    print(f"Saved recent games to: {RECENT_GAMES_FOLDER}")
    print()


if __name__ == "__main__":
    main()