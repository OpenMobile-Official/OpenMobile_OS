import pygame
import os

class NotificationCenter:
    def __init__(self, screen, width=None, height=None):
        self.screen = screen
        self.width = width or screen.get_width()
        self.height = height or screen.get_height()
        self.offset_y = 0
        self.scroll_y = 0
        self.is_open = False
        self.scroll_speed = 20
        self.font = pygame.font.SysFont("Arial", max(16, self.width // 30))
        self.log_path = "config/notifications_log.txt"
        self.notify_path = "config/notify.txt"
        self.notifications = []

        self.close_button_rect = None
        self.load_notifications()

    def load_notifications(self):
        """Load notifications from log, filtering out app launch and system lines."""
        if os.path.exists(self.log_path):
            with open(self.log_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.notifications = [
                l for l in lines
                if "Launching" not in l and "Notification Log Cleared" not in l
            ]
        else:
            self.notifications = []

    def open(self):
        self.is_open = True
        self.load_notifications()

    def close(self):
        self.is_open = False
        self.scroll_y = 0

    def handle_event(self, event):
        if not self.is_open:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll_y = min(self.scroll_y + self.scroll_speed, 0)
            elif event.button == 5:
                max_scroll = min(0, self.height - self.get_content_height() - 40)
                self.scroll_y = max(self.scroll_y - self.scroll_speed, max_scroll)
            else:
                if self.close_button_rect and self.close_button_rect.collidepoint(event.pos):
                    self.close()
                    return

                panel_rect = pygame.Rect(30, 30, self.width - 60, min(self.height * 0.8, self.height - 40))
                if not panel_rect.collidepoint(event.pos):
                    self.close()

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()

    def update(self, events=None):
        if events:
            for e in events:
                self.handle_event(e)

        if os.path.exists(self.notify_path):
            with open(self.notify_path, "r") as f:
                message = f.read().strip()
            if message:
                self.notifications.append(message)
                with open(self.log_path, "a") as log:
                    log.write(message + "\n")
                open(self.notify_path, "w").close()

    def get_content_height(self):
        return 20 + len(self.notifications) * 40

    def draw(self):
        if not self.is_open:
            return

        # 1️⃣ Draw dim background first
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # 2️⃣ Draw the main panel
        panel_height = min(self.height * 0.8, self.height - 40)
        panel_rect = pygame.Rect(30, 30, self.width - 60, panel_height)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, (200, 200, 200), panel_rect, 2, border_radius=12)

        # 3️⃣ Draw close button
        self.close_button_rect = pygame.Rect(panel_rect.right - 40, panel_rect.top + 10, 25, 25)
        pygame.draw.rect(self.screen, (80, 80, 80), self.close_button_rect, border_radius=4)
        x_text = self.font.render("X", True, (255, 255, 255))
        self.screen.blit(x_text, (self.close_button_rect.x + 6, self.close_button_rect.y))

        # 4️⃣ Draw notifications
        y = panel_rect.top + 50 + self.scroll_y
        visible_area = pygame.Rect(panel_rect.left + 20, panel_rect.top + 50, panel_rect.width - 40, panel_rect.height - 70)

        if not self.notifications:
            no_notif = self.font.render("No notifications", True, (180, 180, 180))
            self.screen.blit(no_notif, (visible_area.x + 10, visible_area.y + 10))
            return

        for text in reversed(self.notifications[-50:]):  # last 50 only
            bg_rect = pygame.Rect(panel_rect.left + 20, y, panel_rect.width - 40, 30)
            if bg_rect.bottom > visible_area.bottom or bg_rect.top < visible_area.top:
                y += 40
                continue  # skip drawing if outside visible area
            pygame.draw.rect(self.screen, (60, 60, 60), bg_rect, border_radius=6)
            text_surface = self.font.render(text, True, (255, 255, 255))
            self.screen.blit(text_surface, (bg_rect.x + 10, bg_rect.y + 5))
            y += 40
