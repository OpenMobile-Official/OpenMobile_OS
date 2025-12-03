import pygame
import sys
import requests
import zipfile
import io
import os
import json
import threading
import queue
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard  # Use your keyboard module

# --- Constants ---
GITHUB_BASE = "https://raw.githubusercontent.com/OpenMobile-Official/OpenMobile_OS/appstore"
LOCAL_APPS_DIR = "./apps/"
CONFIG_PATH = "./config/apps.json"
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 320

# --- Globals ---
status_message = ""
scroll_offset = 0
scroll_speed = 0
touch_start_y = None
apps = []
icons = {}
loading_apps = True
task_queue = queue.Queue()

# --- Networking & File Helpers ---
def fetch_app_list():
    global apps, loading_apps
    url = f"{GITHUB_BASE}/appstore.json"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        apps[:] = [app for app in data if app.get("App:")]
        task_queue.put(lambda: set_status(f"{len(apps)} apps loaded."))
        load_all_icons()
    except Exception as e:
        task_queue.put(lambda: set_status(f"Failed to fetch app list: {e}"))
    finally:
        loading_apps = False

def load_icon(app_name, folder):
    icon_url = f"{GITHUB_BASE}/{folder}/icon.jpg"
    try:
        response = requests.get(icon_url, timeout=5)
        surf = pygame.image.load(io.BytesIO(response.content))
        surf = pygame.transform.scale(surf, (64, 64))
        task_queue.put(lambda: icons.update({app_name: surf}))
    except:
        task_queue.put(lambda: icons.update({app_name: None}))

def load_all_icons():
    for app in apps:
        app_name = app["App:"].strip()
        folder = app.get("Thumb:", "").strip()
        threading.Thread(target=load_icon, args=(app_name, folder), daemon=True).start()

def flatten_zip(zip_file, target_dir):
    for zip_info in zip_file.infolist():
        if zip_info.is_dir(): continue
        if zip_info.filename.startswith("__MACOSX") or zip_info.filename.endswith(".DS_Store"):
            continue
        parts = zip_info.filename.split('/')
        if len(parts) > 1 and parts[0].lower() == target_dir.split('/')[-1].lower():
            parts = parts[1:]
        flattened_path = os.path.join(target_dir, *parts)
        os.makedirs(os.path.dirname(flattened_path), exist_ok=True)
        with zip_file.open(zip_info) as source, open(flattened_path, "wb") as target:
            target.write(source.read())

