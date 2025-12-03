# ui_final_with_remove_modal.py
# Full replacement file — paste over your previous UI main file.
# Keep config/, apps.json, folders.json, modules/ as before.

import pygame
import sys
from datetime import datetime
import os
import json
import subprocess
import math

import time
from modules.keyboard import run_keyboard

from modules.notification_manager import NotificationManager
from modules.notification_center import NotificationCenter

pygame.init()

# --- Load configuration ---
CONFIG_DIR = "config"
os.makedirs(CONFIG_DIR, exist_ok=True)

with open(os.path.join(CONFIG_DIR, "config.json")) as f:
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
ACCENT = (60, 140, 220)

# Animation
ANIMATION_DURATION = 300
animation_start_time = None
animation_direction = 0
previous_page = 0
next_apps = []

# Managers
notification_manager = NotificationManager(SCREEN_WIDTH, SCREEN_HEIGHT, font_small)
notification_center = NotificationCenter(screen, notification_manager.notifications)

# --- Folder system files
FOLDERS_PATH = os.path.join(CONFIG_DIR, "folders.json")
if not os.path.exists(FOLDERS_PATH):
    default_folders = [{"name": "Utilities", "apps": []}]
    with open(FOLDERS_PATH, "w") as f:
        json.dump(default_folders, f, indent=4)

with open(FOLDERS_PATH) as f:
    folder_data = json.load(f)

# --- Constants for interaction
LONG_PRESS_MS = 500  # long-press threshold in milliseconds
DRAG_START_DISTANCE = 8  # pixels tolerance to start drag

