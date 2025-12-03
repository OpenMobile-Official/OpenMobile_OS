import pygame, sys, requests, io, threading, re, time, random
from bs4 import BeautifulSoup
from PIL import Image
from urllib.parse import urljoin, quote_plus

class render:
    def __init__(self, width=480, height=320):
        pygame.init()
        pygame.display.set_caption("Enhanced Mini Browser")

        self.W, self.H = width, height
        self.screen = pygame.display.set_mode((self.W, self.H))

        # Fonts & colors
        self.TITLE_FONT = pygame.font.Font(None, 22)
        self.BIG_FONT = pygame.font.Font(None, 26)
        self.DESC_FONT = pygame.font.Font(None, 18)
        self.WHITE = (240,240,240)
        self.BLUE = (100,150,255)
        self.GRAY = (40,40,40)
        self.BG = (25,25,25)
        self.LOADING_COLOR = (200,200,50)
        self.BUTTON_COLOR = (60,60,60)
        self.BUTTON_HOVER = (80,80,80)

        # State
        self.scroll_y = 0
        self.elements = []  # (surf, desc_surf, href, rect)
        self.current_url = ""
        self.search_text = ""
        self.history = []
        self.loading = False
        self.buttons = []  # (rect, label, callback)
        self.button_timer = 0
        self.dragging = False
        self.last_y = 0

        self.HEADERS = {
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
    def set_loading(self, val=True):
        self.loading = val

    def is_url(self, text):
        pattern = r'^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$'
        return re.match(pattern, text)

    def fetch_image(self, url, max_width=None, max_height=100):
        max_width = max_width or self.W - 20
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10, allow_redirects=True)
            resp.raise_for_status()
            im = Image.open(io.BytesIO(resp.content)).convert("RGB")
            if im.width < 20 or im.height < 20:
                return None
            im.thumbnail((max_width, max_height))
            surf = pygame.image.fromstring(im.tobytes(), im.size, im.mode)
            return surf
        except:
            return None

    # --------------------------
    # Page loaders
    # --------------------------
    def load_duckduckgo_search(self, query):
        def task():
            self.set_loading(True)
            self.scroll_y = 0
            self.elements.clear()
            self.buttons.clear()
            self.current_url = f"duckduckgo_search://{query}"
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=10).json()
            except:
                self.elements.append((self.TITLE_FONT.render("❌ Error fetching search results", True, (255,80,80)), None, None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return

            y = 40
            if resp.get("AbstractText"):
                title_surf = self.TITLE_FONT.render(resp.get("Heading","DuckDuckGo Result"), True, self.WHITE)
                desc_surf = self.DESC_FONT.render(resp["AbstractText"], True, self.WHITE)
                rect = pygame.Rect(10,y,self.W-20,title_surf.get_height()+desc_surf.get_height()+5)
                self.elements.append((title_surf, desc_surf, resp.get("AbstractURL"), rect))
                y += title_surf.get_height() + desc_surf.get_height() + 10

            for topic in resp.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    text = topic["Text"]
                    url_link = topic["FirstURL"]
                    if " - " in text:
                        title_text, desc_text = text.split(" - ",1)
                    else:
                        title_text, desc_text = text, ""
                    title_surf = self.TITLE_FONT.render(title_text, True, self.BLUE)
                    desc_surf = self.DESC_FONT.render(desc_text, True, self.WHITE)
                    rect_height = title_surf.get_height() + desc_surf.get_height() + 5
                    rect = pygame.Rect(10,y,self.W-20,rect_height)
                    self.elements.append((title_surf, desc_surf, url_link, rect))
                    y += rect_height + 8
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_html_page(self, url):
        def task():
            self.set_loading(True)
            if self.current_url:
                self.history.append(self.current_url)
            self.scroll_y = 0
            self.elements.clear()
            self.buttons.clear()
            self.current_url = url
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
            except:
                self.elements.append((self.TITLE_FONT.render("❌ Error loading page", True, (255,80,80)), None, None, pygame.Rect(10,40,0,0)))
                self.set_loading(False)
                return

            y = 40
            for tag in soup.find_all(["h1","h2","h3","h4","h5","h6","p","li","a","img","br","b","i","u","hr","ul","ol"]):
                if tag.name=="br" or tag.name=="hr":
                    y += 10
                elif tag.name in ["b","i","u"]:
                    text = tag.get_text(strip=True)
                    if not text: continue
                    bold = tag.name=="b"
                    italic = tag.name=="i"
                    surf = pygame.font.SysFont(None,18,bold=bold,italic=italic).render(text, True, self.WHITE)
                    rect = surf.get_rect(topleft=(10,y))
                    self.elements.append((surf,None,None,rect))
                    y += rect.height + 2
                elif tag.name in ["ul","ol"]:
                    for li in tag.find_all("li"):
                        text = "• " + li.get_text(strip=True)
                        surf = self.DESC_FONT.render(text, True, self.WHITE)
                        rect = surf.get_rect(topleft=(20,y))
                        self.elements.append((surf,None,None,rect))
                        y += rect.height + 2
                elif tag.name=="img" and tag.get("src"):
                    src = urljoin(url, tag["src"])
                    surf = self.fetch_image(src)
                    if surf:
                        rect = surf.get_rect(topleft=(10,y))
                        self.elements.append((surf,None,None,rect))
                        y += rect.height + 5
                else:
                    text = tag.get_text(strip=True)
                    if not text: continue
                    font = self.BIG_FONT if tag.name.startswith("h") else self.DESC_FONT
                    color = self.BLUE if tag.name=="a" else self.WHITE
                    href = tag.get("href") if tag.name=="a" else None
                    if href: href = urljoin(url, href)
                    words = text.split()
                    line = ""
                    for w in words:
                        test = font.render(line + w + " ", True, color)
                        if test.get_width() > self.W-20:
                            surf = font.render(line, True, color)
                            rect = surf.get_rect(topleft=(10,y))
                            self.elements.append((surf,None,href,rect))
                            y += rect.height + 2
                            line = w + " "
                        else:
                            line += w + " "
                    if line:
                        surf = font.render(line, True, color)
                        rect = surf.get_rect(topleft=(10,y))
                        self.elements.append((surf,None,href,rect))
                        y += rect.height + 5
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    def load_loremflickr_gallery(self, term):
        def task():
            self.set_loading(True)
            self.scroll_y = 0
            self.elements.clear()
            self.buttons.clear()
            self.current_url = f"loremflickr://{term}"
            y = 40
            for i in range(10):
                url_img = f"https://loremflickr.com/320/240/{term}?lock={random.randint(1,9999)}"
                surf = self.fetch_image(url_img, max_height=100)
                if surf:
                    rect = surf.get_rect(topleft=(10,y))
                    self.elements.append((surf,None,url_img,rect))
                    y += rect.height + 10
            self.set_loading(False)
        threading.Thread(target=task, daemon=True).start()

    # --------------------------
    # Draw
    # --------------------------
    def draw(self):
        self.screen.fill(self.BG)
        for surf, desc, href, rect in self.elements:
            self.screen.blit(surf, rect.move(0,self.scroll_y))
            if desc:
                self.screen.blit(desc, (rect.x, rect.y + surf.get_height() + self.scroll_y))
        pygame.draw.rect(self.screen, self.GRAY, (0,0,self.W,30))
        txt = self.TITLE_FONT.render(self.search_text or "Type URL or search + Enter", True, self.WHITE)
        self.screen.blit(txt, (5,5))

        mouse_pos = pygame.mouse.get_pos()
        for rect, label, _ in self.buttons:
            color = self.BUTTON_HOVER if rect.collidepoint(mouse_pos) else self.BUTTON_COLOR
            pygame.draw.rect(self.screen, color, rect)
            label_surf = self.TITLE_FONT.render(label, True, self.WHITE)
            self.screen.blit(label_surf, (rect.x+5, rect.y+5))

        if self.loading:
            loading_surf = self.TITLE_FONT.render("Loading...", True, self.LOADING_COLOR)
            self.screen.blit(loading_surf, (self.W-100,5))

    # --------------------------
    # Main loop
    # --------------------------
    def run(self):
        running = True
        while running:
            self.draw()
            pygame.display.flip()
            now = time.time()
            # Auto-select DuckDuckGo after 1 second
            if self.buttons and now - self.button_timer > 1:
                _, _, callback = self.buttons[0]
                self.buttons.clear()
                callback()
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    running=False
                elif event.type==pygame.MOUSEBUTTONDOWN:
                    if event.pos[1]>30:
                        self.dragging=True
                        self.last_y = event.pos[1]
                    for rect, _, callback in self.buttons:
                        if rect.collidepoint(event.pos):
                            self.buttons.clear()
                            callback()
                    for surf, desc, href, rect in self.elements:
                        if href and rect.move(0,self.scroll_y).collidepoint(event.pos):
                            if self.current_url.startswith("loremflickr://"):
                                self.load_html_page(href)
                            elif href.startswith("duckduckgo_search://"):
                                self.load_duckduckgo_search(href.split("://")[1])
                            else:
                                self.load_html_page(href)
                elif event.type==pygame.MOUSEBUTTONUP:
                    self.dragging=False
                elif event.type==pygame.MOUSEMOTION:
                    if self.dragging:
                        dy = event.pos[1] - self.last_y
                        self.scroll_y += dy
                        self.scroll_y = min(0, self.scroll_y)
                        self.last_y = event.pos[1]
                elif event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_RETURN:
                        text = self.search_text.strip()
                        if not text:
                            self.elements.clear()
                            self.search_text=""
                            continue
                        if self.is_url(text):
                            self.buttons.clear()
                            if not text.startswith("http"):
                                text = "http://" + text
                            self.load_html_page(text)
                            self.search_text=""
                        else:
                            self.buttons.clear()
                            btn1 = pygame.Rect(5, 32, 150, 24)
                            btn2 = pygame.Rect(160, 32, 150, 24)
                            term = text
                            self.buttons.append((btn1, "Search DuckDuckGo", lambda t=term: self.load_duckduckgo_search(t)))
                            self.buttons.append((btn2, "Search LoremFlickr", lambda t=term: self.load_loremflickr_gallery(t)))
                            self.button_timer = time.time()  # Start 1-second timer
                            self.search_text=""
                    elif event.key==pygame.K_BACKSPACE:
                        self.search_text = self.search_text[:-1]
                    else:
                        ch = event.unicode
                        if ch.isprintable():
                            self.search_text += ch
        pygame.quit()
        sys.exit()
