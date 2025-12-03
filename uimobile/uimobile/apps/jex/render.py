import pygame, sys, requests, io, threading, re, time
from bs4 import BeautifulSoup
from PIL import Image
from urllib.parse import urljoin, quote_plus
import random

pygame.init()
pygame.display.set_caption("Enhanced Mini Browser")
W, H = 480, 320
screen = pygame.display.set_mode((W, H))

# Fonts & colors
TITLE_FONT = pygame.font.Font(None, 22)
BIG_FONT = pygame.font.Font(None, 26)
DESC_FONT = pygame.font.Font(None, 18)
WHITE = (240,240,240)
BLUE = (100,150,255)
GRAY = (40,40,40)
BG = (25,25,25)
LOADING_COLOR = (200,200,50)
BUTTON_COLOR = (60,60,60)
BUTTON_HOVER = (80,80,80)

scroll_y = 0
elements = []  # (surf, desc_surf, href, rect)
current_url = ""
search_text = ""
history = []
loading = False
buttons = []  # (rect, label, callback)
button_timer = 0  # For auto-hide

# --------------------------
# Headers
# --------------------------
HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/114.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language":"en-US,en;q=0.9",
    "Accept-Encoding":"gzip, deflate",
    "Connection":"keep-alive",
    "Upgrade-Insecure-Requests":"1",
    "DNT":"1"
}

# --------------------------
# Utilities
# --------------------------
def set_loading(val=True):
    global loading
    loading = val

def is_url(text):
    pattern = r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$'
    return re.match(pattern, text)

def fetch_image(url, max_width=W-20, max_height=100):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        img_data = resp.content
        im = Image.open(io.BytesIO(img_data)).convert("RGB")
        if im.width < 20 or im.height < 20:
            return None
        im.thumbnail((max_width, max_height))
        mode, size, data = im.mode, im.size, im.tobytes()
        surf = pygame.image.fromstring(data, size, mode)
        return surf
    except:
        return None

# --------------------------
# Page loaders
# --------------------------
def load_duckduckgo_search(query):
    def task():
        set_loading(True)
        global elements, scroll_y, current_url, buttons
        scroll_y = 0
        elements.clear()
        buttons.clear()
        current_url = f"duckduckgo_search://{query}"
        url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10).json()
        except:
            elements.append((TITLE_FONT.render("❌ Error fetching search results", True, (255,80,80)), None, None, pygame.Rect(10,40,0,0)))
            set_loading(False)
            return

        y = 40
        if resp.get("AbstractText"):
            title_surf = TITLE_FONT.render(resp.get("Heading","DuckDuckGo Result"), True, WHITE)
            desc_surf = DESC_FONT.render(resp["AbstractText"], True, WHITE)
            rect = pygame.Rect(10,y,W-20,title_surf.get_height()+desc_surf.get_height()+5)
            elements.append((title_surf, desc_surf, resp.get("AbstractURL"), rect))
            y += title_surf.get_height() + desc_surf.get_height() + 10

        for topic in resp.get("RelatedTopics", []):
            if "Text" in topic and "FirstURL" in topic:
                text = topic["Text"]
                url_link = topic["FirstURL"]
                if " - " in text:
                    title_text, desc_text = text.split(" - ",1)
                else:
                    title_text, desc_text = text, ""
                title_surf = TITLE_FONT.render(title_text, True, BLUE)
                desc_surf = DESC_FONT.render(desc_text, True, WHITE)
                rect_height = title_surf.get_height() + desc_surf.get_height() + 5
                rect = pygame.Rect(10,y,W-20,rect_height)
                elements.append((title_surf, desc_surf, url_link, rect))
                y += rect_height + 8
        set_loading(False)
    threading.Thread(target=task, daemon=True).start()

def load_html_page(url):
    def task():
        set_loading(True)
        global elements, scroll_y, current_url, history, buttons
        if current_url:
            history.append(current_url)
        scroll_y = 0
        elements.clear()
        buttons.clear()
        current_url = url
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except:
            elements.append((TITLE_FONT.render("❌ Error loading page", True, (255,80,80)), None, None, pygame.Rect(10,40,0,0)))
            set_loading(False)
            return

        y = 40
        for tag in soup.find_all(["h1","h2","h3","h4","h5","h6","p","li","a","img","br","b","i","u","hr","ul","ol"]):
            if tag.name=="br":
                y += 10
            elif tag.name=="hr":
                y += 10
            elif tag.name in ["b","i","u"]:
                text = tag.get_text(strip=True)
                if not text: continue
                font = DESC_FONT
                bold = tag.name=="b"
                italic = tag.name=="i"
                surf = pygame.font.SysFont(None,18,bold=bold,italic=italic).render(text, True, WHITE)
                rect = surf.get_rect(topleft=(10,y))
                elements.append((surf,None,None,rect))
                y += rect.height + 2
            elif tag.name in ["ul","ol"]:
                for li in tag.find_all("li"):
                    text = "• " + li.get_text(strip=True)
                    surf = DESC_FONT.render(text, True, WHITE)
                    rect = surf.get_rect(topleft=(20,y))
                    elements.append((surf,None,None,rect))
                    y += rect.height + 2
            elif tag.name=="img" and tag.get("src"):
                src = urljoin(url, tag["src"])
                surf = fetch_image(src)
                if surf:
                    rect = surf.get_rect(topleft=(10,y))
                    elements.append((surf,None,None,rect))
                    y += rect.height + 5
            else:
                text = tag.get_text(strip=True)
                if not text: continue
                font = BIG_FONT if tag.name.startswith("h") else DESC_FONT
                color = BLUE if tag.name=="a" else WHITE
                href = tag.get("href") if tag.name=="a" else None
                if href: href = urljoin(url, href)
                words = text.split()
                line = ""
                for w in words:
                    test = font.render(line + w + " ", True, color)
                    if test.get_width() > W-20:
                        surf = font.render(line, True, color)
                        rect = surf.get_rect(topleft=(10,y))
                        elements.append((surf,None,href,rect))
                        y += rect.height + 2
                        line = w + " "
                    else:
                        line += w + " "
                if line:
                    surf = font.render(line, True, color)
                    rect = surf.get_rect(topleft=(10,y))
                    elements.append((surf,None,href,rect))
                    y += rect.height + 5
        set_loading(False)
    threading.Thread(target=task, daemon=True).start()

