import pygame
import sys
import os
import json
import subprocess
from modules.top_bar import TopBarManager
from modules.file_previewer import FilePreviewer

# Styling constants
BG_COLOR = (30, 30, 30)
BREADCRUMB_BG = (50, 50, 50)
BREADCRUMB_TEXT_COLOR = (230, 230, 230)
TOPBAR_HEIGHT = 30

# FileIcon class
class FileIcon:
    def __init__(self, name, path, cfg):
        self.name = name
        self.path = path
        self.rect = pygame.Rect(0, 0, cfg["icon_width"], cfg["icon_height"])
        self.font = pygame.font.SysFont(None, 16)
        self.is_dir = os.path.isdir(path)

    def draw(self, surface):
        color = (100, 160, 220) if self.is_dir else (180, 180, 180)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        label = self.font.render(self.name[:12], True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, event, callback=None):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and callback:
                callback(self)

# FileGrid class
class FileGrid:
    def __init__(self, base_path, cfg, on_file_click):
        self.cfg = cfg
        self.cols = cfg["columns"]
        self.icons_per_page = cfg["icons_per_page"]
        self.padding = cfg["icon_padding"]
        self.font = pygame.font.SysFont(None, 20)
        self.on_file_click = on_file_click

        self.base_path = os.path.abspath(base_path)
        self.current_path = self.base_path
        self.icons = []
        self.pages = []
        self.page = 0

        self.load_files()

    def load_files(self):
        try:
            files = os.listdir(self.current_path)
        except PermissionError:
            files = []
        files.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_path, x)), x.lower()))
        self.icons = [
            FileIcon(name=f, path=os.path.join(self.current_path, f), cfg=self.cfg)
            for f in files
        ]
        self.pages = [self.icons[i:i + self.icons_per_page] for i in range(0, len(self.icons), self.icons_per_page)]
        self.page = 0

    def draw(self, surface):
        if not self.pages:
            return
        for idx, icon in enumerate(self.pages[self.page]):
            row, col = divmod(idx, self.cols)
            icon.rect.topleft = (
                self.padding + col * (icon.rect.width + self.padding),
                60 + row * (icon.rect.height + 40 + self.padding),
            )
            icon.draw(surface)

    def handle_event(self, event):
        if not self.pages:
            return
        for icon in self.pages[self.page]:
            icon.handle_event(event, callback=self.on_file_click)

    def next_page(self):
        self.page = min(self.page + 1, len(self.pages) - 1)

    def prev_page(self):
        self.page = max(self.page - 1, 0)

    def navigate_up(self, breadcrumb=None):
        parent = os.path.dirname(self.current_path)
        if parent.startswith(self.base_path) and parent != self.current_path:
            self.current_path = parent
            self.load_files()
            if breadcrumb:
                breadcrumb.update_path(self.current_path)

    def navigate_to(self, folder_path, breadcrumb=None):
        folder_path = os.path.abspath(folder_path)
        if folder_path.startswith(self.base_path) and os.path.isdir(folder_path):
            self.current_path = folder_path
            self.load_files()
            if breadcrumb:
                breadcrumb.update_path(self.current_path)

