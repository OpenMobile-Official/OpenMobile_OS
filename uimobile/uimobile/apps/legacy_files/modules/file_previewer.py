import pygame
import os
import json

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

class FilePreviewer:
    def __init__(self, screen, font, width=500, height=400):
        self.screen = screen
        self.font = font
        self.width = width
        self.height = height
        self.active = False
        self.text_lines = []
        self.image = None
        self.scroll_offset = 0
        self.max_scroll = 0
        self.dragging = False
        self.drag_start_y = 0
        self.scroll_start_offset = 0
        self.is_image = False
        self.is_audio = False
        self.is_pdf = False
        self.audio_playing = False
        self.audio_file = None

        screen_width, screen_height = screen.get_size()
        self.rect = pygame.Rect(
            (screen_width - width) // 2,
            (screen_height - height) // 2,
            width,
            height
        )
        self.close_rect = pygame.Rect(self.rect.right - 30, self.rect.top + 10, 20, 20)

        # For audio playback buttons
        self.play_rect = pygame.Rect(self.rect.left + 10, self.rect.bottom - 40, 60, 25)
        self.stop_rect = pygame.Rect(self.rect.left + 80, self.rect.bottom - 40, 60, 25)

    def open(self, filepath):
        """Open file and prepare preview depending on type"""
        self.active = True
        self.scroll_offset = 0
        self.image = None
        self.text_lines = []
        self.is_image = False
        self.is_audio = False
        self.is_pdf = False
        self.audio_playing = False
        self.audio_file = None

        if not os.path.isfile(filepath):
            self.text_lines = [f"Not a file: {filepath}"]
            return

        ext = os.path.splitext(filepath)[1].lower()

        try:
            # --- Image Preview ---
            if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                self.image = pygame.image.load(filepath).convert()
                self.is_image = True
                self.max_scroll = max(0, self.image.get_height() - self.rect.height + 20)

            # --- Text Preview ---
            elif ext in [".txt", ".py", ".json", ".ini", ".cfg", ".log", ".md"]:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    self.text_lines = f.read().splitlines()
                line_height = self.font.get_height()
                content_height = len(self.text_lines) * line_height
                self.max_scroll = max(0, content_height - self.rect.height + 40)

            # --- Audio Preview ---
            elif ext in [".mp3", ".wav", ".ogg"]:
                self.is_audio = True
                self.audio_file = filepath
                self.text_lines = [f"Audio file: {os.path.basename(filepath)}",
                                   "Click Play to listen."]
                self.max_scroll = 0

            # --- PDF Preview ---
            elif ext == ".pdf" and PdfReader:
                self.is_pdf = True
                reader = PdfReader(filepath)
                num_pages = len(reader.pages)
                self.text_lines = [
                    f"PDF file: {os.path.basename(filepath)}",
                    f"Pages: {num_pages}",
                    "Preview not implemented (stub)."
                ]
                self.max_scroll = 0

            else:
                self.text_lines = [f"Unsupported file type: {ext}"]

        except Exception as e:
            self.text_lines = [f"Error loading file: {e}"]

    def close(self):
        self.active = False
        if self.audio_playing:
            pygame.mixer.music.stop()
            self.audio_playing = False

    def handle_event(self, event):
        if not self.active:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                if self.close_rect.collidepoint(event.pos):
                    self.close()
                elif self.is_audio:
                    if self.play_rect.collidepoint(event.pos) and self.audio_file:
                        pygame.mixer.music.load(self.audio_file)
                        pygame.mixer.music.play()
                        self.audio_playing = True
                    elif self.stop_rect.collidepoint(event.pos):
                        pygame.mixer.music.stop()
                        self.audio_playing = False
                elif self.rect.collidepoint(event.pos):
                    self.dragging = True
                    self.drag_start_y = event.pos[1]
                    self.scroll_start_offset = self.scroll_offset

            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 30)
            elif event.button == 5:  # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + 30)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dy = event.pos[1] - self.drag_start_y
            self.scroll_offset = self.scroll_start_offset - dy
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def draw(self):
        if not self.active:
            return

        # Background
        pygame.draw.rect(self.screen, (30, 30, 30), self.rect, border_radius=8)
        pygame.draw.rect(self.screen, (200, 200, 200), self.rect, 2, border_radius=8)

        # Close button
        pygame.draw.rect(self.screen, (200, 80, 80), self.close_rect)
        x_surf = self.font.render("X", True, (255, 255, 255))
        x_rect = x_surf.get_rect(center=self.close_rect.center)
        self.screen.blit(x_surf, x_rect)

        # Image Preview
        if self.is_image and self.image:
            visible_area = pygame.Rect(0, self.scroll_offset, self.rect.width - 20, self.rect.height - 20)
            try:
                cropped = self.image.subsurface(visible_area).copy()
                self.screen.blit(cropped, (self.rect.left + 10, self.rect.top + 10))
            except ValueError:
                pass

        # Text / PDF Preview
        else:
            line_height = self.font.get_height()
            visible_lines = self.rect.height // line_height
            start_index = self.scroll_offset // line_height
            end_index = min(len(self.text_lines), start_index + visible_lines + 1)

            for i in range(start_index, end_index):
                line = self.text_lines[i]
                y = self.rect.top + 10 + (i - start_index) * line_height - (self.scroll_offset % line_height)
                text_surf = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(text_surf, (self.rect.left + 10, y))

        # Audio Controls
        if self.is_audio:
            pygame.draw.rect(self.screen, (80, 200, 80), self.play_rect)
            pygame.draw.rect(self.screen, (200, 80, 80), self.stop_rect)

            play_txt = self.font.render("Play", True, (0, 0, 0))
            stop_txt = self.font.render("Stop", True, (0, 0, 0))
            self.screen.blit(play_txt, self.play_rect.move(10, 3))
            self.screen.blit(stop_txt, self.stop_rect.move(10, 3))
