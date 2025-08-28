import pygame
import sys
from datetime import datetime

# Initialize Pygame
pygame.init()

# Screen dimensions for 3.5" landscape (480x320)
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Mobile Phone UI")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
LIGHT_BLUE = (173, 216, 230)

# Fonts
font_small = pygame.font.SysFont("Arial", 16)
font_medium = pygame.font.SysFont("Arial", 20)

# Load app icons (using colored rectangles as placeholders)
def draw_app_icon(x, y, name):
    icon_rect = pygame.Rect(x, y, 60, 60)
    pygame.draw.rect(screen, LIGHT_BLUE, icon_rect, border_radius=10)
    label = font_small.render(name, True, BLACK)
    screen.blit(label, (x + 5, y + 65))

# Draw status bar
def draw_status_bar():
    pygame.draw.rect(screen, GRAY, (0, 0, SCREEN_WIDTH, 30))
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    battery_str = "🔋 80%"
    screen.blit(font_small.render(time_str, True, BLACK), (10, 7))
    screen.blit(font_small.render(battery_str, True, BLACK), (SCREEN_WIDTH - 70, 7))

# App icons layout (simple 3x2 grid)
app_grid = [
    ("Phone", 40, 50),
    ("Messages", 140, 50),
    ("Camera", 240, 50),
    ("Browser", 40, 150),
    ("Settings", 140, 150),
    ("Clock", 240, 150),
]

# Main loop
clock = pygame.time.Clock()
running = True

while running:
    screen.fill(WHITE)

    draw_status_bar()

    for app in app_grid:
        draw_app_icon(app[1], app[2], app[0])

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
