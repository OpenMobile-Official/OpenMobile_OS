import pygame
import sys
import os
import json
import subprocess
from datetime import datetime

pygame.init()

# --- Screen Setup ---
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mobile Phone UI")

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
LIGHT_BLUE = (173, 216, 230)
SHADOW = (200, 200, 200)

# --- Fonts ---
font_small = pygame.font.SysFont("Arial", 16)
font_medium = pygame.font.SysFont("Arial", 20)

# --- Load Apps from JSON ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "apps.json")

if not os.path.exists(CONFIG_PATH):
    print(f"Missing {CONFIG_PATH}")
    sys.exit()

with open(CONFIG_PATH, "r") as f:
    apps = json.load(f)
    # --- Fix relative app commands ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    fixed_apps = []
    for app in apps:
        command = app["command"]

        # Split: "python3 apps/TestApp/testapp.py"
        parts = command.split(" ", 1)

        if len(parts) == 2:
            launcher = parts[0]           # python3
            script_path = parts[1]        # apps/TestApp/testapp.py

            # Convert script path to absolute path
            absolute_script = os.path.join(BASE_DIR, script_path)

            # Wrap in quotes to protect spaces
            absolute_script = f'"{absolute_script}"'

            fixed_command = f"{launcher} {absolute_script}"
        else:
            # No space? unexpected, keep original
            fixed_command = command

        fixed_apps.append({
            "name": app["name"],
            "command": fixed_command
        })

    # Replace original apps list
    apps = fixed_apps


# --- Grid Settings ---
ICON_SIZE = 60
ICON_SPACING_X = 100
ICON_SPACING_Y = 100
ICONS_PER_ROW = 3
START_X = 40
START_Y = 50 + 30  # Leave space for top bar

# --- Scroll Variables ---
scroll_offset = 0
scroll_velocity = 0
scroll_friction = 0.9
scroll_speed_limit = 40
drag_threshold = 10
is_dragging = False
drag_start_y = 0
drag_last_y = 0
drag_total = 0

max_scroll = max(0, (len(apps) // ICONS_PER_ROW) * ICON_SPACING_Y - (SCREEN_HEIGHT - 130))

# --- Draw App Icon ---
def draw_app_icon(x, y, name):
    icon_rect = pygame.Rect(x, y, ICON_SIZE, ICON_SIZE)
    pygame.draw.rect(screen, LIGHT_BLUE, icon_rect, border_radius=10)
    label = font_small.render(name, True, BLACK)
    text_rect = label.get_rect(center=(x + ICON_SIZE // 2, y + ICON_SIZE + 12))
    screen.blit(label, text_rect)
    return icon_rect

# --- Draw Status Bar ---
def draw_status_bar():
    pygame.draw.rect(screen, GRAY, (0, 0, SCREEN_WIDTH, 30))
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    battery_str = "🔋 80%"
    screen.blit(font_small.render(time_str, True, BLACK), (10, 7))
    screen.blit(font_small.render(battery_str, True, BLACK), (SCREEN_WIDTH - 70, 7))
    # Add a subtle bottom shadow line
    pygame.draw.line(screen, SHADOW, (0, 30), (SCREEN_WIDTH, 30), 2)

# --- Launch App ---
def launch_app(command):
    try:
        pygame.quit()
        sys.exit(subprocess.Popen(command, shell=True))
    except Exception as e:
        print(f"Failed to launch app: {e}")

# --- Main Loop ---
clock = pygame.time.Clock()
running = True

while running:
    screen.fill(WHITE)

    # --- Draw Apps with Scroll ---
    icon_rects = []
    for i, app in enumerate(apps):
        row = i // ICONS_PER_ROW
        col = i % ICONS_PER_ROW
        x = START_X + col * ICON_SPACING_X
        y = START_Y + row * ICON_SPACING_Y + scroll_offset

        if -100 < y < SCREEN_HEIGHT:
            rect = draw_app_icon(x, y, app["name"])
            icon_rects.append((rect, app["command"], app["name"], x, y))

    # --- Always Draw Status Bar on Top ---
    draw_status_bar()

    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Touch / left click
                is_dragging = True
                drag_start_y = event.pos[1]
                drag_last_y = event.pos[1]
                drag_total = 0
                scroll_velocity = 0

        elif event.type == pygame.MOUSEMOTION and is_dragging:
            dy = event.pos[1] - drag_last_y
            drag_last_y = event.pos[1]
            scroll_offset += dy
            scroll_velocity = dy
            drag_total += abs(dy)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                is_dragging = False
                # Tap detection (no drag)
                if drag_total < drag_threshold and event.pos[1] > 30:  # Ignore taps on top bar
                    for rect, command, name, x, y in icon_rects:
                        if rect.collidepoint(event.pos):
                            launch_app(command)

        elif event.type == pygame.MOUSEWHEEL:
            scroll_offset += event.y * 20  # Optional mouse wheel scroll

    # --- Inertia Scroll ---
    if not is_dragging:
        scroll_offset += scroll_velocity
        scroll_velocity *= scroll_friction
        if abs(scroll_velocity) < 0.1:
            scroll_velocity = 0

    # --- Clamp Scroll Offset ---
    scroll_offset = max(-max_scroll, min(0, scroll_offset))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