# --- App Management ---
def download_and_install(app):
    try:
        app_name = app["App:"].strip()
        zip_url = f"{GITHUB_BASE}/{app['File:']}"
        response = requests.get(zip_url, timeout=10)
        app_path = os.path.join(LOCAL_APPS_DIR, app_name)
        os.makedirs(app_path, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            flatten_zip(z, app_path)
        task_queue.put(lambda: update_config(app_name))
        task_queue.put(lambda: set_status(f"{app_name} installed successfully!"))
    except Exception as e:
        task_queue.put(lambda: set_status(f"Error installing {app_name}: {e}"))

def uninstall_app(app_name):
    try:
        app_path = os.path.join(LOCAL_APPS_DIR, app_name)
        if os.path.exists(app_path):
            for root, dirs, files in os.walk(app_path, topdown=False):
                for file in files: os.remove(os.path.join(root, file))
                for dir in dirs: os.rmdir(os.path.join(root, dir))
            os.rmdir(app_path)
        task_queue.put(lambda: remove_from_config(app_name))
        task_queue.put(lambda: set_status(f"{app_name} uninstalled."))
    except Exception as e:
        task_queue.put(lambda: set_status(f"Error uninstalling {app_name}: {e}"))

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

def remove_from_config(app_name):
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config = [entry for entry in config if entry["name"] != app_name]
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except:
        pass

def is_installed(app_name):
    return os.path.exists(os.path.join(LOCAL_APPS_DIR, app_name))

def set_status(msg):
    global status_message
    status_message = msg

# --- Main ---
def main():
    global scroll_offset, touch_start_y, scroll_speed
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("App Store")
    font_small = pygame.font.SysFont("Arial", 16)
    font_medium = pygame.font.SysFont("Arial", 20)
    font_title = pygame.font.SysFont("Arial", 24, bold=True)

    topbar = TopBarManager(SCREEN_WIDTH, SCREEN_HEIGHT, font_small, font_medium, app_key="appstore")
    clock = pygame.time.Clock()

    search_text = ""
    filtered_apps = apps.copy()

    threading.Thread(target=fetch_app_list, daemon=True).start()

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

                # Search button click
                search_btn_rect = pygame.Rect(SCREEN_WIDTH - 110, 20, 90, 30)
                if search_btn_rect.collidepoint(event.pos):
                    search_text = run_keyboard()
                    filtered_apps = [app for app in apps if search_text.lower() in app["App:"].lower()]

            elif event.type == pygame.MOUSEBUTTONUP:
                touch_start_y = None
                scroll_speed *= 0.9

            elif event.type == pygame.MOUSEMOTION and touch_start_y is not None:
                dy = event.pos[1] - touch_start_y
                scroll_offset += dy
                scroll_speed = dy
                touch_start_y = event.pos[1]

        if touch_start_y is None:
            scroll_offset += scroll_speed
            scroll_speed *= 0.9

        while not task_queue.empty():
            task_queue.get()()

        # --- Draw ---
        screen.fill((30, 30, 30))

        # Draw apps first (background content)
        top_height = 70
        y_offset = top_height + 10 + scroll_offset
        draw_apps = filtered_apps if search_text else apps
        for i, app in enumerate(draw_apps):
            app_name = app["App:"].strip()
            icon = icons.get(app_name)
            y = y_offset + i * 100
            if -120 < y < SCREEN_HEIGHT:
                card_rect = pygame.Rect(10, y, SCREEN_WIDTH - 20, 90)
                pygame.draw.rect(screen, (50, 50, 50), card_rect, border_radius=10)

                if icon:
                    screen.blit(icon, (20, y + 13))
                else:
                    pygame.draw.rect(screen, (100, 100, 100), (20, y + 13, 64, 64), border_radius=8)

                name_surf = font_medium.render(app_name, True, (255, 255, 255))
                screen.blit(name_surf, (100, y + 15))
                desc_surf = font_small.render(app.get("Desc:", ""), True, (180, 180, 180))
                screen.blit(desc_surf, (100, y + 40))

                btn_color = (70, 130, 180)
                btn_text = "Install"
                if is_installed(app_name):
                    btn_color = (180, 70, 70)
                    btn_text = "Uninstall"
                btn_rect = pygame.Rect(SCREEN_WIDTH - 120, y + 40, 100, 35)
                if btn_rect.collidepoint(mouse_pos):
                    btn_color = tuple(min(c + 30, 255) for c in btn_color)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=8)
                btn_surf = font_small.render(btn_text, True, (255, 255, 255))
                screen.blit(btn_surf, btn_surf.get_rect(center=btn_rect.center))

                if btn_rect.collidepoint(mouse_pos) and mouse_clicked:
                    if is_installed(app_name):
                        threading.Thread(target=uninstall_app, args=(app_name,), daemon=True).start()
                    else:
                        threading.Thread(target=download_and_install, args=(app,), daemon=True).start()

        # Draw gradient over apps
        for i in range(top_height):
            pygame.draw.line(screen, (40 + i, 80 + i, 120 + i), (0, i), (SCREEN_WIDTH, i))

        # UI text and buttons
        title_surf = font_title.render("App Store", True, (255, 255, 255))
        screen.blit(title_surf, (20, 20))

        search_btn_rect = pygame.Rect(SCREEN_WIDTH - 110, 20, 90, 30)
        pygame.draw.rect(screen, (70, 130, 180), search_btn_rect, border_radius=6)
        search_label = font_small.render("Search", True, (255, 255, 255))
        screen.blit(search_label, search_label.get_rect(center=search_btn_rect.center))

        # Status message
        if status_message:
            status_surf = font_small.render(status_message, True, (255, 255, 0))
            screen.blit(status_surf, (20, SCREEN_HEIGHT - 30))

        # TopBar overlay (last layer)
        topbar.update()
        topbar.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
