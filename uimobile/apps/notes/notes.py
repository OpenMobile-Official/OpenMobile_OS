import pygame, sys, time, os, json
from modules.top_bar import TopBarManager
from modules.keyboard import run_keyboard

pygame.init()

# Screen
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 320
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Advanced Notes App")

# Fonts
FONT_SMALL = pygame.font.SysFont("Arial", 14)
FONT_MEDIUM = pygame.font.SysFont("Arial", 18)
FONT_LARGE = pygame.font.SysFont("Arial", 22)
FONT_INSTR = pygame.font.SysFont("Arial", 14)

# Colors
BG_COLOR = (40, 42, 54)
NOTE_BG = (60, 63, 82)
NOTE_HOVER = (80, 85, 110)
TEXT_COLOR = (230, 230, 230)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 160, 210)
TOPBAR_COLOR = (35, 35, 35)
DELETE_COLOR = (180, 60, 60)
DELETE_HOVER = (210, 80, 80)
SEARCH_BG = (50, 50, 70)

# Paths
NOTES_FILE = os.path.join(os.path.dirname(__file__), "notes.json")

# Load notes
if os.path.exists(NOTES_FILE):
    with open(NOTES_FILE, "r") as f:
        notes = json.load(f)
else:
    notes = []

topbar = TopBarManager(SCREEN_WIDTH, SCREEN_HEIGHT, FONT_SMALL, FONT_LARGE, app_key="advanced_notes")

clock = pygame.time.Clock()

# UI Elements
btn_write_rect = pygame.Rect(160, 40, 160, 40)
search_rect = pygame.Rect(20, 100, SCREEN_WIDTH - 40, 30)
scroll_offset = 0
search_text = ""
editing_index = None

dragging = False
drag_start_y = 0
scroll_start = 0

def save_notes():
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f)

def filter_notes():
    if not search_text.strip():
        return notes
    return [n for n in notes if search_text.lower() in n["text"].lower()]

def draw_notes(filtered_notes):
    global scroll_offset
    y_start = 140 - scroll_offset
    note_height = 40
    spacing = 10
    keys_hovered = []

    for idx, note in enumerate(filtered_notes):
        text, ts = note["text"], note["timestamp"]
        rect = pygame.Rect(20, y_start, SCREEN_WIDTH - 40, note_height)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)

        color = NOTE_HOVER if hover else NOTE_BG
        pygame.draw.rect(screen, color, rect, border_radius=6)

        note_text = FONT_MEDIUM.render(text, True, TEXT_COLOR)
        screen.blit(note_text, (rect.x + 10, rect.y + 5))
        ts_text = FONT_SMALL.render(ts, True, (180, 180, 180))
        screen.blit(ts_text, (rect.right - 80, rect.y + 10))

        del_rect = pygame.Rect(rect.right - 30, rect.y + 5, 20, 20)
        del_color = DELETE_HOVER if del_rect.collidepoint(mx, my) else DELETE_COLOR
        pygame.draw.rect(screen, del_color, del_rect, border_radius=4)
        del_text = FONT_SMALL.render("X", True, TEXT_COLOR)
        screen.blit(del_text, del_text.get_rect(center=del_rect.center))

        keys_hovered.append((hover, del_rect, idx, rect))
        y_start += note_height + spacing

    return keys_hovered

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        topbar.handle_event(event)

        # Touch or mouse scrolling
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_clicked = True
                if search_rect.collidepoint(event.pos):
                    # Focus search
                    pass
                else:
                    dragging = True
                    drag_start_y = event.pos[1]
                    scroll_start = scroll_offset
            if event.button == 4:  # Wheel up
                scroll_offset = max(0, scroll_offset - 20)
            if event.button == 5:  # Wheel down
                scroll_offset += 20

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging = False

        elif event.type == pygame.MOUSEMOTION and dragging:
            dy = event.pos[1] - drag_start_y
            scroll_offset = max(0, scroll_start - dy)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                search_text = search_text[:-1]
            elif event.key == pygame.K_RETURN:
                pass
            else:
                search_text += event.unicode

    screen.fill(BG_COLOR)
    topbar.update()

    # Instructions
    instr_text = FONT_INSTR.render("Write, edit, search and delete notes. Scroll by dragging or wheel.", True, TEXT_COLOR)
    screen.blit(instr_text, (10, 10))

    # Write note button
    if btn_write_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, BUTTON_HOVER, btn_write_rect, border_radius=6)
        if mouse_clicked:
            note_text = run_keyboard()
            if note_text.strip():
                timestamp = time.strftime("%H:%M:%S")
                notes.append({"text": note_text, "timestamp": timestamp})
                save_notes()
                scroll_offset = max(0, len(notes)*50 - SCREEN_HEIGHT + 150)
    else:
        pygame.draw.rect(screen, BUTTON_COLOR, btn_write_rect, border_radius=6)

    btn_txt = FONT_MEDIUM.render("Write Note", True, TEXT_COLOR)
    screen.blit(btn_txt, btn_txt.get_rect(center=btn_write_rect.center))

    # Search bar
    pygame.draw.rect(screen, SEARCH_BG, search_rect, border_radius=6)
    search_surf = FONT_SMALL.render(search_text or "Search notes...", True, (180,180,180))
    screen.blit(search_surf, (search_rect.x + 5, search_rect.y + 5))

    filtered = filter_notes()
    keys_hovered = draw_notes(filtered)

    if mouse_clicked:
        for hover, del_rect, idx, rect in keys_hovered:
            if del_rect.collidepoint(mouse_pos):
                note_idx = notes.index(filtered[idx])
                notes.pop(note_idx)
                save_notes()
                break
            elif rect.collidepoint(mouse_pos):
                note_idx = notes.index(filtered[idx])
                edited_text = run_keyboard()
                if edited_text.strip():
                    notes[note_idx]["text"] = edited_text
                    notes[note_idx]["timestamp"] = time.strftime("%H:%M:%S")
                    save_notes()
                break

    topbar.draw(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
