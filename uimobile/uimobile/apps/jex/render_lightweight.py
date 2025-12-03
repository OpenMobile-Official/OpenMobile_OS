# Mini Browser Lite + Optional Image Mode
# ---------------------------------------
# Works great on Raspberry Pi Zero 2 W
# Controls:
#   - Type URL or search term, then press ENTER
#   - Scroll: click + drag
#   - Toggle image loading: press I
# ---------------------------------------

import pygame, sys, requests, threading, re, time, io
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
from PIL import Image

pygame.init()
pygame.display.set_caption("Mini Browser Lite + Image Mode")

W, H = 480, 320
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()

# --- Fonts & Colors ---
FONT = pygame.font.Font(None, 20)
TITLE_FONT = pygame.font.Font(None, 22)
WHITE = (240, 240, 240)
BLUE = (100, 150, 255)
GRAY = (40, 40, 40)
BG = (25, 25, 25)
LOADING_COLOR = (200, 200, 50)

# --- Global State ---
scroll_y = 0
elements = []  # (surf, href, rect)
current_url = ""
search_text = ""
history = []
loading = False
image_mode = False  # <-- NEW toggle

HEADERS = {
    "User-Agent": "Mozilla/5.0 (RaspberryPi; Linux) MiniBrowser/1.1"
}

# ------------------------------------------------
# Utility
# ------------------------------------------------
def set_loading(v=True):
    global loading
    loading = v

def is_url(text):
    return re.match(r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$', text)

def fetch_image(url, max_width=W-20, max_height=120):
    """Lightweight image fetcher with scaling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5, stream=True)
        img_data = resp.content
        im = Image.open(io.BytesIO(img_data)).convert("RGB")
        im.thumbnail((max_width, max_height))
        mode, size, data = im.mode, im.size, im.tobytes()
        surf = pygame.image.fromstring(data, size, mode)
        return surf
    except Exception:
        return None

# ------------------------------------------------
# Page Loaders
# ------------------------------------------------
def load_duckduckgo_search(query):
    def task():
        set_loading(True)
        global elements, scroll_y, current_url
        scroll_y = 0
        elements.clear()
        current_url = f"duckduckgo://{query}"

        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10).json()
        except Exception as e:
            elements.append((FONT.render(f"❌ Error: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
            set_loading(False)
            return

        y = 40
        for topic in resp.get("RelatedTopics", []):
            if "Text" in topic and "FirstURL" in topic:
                title = topic["Text"]
                link = topic["FirstURL"]
                surf = FONT.render(title, True, BLUE)
                rect = surf.get_rect(topleft=(10, y))
                elements.append((surf, link, rect))
                y += rect.height + 6

        if not elements:
            elements.append((FONT.render("No results.", True, WHITE), None, pygame.Rect(10,40,0,0)))

        set_loading(False)
    threading.Thread(target=task, daemon=True).start()

def load_html_page(url):
    def task():
        set_loading(True)
        global elements, scroll_y, current_url, history
        if current_url:
            history.append(current_url)
        scroll_y = 0
        elements.clear()
        current_url = url
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            elements.append((FONT.render(f"❌ Error loading: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
            set_loading(False)
            return

        y = 40
        for tag in soup.find_all(["h1","h2","p","a","li","img"]):
            if tag.name == "img" and image_mode:
                src = tag.get("src")
                if src:
                    full = urljoin(url, src)
                    surf = fetch_image(full)
                    if surf:
                        rect = surf.get_rect(topleft=(10, y))
                        elements.append((surf, None, rect))
                        y += rect.height + 5
                continue

            text = tag.get_text(strip=True)
            if not text: 
                continue
            href = tag.get("href") if tag.name == "a" else None
            if href:
                href = urljoin(url, href)
            color = BLUE if tag.name == "a" else WHITE
            surf = FONT.render(text[:100], True, color)
            rect = surf.get_rect(topleft=(10, y))
            elements.append((surf, href, rect))
            y += rect.height + 4

        set_loading(False)
    threading.Thread(target=task, daemon=True).start()

# ------------------------------------------------
# Draw
# ------------------------------------------------
def draw():
    screen.fill(BG)
    for surf, href, rect in elements:
        screen.blit(surf, rect.move(0, scroll_y))
    pygame.draw.rect(screen, GRAY, (0,0,W,30))
    hint = search_text or "Type URL or search + Enter"
    txt = FONT.render(hint, True, WHITE)
    screen.blit(txt, (5,5))
    mode_text = "[Images: ON]" if image_mode else "[Images: OFF]"
    mode_surf = FONT.render(mode_text, True, (180,180,180))
    screen.blit(mode_surf, (W - 110, 5))
    if loading:
        load_surf = FONT.render("Loading...", True, LOADING_COLOR)
        screen.blit(load_surf, (W - 220, 5))

# ------------------------------------------------
# Main Loop
# ------------------------------------------------
dragging = False
last_y = 0
running = True

while running:
    draw()
    pygame.display.flip()
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.pos[1] > 30:
                dragging = True
                last_y = event.pos[1]
            for surf, href, rect in elements:
                if href and rect.move(0, scroll_y).collidepoint(event.pos):
                    load_html_page(href)

        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                dy = event.pos[1] - last_y
                scroll_y += dy
                scroll_y = min(0, scroll_y)
                last_y = event.pos[1]

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                text = search_text.strip()
                if not text:
                    continue
                if is_url(text):
                    if not text.startswith("http"):
                        text = "http://" + text
                    load_html_page(text)
                else:
                    load_duckduckgo_search(text)
                search_text = ""
            elif event.key == pygame.K_BACKSPACE:
                search_text = search_text[:-1]
            elif event.key == pygame.K_i:
                image_mode = not image_mode  # toggle image mode
            else:
                ch = event.unicode
                if ch.isprintable():
                    search_text += ch

pygame.quit()
sys.exit()
