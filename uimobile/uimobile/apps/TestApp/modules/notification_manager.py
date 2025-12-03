import pygame
import time
import os

class Notification:
    def __init__(self, text, duration=3, is_dialogue=False):
        self.text = text
        self.start_time = time.time()
        self.duration = duration
        self.alpha = 0
        self.state = "fade_in"
        self.is_dialogue = is_dialogue


class NotificationManager:
    def __init__(self, screen):
        self.screen = screen
        self.notifications = []
        self.font = pygame.font.SysFont("Arial", 18)
        self.last_read_time = 0
        self.read_interval = 2  # seconds between file checks
        self.notify_path = self.get_notify_path()
        self.shown_notifications = set()

    def get_notify_path(self):
        """Find notify.txt inside config/ relative to this module."""
        module_dir = os.path.dirname(os.path.abspath(__file__))  # /apps/testapp/modules
        config_path = os.path.join(module_dir, "..", "config", "notify.txt")
        return os.path.normpath(config_path)

    def read_notify_file(self):
        """Read new lines from notify.txt and add as notifications."""
        if not os.path.exists(self.notify_path):
            print(f"[NotificationManager] notify.txt not found at: {self.notify_path}")
            return

        try:
            with open(self.notify_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"[NotificationManager] Error reading notify.txt: {e}")
            return

        for line in lines:
            if line in self.shown_notifications:
                continue  # Skip duplicates

            # Dialogue support: dialogue="Text"
            if line.lower().startswith("dialogue="):
                msg = line.split("=", 1)[1].strip().strip('"')
                self.add_notification(msg, duration=6, is_dialogue=True)
            else:
                self.add_notification(line, duration=3)

            self.shown_notifications.add(line)

    def add_notification(self, text, duration=3, is_dialogue=False):
        """Add a new notification."""
        print(f"[NotificationManager] Added: {text}")
        self.notifications.append(Notification(text, duration, is_dialogue))

    def update(self):
        """Update notifications and periodically read notify.txt."""
        current_time = time.time()

        # Check for new notifications
        if current_time - self.last_read_time > self.read_interval:
            self.read_notify_file()
            self.last_read_time = current_time

        # Handle fade animations
        for n in self.notifications[:]:
            elapsed = current_time - n.start_time

            if n.state == "fade_in":
                n.alpha += 10
                if n.alpha >= 255:
                    n.alpha = 255
                    n.state = "show"

            elif n.state == "show":
                if elapsed >= n.duration:
                    n.state = "fade_out"

            elif n.state == "fade_out":
                n.alpha -= 10
                if n.alpha <= 0:
                    self.notifications.remove(n)

    def draw(self):
        """Draw all active notifications."""
        for i, n in enumerate(self.notifications):
            text_surface = self.font.render(n.text, True, (255, 255, 255))
            text_surface.set_alpha(n.alpha)

            bg_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, 40 + i * 30))
            pygame.draw.rect(self.screen, (0, 0, 0), bg_rect.inflate(20, 10))
            self.screen.blit(text_surface, bg_rect)

            # Optional dialogue outline
            if n.is_dialogue:
                pygame.draw.rect(self.screen, (0, 120, 255), bg_rect.inflate(24, 14), 2)
