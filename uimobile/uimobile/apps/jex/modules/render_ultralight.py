import pygame, sys, requests, re, threading
from html import unescape

class RenderUltraLight:
    """Ultra-lightweight Pygame web/text renderer
       - Type URL or text + press ENTER
       - Scroll: click + drag
       - No images, no heavy parsing, no dependencies beyond pygame+requests
       Ideal for Raspberry Pi Zero or embedded systems."""

    def __init__(self, width=480, height=320):
        pygame.init()
        pygame.display.set_caption("Render UltraLight")

        # --- Window ---
        self.W, self.H = width, height
        self.screen = pygame.display.set_mode((self.W, self.H))
        self.clock = pygame.time.Clock()

        # --- Fonts & Colors ---
        self.FONT = pygame.font.Font(None, 18)
        self.WHITE = (240, 240, 240)
        self.BLUE = (120, 170, 255)
        self.GRAY = (40, 40, 40)
        self.BG = (20, 20, 20)
        self.LOAD_COLOR = (220, 200, 60)

        # --- State ---
        self.scroll_y = 0
        self.dragging = False
        self.last_y = 0
        self.search_text = ""
        self.elements = []  # (surf, href, rect)
        self.loading = False
        self.running = True

        self.HEADERS = {"User-Agent": "RenderUltraLight/1.0"}

    # ------------------------------------------------
    # Helpers
    # ------------------------------------------------
    def set_loading(self, v=True):
        self.loading = v

    def is_url(self, text):
        return re.match(r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}', text)

    def strip_html(self, html):
        """Basic HTML to plaintext conversion (no BeautifulSoup)."""
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.S)
        text = re.sub(r'<[^>]+>', '', text)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    # ------------------------------------------------
    # Page loader
    # ------------------------------------------------
    def load_page(self, url_or_query):
        def task():
            self.set_loading(True)
            self.elements.clear()
            y = 40
            text = ""

            try:
                if self.is_url(url_or_query):
                    u = url_or_query
                    if not u.startswith("http"):
                        u = "http://" + u
                    resp = requests.get(u, headers=self.HEADERS, timeout=8)
                    resp.raise_for_status()
                    text = self.strip_html(resp.text)
                else:
                    # DuckDuckGo search
                    q = re.sub(r'\s+', '+', url_or_query)
                    resp = requests.get(f"https://duckduckgo.com/html/?q={q}",
                                        headers=self.HEADERS, timeout=8)
                    text = self.strip_html(resp.text)
            except Exception as e:
                text = f"Error loading: {e}"

            # Word wrap and surface generation
            for line in self.wrap_text(text, self.FONT, self.W - 20):
                surf = self.FONT.render(line, True, self.WHITE)
                rect = surf.get_rect(topleft=(10, y))
                self.elements.append((surf, None, rect))
                y += rect.height + 2
                if y > 3000:  # limit memory
                    break

            self.set_loading(False)

        threading.Thread(target=task, daemon=True).start()

    def wrap_text(self, text, font, width):
        """Simple word-wrap generator."""
        words = text.split()
        line = ""
        for w in words:
            if font.size(line + w + " ")[0] > width:
                yield line
                line = w + " "
            else:
                line += w + " "
        if line:
            yield line

    # ------------------------------------------------
    # Drawing
    # ------------------------------------------------
    def draw(self):
        self.screen.fill(self.BG)
        for surf, _, rect in self.elements:
            self.screen.blit(surf, rect.move(0, self.scroll_y))
        pygame.draw.rect(self.screen, self.GRAY, (0, 0, self.W, 25))
        hint = self.search_text or "Type URL or text + Enter"
        txt = self.FONT.render(hint, True, self.WHITE)
        self.screen.blit(txt, (5, 5))
        if self.loading:
            load = self.FONT.render("Loading...", True, self.LOAD_COLOR)
            self.screen.blit(load, (self.W - 110, 5))

    # ------------------------------------------------
    # Main Loop
    # ------------------------------------------------
    def run(self):
        while self.running:
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False

                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if e.pos[1] > 25:
                        self.dragging = True
                        self.last_y = e.pos[1]

                elif e.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False

                elif e.type == pygame.MOUSEMOTION and self.dragging:
                    dy = e.pos[1] - self.last_y
                    self.scroll_y += dy
                    self.scroll_y = min(0, self.scroll_y)
                    self.last_y = e.pos[1]

                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        t = self.search_text.strip()
                        if t:
                            self.load_page(t)
                        self.search_text = ""
                    elif e.key == pygame.K_BACKSPACE:
                        self.search_text = self.search_text[:-1]
                    else:
                        ch = e.unicode
                        if ch.isprintable():
                            self.search_text += ch

        pygame.quit()
        sys.exit()
