import pygame
import sys
from modules.keyboard import run_keyboard  # ✅ Correct import



def main():
    pygame.init()

    SCREEN_WIDTH = 480
    SCREEN_HEIGHT = 320
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Keyboard Test Scene")

    FONT = pygame.font.SysFont("Arial", 28)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (0, 120, 215)

    input_text = ""
    button_rect = pygame.Rect(140, 120, 200, 60)

    running = True
    while running:
        screen.fill(BLACK)

        # Draw button
        pygame.draw.rect(screen, BLUE, button_rect)
        button_text = FONT.render("Open Keyboard", True, WHITE)
        screen.blit(button_text, button_text.get_rect(center=button_rect.center))

        # Display typed input
        input_surface = FONT.render("Typed: " + input_text, True, WHITE)
        screen.blit(input_surface, (20, 220))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    input_text = run_keyboard()  # Call from imported function

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
