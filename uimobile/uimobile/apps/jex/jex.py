# jex_browser_final.py
# Jex — final browser with top controls, sliding solid overlays (Favs/History/Archive),
# archive saving (HTML + images), toast notifications, and LoremFlickr search in Full mode.
#
# Place next to your modules folder (modules/top_bar.py and modules/keyboard.py).
# Requires: pygame, requests, bs4, pillow

import os, sys, time, json, threading, io, re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pygame
import random

# local modules (same API as your template)
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

# ---------- Data paths ----------
DATA_DIR = "browser_data"
ARCH_DIR = os.path.join(DATA_DIR, "archives")
META_FAV = os.path.join(DATA_DIR, "favourites.json")
META_HISTORY = os.path.join(DATA_DIR, "history.json")
META_ARCH_INDEX = os.path.join(DATA_DIR, "archives_index.json")
# --------------------------
# Quick-search buttons
# --------------------------
quick_buttons = []  # persistent buttons for search terms
quick_timer = 0    # tracks when buttons were created for auto-click

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCH_DIR, exist_ok=True)
for p, default in [(META_FAV, []), (META_HISTORY, []), (META_ARCH_INDEX, {})]:
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
# Example: inside your page load function
def parse_ascii_block(self, tag, y_start):
    ascii_text = tag.get_text()
    padding_left = 10
    padding_right = 10
    max_width = self.screen.get_width() - padding_left - padding_right
    line_spacing = 2

    # Auto-scale font
    test_font_size = 16
    ascii_font = pygame.font.SysFont("Courier", test_font_size)
    max_line_width = max(ascii_font.size(line)[0] for line in ascii_text.splitlines())
    if max_line_width > max_width:
        scale_ratio = max_width / max_line_width
        test_font_size = max(int(test_font_size * scale_ratio), 8)
        ascii_font = pygame.font.SysFont("Courier", test_font_size)

    # Render each line and return surfaces
    surfaces = []
    y_offset = y_start
    for line in ascii_text.splitlines():
        surf = ascii_font.render(line, True, (240, 240, 240))
        rect = surf.get_rect(topleft=(padding_left, y_offset))
        surfaces.append((surf, None, rect))
        y_offset += rect.height + line_spacing

    return surfaces, y_offset + 10  # Return surfaces and updated y

# --- ASCII RENDERING FUNCTION ---
def render_ascii_block(self, ascii_text, y_start):
    """
    Renders ASCII art text as pygame surfaces, auto-scaling to screen width,
    and returns a list of surfaces with rects plus the new y position.
    """
    padding_left = 10
    padding_right = 10
    line_spacing = 2
    screen_width = self.screen.get_width()
    max_width = screen_width - padding_left - padding_right

    # Start with default font size
    font_size = 16
    font = pygame.font.SysFont("Courier", font_size)

    # Check the longest line width
    lines = ascii_text.splitlines()
    if not lines:
        return [], y_start + 10

    max_line_width = max(font.size(line)[0] for line in lines)
    
    # Auto-scale if too wide
    if max_line_width > max_width:
        scale_ratio = max_width / max_line_width
        font_size = max(int(font_size * scale_ratio), 8)  # Minimum readable size
        font = pygame.font.SysFont("Courier", font_size)

    surfaces = []
    y_offset = y_start

    for line in lines:
        surf = font.render(line, True, (240, 240, 240))  # light color
        rect = surf.get_rect(topleft=(padding_left, y_offset))
        surfaces.append((surf, None, rect))
        y_offset += rect.height + line_spacing

    # Add extra spacing below
    y_offset += 10

    return surfaces, y_offset

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Save JSON error:", e)


