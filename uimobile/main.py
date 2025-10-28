import pygame
import sys
import os
import time
import json
import subprocess

# --- Paths ---
CONFIG_FOLDER = 'config'
TO_JSON = os.path.join(CONFIG_FOLDER, 'boot.json')
CONFIG_JSON = os.path.join(CONFIG_FOLDER, 'config.json')
KEY_FILE = os.path.join(CONFIG_FOLDER, 'user.enc')  # Encrypted key file
LOGO_PATH = 'logo.png'
NOTIFICATIONS_LOG = os.path.join(CONFIG_FOLDER, 'notifications_log.txt')

# --- Auto-clear notification history ---
try:
    if os.path.exists(NOTIFICATIONS_LOG):
        with open(NOTIFICATIONS_LOG, "w", encoding="utf-8") as f:
            f.write("=== Notification Log Cleared on Boot ===\n")
        print("🧹 Cleared notification history.")
    else:
        # Ensure config folder exists and create an empty log
        os.makedirs(CONFIG_FOLDER, exist_ok=True)
        with open(NOTIFICATIONS_LOG, "w", encoding="utf-8") as f:
            f.write("=== Notification Log Initialized ===\n")
        print("🧾 Notification log initialized.")
except Exception as e:
    print(f"⚠️ Failed to clear notification history: {e}")

# --- Load configuration ---
try:
    with open(CONFIG_JSON, 'r') as f:
        config = json.load(f)
        resolution = tuple(config.get("resolution", [800, 600]))
        background_path = config.get("background", None)
except Exception as e:
    print(f"Failed to load config.json: {e}")
    resolution = (800, 600)
    background_path = None

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode(resolution)
pygame.display.set_caption("Boot Screen")
font = pygame.font.SysFont('Arial', 24)

# --- Load background ---
background = None
if background_path and os.path.exists(background_path):
    try:
        background = pygame.image.load(background_path)
        background = pygame.transform.scale(background, resolution)
    except Exception as e:
        print(f"Failed to load background: {e}")
        background = None

# --- Load and scale logo to fit window ---
try:
    logo = pygame.image.load(LOGO_PATH)
    logo_w, logo_h = logo.get_size()
    win_w, win_h = resolution

    # Scale to fit within 80% width and 60% height of window
    max_width = win_w * 0.8
    max_height = win_h * 0.6
    scale_factor = min(max_width / logo_w, max_height / logo_h, 1)
    new_size = (int(logo_w * scale_factor), int(logo_h * scale_factor))
    logo = pygame.transform.smoothscale(logo, new_size)
    logo_rect = logo.get_rect(center=(win_w // 2, win_h // 2))
except Exception as e:
    print(f"Error loading logo: {e}")
    pygame.quit()
    sys.exit()

# --- Boot screen loop ---
start_time = time.time()
booting = True
while booting:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    screen.fill((255, 255, 255))
    screen.blit(logo, logo_rect)

    # Booting text
    text_surface = font.render("Booting...", True, (0, 0, 0))
    text_rect = text_surface.get_rect(center=(resolution[0] // 2, resolution[1] - 30))
    screen.blit(text_surface, text_rect)

    pygame.display.flip()

    # Wait 5 seconds
    if time.time() - start_time >= 5:
        booting = False

pygame.quit()

# --- Decide what to launch ---
if not os.path.exists(KEY_FILE):
    # No user.enc found, launch OOBE
    oobe_path = os.path.abspath('oobe.py')
    if os.path.exists(oobe_path):
        print("Launching OOBE (first-time setup)...")
        subprocess.Popen([sys.executable, oobe_path])
    else:
        print("OOBE script not found!")
else:
    # user.enc exists, launch what boot.json specifies (default desktop)
    try:
        with open(TO_JSON, 'r') as f:
            to_config = json.load(f)
            file_to_launch = to_config.get("launch")

            if file_to_launch:
                launch_path = os.path.abspath(file_to_launch)
                if os.path.exists(launch_path):
                    print(f"Launching {file_to_launch}...")
                    subprocess.Popen([sys.executable, launch_path])
                else:
                    print(f"File to launch not found: {launch_path}")
            else:
                print("No 'launch' key in boot.json")
    except Exception as e:
        print(f"Error reading boot.json: {e}")
