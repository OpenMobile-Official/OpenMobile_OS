import pygame
import sys
import os
import shutil
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

#initiate pygame mixer for audio
pygame.mixer.init()

# --- Config ---
BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Files", "User", "Home")

# --- Colors ---
BG_COLOR = (40, 40, 40)
ROW_COLOR1 = (60, 60, 60)
ROW_COLOR2 = (70, 70, 70)
HOVER_COLOR = (100, 100, 140)
BUTTON_COLOR = (70, 130, 180)
TEXT_COLOR = (255, 255, 255)
TOAST_BG = (30, 30, 30)

# --- File list helper ---
def list_directory(path):
    items = []
    try:
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            items.append((name, os.path.isdir(full_path), full_path))
        items.sort(key=lambda x: (not x[1], x[0].lower()))
    except Exception as e:
        print("Error reading directory:", e)
    return items

# --- Toast notification ---
class Toast:
    def __init__(self, text, duration=2):
        self.text = text
        self.duration = duration
        self.start_time = pygame.time.get_ticks()

# --- Preview overlay ---
class Preview:
    def __init__(self, file_path):
        self.file_path = file_path
        self.active = True

def main():
    pygame.init()
    dragging = False
    drag_start_y = 0
    scroll_start_offset = 0

    screen_width, screen_height = 480, 320
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("File Manager")

    font_small = pygame.font.SysFont("Arial", 16)
    font_medium = pygame.font.SysFont("Arial", 20)

    topbar = TopBarManager(screen_width, screen_height, font_small, font_medium, app_key="files")
    clock = pygame.time.Clock()

    current_path = BASE_PATH
    file_items = list_directory(current_path)
    scroll_offset = 0
    item_height = 40
    margin_top = 70
    margin_left = 20
    visible_items = (screen_height - margin_top - 40) // item_height
    
    # Buttons
    back_button_rect = pygame.Rect(10, 40, 80, 25)
    add_folder_rect = pygame.Rect(screen_width - 100, 40, 90, 25)
    paste_button_rect = pygame.Rect(screen_width - 200, 40, 80, 25)

    preview_overlay = None
    toast_messages = []
    delete_popup = None
    delete_rects = {}
    copy_buffer = None
    copy_is_folder = False

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            # Start dragging
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                drag_start_y = event.pos[1]
                scroll_start_offset = scroll_offset

            # Stop dragging
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False

            # Move during drag
            elif event.type == pygame.MOUSEMOTION and dragging:
                delta = event.pos[1] - drag_start_y
                # Sensitivity factor (smaller number = slower scroll)
                scroll_offset = scroll_start_offset - int(delta / item_height)
                scroll_offset = max(0, min(scroll_offset, max(0, len(file_items) - visible_items)))

            if event.type == pygame.QUIT:
                running = False
            topbar.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                elif event.button == 4:
                    scroll_offset = max(scroll_offset - 1, 0)
                elif event.button == 5:
                    scroll_offset = min(scroll_offset + 1, max(0, len(file_items) - visible_items))

        topbar.update()
        screen.fill(BG_COLOR)

        # --- Top buttons ---
        pygame.draw.rect(screen, BUTTON_COLOR, back_button_rect, border_radius=6)
        screen.blit(font_small.render("← Back", True, TEXT_COLOR), (back_button_rect.x + 10, back_button_rect.y + 5))
        pygame.draw.rect(screen, BUTTON_COLOR, add_folder_rect, border_radius=6)
        screen.blit(font_small.render("+ Folder", True, TEXT_COLOR), (add_folder_rect.x + 10, add_folder_rect.y + 5))
        if copy_buffer:
            pygame.draw.rect(screen, BUTTON_COLOR, paste_button_rect, border_radius=6)
            screen.blit(font_small.render("Paste", True, TEXT_COLOR), (paste_button_rect.x + 10, paste_button_rect.y + 5))

        # Back button action
        if mouse_clicked and back_button_rect.collidepoint(mouse_pos):
            parent = os.path.dirname(current_path)
            if os.path.commonpath([BASE_PATH]) in os.path.commonpath([parent]):
                current_path = parent
                file_items = list_directory(current_path)
                scroll_offset = 0

        # Add folder action
        if mouse_clicked and add_folder_rect.collidepoint(mouse_pos):
            folder_name = run_keyboard()
            if folder_name:
                new_path = os.path.join(current_path, folder_name)
                try:
                    os.makedirs(new_path, exist_ok=True)
                    toast_messages.append(Toast(f"Folder '{folder_name}' created!"))
                    file_items = list_directory(current_path)
                except Exception as e:
                    toast_messages.append(Toast(f"Error: {e}"))

        # Paste button
        if copy_buffer and mouse_clicked and paste_button_rect.collidepoint(mouse_pos):
            try:
                dest_path = os.path.join(current_path, os.path.basename(copy_buffer))
                if copy_is_folder:
                    shutil.copytree(copy_buffer, dest_path)
                else:
                    shutil.copy2(copy_buffer, dest_path)
                toast_messages.append(Toast(f"Pasted {os.path.basename(copy_buffer)}"))
                file_items = list_directory(current_path)
                copy_buffer = None
            except Exception as e:
                toast_messages.append(Toast(f"Error: {e}"))

        # --- Path display ---
        path_text = font_small.render(current_path.replace(BASE_PATH, "Home"), True, (200, 200, 200))
        screen.blit(path_text, (110, 45))

        # --- File/Folder list ---
        start_y = margin_top
        for idx, (name, is_dir, full_path) in enumerate(file_items[scroll_offset:scroll_offset + visible_items]):
            rect = pygame.Rect(margin_left, start_y + idx * item_height, screen_width - 40, item_height - 5)
            color = ROW_COLOR1 if idx % 2 == 0 else ROW_COLOR2
            if rect.collidepoint(mouse_pos):
                color = HOVER_COLOR
            pygame.draw.rect(screen, color, rect, border_radius=4)

            # Icon
            icon_color = (0, 180, 255) if is_dir else (255, 200, 100)
            pygame.draw.circle(screen, icon_color, (margin_left + 10, rect.centery), 6)

            # Name
            screen.blit(font_small.render(name, True, TEXT_COLOR), (margin_left + 25, rect.y + 10))

            # Trash / Rename / Copy icons
            trash_rect = pygame.Rect(rect.right - 30, rect.y + 10, 20, 20)
            rename_rect = pygame.Rect(rect.right - 60, rect.y + 10, 20, 20)
            copy_rect = pygame.Rect(rect.right - 90, rect.y + 10, 20, 20)
            pygame.draw.rect(screen, (200, 50, 50), trash_rect, border_radius=3)
            pygame.draw.rect(screen, (50, 200, 50), rename_rect, border_radius=3)
            pygame.draw.rect(screen, (50, 50, 200), copy_rect, border_radius=3)

            if mouse_clicked:
                if trash_rect.collidepoint(mouse_pos):
                    delete_popup = full_path
                elif rename_rect.collidepoint(mouse_pos):
                    new_name = run_keyboard()
                    if new_name:
                        new_path = os.path.join(current_path, new_name)
                        try:
                            os.rename(full_path, new_path)
                            toast_messages.append(Toast(f"Renamed to {new_name}!"))
                            file_items = list_directory(current_path)
                        except Exception as e:
                            toast_messages.append(Toast(f"Error: {e}"))
                elif copy_rect.collidepoint(mouse_pos):
                    copy_buffer = full_path
                    copy_is_folder = is_dir
                    toast_messages.append(Toast(f"Copied {name}"))

            # Tap row to open file/folder
            if mouse_clicked and rect.collidepoint(mouse_pos) and preview_overlay is None:
                if is_dir:
                    current_path = full_path
                    file_items = list_directory(current_path)
                    scroll_offset = 0
                else:
                    preview_overlay = Preview(full_path)

        # --- Scroll bar ---
        if len(file_items) > visible_items:
            bar_height = int((visible_items / len(file_items)) * (screen_height - margin_top - 40))
            bar_y = margin_top + int((scroll_offset / len(file_items)) * (screen_height - margin_top - 40))
            pygame.draw.rect(screen, (120, 120, 120), (screen_width - 10, bar_y, 6, bar_height), border_radius=3)

        # --- Preview overlay ---
        if preview_overlay:
            overlay_rect = pygame.Rect(40, 60, screen_width - 80, screen_height - 120)
            pygame.draw.rect(screen, (50, 50, 50), overlay_rect, border_radius=8)
            close_rect = pygame.Rect(overlay_rect.right - 25, overlay_rect.y + 5, 20, 20)
            pygame.draw.rect(screen, (200, 50, 50), close_rect, border_radius=4)
            if mouse_clicked and close_rect.collidepoint(mouse_pos):
                preview_overlay = None

            # Safe preview
            try:
                file_ext = os.path.splitext(preview_overlay.file_path)[1].lower()
                if file_ext == ".txt":
                    with open(preview_overlay.file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for i, line in enumerate(lines[:int((overlay_rect.height-40)//18)]):
                        screen.blit(font_small.render(line.strip(), True, TEXT_COLOR),
                                    (overlay_rect.x + 10, overlay_rect.y + 30 + i*18))
                elif file_ext in [".jpg", ".png"]:
                    img = pygame.image.load(preview_overlay.file_path)
                    img = pygame.transform.scale(img, (overlay_rect.width-20, overlay_rect.height-50))
                    screen.blit(img, (overlay_rect.x + 10, overlay_rect.y + 30))
                elif file_ext == ".csv":
                    try:
                        with open(preview_overlay.file_path, newline='', encoding="utf-8", errors="ignore") as f:
                            reader = csv.reader(f)
                            for i, row in enumerate(reader):
                                line = ", ".join(row)
                                screen.blit(font_small.render(line[:100], True, TEXT_COLOR),
                                            (overlay_rect.x + 10, overlay_rect.y + 30 + i * 18))
                                if i > (overlay_rect.height - 40) // 18:
                                    break
                    except Exception as e:
                        screen.blit(font_small.render(f"CSV error: {e}", True, TEXT_COLOR),
                                    (overlay_rect.x + 10, overlay_rect.y + 30))

                elif file_ext == ".json":
                    try:
                        with open(preview_overlay.file_path, "r", encoding="utf-8", errors="ignore") as f:
                            data = json.load(f)
                            lines = json.dumps(data, indent=2).splitlines()
                            for i, line in enumerate(lines[:int((overlay_rect.height - 40) // 18)]):
                                screen.blit(font_small.render(line.strip()[:100], True, TEXT_COLOR),
                                            (overlay_rect.x + 10, overlay_rect.y + 30 + i * 18))
                    except Exception as e:
                        screen.blit(font_small.render(f"JSON error: {e}", True, TEXT_COLOR),
                                    (overlay_rect.x + 10, overlay_rect.y + 30))

                # AUDIO PREVIEW BLOCK
                elif file_ext in [".mp3", ".wav", ".ogg"]:
                        try:
                            # Draw label
                            screen.blit(font_small.render("🎵 Audio file detected", True, TEXT_COLOR),
                                        (overlay_rect.x + 10, overlay_rect.y + 30))

                            # Playback controls
                            button_width = 80
                            button_height = 30
                            button_y = overlay_rect.y + overlay_rect.height - 50
                            button_x = overlay_rect.x + 10

                            # Play button
                            play_rect = pygame.Rect(button_x, button_y, button_width, button_height)
                            pygame.draw.rect(screen, (70, 130, 180), play_rect)
                            screen.blit(font_small.render("Play", True, (255, 255, 255)), (button_x + 20, button_y + 5))
                            if event.type == pygame.MOUSEBUTTONDOWN and play_rect.collidepoint(event.pos):
                                try:
                                    pygame.mixer.music.load(preview_overlay.file_path)
                                    pygame.mixer.music.play()
                                except Exception as e:
                                    print(f"Play error: {e}")

                            # Pause/Resume button
                            pause_rect = pygame.Rect(button_x + 90, button_y, button_width, button_height)
                            pygame.draw.rect(screen, (255, 165, 0), pause_rect)
                            screen.blit(font_small.render("Pause", True, (0, 0, 0)), (button_x + 110, button_y + 5))
                            if event.type == pygame.MOUSEBUTTONDOWN and pause_rect.collidepoint(event.pos):
                                if pygame.mixer.music.get_busy():
                                    pygame.mixer.music.pause()
                                else:
                                    pygame.mixer.music.unpause()

                            # Stop button
                            stop_rect = pygame.Rect(button_x + 180, button_y, button_width, button_height)
                            pygame.draw.rect(screen, (220, 20, 60), stop_rect)
                            screen.blit(font_small.render("Stop", True, (255, 255, 255)), (button_x + 200, button_y + 5))
                            if event.type == pygame.MOUSEBUTTONDOWN and stop_rect.collidepoint(event.pos):
                                pygame.mixer.music.stop()

                            # Volume label
                            volume = int(pygame.mixer.music.get_volume() * 100)
                            volume_label = font_small.render(f"Volume: {volume}%", True, TEXT_COLOR)
                            screen.blit(volume_label, (button_x + 280, button_y + 5))

                        except Exception as e:
                            screen.blit(font_small.render(f"Audio error: {e}", True, TEXT_COLOR),
                                        (overlay_rect.x + 10, overlay_rect.y + 60))

                elif file_ext in [".mp4", ".mov", ".avi", ".webm"]:
                    screen.blit(font_small.render("🎬 Video file detected (preview not supported)", True, TEXT_COLOR),
                                (overlay_rect.x + 10, overlay_rect.y + 30))

                elif file_ext == ".pdf":
                    screen.blit(font_small.render("📄 PDF file detected (preview not supported)", True, TEXT_COLOR),
                                (overlay_rect.x + 10, overlay_rect.y + 30))

                elif file_ext in [".zip", ".rar", ".7z"]:
                    screen.blit(font_small.render("🗜️ Archive file detected", True, TEXT_COLOR),
                                (overlay_rect.x + 10, overlay_rect.y + 30))

                elif file_ext in [".py", ".js", ".html", ".css", ".cpp", ".java"]:
                    try:
                        with open(preview_overlay.file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        for i, line in enumerate(lines[:int((overlay_rect.height - 40) // 18)]):
                            screen.blit(font_small.render(line.strip()[:100], True, TEXT_COLOR),
                                        (overlay_rect.x + 10, overlay_rect.y + 30 + i * 18))
                    except Exception as e:
                        screen.blit(font_small.render(f"Code error: {e}", True, TEXT_COLOR),
                                    (overlay_rect.x + 10, overlay_rect.y + 30))
                else:
                    screen.blit(font_small.render(f"Cannot preview {file_ext}", True, TEXT_COLOR),
                                (overlay_rect.x + 10, overlay_rect.y + 30))
            except Exception as e:
                screen.blit(font_small.render(f"Error opening file", True, TEXT_COLOR),
                            (overlay_rect.x + 10, overlay_rect.y + 30))

        # --- Delete popup ---
        if delete_popup:
            popup_rect = pygame.Rect(60, 100, screen_width - 120, 120)
            pygame.draw.rect(screen, (60, 60, 60), popup_rect, border_radius=8)
            text_surf = font_medium.render(f"Delete '{os.path.basename(delete_popup)}'?", True, TEXT_COLOR)
            screen.blit(text_surf, (popup_rect.x + 10, popup_rect.y + 20))
            delete_btn = pygame.Rect(popup_rect.x + 20, popup_rect.y + 70, 80, 30)
            cancel_btn = pygame.Rect(popup_rect.right - 100, popup_rect.y + 70, 80, 30)
            pygame.draw.rect(screen, (200, 50, 50), delete_btn, border_radius=6)
            pygame.draw.rect(screen, (100, 100, 100), cancel_btn, border_radius=6)
            screen.blit(font_small.render("Delete", True, TEXT_COLOR), (delete_btn.x+10, delete_btn.y+5))
            screen.blit(font_small.render("Cancel", True, TEXT_COLOR), (cancel_btn.x+10, cancel_btn.y+5))
            delete_rects = {"delete": delete_btn, "cancel": cancel_btn}

            if mouse_clicked:
                if delete_rects["delete"].collidepoint(mouse_pos):
                    try:
                        if os.path.isdir(delete_popup):
                            shutil.rmtree(delete_popup)
                        else:
                            os.remove(delete_popup)
                        toast_messages.append(Toast("Deleted successfully!"))
                    except Exception as e:
                        toast_messages.append(Toast(f"Error: {e}"))
                    file_items = list_directory(current_path)
                    delete_popup = None
                elif delete_rects["cancel"].collidepoint(mouse_pos):
                    delete_popup = None

        # --- Toast messages ---
        now = pygame.time.get_ticks()
        y_offset = 10
        for toast in toast_messages[:]:
            if now - toast.start_time > toast.duration*1000:
                toast_messages.remove(toast)
                continue
            toast_rect = pygame.Rect(20, y_offset, screen_width - 40, 25)
            pygame.draw.rect(screen, TOAST_BG, toast_rect, border_radius=6)
            toast_surf = font_small.render(toast.text, True, (255,255,255))
            screen.blit(toast_surf, (toast_rect.x+5, toast_rect.y+4))
            y_offset += 35

        # --- Draw top bar ---
        topbar.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
