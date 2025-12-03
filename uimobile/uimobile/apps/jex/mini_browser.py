"""
jex_browser_full.py

Jex — Pygame browser with:
 - Single-window renderer (Full / Lite / Ultra)
 - Top bar integration (TopBarManager)
 - On-screen keyboard integration (run_keyboard)
 - Favourites, History, Archive (persisted to JSON under browser_data/)
 - Archive saves HTML + images (stored per-archive)
 - Touch-friendly sliding overlay sidebar (left)
"""

import os
import sys
import json
import threading
import time
import io
import re
import random
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image
import pygame

# --- Local UI/keyboard modules (your template) ---
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

# ---------------------------
# Utility / Data directories
# ---------------------------
DATA_DIR = "browser_data"
ARCH_DIR = os.path.join(DATA_DIR, "archives")
META_FAV = os.path.join(DATA_DIR, "favourites.json")
META_HISTORY = os.path.join(DATA_DIR, "history.json")
META_ARCH_INDEX = os.path.join(ARCH_DIR, "index.json")

for d in (DATA_DIR, ARCH_DIR):
    os.makedirs(d, exist_ok=True)

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
        print("Error saving", path, e)

# ensure meta files exist
if not os.path.exists(META_FAV):
    save_json(META_FAV, [])
if not os.path.exists(META_HISTORY):
    save_json(META_HISTORY, [])
if not os.path.exists(META_ARCH_INDEX):
    save_json(META_ARCH_INDEX, {})

