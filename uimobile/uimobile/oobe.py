# setup.py
import os
import sys
import json
import pygame
import subprocess
from modules import pass_keyboard
from modules.encryption import encrypt_string

# --- Constants ---
AUTOLOGIN_FLAG = "no_password_created_by_user_autologin"
CONFIG_FILE = os.path.join("config", "config.json")
CONFIG_PATH = os.path.join("config", "user.enc")
default_resolution = (480, 320)

# --- Load resolution ---
try:
    with open(CONFIG_FILE, 'r') as f:
        config_data = json.load(f)
        resolution = tuple(config_data.get("resolution", default_resolution))
except Exception as e:
    print(f"Error loading config.json: {e}")
    resolution = default_resolution

# --- Skip if already configured ---
if os.path.exists(CONFIG_PATH):
    print("OOBE skipped: password already set.")
    subprocess.Popen(["python3", "main.py"])
    sys.exit(0)

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode(resolution)
pygame.display.set_caption("Device Setup")
SCREEN_WIDTH, SCREEN_HEIGHT = resolution

# --- Fonts ---
font_title = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.09), bold=True)
font = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.07))
font_hint = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.05), italic=True)

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (60, 60, 60)

# --- Helpers ---
def wait_for_touch():
    while True:
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return

def draw_boxed_text(title, lines, bottom_hint=True):
    screen.fill(WHITE)

    margin_x = int(SCREEN_WIDTH * 0.04)
    title_h = int(SCREEN_HEIGHT * 0.15)
    content_w = SCREEN_WIDTH - 2 * margin_x

    # Title box
    pygame.draw.rect(screen, GRAY, pygame.Rect(margin_x, margin_x, content_w, title_h), border_radius=8)
    title_surf = font_title.render(title, True, BLACK)
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, margin_x + title_h // 2)))

    # Content box
    line_height = int(SCREEN_HEIGHT * 0.08)
    total_height = len(lines) * line_height + 20
    content_top = SCREEN_HEIGHT // 2 - total_height // 2
    pygame.draw.rect(screen, GRAY, pygame.Rect(margin_x, content_top - 20, content_w, total_height), border_radius=10)

    for i, line in enumerate(lines):
        rendered = font.render(line, True, BLACK)
        rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, content_top + i * line_height))
        screen.blit(rendered, rect)

    if bottom_hint:
        hint = font_hint.render("Tap anywhere to continue", True, DARK_GRAY)
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))

    pygame.display.flip()

def get_password(prompt_text):
    screen.fill(WHITE)
    prompt = font_title.render(prompt_text, True, BLACK)
    screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)))
    pygame.display.flip()
    return pass_keyboard.run_keyboard()

def show_yes_no_choice(title, question):
    screen.fill(WHITE)

    title_surf = font_title.render(title, True, BLACK)
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4)))

    question_surf = font.render(question, True, BLACK)
    screen.blit(question_surf, question_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))

    yes_button = pygame.Rect(SCREEN_WIDTH // 4 - 60, SCREEN_HEIGHT // 2 + 40, 120, 60)
    no_button = pygame.Rect(3 * SCREEN_WIDTH // 4 - 60, SCREEN_HEIGHT // 2 + 40, 120, 60)

    pygame.draw.rect(screen, (0, 200, 0), yes_button, border_radius=8)
    pygame.draw.rect(screen, (200, 0, 0), no_button, border_radius=8)

    yes_text = font.render("Yes", True, WHITE)
    no_text = font.render("No", True, WHITE)
    screen.blit(yes_text, yes_text.get_rect(center=yes_button.center))
    screen.blit(no_text, no_text.get_rect(center=no_button.center))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if yes_button.collidepoint(event.pos):
                    return True
                elif no_button.collidepoint(event.pos):
                    return False

# --- UI Steps ---
def show_welcome():
    draw_boxed_text("Welcome", [
        "This device needs a quick setup.",
        "",
        "You'll create a password to secure it."
    ])
    wait_for_touch()

def show_instruction():
    draw_boxed_text("Step 1", [
        "Please enter a password using the keyboard.",
        "",
        "You'll confirm it on the next screen."
    ])
    wait_for_touch()

def show_mismatch():
    draw_boxed_text("Try Again", [
        "The passwords didn't match.",
        "",
        "Let's try that one more time."
    ], bottom_hint=False)
    pygame.time.wait(2500)

def show_success():
    draw_boxed_text("Setup Complete", [
        "Your password was saved securely.",
        "",
        "Rebooting... Please Wait"
    ], bottom_hint=False)
    pygame.time.wait(2500)

# --- Run OOBE ---
show_welcome()

use_password = show_yes_no_choice("Set a Password?", "Would you like to use a password?")

if not use_password:
    # Save autologin flag
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_PATH, "wb") as f:
        f.write(encrypt_string(AUTOLOGIN_FLAG))
    show_success()
    subprocess.Popen(["python3", "main.py"])
    pygame.quit()
    sys.exit(0)

show_instruction()

# --- Password Entry Loop ---
while True:
    pwd1 = get_password("Enter your password")
    if not pwd1.strip():
        draw_boxed_text("Empty Password", [
            "Password cannot be empty.",
            "",
            "Tap to try again."
        ])
        wait_for_touch()
        continue

    pwd2 = get_password("Confirm password")
    if pwd1 != pwd2:
        show_mismatch()
        continue

    # Save password
    os.makedirs("config", exist_ok=True)
    with open(CONFIG_PATH, "wb") as f:
        f.write(encrypt_string(pwd1))

    show_success()
    subprocess.Popen(["python3", "main.py"])
    pygame.quit()
    sys.exit(0)