# BreadcrumbBar class
class BreadcrumbBar:
    def __init__(self, font, height, screen_width, base_path):
        self.font = font
        self.height = height
        self.screen_width = screen_width
        self.parts = []
        self.rects = []
        self.base_path = os.path.abspath(base_path)

    def update_path(self, path):
        path = os.path.abspath(path)
        try:
            rel_path = os.path.relpath(path, self.base_path)
        except ValueError:
            rel_path = path

        if rel_path == ".":
            self.parts = []
        else:
            self.parts = rel_path.split(os.sep)

    def draw(self, surface):
        pygame.draw.rect(surface, BREADCRUMB_BG, (0, TOPBAR_HEIGHT, self.screen_width, self.height))
        x = 10
        self.rects.clear()

        label_home = self.font.render("Home", True, BREADCRUMB_TEXT_COLOR)
        rect_home = label_home.get_rect(topleft=(x, TOPBAR_HEIGHT + (self.height - label_home.get_height()) // 2))
        surface.blit(label_home, rect_home)
        self.rects.append((rect_home, -1))  # -1 = base_path
        x += rect_home.width + 15

        if self.parts:
            for i, part in enumerate(self.parts):
                sep = self.font.render(">", True, BREADCRUMB_TEXT_COLOR)
                sep_rect = sep.get_rect(topleft=(x, TOPBAR_HEIGHT + (self.height - sep.get_height()) // 2))
                surface.blit(sep, sep_rect)
                x += sep_rect.width + 10

                label = self.font.render(part, True, BREADCRUMB_TEXT_COLOR)
                rect = label.get_rect(topleft=(x, TOPBAR_HEIGHT + (self.height - label.get_height()) // 2))
                surface.blit(label, rect)
                self.rects.append((rect, i))
                x += rect.width + 15

    def handle_event(self, event, file_grid):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for rect, idx in self.rects:
                if rect.collidepoint(pos):
                    if idx == -1:  # Home button
                        file_grid.current_path = file_grid.base_path
                        file_grid.load_files()
                        self.update_path(file_grid.current_path)
                    else:
                        new_path = os.path.join(file_grid.base_path, *self.parts[: idx + 1])
                        file_grid.navigate_to(new_path, self)
                    break

# Load config helper
def load_config():
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "..", "..", "config", "config.json")
    try:
        with open(p, "r") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        cfg = {}
    return {
        "resolution": cfg.get("resolution", [800, 600]),
        "background": cfg.get("background", ""),
        "time_format": cfg.get("time_format", "%H:%M"),
        "battery_display": cfg.get("battery_display", "🔋 80%"),
        "icon_width": cfg.get("icon_width", 80),
        "icon_height": cfg.get("icon_height", 80),
        "icon_padding": cfg.get("icon_padding", 20),
        "icons_per_page": cfg.get("icons_per_page", 12),
        "columns": cfg.get("columns", 4),
        "breadcrumb_height": cfg.get("breadcrumb_height", 30),
    }

def main():
    pygame.init()
    cfg = load_config()
    w, h = cfg["resolution"]
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("Modern File Manager")

    font_small = pygame.font.SysFont(None, 18)
    font_medium = pygame.font.SysFont(None, 22)
    font_breadcrumb = pygame.font.SysFont(None, 20)

    topbar = TopBarManager(w, h, font_small, font_medium, app_key="filemanager")
    file_previewer = FilePreviewer(screen, font_medium, w, h)

    bg = None
    if cfg["background"]:
        base = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(base, "..", "..", "backgrounds", cfg["background"])
        if os.path.exists(bg_path):
            bg = pygame.transform.scale(pygame.image.load(bg_path), (w, h))

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Files", "User", "Home")
    os.makedirs(base_dir, exist_ok=True)

    fg = None  # define ahead so it's visible in callback

    def on_file_click(file_icon):
        if file_previewer.active:
            return  # ignore clicks while preview is open

        if file_icon.is_dir:
            fg.navigate_to(file_icon.path, breadcrumb)
        else:
            file_previewer.open(file_icon.path)

    fg = FileGrid(base_dir, cfg, on_file_click)
    breadcrumb = BreadcrumbBar(font_breadcrumb, cfg["breadcrumb_height"], w, base_dir)
    breadcrumb.update_path(fg.current_path)

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if file_previewer.active:
                file_previewer.handle_event(event)
            else:
                topbar.handle_event(event)
                breadcrumb.handle_event(event, fg)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        fg.next_page()
                    elif event.key == pygame.K_LEFT:
                        fg.prev_page()
                    elif event.key == pygame.K_BACKSPACE:
                        fg.navigate_up(breadcrumb)

                fg.handle_event(event)

        topbar.update()

        screen.fill(BG_COLOR)
        if bg:
            screen.blit(bg, (0, 0))

        if file_previewer.active:
            file_previewer.draw()
        else:
            fg.draw(screen)
            breadcrumb.draw(screen)
            topbar.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