# ---------------------------
# SimpleRenderer (embedded)
# ---------------------------
class SimpleRenderer:
    def __init__(self, width, height, mode="Full"):
        self.W = width
        # content area height will be provided by caller; renderer will assume content_top offset when drawing
        self.mode = mode  # Full / Lite / Ultra
        self.scroll_y = 0
        self.elements = []
        self.current_url = ""
        self.current_title = ""
        self.loading = False
        self.headers = {"User-Agent":"JexBrowser/1.0"}
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
        # If src is a file path (starts with file:// or exists locally), load locally else requests
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

    # Load HTML from remote URL
    def load_html_page(self, url):
        def task():
            self.set_loading(True)
            self.current_url = url
            self.elements.clear()
            self.scroll_y = 0
            try:
                resp = requests.get(url, headers=self.headers, timeout=12)
                resp.raise_for_status()
                html = resp.text
            except Exception as e:
                t = self.FONT_TITLE.render(f"Error: {e}", True, (255,80,80))
                self.elements.append((t, None, pygame.Rect(10,40,t.get_width(),t.get_height())))
                self.set_loading(False)
                return
            self._parse_and_build(html, base_url=url)
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    # Load HTML from a file (local archived html)
    def load_html_from_file(self, filepath):
        def task():
            self.set_loading(True)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    html = f.read()
                base = "file://" + os.path.dirname(os.path.abspath(filepath)) + "/"
            except Exception as e:
                t = self.FONT_TITLE.render(f"Error reading archive: {e}", True, (255,80,80))
                self.elements.append((t, None, pygame.Rect(10,40,t.get_width(),t.get_height())))
                self.set_loading(False)
                return
            self.current_url = filepath
            self.elements.clear()
            self.scroll_y = 0
            self._parse_and_build(html, base_url=base)
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_duckduckgo_search(self, query):
        def task():
            self.set_loading(True)
            self.elements.clear()
            self.scroll_y = 0
            self.current_url = f"duckduckgo://{query}"
            url = f"https://api.duckduckgo.com/?q={requests.utils.requote_uri(query)}&format=json&no_html=1&skip_disambig=1"
            try:
                resp = requests.get(url, headers=self.headers, timeout=8).json()
            except Exception as e:
                t = self.FONT_TITLE.render("Search error", True, (255,80,80))
                self.elements.append((t, None, pygame.Rect(10,40,t.get_width(),t.get_height())))
                self.set_loading(False)
                return
            y = 40
            if resp.get("AbstractText"):
                title = resp.get("Heading","Result")
                desc = resp.get("AbstractText","")
                ts = self.FONT_TITLE.render(title[:60], True, (240,240,240))
                ds = self.FONT_DESC.render(desc[:120], True, (220,220,220))
                self.elements.append((ts, None, pygame.Rect(10,y,ts.get_width(),ts.get_height())))
                y += ts.get_height() + 4
                self.elements.append((ds, None, pygame.Rect(10,y,ds.get_width(),ds.get_height())))
                y += ds.get_height() + 8
            for tpic in resp.get("RelatedTopics", []):
                if "Text" in tpic and "FirstURL" in tpic:
                    text = tpic["Text"]
                    link = tpic["FirstURL"]
                    if " - " in text:
                        title_text, desc_text = text.split(" - ",1)
                    else:
                        title_text, desc_text = text, ""
                    ts = self.FONT_TITLE.render(title_text[:60], True, (100,150,255))
                    ds = self.FONT_DESC.render(desc_text[:120], True, (220,220,220))
                    self.elements.append((ts, link, pygame.Rect(10,y,ts.get_width(),ts.get_height())))
                    y += ts.get_height() + 2
                    self.elements.append((ds, None, pygame.Rect(10,y,ds.get_width(),ds.get_height())))
                    y += ds.get_height() + 8
            if not self.elements:
                self.elements.append((self.FONT_TITLE.render("No results", True, (220,220,220)), None, pygame.Rect(10,40,0,0)))
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    # load query or url intelligently
    def load_query_or_url(self, text):
        if self.is_url(text):
            url = text if text.startswith("http") else ("http://" + text)
            self.load_html_page(url)
        else:
            self.load_duckduckgo_search(text)

    # internal parse + build surfaces list
    def _parse_and_build(self, html, base_url=None):
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        self.current_title = title_tag.get_text(strip=True) if title_tag else base_url or ""
        y = 40
        include_images = (self.mode in ("Full","Lite"))
        for tag in soup.find_all(["h1","h2","p","li","a","img","br","hr","strong","em"]):
            if tag.name in ("br","hr"):
                y += 8
                continue
            if tag.name == "img" and include_images:
                src = tag.get("src")
                if not src:
                    continue
                full = urljoin(base_url, src) if base_url else src
                surf = self.fetch_image_surface(full, max_w=self.W-20, max_h=self.IMAGE_MAX_H)
                if surf:
                    rect = surf.get_rect(topleft=(10,y))
                    self.elements.append((surf, full, rect))
                    y += rect.height + 6
                continue
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            font = self.FONT_TITLE if tag.name.startswith("h") else self.FONT_DESC
            color = (100,150,255) if tag.name == "a" else (240,240,240)
            href = None
            if tag.name == "a" and tag.get("href"):
                href = urljoin(base_url, tag["href"]) if base_url else tag["href"]
            # naive wrap
            words = text.split()
            line = ""
            for w in words:
                test = font.render(line + w + " ", True, color)
                if test.get_width() > self.W-20:
                    surf = font.render(line.strip(), True, color)
                    rect = surf.get_rect(topleft=(10,y))
                    self.elements.append((surf, href, rect))
                    y += rect.height + 4
                    line = w + " "
                else:
                    line += w + " "
            if line:
                surf = font.render(line.strip(), True, color)
                rect = surf.get_rect(topleft=(10,y))
                self.elements.append((surf, href, rect))
                y += rect.height + 6
            if y > 5000:
                break

    def draw(self, surface, offset_y):
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
        if self.loading:
            s = self.FONT_DESC.render("Loading...", True, (200,180,50))
            surface.blit(s, (surface.get_width() - 110, offset_y + 4))

    def content_click(self, pos, offset_y):
        x, y = pos
        local_y = y - offset_y - self.scroll_y
        for surf, href, rect in self.elements:
            if rect.collidepoint(x, local_y):
                return href
        return None

