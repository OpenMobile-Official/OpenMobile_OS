import pygame
import sys
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

def main():
    pygame.init()
    screen_width, screen_height = 480, 320
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Test App")

    font_small = pygame.font.SysFont("Arial", 18)
    font_medium = pygame.font.SysFont("Arial", 22)
    font_instructions = pygame.font.SysFont("Arial", 16)

    topbar = TopBarManager(screen_width, screen_height, font_small, font_medium, app_key="testapp")

    clock = pygame.time.Clock()

    # Button properties
    button_width = 160
    button_height = 40
    button_x = (screen_width - button_width) // 2
    button_y = screen_height // 2
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    button_color = (70, 130, 180)  # Steel Blue
    button_hover_color = (100, 160, 210)
    button_text = "Open Keyboard"
    button_font = pygame.font.SysFont("Arial", 20)

    # Text output from keyboard
    keyboard_output = ""

    # Instruction text about top bar usage
    instruction_text = "Use the top bar to close teh app. Pull it down from top of screen"

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            topbar.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True

        topbar.update()

        # Draw background
        screen.fill((100, 100, 100))

        # Draw instruction text near top (under top bar)
        instruction_surf = font_instructions.render(instruction_text, True, (255, 255, 255))
        screen.blit(instruction_surf, (10, 50))

        # Draw button (hover effect)
        if button_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, button_hover_color, button_rect, border_radius=6)
            if mouse_clicked:
                # Launch keyboard on button click
                keyboard_output = run_keyboard()
        else:
            pygame.draw.rect(screen, button_color, button_rect, border_radius=6)

        # Draw button text
        text_surf = button_font.render(button_text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect)

        # Draw keyboard output text below the button
        output_label_surf = font_small.render("Keyboard Output:", True, (255, 255, 255))
        screen.blit(output_label_surf, (button_x, button_y + button_height + 10))

        output_surf = font_small.render(keyboard_output, True, (230, 230, 230))
        screen.blit(output_surf, (button_x, button_y + button_height + 30))

        # Draw top bar on top
        topbar.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
