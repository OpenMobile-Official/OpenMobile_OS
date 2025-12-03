import pygame, sys, requests, threading, re, time, io
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
from PIL import Image

class RenderLightweight:
    """Mini Browser Lite + Optional Image Mode
       Designed for Raspberry Pi or low-power devices."""

    def __init__(self, width=480, height=320):
        pygame.init()
        pygame.display.set_caption("Mini Browser Lite + Image Mode")

        # --- Display setup ---
        self.W, self.H = width, height
        self.screen = pygame.display.set_mode((self.W, self.H))
        self.clock = pygame.time.Clock()

        # --- Fonts & Colors ---
        self.FONT = pygame.font.Font(None, 20)
        self.TITLE_FONT = pygame.font.Font(None, 22)
        self.WHITE = (240, 240, 240)
        self.BLUE = (100, 150, 255)
        self.GRAY = (40, 40, 40)
        self.BG = (25, 25, 25)
        self.LOADING_COLOR = (200, 200, 50)

        # --- Global State ---
        self.scroll_y = 0
        self.elements = []  # (surf, href, rect)
        self.current_url = ""
        self.search_text = ""
        self.history = []
        self.loading = False
        self.image_mode = False  # Toggle images ON/OFF
        self.dragging = False
        self.last_y = 0
        self.running = True

        self.HEADERS = {
            "User-Agent": "Mozilla/5.0 (RaspberryPi; Linux) MiniBrowser/1.1"
        }

    # ------------------------------------------------
    # Utility
    # ------------------------------------------------
    def set_loading(self, v=True):
        self.loading = v

    def is_url(self, text):
        return re.match(r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$', text)

    def fetch_image(self, url, max_width=None, max_height=120):
        """Lightweight image fetcher with scaling."""
        max_width = max_width or self.W - 20
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=5, stream=True)
            img_data = resp.content
            im = Image.open(io.BytesIO(img_data)).convert("RGB")
            im.thumbnail((max_width, max_height))
            surf = pygame.image.fromstring(im.tobytes(), im.size, im.mode)
            return surf
        except Exception:
            return None

    # ------------------------------------------------
    # Page Loaders
    # ------------------------------------------------
    def load_duckduckgo_search(self, query):
        def task():
            self.set_loading(True)
            self.scroll_y = 0
            self.elements.clear()
            self.current_url = f"duckduckgo://{query}"

            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=10).json()
            except Exception as e:
                self.elements.append((self.FONT.render(f"❌ Error: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return

            y = 40
            for topic in resp.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    title = topic["Text"]
                    link = topic["FirstURL"]
                    surf = self.FONT.render(title, True, self.BLUE)
                    rect = surf.get_rect(topleft=(10, y))
                    self.elements.append((surf, link, rect))
                    y += rect.height + 6

            if not self.elements:
                self.elements.append((self.FONT.render("No results.", True, self.WHITE), None, pygame.Rect(10,40,0,0)))

            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_html_page(self, url):
        def task():
            self.set_loading(True)
            if self.current_url:
                self.history.append(self.current_url)
            self.scroll_y = 0
            self.elements.clear()
            self.current_url = url
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                self.elements.append((self.FONT.render(f"❌ Error loading: {e}", True, (255,80,80)), None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return

            y = 40
            for tag in soup.find_all(["h1","h2","p","a","li","img"]):
                if tag.name == "img" and self.image_mode:
                    src = tag.get("src")
                    if src:
                        full = urljoin(url, src)
                        surf = self.fetch_image(full)
                        if surf:
                            rect = surf.get_rect(topleft=(10, y))
                            self.elements.append((surf, None, rect))
                            y += rect.height + 5
                    continue

                text = tag.get_text(strip=True)
                if not text:
                    continue
                href = tag.get("href") if tag.name == "a" else None
                if href:
                    href = urljoin(url, href)
                color = self.BLUE if tag.name == "a" else self.WHITE
                surf = self.FONT.render(text[:100], True, color)
                rect = surf.get_rect(topleft=(10, y))
                self.elements.append((surf, href, rect))
                y += rect.height + 4

            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    # ------------------------------------------------
    # Draw
    # ------------------------------------------------
    def draw(self):
        self.screen.fill(self.BG)
        for surf, href, rect in self.elements:
            self.screen.blit(surf, rect.move(0, self.scroll_y))
        pygame.draw.rect(self.screen, self.GRAY, (0,0,self.W,30))
        hint = self.search_text or "Type URL or search + Enter"
        txt = self.FONT.render(hint, True, self.WHITE)
        self.screen.blit(txt, (5,5))
        mode_text = "[Images: ON]" if self.image_mode else "[Images: OFF]"
        mode_surf = self.FONT.render(mode_text, True, (180,180,180))
        self.screen.blit(mode_surf, (self.W - 110, 5))
        if self.loading:
            load_surf = self.FONT.render("Loading...", True, self.LOADING_COLOR)
            self.screen.blit(load_surf, (self.W - 220, 5))

    # ------------------------------------------------
    # Main Loop
    # ------------------------------------------------
    def run(self):
        """Launch the interactive render loop."""
        while self.running:
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.pos[1] > 30:
                        self.dragging = True
                        self.last_y = event.pos[1]
                    for surf, href, rect in self.elements:
                        if href and rect.move(0, self.scroll_y).collidepoint(event.pos):
                            self.load_html_page(href)

                elif event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging:
                        dy = event.pos[1] - self.last_y
                        self.scroll_y += dy
                        self.scroll_y = min(0, self.scroll_y)
                        self.last_y = event.pos[1]

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        text = self.search_text.strip()
                        if not text:
                            continue
                        if self.is_url(text):
                            if not text.startswith("http"):
                                text = "http://" + text
                            self.load_html_page(text)
                        else:
                            self.load_duckduckgo_search(text)
                        self.search_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.search_text = self.search_text[:-1]
                    elif event.key == pygame.K_i:
                        self.image_mode = not self.image_mode  # toggle image mode
                    else:
                        ch = event.unicode
                        if ch.isprintable():
                            self.search_text += ch

        pygame.quit()
        sys.exit()