# ---------- Embedded renderer (keeps single-window behavior) ----------
class SimpleRenderer:
    """
    Embedded renderer.
    Modes: Full (images + loremflickr option), Lite (text + images optional), Ultra (text only).
    """

    def __init__(self, width, height, mode="Full"):
        self.W = width
        self.H = height
        self.mode = mode
        self.scroll_y = 0
        self.elements = []  # list of tuples: (surface, href, rect)
        self.current_url = ""
        self.current_title = ""
        self.loading = False
        self.headers = {"User-Agent": "JexBrowser/1.0"}
        self.FONT_TITLE = pygame.font.Font(None, 22)
        self.FONT_DESC = pygame.font.Font(None, 18)
        self.IMAGE_MAX_H = 110

    def set_mode(self, mode):
        self.mode = mode

    def set_loading(self, v=True):
        self.loading = v

    def is_url(self, text):
        return re.match(r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$', text)

    def fetch_image_surface(self, src, max_w=None, max_h=None):
        max_w = max_w or (self.W - 20)
        max_h = max_h or self.IMAGE_MAX_H
        try:
            if src.startswith("file://"):
                path = src[len("file://"):]
                with open(path, "rb") as f:
                    data = f.read()
            elif os.path.exists(src):
                with open(src, "rb") as f:
                    data = f.read()
            else:
                resp = requests.get(src, headers=self.headers, timeout=10)
                resp.raise_for_status()
                data = resp.content
            im = Image.open(io.BytesIO(data)).convert("RGB")
            if im.width < 12 or im.height < 12:
                return None
            im.thumbnail((max_w, max_h))
            surf = pygame.image.fromstring(im.tobytes(), im.size, im.mode)
            return surf
        except Exception:
            return None

    def clear(self):
        self.elements.clear()
        self.scroll_y = 0
        self.current_url = ""
        self.current_title = ""

    def load_loremflickr_gallery(self, term):
        def task():
            self.set_loading(True)
            self.elements.clear()
            self.scroll_y = 0
            self.current_url = f"loremflickr://{term}"
            y = 40
            # fetch a handful of random-ish images
            for i in range(10):
                url_img = f"https://loremflickr.com/320/240/{term}?lock={random.randint(1,999999)}"
                surf = self.fetch_image_surface(url_img, max_w=self.W - 20, max_h=100)
                if surf:
                    rect = surf.get_rect(topleft=(10, y))
                    self.elements.append((surf, url_img, rect))
                    y += rect.height + 10
            if not self.elements:
                self.elements.append((self.FONT_TITLE.render("No images found", True, (220,220,220)), None, pygame.Rect(10,40,0,0)))
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_duckduckgo_search(self, query):
        def task():
            self.set_loading(True)
            self.elements.clear()
            self.scroll_y = 0
            self.current_url = f"duckduckgo_search://{query}"
            url = f"https://api.duckduckgo.com/?q={requests.utils.requote_uri(query)}&format=json&no_html=1&skip_disambig=1"
            try:
                resp = requests.get(url, headers=self.headers, timeout=8).json()
            except Exception:
                self.elements.append((self.FONT_TITLE.render("❌ Error fetching search results", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return
            y = 40
            if resp.get("AbstractText"):
                title_surf = self.FONT_TITLE.render(resp.get("Heading","DuckDuckGo Result"), True, (240,240,240))
                desc_surf = self.FONT_DESC.render(resp["AbstractText"][:200], True, (220,220,220))
                self.elements.append((title_surf, None, pygame.Rect(10,y,title_surf.get_width(),title_surf.get_height())))
                y += title_surf.get_height() + 4
                self.elements.append((desc_surf, None, pygame.Rect(10,y,desc_surf.get_width(),desc_surf.get_height())))
                y += desc_surf.get_height() + 8

            for topic in resp.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    text = topic["Text"]
                    url_link = topic["FirstURL"]
                    if " - " in text:
                        title_text, desc_text = text.split(" - ",1)
                    else:
                        title_text, desc_text = text, ""
                    title_surf = self.FONT_TITLE.render(title_text[:60], True, (100,150,255))
                    desc_surf = self.FONT_DESC.render(desc_text[:120], True, (220,220,220))
                    self.elements.append((title_surf, url_link, pygame.Rect(10,y,title_surf.get_width(),title_surf.get_height())))
                    y += title_surf.get_height() + 2
                    self.elements.append((desc_surf, None, pygame.Rect(10,y,desc_surf.get_width(),desc_surf.get_height())))
                    y += desc_surf.get_height() + 8

            # Add buttons to allow user to pick DuckDuckGo or LoremFlickr image search after typing a query.
            # We emulate the original behavior: when the search is *not* a URL, we present two choice buttons on top.
            btn_y = 32
            btn1 = ("Search DuckDuckGo", lambda q=query: self.load_duckduckgo_search(q))
            btn2 = ("Search LoremFlickr", lambda q=query: self.load_loremflickr_gallery(q))
            # Represent buttons as small surface elements (they will be handled by outer UI using renderer.buttons)
            # We store them in self.buttons attribute for the app to display and handle.
            self.buttons = [
                (pygame.Rect(8, btn_y, 160, 24), btn1[0], btn1[1]),
                (pygame.Rect(176, btn_y, 160, 24), btn2[0], btn2[1]),
            ]

            if not self.elements:
                self.elements.append((self.FONT_TITLE.render("No results", True, (220,220,220)), None, pygame.Rect(10,40,0,0)))
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_html_page(self, url):
        def task():
            self.set_loading(True)
            self.elements.clear()
            self.scroll_y = 0
            self.current_url = url
            try:
                resp = requests.get(url, headers=self.headers, timeout=12)
                resp.raise_for_status()
                html = resp.text
            except Exception as e:
                self.elements.append((self.FONT_TITLE.render(f"❌ Error loading page: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return
            self._parse_and_build(html, base_url=url)
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_html_from_file(self, path):
        def task():
            self.set_loading(True)
            self.elements.clear()
            self.scroll_y = 0
            self.current_url = path
            try:
                with open(path, "r", encoding="utf-8") as f:
                    html = f.read()
                base = "file://" + os.path.dirname(os.path.abspath(path)) + "/"
            except Exception as e:
                self.elements.append((self.FONT_TITLE.render(f"❌ Error loading archive: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return
            self._parse_and_build(html, base_url=base)
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_query_or_url(self, text):
        if self.is_url(text):
            u = text if text.startswith("http") else ("http://" + text)
            self.load_html_page(u)
            self.buttons = []  # hide quick buttons for URLs
        else:
            self.load_duckduckgo_search(text)

    def _parse_and_build(self, html, base_url=None):
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        self.current_title = title_tag.get_text(strip=True) if title_tag else base_url or ""
        y = 40
        include_images = (self.mode in ("Full", "Lite"))
        self.buttons = []  # clear any previous quick buttons
        for tag in soup.find_all(["h1","h2","h3","p","li","a","img","br","hr","strong","em","ul","ol","pre","ascii"]):
            if tag.name in ("br","hr"):
                y += 8
                continue
            # --- ASCII block rendering for <pre class="ascii"> ---
            # --- ASCII block rendering with auto-scaling ---
                        # --- ASCII RENDERING FUNCTION ---
            # --- ASCII block rendering with auto-scaling ---
            if tag.name == "pre" and "ascii" in tag.get("class", []):
                text = tag.get_text()
                # split lines exactly, keep spacing
                for line in text.splitlines():
                    surf = pygame.font.SysFont("Courier", 10).render(line, True, (240,240,240))
                    rect = surf.get_rect(topleft=(10, y))
                    self.elements.append((surf, None, rect))
                    y += rect.height
                y += 10  # extra space below the ASCII block
                continue



            if tag.name == "img" and include_images:
                src = tag.get("src")
                if not src:
                    continue
                full = urljoin(base_url, src) if base_url else src
                surf = self.fetch_image_surface(full, max_w=self.W-20, max_h=self.IMAGE_MAX_H)
                if surf:
                    rect = surf.get_rect(topleft=(10, y))
                    self.elements.append((surf, full, rect))
                    y += rect.height + 6
                continue
            if tag.name in ("ul","ol"):
                for li in tag.find_all("li"):
                    text = "• " + li.get_text(strip=True)
                    surf = self.FONT_DESC.render(text, True, (240,240,240))
                    rect = surf.get_rect(topleft=(20, y))
                    self.elements.append((surf, None, rect))
                    y += rect.height + 4
                continue
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            font = self.FONT_TITLE if tag.name.startswith("h") else self.FONT_DESC
            color = (100,150,255) if tag.name == "a" else (240,240,240)
            href = None
            if tag.name == "a" and tag.get("href"):
                href = urljoin(base_url, tag["href"]) if base_url else tag["href"]
            # simple wrapping
            words = text.split()
            line = ""
            for w in words:
                test = font.render(line + w + " ", True, color)
                if test.get_width() > self.W - 20:
                    surf = font.render(line.strip(), True, color)
                    rect = surf.get_rect(topleft=(10, y))
                    self.elements.append((surf, href, rect))
                    y += rect.height + 4
                    line = w + " "
                else:
                    line += w + " "
            if line:
                surf = font.render(line.strip(), True, color)
                rect = surf.get_rect(topleft=(10, y))
                self.elements.append((surf, href, rect))
                y += rect.height + 6
            if y > 5000:
                break

    def draw(self, surface, offset_y):
        # draws content into provided surface, offset_y = top of content area
        content_rect = pygame.Rect(0, offset_y, surface.get_width(), surface.get_height()-offset_y)
        pygame.draw.rect(surface, (18,18,18), content_rect)
        for surf, href, rect in self.elements:
            target = rect.move(0, self.scroll_y + offset_y)
            if target.bottom < offset_y or target.top > surface.get_height():
                continue
            try:
                surface.blit(surf, target)
            except Exception:
                pass
        # draw quick buttons if present (these are relative to screen, not content)
        if hasattr(self, "buttons") and self.buttons:
            mx,my = pygame.mouse.get_pos()
            for r, label, _cb in self.buttons:
                color = (80,80,80) if r.collidepoint((mx,my)) else (60,60,60)
                pygame.draw.rect(surface, color, r)
                txt = self.FONT_DESC.render(label, True, (240,240,240))
                surface.blit(txt, (r.x+6, r.y+4))
        if self.loading:
            s = self.FONT_DESC.render("Loading...", True, (200,180,50))
            surface.blit(s, (surface.get_width() - 120, offset_y + 6))

    def content_click(self, pos, offset_y):
        x, y = pos
        local_y = y - offset_y - self.scroll_y
        # check element rects
        for surf, href, rect in self.elements:
            if rect.collidepoint(x, local_y):
                return href
        # no link clicked
        return None


# ---------- Toast Notifications ----------
class ToastManager:
    def __init__(self):
        self.msg = None
        self.start = 0
        self.duration = 2.5

    def show(self, msg, duration=2.5):
        self.msg = msg
        self.start = time.time()
        self.duration = duration

    def draw(self, surface):
        if not self.msg:
            return
        elapsed = time.time() - self.start
        if elapsed > self.duration:
            self.msg = None
            return
        alpha = 255
        # draw a small rectangle at bottom center
        w = 360
        h = 30
        x = (surface.get_width() - w) // 2
        y = surface.get_height() - h - 10
        s = pygame.Surface((w, h))
        s.set_alpha(220)
        s.fill((40, 40, 40))
        surface.blit(s, (x, y))
        font = pygame.font.Font(None, 18)
        txt = font.render(self.msg, True, (240,240,240))
        surface.blit(txt, (x + 10, y + 6))
    # opens the on-screen keyboard and loads the query/URL



# ---------- Main Jex Browser App ----------
class JexBrowserFinal:
    def __init__(self, w=480, h=320):
        pygame.init()
        self.W, self.H = w, h
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Jex Browser")
        self.clock = pygame.time.Clock()

        # fonts
        self.font_sm = pygame.font.SysFont("Arial", 14)
        self.font_md = pygame.font.SysFont("Arial", 18)

        # topbar
        self.topbar = TopBarManager(self.W, self.H, self.font_sm, self.font_md, app_key="jex")

        # control bar (moved to top under topbar)
                # Button dimensions
                # ---------------- Control bar: single horizontal panel ----------------
        button_width = 80
        button_height = 28
                # ---------------- Control bar: top horizontal panel ----------------
        spacing = 8
        start_x = 8
        start_y = 5  # just under topbar

        # List of buttons
        self.buttons_data = [
            {"label": "Fav", "action": lambda: self.run_quick_action("add_fav")},
            {"label": "His", "action": lambda: self.toggle_sidebar("history")},
            {"label": "Arch", "action": lambda: self.toggle_sidebar("archives")},
            {"label": "+", "action": self.open_actions},
            {"label": "Search", "action": self.open_keyboard_and_load},
            {"label": "Eng", "action": self.set_engine}
        ]

        # Create rects dynamically based on text width
        self.button_rects = []
        font = pygame.font.Font(None, 24)
        x = start_x
        for btn in self.buttons_data:
            text_surf = font.render(btn["label"], True, (240,240,240))
            width = text_surf.get_width() + 16  # 8px padding each side
            height = text_surf.get_height() + 8  # vertical padding
            rect = pygame.Rect(x, start_y, width, height)
            btn["rect"] = rect
            self.button_rects.append(rect)
            x += width + spacing  # next button


        # renderer (background layer)
        self.renderer = SimpleRenderer(self.W, self.H, mode="Full")
        
        self.content_top = 30
        #home page


        # Get the directory the script is in
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        HOME_PATH = os.path.join(BASE_DIR, "home.html")

        if os.path.exists(HOME_PATH):
            self.renderer.load_html_from_file(HOME_PATH)
        else:
            print(f"⚠️ home.html not found at {HOME_PATH}")

        # sidebar (sliding overlay)
        self.sidebar_open = False
        self.sidebar_w = 260
        self.sidebar_x = -self.sidebar_w
        self.sidebar_target = -self.sidebar_w
        self.sidebar_speed = 700  # px/sec
        self.sidebar_tab = "favourites"
        self.sidebar_scroll = 0
        self.sidebar_dragging = False
        self.sidebar_last_y = 0

        # quick actions panel (small overlay from right)
        self.actions_open = False
        self.actions_rect = pygame.Rect(self.W - 140, 36, 130, 120)

        # persistence
        self.favourites = load_json(META_FAV, [])
        self.history = load_json(META_HISTORY, [])
        self.arch_index = load_json(META_ARCH_INDEX, {})

        # toast
        self.toast = ToastManager()

        # interaction state
        self.dragging = False
        self.last_y = 0

    # ---------------- Persistence helpers ----------------
    def add_history(self, url):
        self.history.insert(0, {"ts": time.time(), "url": url})
        self.history = self.history[:400]
        save_json(META_HISTORY, self.history)

    def add_favourite(self, title, url):
        if not url:
            return
        self.favourites.insert(0, {"title": title, "url": url, "ts": time.time()})
        # dedupe
        seen = set()
        new = []
        for item in self.favourites:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            new.append(item)
        self.favourites = new[:300]
        save_json(META_FAV, self.favourites)

    def remove_favourite(self, url):
        self.favourites = [f for f in self.favourites if f["url"] != url]
        save_json(META_FAV, self.favourites)

    # ---------------- Archive: save HTML + images ----------------
    def archive_current(self, name=None):
        url = self.renderer.current_url
        if not url:
            return False, "No page loaded"
        try:
            resp = requests.get(url, headers=self.renderer.headers, timeout=12)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return False, f"Download failed: {e}"

        # build name
        if not name:
            parsed = urlparse(url)
            safe = (parsed.netloc + parsed.path).strip("/").replace("/", "_") or "page"
            name = f"{safe}_{int(time.time())}"
        arch_path = os.path.join(ARCH_DIR, name)
        os.makedirs(arch_path, exist_ok=True)
        assets = os.path.join(arch_path, "assets")
        os.makedirs(assets, exist_ok=True)

        soup = BeautifulSoup(html, "html.parser")
        # download images & rewrite src to local
        for i, img in enumerate(soup.find_all("img")):
            src = img.get("src")
            if not src:
                continue
            full = urljoin(url, src)
            try:
                r = requests.get(full, headers=self.renderer.headers, timeout=10)
                r.raise_for_status()
                ext = os.path.splitext(urlparse(full).path)[1] or ".jpg"
                fname = f"img_{i}{ext}"
                path = os.path.join(assets, fname)
                with open(path, "wb") as f:
                    f.write(r.content)
                img["src"] = "assets/" + fname
            except Exception:
                # skip any image that fails
                continue

        local_index = os.path.join(arch_path, "index.html")
        with open(local_index, "w", encoding="utf-8") as f:
            f.write(str(soup))

        # update index
        self.arch_index[name] = {"name": name, "url": url, "path": local_index, "ts": time.time()}
        save_json(META_ARCH_INDEX, self.arch_index)
        return True, name

    def open_archive(self, name):
        meta = self.arch_index.get(name)
        if not meta:
            return False
        path = meta.get("path")
        if not path or not os.path.exists(path):
            return False
        self.renderer.load_html_from_file(path)
        self.add_history("archive://" + name)
        return True

    # ---------------- UI helpers ----------------
    def toggle_sidebar(self, tab=None):
        self.sidebar_open = not self.sidebar_open
        if tab:
            self.sidebar_tab = tab
        self.sidebar_target = 0 if self.sidebar_open else -self.sidebar_w

    def open_actions(self):
        self.actions_open = not self.actions_open

    def run_quick_action(self, action):
        # actions: add_fav, archive, clear_history
        if action == "add_fav":
            title = self.renderer.current_title or self.renderer.current_url or "Untitled"
            url = self.renderer.current_url or ""
            if url:
                self.add_favourite(title, url)
                self.toast.show("Added to favourites")
        elif action == "archive":
            ok, name = self.archive_current()
            if ok:
                self.toast.show(f"Archived: {name}")
            else:
                self.toast.show(f"Archive failed")
        elif action == "clear_history":
            self.history = []
            save_json(META_HISTORY, self.history)
            self.toast.show("History cleared")
        # close actions
        self.actions_open = False

#draw ui
    def draw_controls(self):
        # Draw a solid bar behind buttons
        bar_height = max(btn["rect"].height for btn in self.buttons_data) + 8
        pygame.draw.rect(self.screen, (40,40,40), (0, 0, self.W, bar_height))

        mouse_pos = pygame.mouse.get_pos()
        font = pygame.font.Font(None, 24)
        for btn in self.buttons_data:
            rect = btn["rect"]
            color = (80,80,80) if rect.collidepoint(mouse_pos) else (60,60,60)
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            text_surf = font.render(btn["label"], True, (240,240,240))
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)


    # ---------------- Keyboard & Renderer Mode ----------------
    def open_keyboard_and_load(self):
        """Opens the on-screen keyboard and loads the query/URL."""
        out = run_keyboard()  # from modules.keyboard
        if out:
            self.renderer.load_query_or_url(out)
            self.add_history(out)

    def set_engine(self):
        """Cycles renderer mode: Full → Lite → Ultra."""
        modes = ["Full", "Lite", "Ultra"]
        idx = modes.index(self.renderer.mode)
        new_mode = modes[(idx + 1) % len(modes)]
        self.renderer.set_mode(new_mode)
        self.toast.show(f"Renderer mode: {new_mode}")

    def draw_sidebar(self, dt):
        # animate
        if self.sidebar_x < self.sidebar_target:
            self.sidebar_x = min(self.sidebar_target, self.sidebar_x + self.sidebar_speed * dt)
        elif self.sidebar_x > self.sidebar_target:
            self.sidebar_x = max(self.sidebar_target, self.sidebar_x - self.sidebar_speed * dt)
        sx = int(self.sidebar_x)
        panel = pygame.Rect(sx, 0, self.sidebar_w, self.H)
        pygame.draw.rect(self.screen, (30,30,30), panel)  # solid panel as requested

        # tabs
        tab_h = 28
        tab_w = self.sidebar_w // 3
        labels = [("Favs","favourites"),("Hist","history"),("Arch","archives")]
        for i, (lab, key) in enumerate(labels):
            r = pygame.Rect(sx + i*tab_w, 30, tab_w, tab_h)
            active = (key == self.sidebar_tab)
            pygame.draw.rect(self.screen, (60,60,60) if active else (48,48,48), r)
            t = self.font_sm.render(lab, True, (240,240,240))
            self.screen.blit(t, (r.x+8, r.y+6))

        # list region
        list_top = 30 + tab_h + 6
        list_h = self.H - list_top - 10
        list_rect = pygame.Rect(sx+6, list_top, self.sidebar_w-12, list_h)
        pygame.draw.rect(self.screen, (22,22,22), list_rect)

        # select items
        items = []
        if self.sidebar_tab == "favourites":
            items = [{"label": f"{f['title']}", "meta": f} for f in self.favourites]
        elif self.sidebar_tab == "history":
            items = [{"label": f"{h['url']}", "meta": h} for h in self.history]
        else:
            items = [{"label": v.get("name") or v.get("url"), "meta": v} for k,v in self.arch_index.items()]

        # draw items with small remove button
        y = list_top + 8 + int(self.sidebar_scroll)
        tile_h = 40
        mx,my = pygame.mouse.get_pos()
        cache = []
        for it in items:
            tile = pygame.Rect(sx+8, y, self.sidebar_w-24, tile_h)
            if tile.bottom < list_top or tile.top > list_top + list_h:
                y += tile_h + 6
                continue
            pygame.draw.rect(self.screen, (44,44,44), tile, border_radius=6)
            label = it["label"][:36]
            txt = self.font_sm.render(label, True, (230,230,230))
            self.screen.blit(txt, (tile.x + 8, tile.y + 8))
            xbtn = pygame.Rect(tile.right - 28, tile.y + 8, 20, 20)
            pygame.draw.rect(self.screen, (80,80,80), xbtn, border_radius=4)
            x_txt = self.font_sm.render("X", True, (220,220,220))
            self.screen.blit(x_txt, (xbtn.x + 5, xbtn.y + 0))
            it["_tile_rect"] = tile
            it["_xbtn_rect"] = xbtn
            cache.append(it)
            y += tile_h + 6
        self._sidebar_items_cache = cache

    def draw_actions_panel(self):
        if not self.actions_open:
            return
        pygame.draw.rect(self.screen, (35,35,35), self.actions_rect, border_radius=6)
        # options: Add to favourites, Archive page, Clear history
        labels = [("Add to favourites","add_fav"), ("Archive page","archive"), ("Clear history","clear_history")]
        for i, (lab, key) in enumerate(labels):
            r = pygame.Rect(self.actions_rect.x + 6, self.actions_rect.y + 6 + i*36, self.actions_rect.width - 12, 30)
            pygame.draw.rect(self.screen, (60,60,60), r, border_radius=6)
            t = self.font_sm.render(lab, True, (240,240,240))
            self.screen.blit(t, (r.x + 8, r.y + 6))

    # ---------------- Event handling ----------------
    def handle_mouse_down(self, event):
        mx, my = event.pos
        if event.button != 1:
            return

        # ---------------- Control bar buttons ----------------
        for btn in self.buttons_data:
            if btn["rect"].collidepoint((mx, my)):
                btn["action"]()
                return

        # ---------------- Actions panel clicks ----------------
        if self.actions_open and self.actions_rect.collidepoint((mx, my)):
            rel_y = my - (self.actions_rect.y + 6)
            idx = rel_y // 36
            if idx == 0:
                self.run_quick_action("add_fav")
            elif idx == 1:
                self.run_quick_action("archive")
            elif idx == 2:
                self.run_quick_action("clear_history")
            return

        # ---------------- Sidebar clicks ----------------
        if self.sidebar_x <= mx <= self.sidebar_x + self.sidebar_w:
            sx = int(self.sidebar_x)
            # tabs
            tab_h = 28
            tab_w = self.sidebar_w // 3
            if 30 <= my <= 30 + tab_h:
                i = (mx - sx) // tab_w
                if i == 0:
                    self.sidebar_tab = "favourites"
                elif i == 1:
                    self.sidebar_tab = "history"
                else:
                    self.sidebar_tab = "archives"
                return

            # list items
            if hasattr(self, "_sidebar_items_cache"):
                for it in self._sidebar_items_cache:
                    tr = it.get("_tile_rect")
                    xb = it.get("_xbtn_rect")
                    if tr and tr.collidepoint((mx, my)):
                        meta = it["meta"]
                        if self.sidebar_tab == "favourites":
                            self.renderer.load_query_or_url(meta["url"])
                            self.add_history(meta["url"])
                        elif self.sidebar_tab == "history":
                            self.renderer.load_query_or_url(meta["url"])
                            self.add_history(meta["url"])
                        else:
                            name = meta.get("name")
                            if name:
                                self.open_archive(name)
                        self.toggle_sidebar()
                        return
                    if xb and xb.collidepoint((mx, my)):
                        meta = it["meta"]
                        if self.sidebar_tab == "favourites":
                            self.remove_favourite(meta["url"])
                        elif self.sidebar_tab == "history":
                            self.history = [h for h in self.history if not (h["url"]==meta["url"] and h["ts"]==meta["ts"])]
                            save_json(META_HISTORY, self.history)
                        else:
                            name = meta.get("name")
                            if name and name in self.arch_index:
                                arch_path = os.path.dirname(self.arch_index[name]["path"])
                                try:
                                    for root, dirs, files in os.walk(arch_path, topdown=False):
                                        for f in files:
                                            os.remove(os.path.join(root, f))
                                        for d in dirs:
                                            os.rmdir(os.path.join(root, d))
                                    os.rmdir(arch_path)
                                except Exception:
                                    pass
                                del self.arch_index[name]
                                save_json(META_ARCH_INDEX, self.arch_index)
                        return
            return

        # ---------------- Content area clicks ----------------
        if my > self.content_top:
            # check renderer buttons (quick search buttons)
            if hasattr(self.renderer, "buttons") and self.renderer.buttons:
                for r, label, callback in self.renderer.buttons:
                    if r.collidepoint((mx, my)):
                        callback()
                        self.renderer.buttons = []  # hide after click
                        return

            # check content links
            href = self.renderer.content_click((mx, my), offset_y=self.content_top)
            if href:
                if href.startswith("duckduckgo://") or href.startswith("duckduckgo_search://"):
                    q = href.split("://",1)[1]
                    self.renderer.load_duckduckgo_search(q)
                    self.add_history(q)
                elif href.startswith("loremflickr://") or href.startswith("https://loremflickr.com"):
                    self.renderer.load_html_page(href)
                    self.add_history(href)
                else:
                    self.renderer.load_query_or_url(href)
                    self.add_history(href)
            else:
                # start drag scroll
                self.dragging = True
                self.last_y = my

    def handle_mouse_up(self, event):
        if event.button != 1:
            return
        self.dragging = False
        self.sidebar_dragging = False

    def handle_mouse_motion(self, event):
        mx,my = event.pos
        if self.dragging:
            dy = my - self.last_y
            self.renderer.scroll_y += dy
            self.renderer.scroll_y = min(0, self.renderer.scroll_y)
            self.last_y = my
        if self.sidebar_dragging:
            dy = my - self.sidebar_last_y
            self.sidebar_scroll += dy
            self.sidebar_scroll = min(0, self.sidebar_scroll)
            self.sidebar_last_y = my

    # ---------------- Main Loop ----------------
    def run(self):
        last = time.time()
        while True:
            now = time.time()
            dt = now - last
            last = now
            for ev in pygame.event.get():
                # let topbar handle event first (so pull-down works)
                try:
                    self.topbar.handle_event(ev)
                except Exception:
                    pass

                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        # if click inside sidebar region start dragging list
                        if self.sidebar_x <= ev.pos[0] <= self.sidebar_x + self.sidebar_w:
                            self.sidebar_dragging = True
                            self.sidebar_last_y = ev.pos[1]
                        self.handle_mouse_down(ev)
                elif ev.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(ev)
                elif ev.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(ev)
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if ev.key == pygame.K_k:
                        # keyboard open
                        out = run_keyboard()
                        if out:
                            self.renderer.load_query_or_url(out)
                            self.add_history(out)
                    if ev.key == pygame.K_f:
                        # quick add favourite
                        t = self.renderer.current_title or self.renderer.current_url or "Untitled"
                        u = self.renderer.current_url or ""
                        if u:
                            self.add_favourite(t, u)
                            self.toast.show("Added to favourites")

            # update topbar (if it provides update)
            try:
                self.topbar.update()
            except Exception:
                pass

            # draw background content first (so it's behind UI)
            self.screen.fill((20,20,20))
            self.renderer.draw(self.screen, offset_y=self.content_top)

            # draw control bar & topbar and overlays (topbar last)
            self.draw_controls()
            # draw sidebar overlay (animated)
            self.draw_sidebar(dt)

            # draw actions
            self.draw_actions_panel()

            # draw topbar last so it visually sits on top (pull-down still works)
            try:
                self.topbar.draw(self.screen)
            except Exception:
                pass

            # draw toast
            self.toast.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)

            # small housekeeping: if sidebar_open toggled, set target x
            self.sidebar_target = 0 if self.sidebar_open else -self.sidebar_w

            # persist occasionally (ensure saved state)
            # (This keeps the JSON files up-to-date)
            # Not too frequent to avoid disk churn
            try:
                save_json(META_FAV, self.favourites)
                save_json(META_HISTORY, self.history)
                save_json(META_ARCH_INDEX, self.arch_index)
            except Exception:
                pass


# Entry
def main():
    app = JexBrowserFinal(480, 320)
    app.run()


if __name__ == "__main__":
    main()
