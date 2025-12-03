import pygame
import os
from modules.archive_helper import save_page  # Ensure archive_helper.py has this function

class Sidebar:
    def __init__(self, width, height, font_small):
        self.width = 120
        self.height = height
        self.font_small = font_small

        # Sidebar state
        self.visible = False
        self.offset_x = -self.width  # Start hidden
        self.speed = 15

        # Buttons
        self.buttons = []
        self._init_buttons()

        # Swipe tracking
        self.dragging = False
        self.drag_start_x = None

        # Archive folder
        self.archive_dir = os.path.join(os.path.dirname(__file__), "..", "archives")
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)

    def _init_buttons(self):
        # Button: favorites
        fav_rect = pygame.Rect(10, 50, 100, 40)
        self.buttons.append({"rect": fav_rect, "label": "★ Favorite", "action": "favorite"})

        # Button: archive
        arch_rect = pygame.Rect(10, 110, 100, 40)
        self.buttons.append({"rect": arch_rect, "label": "📦 Archive", "action": "archive"})

    def toggle(self):
        self.visible = not self.visible

    def close(self):
        self.visible = False

    def handle_event(self, event, current_url=None, current_elements=None):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if x < 20 and not self.visible:
                self.toggle()
            elif self.visible and x > self.width:
                self.close()
            elif self.visible:
                # Check button clicks
                for btn in self.buttons:
                    if btn["rect"].collidepoint((x - self.offset_x, y)):
                        if btn["action"] == "archive":
                            if current_url and current_elements:
                                save_page(current_url, current_elements, self.archive_dir)
                        elif btn["action"] == "favorite":
                            # Implement favorite logic here
                            print(f"[Sidebar] Favorited: {current_url}")

            # Start swipe
            self.dragging = True
            self.drag_start_x = x

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            dx = event.pos[0] - self.drag_start_x
            if dx > 50:
                self.visible = True
            elif dx < -50:
                self.visible = False

    def update(self):
        target_x = 0 if self.visible else -self.width
        if self.offset_x < target_x:
            self.offset_x = min(self.offset_x + self.speed, target_x)
        elif self.offset_x > target_x:
            self.offset_x = max(self.offset_x - self.speed, target_x)

    def draw(self, surface):
        self.update()
        sidebar_rect = pygame.Rect(self.offset_x, 0, self.width, self.height)
        pygame.draw.rect(surface, (40, 40, 40), sidebar_rect)

        # Draw buttons
        for btn in self.buttons:
            btn_rect = btn["rect"].copy()
            btn_rect.x += self.offset_x
            pygame.draw.rect(surface, (80, 80, 80), btn_rect, border_radius=6)
            label = self.font_small.render(btn["label"], True, (255, 255, 255))
            label_rect = label.get_rect(center=btn_rect.center)
            surface.blit(label, label_rect)
