import pygame
import sys
import os
import subprocess
import json
from datetime import datetime
from modules import pass_keyboard
from modules.encryption import decrypt_string

# --- Paths ---
CONFIG_DIR = "config"
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
USER_ENC_PATH = os.path.join(CONFIG_DIR, "user.enc")
IMAGES_DIR = "images"

# --- Load Config ---
default_resolution = (480, 320)
main_app = "main.py"

try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        resolution = tuple(config.get("resolution", default_resolution))
        main_app = config.get("UI", main_app)
except Exception as e:
    print(f"Error loading config: {e}")
    resolution = default_resolution

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode(resolution)
pygame.display.set_caption("Lock Screen")
font = pygame.font.SysFont("Arial", 72, bold=True)
small_font = pygame.font.SysFont("Arial", 24)  # smaller top-right time
tiny_font = pygame.font.SysFont("Arial", 20)
clock = pygame.time.Clock()
SCREEN_WIDTH, SCREEN_HEIGHT = resolution

# --- UI Elements ---
input_box = pygame.Rect(SCREEN_WIDTH // 4, int(SCREEN_HEIGHT * 0.45), SCREEN_WIDTH // 2, 50)  # moved up
login_button = pygame.Rect(SCREEN_WIDTH // 2 - 60, int(SCREEN_HEIGHT * 0.65), 120, 50)

# --- Load Password ---
try:
    with open(USER_ENC_PATH, "rb") as f:
        encrypted_pw = f.read()
    stored_password = decrypt_string(encrypted_pw).strip()
except Exception as e:
    print(f"Failed to read or decrypt user password: {e}")
    stored_password = None

# --- Load Background Images ---
def load_background_images():
    images = []
    for i in range(1, 6):
        img_path = os.path.join(IMAGES_DIR, f"{i}.jpg")
        if os.path.exists(img_path):
            img = pygame.image.load(img_path).convert()
            img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            images.append(img)
    if not images:
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        surf.fill((255, 255, 255))
        images.append(surf)
    return images

background_images = load_background_images()

# --- Crossfade Settings ---
BG_DISPLAY_TIME = 5000
BG_FADE_TIME = 2000

# --- Arrow Settings ---
ARROW_WIDTH, ARROW_HEIGHT = 40, 30
arrow_base_y = SCREEN_HEIGHT - 60
arrow_x = SCREEN_WIDTH // 2
arrow_y = arrow_base_y
arrow_pulse_direction = 1
arrow_pulse_speed = 0.5
arrow_pulse_range = 10

# --- State Flags ---
unlocked = False
input_password = ""
error_message = ""

# --- Background Indices ---
bg_index = 0
next_bg_index = 1 if len(background_images) > 1 else 0
last_switch_time = pygame.time.get_ticks()
fading = False
fade_start_time = 0

# --- Dragging ---
dragging = False
drag_start_y = None
drag_offset = 0
unlock_threshold = SCREEN_HEIGHT // 3

def draw_pulsing_arrow(surface, x, y, alpha=255):
    arrow_surf = pygame.Surface((ARROW_WIDTH, ARROW_HEIGHT), pygame.SRCALPHA)
    color = (255, 255, 255, alpha)
    points = [(0, 0), (ARROW_WIDTH, 0), (ARROW_WIDTH // 2, ARROW_HEIGHT)]
    pygame.draw.polygon(arrow_surf, color, points)
    surface.blit(arrow_surf, (x - ARROW_WIDTH // 2, y))

def blend_images(img1, img2, alpha):
    blended = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert_alpha()
    img1_copy = img1.copy()
    img2_copy = img2.copy()
    img1_copy.set_alpha(255 - int(alpha * 255))
    img2_copy.set_alpha(int(alpha * 255))
    blended.blit(img1_copy, (0, 0))
    blended.blit(img2_copy, (0, 0))
    return blended

def draw_center_time_with_box():
    """Draws the time in the center with a translucent rounded white background and soft blur."""
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    time_surf = font.render(time_str, True, (0, 0, 0))

    padding = 25
    box_rect = time_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    box_rect.inflate_ip(padding * 2, padding)

    # Create transparent surface for the blur box
    blur_surf = pygame.Surface(box_rect.size, pygame.SRCALPHA)

    # Draw semi-transparent rounded rectangle
    pygame.draw.rect(blur_surf, (255, 255, 255, 75), blur_surf.get_rect(), border_radius=20)

    # Fake soft blur by drawing slightly offset multiple times
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)]:
        screen.blit(blur_surf, (box_rect.x + dx, box_rect.y + dy))

    # Draw the text on top
    screen.blit(time_surf, time_surf.get_rect(center=box_rect.center))


def draw_top_right_time_small():
    """Draws smaller time at the top right (login screen)."""
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    time_surf = small_font.render(time_str, True, (0, 0, 0))
    screen.blit(time_surf, (SCREEN_WIDTH - time_surf.get_width() - 10, 10))

def draw_drag_transition():
    """Interpolates time position/size while dragging."""
    progress = min(1, drag_offset / unlock_threshold)

    # Interpolate position
    start_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    end_pos = (SCREEN_WIDTH - 80, 30)
    interp_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    interp_y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress

    # Interpolate size
    start_size = 72
    end_size = 24
    font_size = int(start_size - (start_size - end_size) * progress)
    interp_font = pygame.font.SysFont("Arial", font_size, bold=True)

    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    time_surf = interp_font.render(time_str, True, (0, 0, 0))
    time_rect = time_surf.get_rect(center=(interp_x, interp_y))

    # Rounded background box for visibility at start of drag
    if progress < 0.8:
        padding = 20
        box_rect = time_rect.copy()
        box_rect.inflate_ip(padding, padding)
        pygame.draw.rect(screen, (255, 255, 255, int(180 * (1 - progress))), box_rect, border_radius=20)

    screen.blit(time_surf, time_rect)

def draw_login_ui():
    pygame.draw.rect(screen, (230, 230, 230), input_box, border_radius=8)
    masked = "*" * len(input_password)
    pw_surface = small_font.render(masked, True, (0, 0, 0))
    screen.blit(pw_surface, (input_box.x + 10, input_box.y + 10))

    pygame.draw.rect(screen, (70, 130, 180), login_button, border_radius=8)
    btn_text = small_font.render("Login", True, (255, 255, 255))
    screen.blit(btn_text, btn_text.get_rect(center=login_button.center))

    if error_message:
        err_surf = tiny_font.render(error_message, True, (255, 0, 0))
        screen.blit(err_surf, err_surf.get_rect(center=(SCREEN_WIDTH // 2, login_button.bottom + 25)))

    title = small_font.render("Enter your password", True, (0, 0, 0))
    title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, input_box.y - 30))
    screen.blit(title, title_rect)

def check_login():
    global input_password, error_message
    if input_password.strip() == stored_password or stored_password == "no_password_created_by_user_autologin":
        return True
    else:
        error_message = "Incorrect password"
        input_password = ""
        return False

def lock_screen():
    global bg_index, next_bg_index, last_switch_time, fading, fade_start_time
    global dragging, drag_start_y, drag_offset, unlocked
    global arrow_y, arrow_pulse_direction, input_password, error_message

    while True:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - last_switch_time

        # Background crossfade
        if not unlocked:
            if not fading and elapsed >= BG_DISPLAY_TIME:
                fading = True
                fade_start_time = current_time

            alpha = 0
            if fading:
                fade_elapsed = current_time - fade_start_time
                alpha = min(fade_elapsed / BG_FADE_TIME, 1)
                if alpha >= 1:
                    fading = False
                    last_switch_time = current_time
                    bg_index = next_bg_index
                    next_bg_index = (next_bg_index + 1) % len(background_images)

            if len(background_images) == 1:
                screen.blit(background_images[0], (0, 0))
            else:
                screen.blit(blend_images(background_images[bg_index], background_images[next_bg_index], alpha), (0, 0))
        else:
            screen.fill((255, 255, 255))

        # Arrow animation
        if not unlocked:
            arrow_y += arrow_pulse_direction * arrow_pulse_speed
            if arrow_y > arrow_base_y + arrow_pulse_range:
                arrow_pulse_direction = -1
            elif arrow_y < arrow_base_y - arrow_pulse_range:
                arrow_pulse_direction = 1

        # Time & Login UI
        if not unlocked and not dragging:
            draw_center_time_with_box()
            draw_pulsing_arrow(screen, arrow_x, int(arrow_y))
        elif dragging and not unlocked:
            draw_drag_transition()
            draw_pulsing_arrow(screen, arrow_x, int(arrow_y))
        elif unlocked:
            draw_top_right_time_small()
            draw_login_ui()

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif not unlocked:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if abs(event.pos[0] - arrow_x) < 40 and abs(event.pos[1] - arrow_y) < 40:
                        dragging = True
                        drag_start_y = event.pos[1]
                elif event.type == pygame.MOUSEMOTION and dragging:
                    drag_offset = max(0, drag_start_y - event.pos[1])
                    if drag_offset > unlock_threshold:
                        unlocked = True
                        dragging = False
                        input_password = ""
                        error_message = ""
                elif event.type == pygame.MOUSEBUTTONUP:
                    dragging = False

            else:  # Unlocked → Login screen
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if input_box.collidepoint(event.pos):
                        typed = pass_keyboard.run_keyboard()
                        if typed is not None:
                            input_password = typed
                    elif login_button.collidepoint(event.pos):
                        if check_login():
                            return True

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_password = input_password[:-1]
                    elif event.key == pygame.K_RETURN:
                        if check_login():
                            return True

        clock.tick(60)

if __name__ == "__main__":
    if lock_screen():
        try:
            subprocess.Popen(["python3", main_app])
        except Exception as e:
            print(f"Failed to launch app '{main_app}': {e}")
    pygame.quit()