# --- Utils ---
def get_icons_for_page(all_icons, page, icons_per_page):
    start_idx = page * icons_per_page
    end_idx = start_idx + icons_per_page
    page_icons = all_icons[start_idx:end_idx]

    # Recalculate positions for this page
    total_width = COLUMNS * ICON_WIDTH + (COLUMNS - 1) * PADDING
    start_x = (SCREEN_WIDTH - total_width) // 2

    for idx, icon in enumerate(page_icons):
        row = idx // COLUMNS
        col = idx % COLUMNS
        icon.rect.topleft = (start_x + col * (ICON_WIDTH + PADDING),
                             MARGIN_TOP + row * (ICON_HEIGHT + SCREEN_HEIGHT // 20))

    return page_icons

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
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surface.blit(overlay, (0, 0))

def save_folders():
    try:
        with open(FOLDERS_PATH, "w") as f:
            json.dump(folder_data, f, indent=4)
    except Exception as e:
        print("Failed to save folders.json:", e)

# --- App Icon / Folder Class ---
class AppIcon:
    def __init__(self, name, command=None, x=0, y=0, is_folder=False, folder_apps=None):
        self.name = name
        self.command = command
        self.rect = pygame.Rect(x, y, ICON_WIDTH, ICON_HEIGHT)
        self.is_folder = is_folder
        self.folder_apps = folder_apps or []
        self.dragging = False
        self.icon_img = None
        if is_folder:
            # generate preview thumbnail surface (rounded)
            self.icon_img = self.create_folder_preview_surface(self.folder_apps)
        else:
            self.icon_img = self.load_icon()

    def load_icon(self):
        # try to find an icon in the app's directory; fall back to None
        if not self.command:
            return None
        try:
            command_parts = self.command.split()
            script_path = None
            for part in command_parts:
                if part.endswith(".py") and os.path.exists(part):
                    script_path = part
                    break
            if script_path:
                app_dir = os.path.dirname(script_path)
                for ext in ["icon.png", "icon.jpg", "icon.jpeg"]:
                    icon_path = os.path.join(app_dir, ext)
                    if os.path.exists(icon_path):
                        try:
                            icon_img = pygame.image.load(icon_path).convert_alpha()
                            return pygame.transform.smoothscale(icon_img, (ICON_WIDTH, ICON_HEIGHT))
                        except Exception:
                            pass
        except Exception as e:
            print(f"Failed icon load for {self.name}: {e}")
        return None

    def create_folder_preview_surface(self, folder_apps):
        """
        Create a rounded folder icon surface which contains a 2x2 mini-preview
        of up to 4 apps inside the folder. We return a surface sized ICON_WIDTH x ICON_HEIGHT
        with alpha so it blits nicely.
        """
        surf = pygame.Surface((ICON_WIDTH, ICON_HEIGHT), pygame.SRCALPHA)
        surf.fill((0,0,0,0))  # transparent

        # draw base rounded rectangle for folder (background)
        base_rect = pygame.Rect(0, 0, ICON_WIDTH, ICON_HEIGHT)
        # background color slightly different
        bg_col = (235, 235, 240)
        pygame.draw.rect(surf, bg_col, base_rect, border_radius=14)

        # inner preview grid margins
        inner = 8
        cell_w = (ICON_WIDTH - inner*3) // 2
        cell_h = (ICON_HEIGHT - inner*3) // 2

        for i in range(4):
            row = i // 2
            col = i % 2
            x = inner + col * (cell_w + inner)
            y = inner + row * (cell_h + inner)
            rect = pygame.Rect(x, y, cell_w, cell_h)

            if i < len(folder_apps):
                app = folder_apps[i]
                icon_surf = None
                # try to load icon similarly
                try:
                    cmd = app.get("command", "")
                    parts = cmd.split()
                    for p in parts:
                        if p.endswith(".py") and os.path.exists(p):
                            ad = os.path.dirname(p)
                            for ext in ["icon.png", "icon.jpg", "icon.jpeg"]:
                                ip = os.path.join(ad, ext)
                                if os.path.exists(ip):
                                    icon_surf = pygame.image.load(ip).convert_alpha()
                                    icon_surf = pygame.transform.smoothscale(icon_surf, (cell_w, cell_h))
                                    break
                            break
                except Exception:
                    icon_surf = None

                if icon_surf:
                    surf.blit(icon_surf, rect)
                else:
                    color = (160 + (i*10)%70, 160 + (i*5)%70, 200)
                    pygame.draw.rect(surf, color, rect, border_radius=6)
                    initial = font_small.render(app["name"][:1].upper(), True, BLACK)
                    surf.blit(initial, initial.get_rect(center=rect.center))
            else:
                pygame.draw.rect(surf, (245,245,245), rect, border_radius=6)

        # add subtle inner border to make it pop
        pygame.draw.rect(surf, (220,220,220), base_rect.inflate(-2,-2), width=1, border_radius=12)
        return surf

    def draw(self, mouse_pos):
        self._draw_with_offset(mouse_pos, 0)

    def _draw_with_offset(self, mouse_pos, x_offset):
        # ensure mouse_pos is a tuple (x,y)
        if not (isinstance(mouse_pos, (tuple, list)) and len(mouse_pos) == 2):
            mouse_pos = pygame.mouse.get_pos()

        rect = self.rect.move(x_offset, 0)
        shadow_rect = rect.move(3, 3)
        pygame.draw.rect(screen, SHADOW, shadow_rect, border_radius=12)

        hover = rect.collidepoint(mouse_pos)
        # draw a rounded rect background for folder or app
        if self.is_folder:
            # slightly different fill when hovered
            fill_col = (225, 225, 235) if not hover else (210,210,230)
            pygame.draw.rect(screen, fill_col, rect, border_radius=14)
            # draw preview image centered with small inset
            if self.icon_img:
                inset = 4
                target = rect.inflate(-inset*2, -inset*2)
                screen.blit(self.icon_img, target.topleft)
        else:
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
            if self.is_folder:
                # find folder contents by name
                fapps = []
                for f in folder_data:
                    if f["name"] == self.name:
                        fapps = [a for a in app_data if a["name"] in f["apps"]]
                        break
                open_folder(fapps, self.name)
            else:
                try:
                    notification_manager.push(f"Launching {self.name}...")
                    subprocess.Popen(self.command.split())
                    pygame.quit()
                except Exception as e:
                    notification_manager.push(f"Failed to launch {self.name}")
                    print(f"Failed to launch '{self.command}': {e}")

# --- Load apps ---
def load_apps():
    with open(os.path.join(CONFIG_DIR, "apps.json")) as f:
        return json.load(f)

app_data = load_apps()

# --- Home Screen Icons (folders + standalone apps) ---
def create_home_icons(app_data, folders):
    icons = []

    # Determine rows dynamically from config.json
    ROWS = max(1, ICONS_PER_PAGE // COLUMNS)
    icons_per_page = COLUMNS * ROWS

    total_width = COLUMNS * ICON_WIDTH + (COLUMNS - 1) * PADDING
    start_x = (SCREEN_WIDTH - total_width) // 2

    # Combine folders + standalone apps
    all_items = []

    # Add folders
    for folder in folders:
        folder_apps = [a for a in app_data if a["name"] in folder["apps"]]
        # pass folder_apps data (dictionaries) into the folder icon
        all_items.append(("folder", folder["name"], None, folder_apps))

    # Add standalone apps
    apps_in_folders = [a_name for f in folders for a_name in f["apps"]]
    for app in app_data:
        if app["name"] not in apps_in_folders:
            all_items.append(("app", app["name"], app.get("command"), None))

    # Position icons page-by-page
    for idx, item in enumerate(all_items):
        page = idx // icons_per_page
        index_in_page = idx % icons_per_page
        row = index_in_page // COLUMNS
        col = index_in_page % COLUMNS

        x = start_x + col * (ICON_WIDTH + PADDING)
        y = MARGIN_TOP + row * (ICON_HEIGHT + SCREEN_HEIGHT // 20)

        type_, name, command, folder_apps = item

        if type_ == "folder":
            icons.append(AppIcon(name, is_folder=True, folder_apps=folder_apps, x=x, y=y))
        else:
            icons.append(AppIcon(name, command=command, x=x, y=y))

    return icons

# --- Folder UI state ---
folder_open = False
current_folder_apps = []
folder_name = ""
folder_page = 0
folder_pages = 1
folder_icons = []  # AppIcon objects for folder content
folder_animation = None  # (start_time, duration, opening True/False)
folder_scale = 0.0

# --- Remove modal state (iOS-style centered modal) ---
show_remove_modal = False
remove_modal_target = None  # AppIcon object (folder-icons)
remove_modal_rect = None
remove_modal_confirm_rect = None
remove_modal_cancel_rect = None

# --- Press & drag state (fix long-press vs click) ---
press_start_time = None
press_target = None  # AppIcon object targeted by press
press_start_pos = (0,0)
dragging_icon = None
drag_offset = (0,0)
dragging_from_home = False
dragging_from_folder = False

swipe_start_x = None
pull_start_y = None
is_pulling = False
overlay_alpha = 0

# --- Folder open/close functions ---
def open_folder(apps, name):
    global folder_open, current_folder_apps, folder_name, folder_page, folder_pages, folder_icons, folder_animation, folder_scale
    folder_open = True
    folder_name = name

    # apps parameter is list of app dicts
    current_folder_apps = apps.copy()

    # create AppIcon objects for folder content using same grid rules
    icons = []
    ROWS = max(1, ICONS_PER_PAGE // COLUMNS)
    icons_per_page = COLUMNS * ROWS
    total_width = COLUMNS * ICON_WIDTH + (COLUMNS - 1) * PADDING
    start_x = (SCREEN_WIDTH - total_width) // 2

    for idx, app in enumerate(current_folder_apps):
        row = idx // COLUMNS
        col = idx % COLUMNS
        x = start_x + col * (ICON_WIDTH + PADDING)
        y = MARGIN_TOP + row * (ICON_HEIGHT + SCREEN_HEIGHT // 20)
        icons.append(AppIcon(app["name"], command=app.get("command"), x=x, y=y, is_folder=False))

    folder_icons[:] = icons
    folder_page = 0
    folder_pages = max(1, math.ceil(len(folder_icons) / icons_per_page))
    # start zoom-in animation
    folder_animation = (pygame.time.get_ticks(), 200, True)
    folder_scale = 0.0

def close_folder():
    global folder_open, current_folder_apps, folder_name, folder_icons, folder_animation, folder_scale, show_remove_modal, remove_modal_target
    folder_open = False
    current_folder_apps = []
    folder_name = ""
    folder_icons[:] = []
    folder_animation = (pygame.time.get_ticks(), 180, False)
    folder_scale = 1.0
    show_remove_modal = False
    remove_modal_target = None

# --- Status Bar & dots ---
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

## --- Main Loop Setup ---
all_home_icons = create_home_icons(app_data, folder_data)
ROWS = max(1, ICONS_PER_PAGE // COLUMNS)
ICONS_PER_PAGE = COLUMNS * ROWS
total_pages = max(1, (len(all_home_icons) + ICONS_PER_PAGE - 1) // ICONS_PER_PAGE)
current_page = 0
apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
next_apps = []

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    screen.blit(background_img, (0, 0))
    draw_status_bar()

    # --- Render UI: folder overlay or home ---
    if folder_open:
        # apply folder open/close animation scale
        if folder_animation:
            start_time, duration, opening = folder_animation
            elapsed = pygame.time.get_ticks() - start_time
            t = min(1.0, elapsed / duration)
            if opening:
                folder_scale = 0.9 + 0.1 * t  # small scale up effect
            else:
                folder_scale = 1.0 - 0.2 * t
            if t >= 1.0:
                folder_animation = None
        else:
            folder_scale = 1.0

        # dim background
        draw_dim_background(screen, 120)

        # folder title and close button
        label = font_medium.render(folder_name, True, BLACK)
        label_rect = label.get_rect(center=(SCREEN_WIDTH // 2, 15))
        screen.blit(label, label_rect)

        close_rect = pygame.Rect(SCREEN_WIDTH - 60, 10, 50, 28)
        pygame.draw.rect(screen, LIGHT_BLUE, close_rect, border_radius=6)
        close_label = font_small.render("Close", True, BLACK)
        screen.blit(close_label, close_label.get_rect(center=close_rect.center))

        # draw page dots for folder
        icons_per_page = COLUMNS * ROWS
        folder_pages = max(1, math.ceil(len(folder_icons) / icons_per_page))
        draw_page_dots(folder_page, folder_pages)

        # determine page apps
        start_idx = folder_page * icons_per_page
        page_icons = folder_icons[start_idx:start_idx+icons_per_page]

        # Draw each app
        for app in page_icons:
            app.draw(mouse_pos)

        # Draw remove modal if active
        if show_remove_modal and remove_modal_rect:
            # modal background shadow
            pygame.draw.rect(screen, (20,20,20,200), remove_modal_rect.inflate(8,8), border_radius=14)
            pygame.draw.rect(screen, (255,255,255), remove_modal_rect, border_radius=12)
            title = font_medium.render("Remove from folder", True, BLACK)
            title_rect = title.get_rect(center=(remove_modal_rect.centerx, remove_modal_rect.y + 26))
            screen.blit(title, title_rect)

            # confirm & cancel buttons
            pygame.draw.rect(screen, (220,50,50), remove_modal_confirm_rect, border_radius=8)
            pygame.draw.rect(screen, (200,200,200), remove_modal_cancel_rect, border_radius=8)
            c_txt = font_small.render("Remove", True, WHITE)
            x_txt = font_small.render("Cancel", True, BLACK)
            screen.blit(c_txt, c_txt.get_rect(center=remove_modal_confirm_rect.center))
            screen.blit(x_txt, x_txt.get_rect(center=remove_modal_cancel_rect.center))

    else:
        # Home UI
        draw_page_dots(current_page, total_pages)

        # --- Handle page animation ---
        if animation_start_time is not None:
            elapsed = pygame.time.get_ticks() - animation_start_time
            progress = min(elapsed / ANIMATION_DURATION, 1)
            offset = int(animation_direction * SCREEN_WIDTH * (1 - progress))

            # Draw current page
            for app in apps:
                app._draw_with_offset(mouse_pos, offset)

            # Draw next page
            for app in next_apps:
                app._draw_with_offset(mouse_pos, offset + (-animation_direction * SCREEN_WIDTH))

            if progress >= 1:
                animation_start_time = None
                apps = next_apps.copy()
                next_apps = []
                for app in apps:
                    app.rect.topleft = app.rect.topleft  # ensures no offset remains

        else:
            for app in apps:
                app.draw(mouse_pos)

    # --- Event handling ---
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        notification_manager.handle_event(event)
        if notification_manager.active_dialogue:
            continue

        # mouse wheel: change pages
        if event.type == pygame.MOUSEWHEEL:
            if folder_open:
                if event.y < 0 and folder_page < folder_pages - 1:
                    folder_page += 1
                elif event.y > 0 and folder_page > 0:
                    folder_page -= 1
            else:
                if event.y < 0 and current_page < total_pages - 1:
                    animation_direction = -1
                    current_page += 1
                    animation_start_time = pygame.time.get_ticks()
                    next_apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
                elif event.y > 0 and current_page > 0:
                    animation_direction = 1
                    current_page -= 1
                    animation_start_time = pygame.time.get_ticks()
                    next_apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)

        # mouse button down: set possible press target; don't start drag immediately
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            swipe_start_x = x
            # pulling for notifications
            if y < 20:
                pull_start_y = y
                is_pulling = True

            # if modal is open, clicks go to modal buttons (we handle on mouseup)
            if show_remove_modal:
                # just record; actual action handled on MOUSEBUTTONUP
                pass
            else:
                if not folder_open:
                    # detect press on any visible home icon (current page icons)
                    for app in apps:
                        if app.rect.collidepoint(event.pos):
                            press_start_time = pygame.time.get_ticks()
                            press_target = app
                            press_start_pos = event.pos
                            # do not start drag immediately
                            break
                else:
                    # folder open: detect press on folder's page icons or close button
                    close_rect = pygame.Rect(SCREEN_WIDTH - 60, 10, 50, 28)
                    if close_rect.collidepoint(event.pos):
                        press_start_time = pygame.time.get_ticks()
                        press_target = None  # pressing close
                        press_start_pos = event.pos
                    else:
                        icons_per_page = COLUMNS * ROWS
                        start_idx = folder_page * icons_per_page
                        page_icons = folder_icons[start_idx:start_idx+icons_per_page]
                        for app in page_icons:
                            if app.rect.collidepoint(event.pos):
                                press_start_time = pygame.time.get_ticks()
                                press_target = app
                                press_start_pos = event.pos
                                # don't start drag yet — allow long-press to occur
                                break

        # mouse up: interpret as click / long-press confirm / drag end
        elif event.type == pygame.MOUSEBUTTONUP:
            # stop pull
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

            # If remove modal is showing, check button clicks
            if show_remove_modal and remove_modal_rect:
                if remove_modal_confirm_rect.collidepoint(event.pos) and remove_modal_target:
                    # perform removal: remove name from the folder_data entry, move app to end of app_data
                    target_name = remove_modal_target.name
                    for f in folder_data:
                        if f["name"] == folder_name:
                            if target_name in f["apps"]:
                                f["apps"].remove(target_name)
                                # move app dict to end of app_data to make it appear last
                                popped = None
                                for i,a in enumerate(app_data):
                                    if a["name"] == target_name:
                                        popped = app_data.pop(i)
                                        break
                                if popped:
                                    app_data.append(popped)
                                save_folders()
                                # rebuild home icons and keep current page
                                all_home_icons = create_home_icons(app_data, folder_data)
                                total_pages = max(1, (len(all_home_icons) + ICONS_PER_PAGE - 1) // ICONS_PER_PAGE)
                                apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
                                notification_manager.push(f"Removed {target_name} from {folder_name}")
                            break
                # hide modal after any click
                show_remove_modal = False
                remove_modal_target = None
                remove_modal_rect = None
                remove_modal_confirm_rect = None
                remove_modal_cancel_rect = None
                press_start_time = None
                press_target = None
                continue  # we've handled the modal click event; skip other logic

            # If we were dragging an icon, handle drop logic
            if dragging_icon and (dragging_from_home or dragging_from_folder):
                # home -> folder drop
                if dragging_from_home:
                    dropped = False
                    for folder_icon in all_home_icons:
                        if folder_icon.is_folder and folder_icon.rect.collidepoint(event.pos):
                            folder_name_target = folder_icon.name
                            for f in folder_data:
                                if f["name"] == folder_name_target:
                                    if dragging_icon.name not in f["apps"]:
                                        f["apps"].append(dragging_icon.name)
                                        # remove from other folders just in case
                                        for other in folder_data:
                                            if other is not f and dragging_icon.name in other["apps"]:
                                                other["apps"].remove(dragging_icon.name)
                                        save_folders()
                                        all_home_icons = create_home_icons(app_data, folder_data)
                                        total_pages = max(1, (len(all_home_icons) + ICONS_PER_PAGE - 1) // ICONS_PER_PAGE)
                                        apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
                                        notification_manager.push(f"Moved {dragging_icon.name} into {folder_name_target}")
                                        dropped = True
                                    break
                            break
                    dragging_icon.dragging = False
                    dragging_icon = None
                    dragging_from_home = False
                    dragging_from_folder = False
                elif dragging_from_folder:
                    # drop-out logic: if released outside folder area (we treat any release not over folder overlay as drop-out)
                    # For simplicity, we'll treat releasing outside the folder overlay area as removal
                    # Remove from folder_data and move to end of app_data
                    target_name = None
                    if dragging_icon:
                        target_name = dragging_icon.name
                    if target_name:
                        for f in folder_data:
                            if f["name"] == folder_name:
                                if target_name in f["apps"]:
                                    f["apps"].remove(target_name)
                                    popped = None
                                    for i,a in enumerate(app_data):
                                        if a["name"] == target_name:
                                            popped = app_data.pop(i)
                                            break
                                    if popped:
                                        app_data.append(popped)
                                    save_folders()
                                    all_home_icons = create_home_icons(app_data, folder_data)
                                    apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
                                    notification_manager.push(f"Removed {target_name} from {folder_name}")
                                break
                    if dragging_icon:
                        dragging_icon.dragging = False
                    dragging_icon = None
                    dragging_from_folder = False
                    dragging_from_home = False

                # reset press tracking
                press_start_time = None
                press_target = None
                continue

            # If no dragging, interpret press duration for click vs long-press
            if press_start_time and press_target:
                duration = pygame.time.get_ticks() - press_start_time
                target = press_target
                press_start_time = None
                press_target = None

                # If short press -> launch / open
                if duration < LONG_PRESS_MS:
                    if folder_open:
                        # If target is app in folder, launch or open rename
                        if target.is_folder:
                            # shouldn't happen: folder icons aren't present inside folder overlay
                            pass
                        else:
                            # launch app
                            # find app's command by name in app_data
                            cmd = None
                            for a in app_data:
                                if a["name"] == target.name:
                                    cmd = a.get("command")
                                    break
                            if cmd:
                                try:
                                    notification_manager.push(f"Launching {target.name}...")
                                    subprocess.Popen(cmd.split())
                                    pygame.quit()
                                except Exception as e:
                                    notification_manager.push(f"Failed to launch {target.name}")
                                    print("Launch error:", e)
                    else:
                        # home short click: open folder or launch app
                        if target.is_folder:
                            # open folder by name
                            fapps = []
                            for f in folder_data:
                                if f["name"] == target.name:
                                    fapps = [a for a in app_data if a["name"] in f["apps"]]
                                    break
                            open_folder(fapps, target.name)
                        else:
                            # launch
                            cmd = None
                            for a in app_data:
                                if a["name"] == target.name:
                                    cmd = a.get("command")
                                    break
                            if cmd:
                                try:
                                    notification_manager.push(f"Launching {target.name}...")
                                    subprocess.Popen(cmd.split())
                                    pygame.quit()
                                except Exception as e:
                                    notification_manager.push(f"Failed to launch {target.name}")
                                    print("Launch error:", e)
                else:
                    # LONG PRESS: show the iOS-style centered remove modal (only valid inside folder)
                    if folder_open and not target.is_folder:
                        # prepare modal rect and buttons
                        modal_w = min(360, SCREEN_WIDTH - 40)
                        modal_h = 120
                        modal_x = (SCREEN_WIDTH - modal_w) // 2
                        modal_y = (SCREEN_HEIGHT - modal_h) // 2
                        remove_modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
                        btn_w = 120
                        btn_h = 40
                        confirm_x = modal_x + modal_w - btn_w - 20
                        confirm_y = modal_y + modal_h - btn_h - 16
                        cancel_x = modal_x + 20
                        cancel_y = confirm_y
                        remove_modal_confirm_rect = pygame.Rect(confirm_x, confirm_y, btn_w, btn_h)
                        remove_modal_cancel_rect = pygame.Rect(cancel_x, cancel_y, btn_w, btn_h)
                        show_remove_modal = True
                        remove_modal_target = target
                        # store modal rects into outer scope
                        # we store by reassigning global names
                        globals()['remove_modal_rect'] = remove_modal_rect
                        globals()['remove_modal_confirm_rect'] = remove_modal_confirm_rect
                        globals()['remove_modal_cancel_rect'] = remove_modal_cancel_rect
                        globals()['show_remove_modal'] = show_remove_modal
                        globals()['remove_modal_target'] = remove_modal_target
                        # nothing else — wait for user to confirm
                        press_target = None
                        press_start_time = None
                        continue

            # reset press target if nothing else
            press_start_time = None
            press_target = None

        # mouse motion: used to detect drag start and pull-to-notif
        elif event.type == pygame.MOUSEMOTION:
            # handle pull-to-open-notification dragging
            if event.buttons and event.buttons[0] and is_pulling:
                _, y = event.pos
                drag_distance = y - (pull_start_y or 0)
                notification_center.offset_y = max(0, min(drag_distance, SCREEN_HEIGHT))
                overlay_alpha = min(180, drag_distance)

            # If user pressed an icon and moved beyond threshold -> start dragging
            if press_target and not dragging_icon:
                mx, my = event.pos
                sx, sy = press_start_pos
                if abs(mx - sx) > DRAG_START_DISTANCE or abs(my - sy) > DRAG_START_DISTANCE:
                    # begin dragging
                    dragging_icon = press_target
                    drag_offset = (sx - dragging_icon.rect.x, sy - dragging_icon.rect.y)
                    # determine origin: if folder_open and target was from folder -> dragging_from_folder
                    if folder_open:
                        dragging_from_folder = True
                        dragging_from_home = False
                    else:
                        dragging_from_home = True
                        dragging_from_folder = False
                    dragging_icon.dragging = True
                    # clear press_target to avoid long-press trigger
                    press_start_time = None
                    press_target = None

            # If dragging an icon, update its position to follow cursor
            if dragging_icon and dragging_icon.dragging:
                mx, my = event.pos
                dragging_icon.rect.x = mx - drag_offset[0]
                dragging_icon.rect.y = my - drag_offset[1]

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r and folder_open:
                # rename the app under mouse in folder (console-based)
                icons_per_page = COLUMNS * ROWS
                start_idx = folder_page * icons_per_page
                page_icons = folder_icons[start_idx:start_idx+icons_per_page]
                for app in page_icons:
                    if app.rect.collidepoint(mouse_pos):
                        try:
                            new_name = input(f"Rename '{app.name}' to: ").strip()
                            if new_name:
                                # update in app_data or folder listings
                                for a in app_data:
                                    if a["name"] == app.name:
                                        a["name"] = new_name
                                        break
                                for f in folder_data:
                                    for i, nm in enumerate(f["apps"]):
                                        if nm == app.name:
                                            f["apps"][i] = new_name
                                save_folders()
                                app.name = new_name
                                notification_manager.push(f"Renamed to {new_name}")
                                all_home_icons = create_home_icons(app_data, folder_data)
                                apps = get_icons_for_page(all_home_icons, current_page, ICONS_PER_PAGE)
                        except Exception as e:
                            print("Rename failed:", e)
                        break

    # --- Notification check (file) ---
    notify_file = os.path.join(CONFIG_DIR, "notify.txt")
    if os.path.exists(notify_file):
        with open(notify_file) as f:
            message = f.read().strip()
        if message:
            notification_manager.push(message)
        open(notify_file, "w").close()

    notification_manager.update()
    notification_center.update(events)

    if notification_center.is_open or is_pulling:
        draw_dim_background(screen, overlay_alpha)
    notification_center.draw()
    notification_manager.draw(screen)

    # Draw dragging icon above everything (fix: pass full mouse tuple)
    if dragging_icon:
        mx, my = pygame.mouse.get_pos()
        dragging_icon._draw_with_offset((mx, my), 0)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