def load_loremflickr_gallery(term):
    def task():
        set_loading(True)
        global elements, scroll_y, current_url, buttons
        scroll_y = 0
        elements.clear()
        buttons.clear()
        current_url = f"loremflickr://{term}"
        y = 40
        for i in range(10):
            url_img = f"https://loremflickr.com/320/240/{term}?lock={random.randint(1,9999)}"
            surf = fetch_image(url_img, max_height=100)
            if surf:
                rect = surf.get_rect(topleft=(10,y))
                elements.append((surf,None,url_img,rect))
                y += rect.height + 10
        set_loading(False)
    threading.Thread(target=task, daemon=True).start()

# --------------------------
# Draw
# --------------------------
def draw():
    screen.fill(BG)
    for surf, desc, href, rect in elements:
        screen.blit(surf, rect.move(0,scroll_y))
        if desc:
            screen.blit(desc, (rect.x, rect.y + surf.get_height() + scroll_y))
    pygame.draw.rect(screen, GRAY, (0,0,W,30))
    txt = TITLE_FONT.render(search_text or "Type URL or search + Enter", True, WHITE)
    screen.blit(txt, (5,5))

    mouse_pos = pygame.mouse.get_pos()
    for rect, label, _ in buttons:
        color = BUTTON_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect)
        label_surf = TITLE_FONT.render(label, True, WHITE)
        screen.blit(label_surf, (rect.x+5, rect.y+5))

    if loading:
        loading_surf = TITLE_FONT.render("Loading...", True, LOADING_COLOR)
        screen.blit(loading_surf, (W-100,5))

# --------------------------
# Main loop
# --------------------------
dragging = False
last_y = 0

running = True
while running:
    draw()
    pygame.display.flip()
    now = time.time()
    # Auto-select DuckDuckGo after 1 second
    if buttons and now - button_timer > 1:
        _, _, callback = buttons[0]
        buttons.clear()
        callback()
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False
        elif event.type==pygame.MOUSEBUTTONDOWN:
            if event.pos[1]>30:
                dragging=True
                last_y = event.pos[1]
            for rect, _, callback in buttons:
                if rect.collidepoint(event.pos):
                    buttons.clear()
                    callback()
            for surf, desc, href, rect in elements:
                if href and rect.move(0,scroll_y).collidepoint(event.pos):
                    if current_url.startswith("loremflickr://"):
                        load_html_page(href)
                    elif href.startswith("duckduckgo_search://"):
                        load_duckduckgo_search(href.split("://")[1])
                    else:
                        load_html_page(href)
        elif event.type==pygame.MOUSEBUTTONUP:
            dragging=False
        elif event.type==pygame.MOUSEMOTION:
            if dragging:
                dy = event.pos[1] - last_y
                scroll_y += dy
                scroll_y = min(0, scroll_y)
                last_y = event.pos[1]
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_RETURN:
                text = search_text.strip()
                if not text:
                    elements.clear()
                    search_text=""
                    continue
                if is_url(text):
                    buttons.clear()
                    if not text.startswith("http"):
                        text = "http://" + text
                    load_html_page(text)
                    search_text=""
                else:
                    buttons.clear()
                    btn1 = pygame.Rect(5, 32, 150, 24)
                    btn2 = pygame.Rect(160, 32, 150, 24)
                    term = text
                    buttons.append((btn1, "Search DuckDuckGo", lambda t=term: load_duckduckgo_search(t)))
                    buttons.append((btn2, "Search LoremFlickr", lambda t=term: load_loremflickr_gallery(t)))
                    button_timer = time.time()  # Start 1-second timer
                    search_text=""
            elif event.key==pygame.K_BACKSPACE:
                search_text = search_text[:-1]
            else:
                ch = event.unicode
                if ch.isprintable():
                    search_text += ch

pygame.quit()
sys.exit()
