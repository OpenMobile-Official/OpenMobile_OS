import pygame
import subprocess
import json
import time
import os
import sys

class TopBarManager:
    def __init__(self, screen_width, screen_height, font_small, font_medium, app_key, config_path="config/config.json"):
        self.visible = False
        self.target_height = 30
        self.current_height = 0
        self.dragging = False
        self.drag_start_y = None
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.font_small = font_small
        self.font_medium = font_medium
        self.app_key = app_key
        self.open_time = None

        # Load config (to get fallback UI if needed)
        with open(config_path, "r") as f:
            self.config = json.load(f)

        # Load app name from apps.json (which is a list of dicts)
        try:
            apps_path = os.path.join(os.path.dirname(__file__), "..", "apps.json")
            with open(apps_path, "r") as f:
                app_list = json.load(f)
                # Find app with matching name or command
                app = next((a for a in app_list if a.get("name") == app_key or a.get("command") == app_key), None)
                if app:
                    self.app_name = app.get("name", app_key)
                else:
                    self.app_name = app_key
        except FileNotFoundError:
            print("Warning: apps.json not found.")
            self.app_name = app_key

    def toggle(self):
        self.visible = not self.visible
        self.open_time = time.time() if self.visible else None

    def update(self):
        speed = 10

        if self.visible and self.current_height < self.target_height:
            self.current_height = min(self.current_height + speed, self.target_height)
            if self.current_height == self.target_height and self.open_time is None:
                self.open_time = time.time()

        elif not self.visible and self.current_height > 0:
            self.current_height = max(self.current_height - speed, 0)
            if self.current_height == 0:
                self.open_time = None

        # Auto-close after 5s
        if self.visible and self.open_time is not None:
            if time.time() - self.open_time > 5:
                self.visible = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.pos[1] < 20:
                self.dragging = True
                self.drag_start_y = event.pos[1]

            if self.current_height == self.target_height:
                close_rect = pygame.Rect(self.SCREEN_WIDTH - 40, 5, 30, 20)
                if close_rect.collidepoint(event.pos):
                    print(f"[TopBar] Closing current app: {self.app_name}")

                    # Launch fallback app if set
                    fallback = self.config.get("UI")
                    if fallback:
                        try:
                            subprocess.Popen(["python3", fallback])
                        except Exception as e:
                            print(f"Failed to launch fallback UI: {e}")

                    pygame.quit()
                    sys.exit()

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            if event.pos[1] - self.drag_start_y > 20:
                self.toggle()
                self.dragging = False

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

    def draw(self, surface):
        if self.current_height <= 0:
            return

        pygame.draw.rect(surface, (40, 40, 40), (0, 0, self.SCREEN_WIDTH, self.current_height))

        if self.current_height == self.target_height:
            close_rect = pygame.Rect(self.SCREEN_WIDTH - 40, 5, 30, 20)
            pygame.draw.rect(surface, (200, 50, 50), close_rect, border_radius=5)
            x_label = self.font_small.render("X", True, (255, 255, 255))
            x_rect = x_label.get_rect(center=close_rect.center)
            surface.blit(x_label, x_rect)

        label_text = f"{self.app_name}"
        label = self.font_small.render(label_text, True, (255, 255, 255))
        surface.blit(label, (10, 5))
