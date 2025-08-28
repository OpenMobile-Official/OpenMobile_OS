import pygame
import sys
import os
import time
import subprocess
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

def reset_password_files():
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(base_path, "../../config"))
    files_to_delete = ["user.enc", "key.key"]
    messages = []

    for filename in files_to_delete:
        file_path = os.path.join(config_path, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                messages.append(f"Deleted: {filename}")
            else:
                messages.append(f"File not found: {filename}")
        except Exception as e:
            messages.append(f"Error deleting {filename}: {e}")

    return "\n".join(messages)

def launch_main_script():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.abspath(os.path.join(base_path, "../../main.py"))
        subprocess.Popen(["python3", script_path])
        return "Launching main.py..."
    except Exception as e:
        return f"Launch failed: {e}"

def draw_button(screen, rect, label, font, is_hovered, bg_color, hover_color, text_color):
    color = hover_color if is_hovered else bg_color
    pygame.draw.rect(screen, color, rect, border_radius=6)
    text_surf = font.render(label, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)

def main():
    pygame.init()
    screen_width, screen_height = 480, 320
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Settings App")

    font_small = pygame.font.SysFont("Arial", 18)
    font_medium = pygame.font.SysFont("Arial", 22)

    TOPBAR_HEIGHT = 50
    topbar = TopBarManager(screen_width, screen_height, font_small, font_medium, app_key="settings")
    clock = pygame.time.Clock()

    settings = [
        "Wi-Fi", "Display", "Sound", "Reset Password", "Keyboard Test",
        "Bluetooth", "Accessibility", "Brightness", "Volume",
        "Time & Date", "About", "Advanced Settings", "Reboot"
    ]

    button_width = 220
    button_height = 45
    spacing = 12
    start_y = 60
    center_x = (screen_width - button_width) // 2

    button_color = (60, 120, 180)
    hover_color = (90, 160, 220)
    text_color = (255, 255, 255)

    scroll_offset = 0
    is_dragging = False
    drag_start_y = 0
    scroll_start_offset = 0

    show_dialog = False
    dialog_type = None
    dialog_buttons = {}
    feedback_message = ""
    feedback_timer = 0

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            topbar.handle_event(event)

            # Scroll with mouse wheel
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_clicked = True
                    is_dragging = True
                    drag_start_y = event.pos[1]
                    scroll_start_offset = scroll_offset
                elif event.button == 4:
                    scroll_offset = min(scroll_offset + 20, 0)
                elif event.button == 5:
                    scroll_offset -= 20

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging = False

            if event.type == pygame.MOUSEMOTION and is_dragging:
                dy = event.pos[1] - drag_start_y
                scroll_offset = scroll_start_offset + dy

        topbar.update()
        screen.fill((70, 70, 70))

        if show_dialog:
            dialog_width, dialog_height = 300, 140
            dialog_rect = pygame.Rect(
                (screen_width - dialog_width) // 2,
                (screen_height - dialog_height) // 2,
                dialog_width,
                dialog_height,
            )
            pygame.draw.rect(screen, (50, 50, 50), dialog_rect, border_radius=8)
            pygame.draw.rect(screen, (200, 200, 200), dialog_rect, 2, border_radius=8)

            message_text = f"Are you sure you want to {dialog_type.lower()}?"
            text_surf = font_small.render(message_text, True, text_color)
            screen.blit(text_surf, text_surf.get_rect(center=(dialog_rect.centerx, dialog_rect.top + 35)))

            yes_rect = pygame.Rect(dialog_rect.left + 40, dialog_rect.bottom - 50, 80, 30)
            cancel_rect = pygame.Rect(dialog_rect.right - 120, dialog_rect.bottom - 50, 80, 30)
            dialog_buttons = {"Yes": yes_rect, "Cancel": cancel_rect}

            for label, rect in dialog_buttons.items():
                hovered = rect.collidepoint(mouse_pos)
                draw_button(screen, rect, label, font_small, hovered, button_color, hover_color, text_color)

            if mouse_clicked:
                if dialog_buttons["Yes"].collidepoint(mouse_pos):
                    if dialog_type == "Reset Password":
                        feedback_message = reset_password_files()
                    elif dialog_type == "Reboot":
                        feedback_message = launch_main_script()
                        pygame.quit()
                        sys.exit()
                    feedback_timer = time.time()
                    show_dialog = False
                elif dialog_buttons["Cancel"].collidepoint(mouse_pos):
                    show_dialog = False

        else:
            buttons = []
            for i, label in enumerate(settings):
                y = start_y + i * (button_height + spacing) + scroll_offset
                rect = pygame.Rect(center_x, y, button_width, button_height)
                buttons.append({"label": label, "rect": rect})

            # Enforce scroll limits
            total_height = start_y + len(settings) * (button_height + spacing)
            min_scroll = screen_height - total_height - 20
            scroll_offset = max(min_scroll, min(0, scroll_offset))

            for button in buttons:
                rect = button["rect"]
                label = button["label"]
                if rect.bottom < TOPBAR_HEIGHT or rect.top > screen_height:
                    continue  # Skip drawing off-screen buttons

                hovered = rect.collidepoint(mouse_pos)
                draw_button(screen, rect, label, font_medium, hovered, button_color, hover_color, text_color)

                if hovered and mouse_clicked:
                    if label == "Keyboard Test":
                        run_keyboard()
                    elif label == "Reset Password":
                        dialog_type = "Reset Password"
                        show_dialog = True
                    elif label == "Reboot":
                        dialog_type = "Reboot"
                        show_dialog = True
                    else:
                        print(f"{label} settings clicked (not yet implemented)")

        if feedback_message and time.time() - feedback_timer < 3:
            feedback_surf = font_small.render(feedback_message, True, (255, 255, 0))
            feedback_rect = feedback_surf.get_rect(center=(screen_width // 2, 40))
            screen.blit(feedback_surf, feedback_rect)

        topbar.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