# ---------------------------
# Browser App with Sidebar
# ---------------------------
class JexBrowser:
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

        # controls
        self.btns = {
            "engine": pygame.Rect(8, 36, 90, 28),
            "search": pygame.Rect(105, 36, 90, 28),
            "home": pygame.Rect(202, 36, 60, 28),
            "fav": pygame.Rect(268, 36, 60, 28),
            "hist": pygame.Rect(336, 36, 60, 28),
            "arch": pygame.Rect(404, 36, 60, 28),
        }

        # renderer
        self.renderer = SimpleRenderer(self.W, self.H, mode="Full")
        self.active_engine = "Full"

        # layout
        self.content_top = 90  # top area height reserved for topbar+controls

        # interactions
        self.running = True
        self.dragging = False
        self.last_y = 0

        # sidebar sliding overlay
        self.sidebar_open = False
        self.sidebar_width = 260
        self.sidebar_x = -self.sidebar_width  # start hidden
        self.sidebar_target_x = -self.sidebar_width
        self.sidebar_speed = 600  # px per second
        self.sidebar_tab = "favourites"  # or "history" or "archives"
        self.sidebar_scroll = 0
        self.sidebar_dragging = False
        self.sidebar_last_y = 0

        # persistence
        self.favourites = load_json(META_FAV, [])
        self.history = load_json(META_HISTORY, [])
        self.arch_index = load_json(META_ARCH_INDEX, {})

    # ---------------------------
    # persistence helpers
    # ---------------------------
    def add_history(self, url):
        ts = time.time()
        self.history.insert(0, {"ts": ts, "url": url})
        # keep limited size
        self.history = self.history[:200]
        save_json(META_HISTORY, self.history)

    def add_favourite(self, title, url):
        self.favourites.insert(0, {"title": title, "url": url, "ts": time.time()})
        # dedupe by url
        seen = []
        new = []
        for f in self.favourites:
            if f["url"] in seen:
                continue
            seen.append(f["url"])
            new.append(f)
        self.favourites = new[:200]
        save_json(META_FAV, self.favourites)

    def remove_favourite(self, url):
        self.favourites = [f for f in self.favourites if f["url"] != url]
        save_json(META_FAV, self.favourites)

    # ---------------------------
    # ARCHIVE: save html + images locally
    # ---------------------------
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

        # create unique archive name
        if not name:
            parsed = urlparse(url)
            safe = (parsed.netloc + parsed.path).strip("/").replace("/", "_") or "page"
            name = f"{safe}_{int(time.time())}"
        arch_path = os.path.join(ARCH_DIR, name)
        os.makedirs(arch_path, exist_ok=True)
        assets_dir = os.path.join(arch_path, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        # parse html, download images and fix img src
        soup = BeautifulSoup(html, "html.parser")
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
                safe_path = os.path.join(assets_dir, fname)
                with open(safe_path, "wb") as f:
                    f.write(r.content)
                img["src"] = "assets/" + fname  # local relative path
            except Exception:
                # skip broken images
                continue

        # write modified html to local file
        local_html_path = os.path.join(arch_path, "index.html")
        with open(local_html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        # update index metadata
        self.arch_index[name] = {"name": name, "url": url, "path": local_html_path, "ts": time.time()}
        save_json(META_ARCH_INDEX, self.arch_index)
        return True, name

    def open_archive(self, name):
        if name not in self.arch_index:
            return False
        path = self.arch_index[name].get("path")
        if not path or not os.path.exists(path):
            return False
        self.renderer.load_html_from_file(path)
        self.add_history("archive://" + name)
        return True

    # ---------------------------
    # UI interactions
    # ---------------------------
    def toggle_sidebar(self, tab=None):
        self.sidebar_open = not self.sidebar_open
        if tab:
            self.sidebar_tab = tab
        self.sidebar_target_x = 0 if self.sidebar_open else -self.sidebar_width

    def set_engine(self, next_mode=None):
        if next_mode:
            self.active_engine = next_mode
        else:
            # cycle
            if self.active_engine == "Full":
                self.active_engine = "Lite"
            elif self.active_engine == "Lite":
                self.active_engine = "Ultra"
            else:
                self.active_engine = "Full"
        self.renderer.set_mode(self.active_engine)

    def open_keyboard_and_load(self):
        out = run_keyboard()
        if out:
            self.renderer.load_query_or_url(out)
            self.add_history(out)

    def go_home(self):
        self.renderer.clear()

    def add_current_to_favs(self):
        t = self.renderer.current_title or self.renderer.current_url or "Untitled"
        u = self.renderer.current_url or ""
        if u:
            self.add_favourite(t, u)

    # ---------------------------
    # drawing helpers
    # ---------------------------
    def draw_controls(self):
        pygame.draw.rect(self.screen, (38,38,38), (0,30,self.W,60))
        mx,my = pygame.mouse.get_pos()
        for k, r in self.btns.items():
            hover = r.collidepoint((mx,my))
            color = (100,100,100) if hover else (70,70,70)
            pygame.draw.rect(self.screen, color, r, border_radius=6)
            label = {
                "engine":"Engine",
                "search":"Search",
                "home":"Home",
                "fav":"Favs",
                "hist":"History",
                "arch":"Archive"
            }[k]
            txt = self.font_sm.render(label, True, (240,240,240))
            self.screen.blit(txt, (r.x+8, r.y+6))
        mode_txt = self.font_sm.render(f"Mode: {self.active_engine}", True, (100,150,255))
        self.screen.blit(mode_txt, (self.W-110, 40))

    def draw_sidebar(self, dt):
        # animate sidebar_x toward target
        if self.sidebar_x < self.sidebar_target_x:
            self.sidebar_x = min(self.sidebar_target_x, self.sidebar_x + self.sidebar_speed * dt)
        elif self.sidebar_x > self.sidebar_target_x:
            self.sidebar_x = max(self.sidebar_target_x, self.sidebar_x - self.sidebar_speed * dt)

        sx = int(self.sidebar_x)
        # panel background
        panel = pygame.Rect(sx, 0, self.sidebar_width, self.H)
        pygame.draw.rect(self.screen, (28,28,28), panel)
        # tabs across top
        tab_h = 28
        tab_w = self.sidebar_width // 3
        tabs = [("FAV","favourites"),("HIS","history"),("ARC","archives")]
        for i, (label, key) in enumerate(tabs):
            rx = sx + i*tab_w
            r = pygame.Rect(rx, 30, tab_w, tab_h)
            active = (self.sidebar_tab == key)
            pygame.draw.rect(self.screen, (60,60,60) if active else (48,48,48), r)
            txt = self.font_sm.render(label, True, (240,240,240))
            self.screen.blit(txt, (r.x + 8, r.y + 6))

        # content list area
        list_top = 30 + tab_h + 6
        list_h = self.H - list_top - 10
        list_rect = pygame.Rect(sx+6, list_top, self.sidebar_width-12, list_h)
        pygame.draw.rect(self.screen, (22,22,22), list_rect)

        # choose items to show
        items = []
        if self.sidebar_tab == "favourites":
            items = [{"label": f["title"], "meta": f} for f in self.favourites]
        elif self.sidebar_tab == "history":
            items = [{"label": h["url"], "meta": h} for h in self.history]
        else:
            # archives: from index dict
            items = [{"label": v.get("name") or v.get("url"), "meta": v} for k,v in self.arch_index.items()]

        # draw item tiles
        y = list_top + 6 + int(self.sidebar_scroll)
        tile_h = 38
        mx,my = pygame.mouse.get_pos()
        for idx, it in enumerate(items):
            tile = pygame.Rect(sx+8, y, self.sidebar_width-24, tile_h)
            # skip if tile out of view
            if tile.bottom < list_top or tile.top > list_top + list_h:
                y += tile_h + 6
                continue
            pygame.draw.rect(self.screen, (44,44,44), tile, border_radius=6)
            label = it["label"][:38]
            txt = self.font_sm.render(label, True, (230,230,230))
            self.screen.blit(txt, (tile.x+6, tile.y+6))
            # small delete "X" area on right
            xbtn = pygame.Rect(tile.right-28, tile.y+6, 20, 20)
            pygame.draw.rect(self.screen, (80,80,80), xbtn, border_radius=4)
            x_txt = self.font_sm.render("X", True, (220,220,220))
            self.screen.blit(x_txt, (xbtn.x+5, xbtn.y+1))
            # store rect for hit testing by index
            it["_tile_rect"] = tile
            it["_xbtn_rect"] = xbtn
            y += tile_h + 6

        # save the last items list for click handling
        self._sidebar_items_cache = items

    # ---------------------------
    # event handling
    # ---------------------------
    def handle_mouse_down(self, event):
        mx,my = event.pos
        if event.button != 1:
            return
        # check control buttons
        for k, r in self.btns.items():
            if r.collidepoint((mx,my)):
                if k == "engine":
                    self.set_engine()
                elif k == "search":
                    self.open_keyboard_and_load()
                elif k == "home":
                    self.go_home()
                elif k == "fav":
                    self.toggle_sidebar("favourites")
                elif k == "hist":
                    self.toggle_sidebar("history")
                elif k == "arch":
                    self.toggle_sidebar("archives")
                return

        # click inside sidebar?
        if self.sidebar_x <= mx <= self.sidebar_x + self.sidebar_width:
            # check tabs
            sx = int(self.sidebar_x)
            tab_h = 28
            tab_w = self.sidebar_width // 3
            if 30 <= my <= 30 + tab_h:
                i = (mx - sx) // tab_w
                if i == 0:
                    self.sidebar_tab = "favourites"
                elif i == 1:
                    self.sidebar_tab = "history"
                else:
                    self.sidebar_tab = "archives"
                return
            # check list items
            if hasattr(self, "_sidebar_items_cache"):
                for it in self._sidebar_items_cache:
                    tr = it.get("_tile_rect")
                    xb = it.get("_xbtn_rect")
                    if tr and tr.collidepoint((mx,my)):
                        # open item
                        meta = it["meta"]
                        if self.sidebar_tab == "favourites":
                            url = meta["url"]
                            self.renderer.load_query_or_url(url)
                            self.add_history(url)
                        elif self.sidebar_tab == "history":
                            url = meta["url"]
                            self.renderer.load_query_or_url(url)
                        else:
                            name = meta.get("name")
                            if name:
                                self.open_archive(name)
                        # close sidebar
                        self.toggle_sidebar()
                        return
                    if xb and xb.collidepoint((mx,my)):
                        # delete item
                        meta = it["meta"]
                        if self.sidebar_tab == "favourites":
                            self.remove_favourite(meta["url"])
                            # refresh
                            self.favourites = load_json(META_FAV, [])
                        elif self.sidebar_tab == "history":
                            # remove this history entry by ts+url
                            self.history = [h for h in self.history if not (h["url"]==meta["url"] and h["ts"]==meta["ts"])]
                            save_json(META_HISTORY, self.history)
                        else:
                            name = meta.get("name")
                            if name and name in self.arch_index:
                                # delete archive folder
                                arch_path = os.path.dirname(self.arch_index[name]["path"])
                                try:
                                    # remove files
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

        # click content area: links or start drag
        if my > self.content_top:
            href = self.renderer.content_click((mx,my), offset_y=self.content_top)
            if href:
                # follow
                if href.startswith("duckduckgo://"):
                    q = href.split("://",1)[1]
                    self.renderer.load_duckduckgo_search(q)
                    self.add_history(q)
                else:
                    self.renderer.load_query_or_url(href)
                    self.add_history(href)
            else:
                # start dragging to scroll content
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
            self.renderer.scroll_y = min(0, self.renderer.scroll_y)  # don't scroll past top
            self.last_y = my
        if self.sidebar_dragging:
            dy = my - self.sidebar_last_y
            self.sidebar_scroll += dy
            # clamp scroll
            self.sidebar_scroll = min(0, self.sidebar_scroll)
            self.sidebar_last_y = my

    # ---------------------------
    # Main loop
    # ---------------------------
    def run(self):
        last = time.time()
        while self.running:
            now = time.time()
            dt = now - last
            last = now
            self.screen.fill((24,24,24))

            # draw controls & renderer content
            try:
                self.topbar.update()
            except Exception:
                pass

            self.draw_controls()
            self.renderer.draw(self.screen, offset_y=self.content_top)

            # draw sidebar overlay (animated)
            self.draw_sidebar(dt)

            # draw topbar last (always on top)
            try:
                self.topbar.draw(self.screen)
            except Exception:
                pass

            pygame.display.flip()
            self.clock.tick(60)

            for event in pygame.event.get():
                # topbar should get events first
                try:
                    self.topbar.handle_event(event)
                except Exception:
                    pass

                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # allow dragging within sidebar list
                        if self.sidebar_x <= event.pos[0] <= self.sidebar_x + self.sidebar_width:
                            self.sidebar_dragging = True
                            self.sidebar_last_y = event.pos[1]
                        self.handle_mouse_down(event)

                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event)

                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if event.key == pygame.K_k:
                        self.open_keyboard_and_load()
                    if event.key == pygame.K_f:
                        self.add_current_to_favs()
                    if event.key == pygame.K_a:
                        # quick archive prompt
                        ok, name = self.archive_current()
                        print("Archive:", ok, name)

        pygame.quit()
        sys.exit()

# ---------------------------
# Entry point
# ---------------------------
def main():
    app = JexBrowser(480,320)
    app.run()

if __name__ == "__main__":
    main()
