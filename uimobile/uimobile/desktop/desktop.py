import pygame
import sys

pygame.init()

# Detect screen resolution
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Fake GNOME Desktop (Pygame)")

# Colors
BG_COLOR = (40, 40, 45)
PANEL_COLOR = (25, 25, 30)
MENU_BG = (50, 50, 60)
WINDOW_COLOR = (210, 210, 220)
TITLE_COLOR = (60, 60, 70)
TEXT_COLOR = (255, 255, 255)
BTN_RED = (220, 80, 80)
BTN_RED_HOVER = (250, 100, 100)

font = pygame.font.SysFont("sans", 18)
big_font = pygame.font.SysFont("sans", 24, bold=True)

clock = pygame.time.Clock()

# App definitions (for launcher)
apps = [
    {"name": "Notes", "color": (130, 170, 255)},
    {"name": "Terminal", "color": (200, 200, 100)},
    {"name": "Files", "color": (100, 200, 150)},
    {"name": "Browser", "color": (255, 180, 100)},
]

windows = []
menu_open = False
window_id = 0


class Window:
    def __init__(self, title, pos):
        global window_id
        self.id = window_id
        window_id += 1
        self.title = title
        self.rect = pygame.Rect(pos[0], pos[1], 400, 300)
        self.drag = False
        self.drag_offset = (0, 0)
        self.close_hover = False

    def draw(self, surf):
        # Draw window
        pygame.draw.rect(surf, WINDOW_COLOR, self.rect, border_radius=5)

        # Title bar
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 30)
        pygame.draw.rect(surf, TITLE_COLOR, title_bar, border_radius=5)

        # Title
        title_text = font.render(self.title, True, TEXT_COLOR)
        surf.blit(title_text, (self.rect.x + 10, self.rect.y + 5))

        # Close button
        close_rect = pygame.Rect(self.rect.right - 30, self.rect.y + 5, 20, 20)
        color = BTN_RED_HOVER if self.close_hover else BTN_RED
        pygame.draw.circle(surf, color, close_rect.center, 8)
        self.close_rect = close_rect

        # Fake content area
        content_rect = pygame.Rect(
            self.rect.x + 10, self.rect.y + 40, self.rect.w - 20, self.rect.h - 50
        )
        pygame.draw.rect(surf, (240, 240, 245), content_rect, border_radius=3)

        # Placeholder content
        content_text = font.render(f"This is {self.title}.", True, (30, 30, 30))
        surf.blit(content_text, (content_rect.x + 10, content_rect.y + 10))

    def handle_event(self, event):
        # Handle window dragging
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 30)
                if title_bar.collidepoint(event.pos):
                    self.drag = True
                    mx, my = event.pos
                    self.drag_offset = (mx - self.rect.x, my - self.rect.y)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            mx, my = event.pos
            self.rect.x = mx - self.drag_offset[0]
            self.rect.y = my - self.drag_offset[1]


def draw_panel():
    pygame.draw.rect(screen, PANEL_COLOR, (0, 0, WIDTH, 40))
    # "Activities" button
    act_text = big_font.render("Activities", True, TEXT_COLOR)
    screen.blit(act_text, (10, 8))
    return pygame.Rect(10, 8, act_text.get_width(), act_text.get_height())


def draw_menu():
    """Draws a simple app launcher menu"""
    menu_rect = pygame.Rect(0, 40, 300, HEIGHT - 40)
    pygame.draw.rect(screen, MENU_BG, menu_rect)

    title = big_font.render("Applications", True, TEXT_COLOR)
    screen.blit(title, (20, 60))

    icon_y = 120
    icon_spacing = 80
    icon_rects = []

    for app in apps:
        rect = pygame.Rect(40, icon_y, 64, 64)
        pygame.draw.rect(screen, app["color"], rect, border_radius=8)
        name_text = font.render(app["name"], True, TEXT_COLOR)
        screen.blit(name_text, (40, icon_y + 70))
        icon_rects.append((rect, app))
        icon_y += icon_spacing

    return icon_rects


def launch_app(name):
    windows.append(Window(name, (250 + len(windows) * 30, 100 + len(windows) * 30)))


def main():
    global menu_open
    app_icon_rects = []
    dragging = False

    while True:
        screen.fill(BG_COLOR)
        act_rect = draw_panel()

        if menu_open:
            app_icon_rects = draw_menu()

        # Draw windows
        for w in windows:
            w.draw(screen)

        pygame.display.flip()

        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Toggle menu if Activities clicked
                if act_rect.collidepoint(event.pos):
                    menu_open = not menu_open

                # Handle clicks in app menu
                elif menu_open:
                    for rect, app in app_icon_rects:
                        if rect.collidepoint(event.pos):
                            launch_app(app["name"])
                            menu_open = False

                # Handle clicks on windows (bring to front, check close)
                for w in reversed(windows):
                    if w.rect.collidepoint(event.pos):
                        # Bring clicked window to front
                        windows.remove(w)
                        windows.append(w)

                        # Check close button
                        if hasattr(w, "close_rect") and w.close_rect.collidepoint(event.pos):
                            windows.remove(w)
                            break
                        w.handle_event(event)
                        break

            elif event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                for w in windows:
                    # Update hover state for close button
                    if hasattr(w, "close_rect"):
                        w.close_hover = w.close_rect.collidepoint(pygame.mouse.get_pos())
                    w.handle_event(event)

        clock.tick(60)


if __name__ == "__main__":
    main()
