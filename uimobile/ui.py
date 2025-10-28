import pygame
import sys
from datetime import datetime
import os
import json
import subprocess
import time

from modules.notification_manager import NotificationManager
from modules.notification_center import NotificationCenter  # ✅ New import

pygame.init()

# --- Load configuration --- 
with open("config/config.json") as f:
    config = json.load(f)

# Load resolution
SCREEN_WIDTH, SCREEN_HEIGHT = config.get("resolution", [480, 320])
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mobile Phone UI")

# Config values
BACKGROUND_PATH = config["background"]
TIME_FORMAT = config["time_format"]
BATTERY_DISPLAY = config["battery_display"]
ICON_WIDTH = config["icon_width"]
ICON_HEIGHT = config["icon_height"]
PADDING = config["icon_padding"]
ICONS_PER_PAGE = config["icons_per_page"]
COLUMNS = config["columns"]

# Fonts
font_small = pygame.font.SysFont("Arial", max(12, SCREEN_HEIGHT // 25))
font_medium = pygame.font.SysFont("Arial", max(16, SCREEN_HEIGHT // 20))

# Background
background_img = pygame.image.load(BACKGROUND_PATH)
background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

clock = pygame.time.Clock()
MARGIN_TOP = SCREEN_HEIGHT // 5

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_BLUE = (150, 200, 255)
BLUE = (100, 150, 255)
SHADOW = (100, 100, 100)

# Animation
ANIMATION_DURATION = 300
animation_start_time = None
animation_direction = 0
previous_page = 0
next_apps = []

# ✅ Managers
notification_manager = NotificationManager(SCREEN_WIDTH, SCREEN_HEIGHT, font_small)
notification_center = NotificationCenter(screen, notification_manager.notifications)


# --- Utils ---
def get_brightness(color):
    r, g, b = color
    return 0.299 * r + 0.587 * g + 0.114 * b

def choose_text_color(bg_color):
    brightness = get_brightness(bg_color)
    if brightness > 200:
        return (60, 60, 60)
    elif brightness > 150:
        return (30, 30, 120)
    elif brightness > 100:
        return (255, 255, 255)
    elif brightness > 50:
        return (255, 220, 180)
    else:
        return (255, 180, 220)

def get_background_color_at(x, y):
    x = max(0, min(SCREEN_WIDTH - 1, x))
    y = max(0, min(SCREEN_HEIGHT - 1, y))
    return background_img.get_at((x, y))[:3]

def draw_dim_background(surface, alpha):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(alpha)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))

# --- App Icon Class ---
class AppIcon:
    def __init__(self, name, command, x, y):
        self.name = name
        self.command = command
        self.rect = pygame.Rect(x, y, ICON_WIDTH, ICON_HEIGHT)
        self.icon_img = self.load_icon()

    def load_icon(self):
        try:
            command_parts = self.command.split()
            script_path = None
            for part in command_parts:
                if part.endswith(".py") and os.path.exists(part):
                    script_path = part
                    break
            if script_path:
                app_dir = os.path.dirname(script_path)
                for ext in ["icon.jpg", "icon.png"]:
                    icon_path = os.path.join(app_dir, ext)
                    if os.path.exists(icon_path):
                        icon_img = pygame.image.load(icon_path)
                        return pygame.transform.smoothscale(icon_img, (ICON_WIDTH, ICON_HEIGHT))
        except Exception as e:
            print(f"Failed to load icon for {self.name}: {e}")
        return None

    def draw(self, mouse_pos):
        self._draw_with_offset(mouse_pos, 0)

    def _draw_with_offset(self, mouse_pos, x_offset):
        rect = self.rect.move(x_offset, 0)
        shadow_rect = rect.move(3, 3)
        pygame.draw.rect(screen, SHADOW, shadow_rect, border_radius=12)

        hover = rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, LIGHT_BLUE if not hover else BLUE, rect, border_radius=12)

        if self.icon_img:
            screen.blit(self.icon_img, rect)
        else:
            pygame.draw.rect(screen, (180, 180, 250), rect.inflate(-10, -10), border_radius=8)

        label_x = rect.centerx
        label_y = rect.bottom + SCREEN_HEIGHT // 40
        bg_color = get_background_color_at(label_x, label_y)
        text_color = choose_text_color(bg_color)
        label = font_small.render(self.name, True, text_color)
        label_rect = label.get_rect(center=(label_x, label_y))
        screen.blit(label, label_rect)

    def handle_click(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            print(f"Launching: {self.command}")
            try:
                notification_manager.push(f"Launching {self.name}...")
                subprocess.Popen(self.command.split())
                pygame.quit()
            except Exception as e:
                notification_manager.push(f"Failed to launch {self.name}")
                print(f"Failed to launch '{self.command}': {e}")

# --- Load apps ---
def load_apps():
    with open("config/apps.json") as f:
        return json.load(f)

def create_page_icons(app_data, page):
    apps = []
    start_index = page * ICONS_PER_PAGE
    page_items = app_data[start_index:start_index + ICONS_PER_PAGE]
    total_width = COLUMNS * ICON_WIDTH + (COLUMNS - 1) * PADDING
    start_x = (SCREEN_WIDTH - total_width) // 2
    for i, app in enumerate(page_items):
        row = i // COLUMNS
        col = i % COLUMNS
        x = start_x + col * (ICON_WIDTH + PADDING)
        y = MARGIN_TOP + row * (ICON_HEIGHT + SCREEN_HEIGHT // 20)
        apps.append(AppIcon(app["name"], app["command"], x, y))
    return apps

def draw_status_bar():
    bar_height = SCREEN_HEIGHT // 10
    for y in range(bar_height):
        grey_value = 100 + int((100 * y) / bar_height)
        pygame.draw.line(screen, (grey_value, grey_value, grey_value), (0, y), (SCREEN_WIDTH, y))
    now = datetime.now()
    screen.blit(font_small.render(now.strftime(TIME_FORMAT), True, BLACK), (10, 7))
    screen.blit(font_small.render(BATTERY_DISPLAY, True, BLACK), (SCREEN_WIDTH - 70, 7))

def draw_page_dots(current_page, total_pages):
    dot_radius = max(3, SCREEN_WIDTH // 160)
    spacing = dot_radius * 4
    center_x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT - 20
    start_x = center_x - ((total_pages - 1) * spacing) // 2
    for i in range(total_pages):
        color = BLACK if i == current_page else GRAY
        pygame.draw.circle(screen, color, (start_x + i * spacing, y), dot_radius)

# --- Main loop ---
app_data = load_apps()
total_pages = max(1, (len(app_data) + ICONS_PER_PAGE - 1) // ICONS_PER_PAGE)
current_page = 0
apps = create_page_icons(app_data, current_page)

swipe_start_x = None
pull_start_y = None
is_pulling = False
overlay_alpha = 0

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    screen.blit(background_img, (0, 0))
    draw_status_bar()
    draw_page_dots(current_page, total_pages)
    current_time = pygame.time.get_ticks()

    # --- Animation ---
    if animation_start_time:
        elapsed = current_time - animation_start_time
        progress = min(1, elapsed / ANIMATION_DURATION)
        offset = int(progress * SCREEN_WIDTH) * animation_direction
        for app in apps:
            app._draw_with_offset(mouse_pos, offset)
        for app in next_apps:
            app._draw_with_offset(mouse_pos, offset - SCREEN_WIDTH * animation_direction)
        if progress >= 1:
            apps = next_apps
            animation_start_time = None
            animation_direction = 0
    else:
        for app in apps:
            app.draw(mouse_pos)

    # --- Events ---
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        # Handle notification events
        notification_manager.handle_event(event)
        if notification_manager.active_dialogue:
            continue

        # Pull-down gesture for Notification Center
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if y < 20:  # top edge
                pull_start_y = y
                is_pulling = True
            swipe_start_x = x

        elif event.type == pygame.MOUSEBUTTONUP:
            if is_pulling:
                if notification_center.is_open:
                    if notification_center.offset_y < SCREEN_HEIGHT * 0.7:
                        notification_center.close()
                else:
                    if notification_center.offset_y > 100:
                        notification_center.open()
                is_pulling = False
                pull_start_y = None
                overlay_alpha = 0

            delta = event.pos[0] - (swipe_start_x or 0)
            if abs(delta) > 30 and animation_start_time is None and not notification_center.is_open:
                if delta < 0 and current_page < total_pages - 1:
                    animation_direction = -1
                    current_page += 1
                    animation_start_time = pygame.time.get_ticks()
                    next_apps = create_page_icons(app_data, current_page)
                elif delta > 0 and current_page > 0:
                    animation_direction = 1
                    current_page -= 1
                    animation_start_time = pygame.time.get_ticks()
                    next_apps = create_page_icons(app_data, current_page)
            else:
                for app in apps:
                    app.handle_click(event.pos)

        elif event.type == pygame.MOUSEMOTION and is_pulling:
            _, y = event.pos
            drag_distance = y - (pull_start_y or 0)
            notification_center.offset_y = max(0, min(drag_distance, SCREEN_HEIGHT))
            overlay_alpha = min(180, drag_distance)

    # --- Notify.txt integration ---
    if os.path.exists("config/notify.txt"):
        with open("config/notify.txt") as f:
            message = f.read().strip()
        if message:
            notification_manager.push(message)
        open("config/notify.txt", "w").close()

    # --- Update notifications and center ---
    notification_manager.update()
    notification_center.update(events)

    # --- Draw overlay and notification center ---
    if notification_center.is_open or is_pulling:
        draw_dim_background(screen, overlay_alpha)
    notification_center.draw()
    notification_manager.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
