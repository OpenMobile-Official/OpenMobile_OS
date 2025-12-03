import pygame
import sys
import os

pygame.mixer.init()
base_path = os.path.dirname(os.path.abspath(__file__))
sound_path = os.path.join(base_path, "type.mp3")
sound = pygame.mixer.Sound(sound_path)

def run_keyboard():
    pygame.init()

    info = pygame.display.Info()
    SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Keyboard")

    PADDING = int(SCREEN_WIDTH * 0.012)
    KEY_W = int(SCREEN_WIDTH * 0.08)
    KEY_H = int(SCREEN_HEIGHT * 0.12)
    START_Y = int(SCREEN_HEIGHT * 0.45)

    FONT_L = pygame.font.SysFont("Arial", int(KEY_H * 0.4))
    FONT_LABEL = pygame.font.SysFont("Arial", int(KEY_H * 0.3))
    FONT_IN = pygame.font.SysFont("Arial", int(SCREEN_HEIGHT * 0.08))

    WHITE = (255, 255, 255); BLACK = (0, 0, 0); GRAY = (180, 180, 180); DARK = (50, 50, 50)

    input_text = ""
    cursor_idx = 0
    scroll_offset = 0
    is_shift = False
    is_number = False

    qwerty = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
        ["SHIFT", "SPACE", "123", "←", "→", "BKSP", "ENTER"]
    ]

    numbers = [
        list("1234567890"),
        list("!@#$%^&*()"),
        list("-_=+[]{}"),
        ["ABC", "SPACE", ".", "←", "→", "BKSP", "ENTER"]
    ]

    current = qwerty
    keys = []

    def draw_kbd():
        nonlocal scroll_offset
        keys.clear()
        screen.fill(BLACK)

        input_rect = pygame.Rect(PADDING, PADDING, SCREEN_WIDTH - 2*PADDING, int(SCREEN_HEIGHT*0.2))
        pygame.draw.rect(screen, DARK, input_rect, border_radius=8)
        txt_surf = FONT_IN.render(input_text, True, WHITE)
        cursor_x = FONT_IN.size(input_text[:cursor_idx])[0]
        visible_w = input_rect.width - 2*PADDING

        if cursor_x - scroll_offset > visible_w:
            scroll_offset = cursor_x - visible_w + 20
        if cursor_x - scroll_offset < 0:
            scroll_offset = max(0, cursor_x - 20)

        screen.blit(txt_surf, (input_rect.x + PADDING - scroll_offset, input_rect.y + PADDING))
        cursor_draw_x = cursor_x - scroll_offset
        pygame.draw.line(screen, WHITE,
                         (input_rect.x + PADDING + cursor_draw_x, input_rect.y + PADDING),
                         (input_rect.x + PADDING + cursor_draw_x, input_rect.y + PADDING + FONT_IN.get_height()),
                         2)

        y = START_Y
        for row in current:
            row_w = len(row)*(KEY_W + PADDING) - PADDING
            x = (SCREEN_WIDTH - row_w)//2
            for key in row:
                rect = pygame.Rect(x, y, KEY_W, KEY_H)
                pygame.draw.rect(screen, GRAY, rect, border_radius=6)
                label = key.upper() if len(key)==1 and is_shift and not is_number else key.lower() if len(key)==1 and not is_number else key
                font = FONT_L if len(key)==1 else FONT_LABEL
                surf = font.render(label, True, BLACK)
                screen.blit(surf, surf.get_rect(center=rect.center))
                keys.append((rect, key))
                x += KEY_W + PADDING
            y += KEY_H + PADDING

        pygame.display.flip()

    while True:
        draw_kbd()
        for ev in pygame.event.get():
            if ev.type in (pygame.QUIT,):
                pygame.quit()
                sys.exit()

            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
                if hasattr(ev, 'x'):  # finger
                    mx, my = int(ev.x * SCREEN_WIDTH), int(ev.y * SCREEN_HEIGHT)
                else:
                    mx, my = ev.pos if hasattr(ev, 'pos') else pygame.mouse.get_pos()
                sound.play()
                for rect, key in keys:
                    if rect.collidepoint(mx, my):
                        if key == "SPACE":
                            input_text = input_text[:cursor_idx] + " " + input_text[cursor_idx:]
                            cursor_idx +=1
                        elif key == "SHIFT":
                            is_shift = not is_shift
                        elif key == "123":
                            is_number = True; current = numbers
                        elif key == "ABC":
                            is_number = False; current = qwerty
                        elif key == "←":
                            if cursor_idx > 0: cursor_idx -=1
                        elif key == "→":
                            if cursor_idx < len(input_text): cursor_idx +=1
                        elif key == "BKSP":
                            if cursor_idx > 0:
                                input_text = input_text[:cursor_idx-1] + input_text[cursor_idx:]
                                cursor_idx -=1
                        elif key == "ENTER":
                          
                            return input_text
                        else:
                            ch = key
                            if is_shift and not is_number: ch=ch.upper()
                            elif not is_shift and not is_number: ch=ch.lower()
                            input_text = input_text[:cursor_idx] + ch + input_text[cursor_idx:]
                            cursor_idx +=1

            elif ev.type == pygame.KEYDOWN:
                sound.play()
                if ev.key == pygame.K_BACKSPACE:
                    if cursor_idx>0:
                        input_text = input_text[:cursor_idx-1] + input_text[cursor_idx:]
                        cursor_idx -=1
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                
                    return input_text
                elif ev.key == pygame.K_SPACE:
                    input_text = input_text[:cursor_idx] + " " + input_text[cursor_idx:]
                    cursor_idx +=1
                elif ev.key == pygame.K_LEFT:
                    if cursor_idx > 0: cursor_idx -=1
                elif ev.key == pygame.K_RIGHT:
                    if cursor_idx < len(input_text): cursor_idx +=1
                elif ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    is_shift = True
                elif ev.key == pygame.K_TAB:
                    is_number = not is_number
                    current = numbers if is_number else qwerty
                else:
                    ch = ev.unicode
                    if ch:
                        if is_shift and not is_number: ch=ch.upper()
                        elif not is_shift and not is_number: ch=ch.lower()
                        input_text = input_text[:cursor_idx] + ch + input_text[cursor_idx:]
                        cursor_idx +=1

            elif ev.type == pygame.KEYUP:
                if ev.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    is_shift = False

if __name__ == "__main__":
    text = run_keyboard()
    print("Final input:", text)
