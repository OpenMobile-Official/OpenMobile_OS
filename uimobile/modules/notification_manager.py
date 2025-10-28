import pygame
import time
import os
import subprocess
import sys

class Notification:
    def __init__(self, text, duration=3):
        self.text = text
        self.start_time = time.time()
        self.duration = duration
        self.alpha = 0
        self.state = "fade_in"


class Dialogue:
    def __init__(self, text, action=None):
        self.text = text
        self.action = action
        self.alpha = 0
        self.state = "fade_in"


class Message:
    def __init__(self, text):
        self.text = text
        self.alpha = 0
        self.state = "fade_in"


class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.hover = False

    def draw(self, screen, font):
        color = (100, 100, 100) if not self.hover else (160, 160, 160)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2, border_radius=8)
        text_surface = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                print(f"✅ Button '{self.text}' clicked")
                self.callback()


class NotificationManager:
    def __init__(self, screen_width, screen_height, font=None, sound_path="sounds/notif.wav"):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.notifications = []
        self.dialogue_queue = []
        self.active_dialogue = None
        self.active_message = None
        self.font = font or pygame.font.Font(None, 22)
        self.fade_speed = 10
        self.padding = 10
        self.max_notifications = 4
        self.buttons = []
        self.sound_effect = None

        # Initialize sound
        print("🔧 Initializing NotificationManager...")
        if os.path.exists(sound_path):
            try:
                pygame.mixer.init()
                self.sound_effect = pygame.mixer.Sound(sound_path)
                print(f"🔊 Sound loaded: {sound_path}")
            except Exception as e:
                print(f"❌ Failed to load sound: {e}")
        else:
            print(f"⚠️ Sound file not found: {sound_path}")

        # ✅ Initialize log file path
        self.log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "notifications_log.txt")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("=== Notification Log ===\n")

        # Set trim limits
        self.max_log_size = 1024 * 1024  # 1 MB
        self.max_log_lines = 200  # keep last 200 lines

    # ------------------------
    # LOGGING
    # ------------------------
    def log_notification(self, text):
        """Logs non-dialogue, non-message notifications to config/notifications_log.txt"""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} {text}\n")
            print(f"📝 Logged notification: {text}")

            # Check file size and trim if necessary
            if os.path.getsize(self.log_file) > self.max_log_size:
                print("⚠️ Log file too large, trimming...")
                self.trim_log_file()
        except Exception as e:
            print(f"❌ Failed to log notification: {e}")

    def trim_log_file(self):
        """Keeps only the last N lines when log exceeds size limit"""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Keep header + last N lines
            header = [lines[0]] if lines and lines[0].startswith("===") else []
            lines_to_keep = header + lines[-self.max_log_lines:]

            with open(self.log_file, "w", encoding="utf-8") as f:
                f.writelines(lines_to_keep)

            print(f"✂️ Trimmed log file to last {len(lines_to_keep)} lines.")
        except Exception as e:
            print(f"❌ Failed to trim log file: {e}")

    # ------------------------
    # PUSH: Handles new inputs
    # ------------------------
    def push(self, text, duration=3):
        print(f"📨 Push called with text: {text}")

        # Dialogue mode
        if text.startswith('dialogue='):
            dialogue_text = "Invalid dialogue format"
            action = None
            try:
                dialogue_text = text.split('dialogue="')[1].split('"')[0]
            except IndexError:
                print("❌ Failed to parse dialogue text")

            if 'if=yesrun' in text:
                try:
                    action = text.split('if=yesrun"')[1].split('"')[0]
                    print(f"🛠️ Parsed action: {action}")
                except IndexError:
                    print("❌ Failed to parse action")

            self.dialogue_queue.append(Dialogue(dialogue_text, action))
            if self.sound_effect:
                self.sound_effect.play()
            return

        # Message mode
        elif text.startswith('message='):
            try:
                message_text = text.split('message="')[1].split('"')[0]
                self.active_message = Message(message_text)
                self.create_message_button()
                if self.sound_effect:
                    self.sound_effect.play()
            except Exception as e:
                print(f"❌ Failed to parse message: {e}")
            return

        # Normal notification
        notif = Notification(text, duration)
        if self.sound_effect:
            self.sound_effect.play()
        self.notifications.append(notif)
        if len(self.notifications) > self.max_notifications:
            self.notifications.pop(0)

        # ✅ Log this notification
        self.log_notification(text)

    # ------------------------
    # DIALOGUE HANDLING
    # ------------------------
    def next_dialogue(self):
        print("➡️ Moving to next dialogue...")
        if self.dialogue_queue:
            self.active_dialogue = self.dialogue_queue.pop(0)
            print(f"🗨️ Active dialogue: {self.active_dialogue.text}")
            self.create_dialogue_buttons()
        else:
            print("✅ No more dialogues.")
            self.active_dialogue = None
            self.buttons.clear()

    def create_dialogue_buttons(self):
        print("🎛️ Creating dialogue buttons...")
        w, h = 100, 40
        y = self.screen_height - 80
        spacing = 20
        total_width = w * 2 + spacing
        start_x = (self.screen_width - total_width) // 2

        def on_yes():
            print("✅ YES clicked")
            if self.active_dialogue.action:
                try:
                    script_path = os.path.abspath(self.active_dialogue.action)
                    print(f"🚀 Launching script: {script_path}")
                    subprocess.Popen([sys.executable, script_path])
                except Exception as e:
                    print(f"❌ Failed to run script: {e}")
            else:
                print("⚠️ No action defined for YES")
            self.next_dialogue()

        def on_no():
            print("❌ NO clicked")
            self.next_dialogue()

        self.buttons = [
            Button((start_x, y, w, h), "Yes", on_yes),
            Button((start_x + w + spacing, y, w, h), "No", on_no)
        ]

    # ------------------------
    # MESSAGE HANDLING
    # ------------------------
    def create_message_button(self):
        w, h = 100, 40
        y = self.screen_height - 80
        x = (self.screen_width - w) // 2

        def on_okay():
            print("✅ OK clicked")
            self.active_message = None
            self.buttons.clear()

        self.buttons = [Button((x, y, w, h), "Okay", on_okay)]

    # ------------------------
    # EVENT HANDLING
    # ------------------------
    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    # ------------------------
    # UPDATE
    # ------------------------
    def update(self):
        now = time.time()

        if not self.active_dialogue and self.dialogue_queue:
            self.next_dialogue()

        for notif in list(self.notifications):
            elapsed = now - notif.start_time
            if notif.state == "fade_in":
                notif.alpha += self.fade_speed
                if notif.alpha >= 255:
                    notif.alpha = 255
                    notif.state = "visible"
            elif notif.state == "visible" and elapsed > notif.duration:
                notif.state = "fade_out"
            elif notif.state == "fade_out":
                notif.alpha -= self.fade_speed
                if notif.alpha <= 0:
                    self.notifications.remove(notif)

        # Clear buttons when nothing active
        if not self.active_dialogue and not self.active_message:
            self.buttons.clear()

    # ------------------------
    # DRAW
    # ------------------------
    def draw(self, screen):
        if self.active_dialogue:
            self.draw_dialogue(screen)
        elif self.active_message:
            self.draw_message(screen)
        else:
            self.draw_notifications(screen)

    def draw_notifications(self, screen):
        y_offset = self.padding
        for notif in self.notifications:
            text_surf = self.font.render(notif.text, True, (255, 255, 255))
            bg_width = text_surf.get_width() + 20
            bg_height = text_surf.get_height() + 10
            x = self.screen_width - bg_width - 20

            bg_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, min(220, notif.alpha)))
            text_surf.set_alpha(notif.alpha)

            pygame.draw.rect(bg_surf, (180, 180, 180, 60), bg_surf.get_rect(), 2, border_radius=6)
            screen.blit(bg_surf, (x, y_offset))
            screen.blit(text_surf, (x + 10, y_offset + 5))
            y_offset += bg_height + self.padding

    def wrap_text(self, text, font, max_width):

        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def draw_dialogue(self, screen):
        dialogue = self.active_dialogue
        if not dialogue:
            return

        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        dialogue.alpha = min(255, dialogue.alpha + self.fade_speed)
        width = 400
        margin_bottom = 100
        line_height = self.font.get_height() + 5

        # ✅ Wrap text and calculate dynamic height
        lines = self.wrap_text(dialogue.text, self.font, width - 40)
        text_height = len(lines) * line_height + 30
        height = max(120, text_height)

        x = (self.screen_width - width) // 2
        y = self.screen_height - height - margin_bottom

        bg = pygame.Surface((width, height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, min(220, dialogue.alpha)))
        pygame.draw.rect(bg, (255, 255, 255, 120), bg.get_rect(), 2, border_radius=8)
        screen.blit(bg, (x, y))

        # ✅ Draw wrapped text lines centered
        text_y = y + 25
        for line in lines:
            text_surface = self.font.render(line, True, (255, 255, 255))
            text_rect = text_surface.get_rect(centerx=self.screen_width // 2, y=text_y)
            screen.blit(text_surface, text_rect)
            text_y += line_height

        # ✅ Draw buttons (below the text box)
        for btn in self.buttons:
            btn.draw(screen, self.font)

    def draw_message(self, screen):
        message = self.active_message
        if not message:
            return

        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        message.alpha = min(255, message.alpha + self.fade_speed)
        width = 400
        margin_bottom = 100
        line_height = self.font.get_height() + 5

        # ✅ Wrap text and calculate dynamic height
        lines = self.wrap_text(message.text, self.font, width - 40)
        text_height = len(lines) * line_height + 30
        height = max(120, text_height)

        x = (self.screen_width - width) // 2
        y = self.screen_height - height - margin_bottom

        bg = pygame.Surface((width, height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, min(220, message.alpha)))
        pygame.draw.rect(bg, (255, 255, 255, 120), bg.get_rect(), 2, border_radius=8)
        screen.blit(bg, (x, y))

        # ✅ Draw wrapped text lines centered
        text_y = y + 25
        for line in lines:
            text_surface = self.font.render(line, True, (255, 255, 255))
            text_rect = text_surface.get_rect(centerx=self.screen_width // 2, y=text_y)
            screen.blit(text_surface, text_rect)
            text_y += line_height

        # ✅ Draw buttons
        for btn in self.buttons:
            btn.draw(screen, self.font)
