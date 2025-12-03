import pygame
import sys
import os
import math
from modules.top_bar import TopBarManager
from modules.file_parser import parse_helpdoc
from modules.help_viewer import HelpViewer


# Simple helper for gradients
def draw_vertical_gradient(surface, color_top, color_bottom):
    w, h = surface.get_size()
    for y in range(h):
        ratio = y / h
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))


def main():
    pygame.init()
    screen_width, screen_height = 480, 320
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Help Center")

    font_small = pygame.font.SysFont("Arial", 16)
    font_medium = pygame.font.SysFont("Arial", 20)
    font_large = pygame.font.SysFont("Arial", 26, bold=True)

    # --- Top Bar ---
    topbar = TopBarManager(screen_width, screen_height, font_small, font_medium, app_key="helpcenter")

    # --- Detect help_docs directory ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    help_docs_path = os.path.join(base_dir, "help_docs")
    os.makedirs(help_docs_path, exist_ok=True)

    # --- Load folder structure ---
    folder_structure = {}
    for root, dirs, files in os.walk(help_docs_path):
        rel = os.path.relpath(root, help_docs_path)
        folder_structure[rel] = [f for f in files if f.endswith(".helpdoc")]

    # Collapsible state and animation
    collapsed = {folder: True for folder in folder_structure}
    folder_animation = {folder: 0.0 for folder in folder_structure}  # 0=collapsed,1=expanded

    # --- Viewer ---
    viewer = HelpViewer(screen, font_small, font_medium, font_large)

    # --- App State ---
    mode = "folder"  # folder | viewer
    selected_folder = None
    selected_doc = None

    # --- Scroll physics (folders) ---
    folder_scroll_y = 0
    scroll_velocity = 0
    dragging = False
    drag_last_y = 0

    # --- Document touch scroll ---
    doc_dragging = False
    doc_drag_start_y = 0

    # --- Transition animation ---
    transition_alpha = 255
    transitioning = False
    transition_dir = 0  # 1 = open, -1 = close

    # --- Back button ---
    back_rect = pygame.Rect(10, 10, 70, 30)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        mouse_x, mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            topbar.handle_event(event)

            if event.type == pygame.QUIT:
                running = False

            # =============================
            # 📁 FOLDER MODE
            # =============================
            if mode == "folder" and not transitioning:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    dragging = True
                    drag_last_y = event.pos[1]
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False
                    # Detect tap
                    if abs(event.pos[1] - drag_last_y) < 5:
                        y_offset = 80 + folder_scroll_y
                        for folder in folder_structure:
                            folder_rect = pygame.Rect(20, y_offset, screen_width - 40, 25)
                            if folder_rect.collidepoint(event.pos):
                                collapsed[folder] = not collapsed[folder]  # Toggle collapse
                                break
                            y_offset += 35
                            anim_count = int(len(folder_structure[folder]) * folder_animation[folder])
                            for i in range(anim_count):
                                file = folder_structure[folder][i]
                                file_rect = pygame.Rect(40, y_offset, screen_width - 60, 25)
                                if file_rect.collidepoint(event.pos):
                                    selected_folder = folder
                                    selected_doc = file
                                    doc_path = os.path.join(help_docs_path, folder, file)
                                    if os.path.exists(doc_path):
                                        doc = parse_helpdoc(doc_path)
                                        viewer.load_document(doc)
                                        viewer.scroll_y = 0
                                        mode = "viewer"
                                        transitioning = True
                                        transition_dir = 1
                                        transition_alpha = 255
                                    break
                                y_offset += 28
                elif event.type == pygame.MOUSEMOTION and dragging:
                    dy = event.rel[1]
                    folder_scroll_y += dy
                    scroll_velocity = dy / dt
                elif event.type == pygame.MOUSEWHEEL:
                    folder_scroll_y += event.y * 40

            # =============================
            # 📖 VIEWER MODE
            # =============================
            elif mode == "viewer" and not transitioning:
                viewer.handle_event(event)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        transitioning = True
                        transition_dir = -1
                        transition_alpha = 0
                    else:
                        doc_dragging = True
                        doc_drag_start_y = event.pos[1]
                elif event.type == pygame.MOUSEBUTTONUP:
                    doc_dragging = False
                elif event.type == pygame.MOUSEMOTION and doc_dragging:
                    dy = event.rel[1]
                    viewer.scroll_y += dy
                elif event.type == pygame.MOUSEWHEEL:
                    viewer.scroll_y += event.y * 25

        # --- Animate folders ---
        for folder in folder_structure:
            target = 0 if collapsed[folder] else 1
            speed = 5 * dt * 60
            if folder_animation[folder] < target:
                folder_animation[folder] = min(folder_animation[folder] + speed, target)
            elif folder_animation[folder] > target:
                folder_animation[folder] = max(folder_animation[folder] - speed, target)

        # --- Momentum scroll for folders ---
        if not dragging and mode == "folder":
            folder_scroll_y += scroll_velocity * dt
            scroll_velocity *= 0.9
            if abs(scroll_velocity) < 5:
                scroll_velocity = 0

        # --- Clamp scroll ---
        folder_scroll_y = max(min(folder_scroll_y, 100), -999)

        # --- Background ---
        draw_vertical_gradient(screen, (35, 40, 60), (20, 20, 30))

        # --- Mode Drawing ---
        if mode == "folder":
            pygame.draw.rect(screen, (50, 55, 75, 80), (10, 10, screen_width - 20, screen_height - 20), border_radius=8)
            title = font_large.render("Help Documents", True, (255, 255, 255))
            screen.blit(title, (20, 20))
            pygame.draw.line(screen, (90, 90, 120), (20, 55), (screen_width - 20, 55), 1)

            y = 80 + folder_scroll_y
            for folder in folder_structure:
                folder_label = ("📁 " if collapsed[folder] else "📂 ") + (folder if folder != "." else "Root")
                folder_surf = font_medium.render(folder_label, True, (180, 200, 255))
                screen.blit(folder_surf, (20, y))
                y += 35

                anim_count = int(len(folder_structure[folder]) * folder_animation[folder])
                for i in range(anim_count):
                    file = folder_structure[folder][i]
                    hover = pygame.Rect(40, y, screen_width - 60, 25).collidepoint(mouse_x, mouse_y)
                    bg_color = (70, 75, 100) if hover else (60, 65, 85)
                    pygame.draw.rect(screen, bg_color, (40, y, screen_width - 60, 25), border_radius=6)
                    file_surf = font_small.render(file, True, (240, 240, 255))
                    screen.blit(file_surf, (50, y + 4))
                    y += 28

        elif mode == "viewer":
            viewer.draw()

            # --- Back Button ---
            pygame.draw.rect(screen, (70, 90, 130), back_rect, border_radius=8)
            back_text = font_small.render("< Back", True, (255, 255, 255))
            screen.blit(back_text, (back_rect.x + 10, back_rect.y + 6))

        # --- Transition overlay ---
        if transitioning:
            transition_speed = 250 * dt
            if transition_dir == 1:
                transition_alpha -= transition_speed
                if transition_alpha <= 0:
                    transition_alpha = 0
                    transitioning = False
            elif transition_dir == -1:
                transition_alpha += transition_speed
                if transition_alpha >= 255:
                    transition_alpha = 255
                    transitioning = False
                    mode = "folder"

            overlay = pygame.Surface((screen_width, screen_height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(transition_alpha))
            screen.blit(overlay, (0, 0))

        # --- Top Bar ---
        topbar.update()
        topbar.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
