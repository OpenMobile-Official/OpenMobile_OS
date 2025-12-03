import pygame
import sys
import requests
import zipfile
import io
import os
import json
from modules.top_bar import TopBarManager

# Constants
GITHUB_BASE = "https://raw.githubusercontent.com/OpenMobile-Official/OpenMobile_OS/appstore"
LOCAL_APPS_DIR = "./apps/"
CONFIG_PATH = "./config/apps.json"
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 320

# Globals
status_message = ""
scroll_offset = 0
scroll_speed = 0
touch_start_y = None

def fetch_app_list():
    url = f"{GITHUB_BASE}/appstore.json"
    response = requests.get(url)
    try:
        data = json.loads(response.text)
        return [app for app in data if app.get("App:")]
    except json.JSONDecodeError:
        print("Failed to decode JSON. Response was:")
        print(response.text)
        return []

def flatten_zip(zip_file, target_dir):
    for zip_info in zip_file.infolist():
        if zip_info.is_dir():
            continue
        if zip_info.filename.startswith("__MACOSX") or zip_info.filename.endswith(".DS_Store"):
            continue
        parts = zip_info.filename.split('/')
        if len(parts) > 1 and parts[0].lower() == target_dir.split('/')[-1].lower():
            parts = parts[1:]
        flattened_path = os.path.join(target_dir, *parts)
        os.makedirs(os.path.dirname(flattened_path), exist_ok=True)
        with zip_file.open(zip_info) as source, open(flattened_path, "wb") as target:
            target.write(source.read())

def download_and_install(app):
    global status_message
    app_name = app["App:"].strip()
    zip_url = f"{GITHUB_BASE}/{app['File:']}"
    status_message = f"Installing {app_name}..."
    pygame.display.flip()
    try:
        response = requests.get(zip_url)
        app_path = os.path.join(LOCAL_APPS_DIR, app_name)
        os.makedirs(app_path, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            flatten_zip(z, app_path)
        update_config(app_name)
        status_message = f"{app_name} installed successfully!"
    except Exception as e:
        status_message = f"Error installing {app_name}: {e}"

def uninstall_app(app_name):
    global status_message
    app_path = os.path.join(LOCAL_APPS_DIR, app_name)
    try:
        if os.path.exists(app_path):
            for root, dirs, files in os.walk(app_path, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(app_path)
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config = [entry for entry in config if entry["name"] != app_name]
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        status_message = f"{app_name} uninstalled."
    except Exception as e:
        status_message = f"Error uninstalling {app_name}: {e}"

def update_config(app_name):
    config_entry = {
        "name": app_name,
        "command": f"python3 apps/{app_name}/{app_name.lower()}.py"
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except:
        config = []
    if config_entry not in config:
        config.append(config_entry)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

def load_icon(app):
    folder = app["Thumb:"].strip()
    icon_url = f"{GITHUB_BASE}/{folder}/icon.jpg"
    try:
        response = requests.get(icon_url)
        return pygame.transform.scale(pygame.image.load(io.BytesIO(response.content)), (64, 64))
    except:
        return None

def is_installed(app_name):
    return os.path.exists(os.path.join(LOCAL_APPS_DIR, app_name))

def main():
    global scroll_offset, scroll_speed, touch_start_y, status_message
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("App Store")

    font_small = pygame.font.SysFont("Arial", 16)
    font_medium = pygame.font.SysFont("Arial", 20)
    topbar = TopBarManager(SCREEN_WIDTH, SCREEN_HEIGHT, font_small, font_medium, app_key="appstore")
    clock = pygame.time.Clock()

    apps = fetch_app_list()
    icons = [load_icon(app) for app in apps]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            topbar.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
                touch_start_y = event.pos[1]
            elif event.type == pygame.MOUSEBUTTONUP:
                touch_start_y = None
                scroll_speed = 0
            elif event.type == pygame.MOUSEMOTION and touch_start_y is not None:
                dy = event.pos[1] - touch_start_y
                scroll_offset += dy
                touch_start_y = event.pos[1]

        topbar.update()
        screen.fill((50, 50, 50))

        y_offset = 70 + scroll_offset
        for i, app in enumerate(apps):
            app_name = app["App:"].strip()
            icon = icons[i]
            y = y_offset + i * 100
            if y > -100 and y < SCREEN_HEIGHT:
                if icon:
                    screen.blit(icon, (20, y))
                name = font_medium.render(app_name, True, (255, 255, 255))
                desc = font_small.render(app["Desc:"], True, (200, 200, 200))
                screen.blit(name, (100, y))
                screen.blit(desc, (100, y + 25))

                if is_installed(app_name):
                    uninstall_rect = pygame.Rect(100, y + 55, 100, 30)
                    pygame.draw.rect(screen, (180, 70, 70), uninstall_rect, border_radius=6)
                    uninstall_label = font_small.render("Uninstall", True, (255, 255, 255))
                    screen.blit(uninstall_label, uninstall_label.get_rect(center=uninstall_rect.center))
                    if uninstall_rect.collidepoint(mouse_pos) and mouse_clicked:
                        uninstall_app(app_name)
                else:
                    install_rect = pygame.Rect(100, y + 55, 100, 30)
                    pygame.draw.rect(screen, (70, 130, 180), install_rect, border_radius=6)
                    install_label = font_small.render("Install", True, (255, 255, 255))
                    screen.blit(install_label, install_label.get_rect(center=install_rect.center))
                    if install_rect.collidepoint(mouse_pos) and mouse_clicked:
                        download_and_install(app)

        if status_message:
            status_surf = font_small.render(status_message, True, (255, 255, 0))
            screen.blit(status_surf, (20, SCREEN_HEIGHT - 30))

        topbar.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
