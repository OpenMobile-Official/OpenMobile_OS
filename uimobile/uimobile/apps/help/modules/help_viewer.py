import pygame
import os
from textwrap import wrap

class HelpViewer:
    def __init__(self, screen, font_small, font_medium, font_large, docs_path="help_docs"):
        self.screen = screen
        self.font_small = font_small
        self.font_medium = font_medium
        self.font_large = font_large
        self.docs_path = docs_path
        self.current_doc = None
        self.scroll_y = 0
        self.scroll_speed = 15

    def load_document(self, parsed_doc):
        self.current_doc = parsed_doc
        self.scroll_y = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y += event.y * self.scroll_speed

    def draw(self):
        if not self.current_doc:
            return

        screen = self.screen
        y = 60 + self.scroll_y  # Start below top bar

        # Title
        title_surf = self.font_large.render(self.current_doc["title"], True, (255, 255, 255))
        screen.blit(title_surf, (20, y))
        y += 40

        for section in self.current_doc["sections"]:
            # Header
            if section["header"]:
                header_surf = self.font_medium.render(section["header"], True, (200, 220, 255))
                screen.blit(header_surf, (20, y))
                y += 30

            # Text
    

        for line in section["text"]:
            wrapped_lines = wrap(line, width=55)
            for wline in wrapped_lines:
                text_surf = self.font_small.render(wline, True, (230, 230, 230))
                screen.blit(text_surf, (40, y))
                y += 22



            # Images
            for img_path in section["images"]:
                full_path = os.path.join("help_docs", img_path)
                if os.path.exists(full_path):
                    image = pygame.image.load(full_path)
                    image = pygame.transform.scale(image, (200, 120))
                    screen.blit(image, (40, y))
                    y += 130

            # Table
            if section["table"]:
                for row in section["table"]:
                    x = 40
                    for cell in row:
                        cell_surf = self.font_small.render(cell, True, (250, 250, 250))
                        screen.blit(cell_surf, (x, y))
                        x += 150
                    y += 25

            y += 20
