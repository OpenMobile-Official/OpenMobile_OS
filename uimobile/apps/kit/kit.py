import pygame
import sys
from kit_module import kit  # Your bot module
from modules.top_bar import TopBarManager

pygame.init()

# --- Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 480, 320
BG_COLOR = (40, 40, 50)
INPUT_BG_COLOR = (60, 60, 70)
TEXT_COLOR = (230, 230, 230)
BOT_COLOR = (100, 180, 255)
USER_COLOR = (180, 255, 180)
FONT = pygame.font.SysFont("Arial", 18)
INPUT_HEIGHT = 30
KEY_HEIGHT = 35
PADDING = 3

# --- State variables ---
is_shift = False
is_symbols = False
conversation_history = []
user_input = ""
cursor_visible = True
cursor_timer = 0
scroll_offset = 0

# --- Keyboard layouts ---
keys_layout_lower = [
    [("q",1),("w",1),("e",1),("r",1),("t",1),("y",1),("u",1),("i",1),("o",1),("p",1)],
    [("a",1),("s",1),("d",1),("f",1),("g",1),("h",1),("j",1),("k",1),("l",1)],
    [("SHIFT",2),("z",1),("x",1),("c",1),("v",1),("b",1),("n",1),("m",1),("BACK",2)],
    [("123",2),("SPACE",5),("ENTER",2)]
]

keys_layout_upper = [
    [("Q",1),("W",1),("E",1),("R",1),("T",1),("Y",1),("U",1),("I",1),("O",1),("P",1)],
    [("A",1),("S",1),("D",1),("F",1),("G",1),("H",1),("J",1),("K",1),("L",1)],
    [("SHIFT",2),("Z",1),("X",1),("C",1),("V",1),("B",1),("N",1),("M",1),("BACK",2)],
    [("123",2),("SPACE",5),("ENTER",2)]
]

keys_layout_symbols = [
    [("1",1),("2",1),("3",1),("4",1),("5",1),("6",1),("7",1),("8",1),("9",1),("0",1)],
    [("@",1),("#",1),("$",1),("_",1),("&",1),("-",1),("+",1),("(",1),(")",1)],
    [("SHIFT",2),("!",1),('"',1),("'",1),(":",1),(";",1),("?",1),("/",1),("BACK",2)],
    [("ABC",2),("SPACE",5),("ENTER",2)]
]

# --- Initialize screen ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Kit AI Touch Chat")
clock = pygame.time.Clock()
topbar = TopBarManager(SCREEN_WIDTH, SCREEN_HEIGHT, FONT, FONT, app_key="kitchat")

# --- Bot ---
bot = kit()

# --- Helper Functions ---
def create_keyboard_buttons(layout):
    buttons = []
    keyboard_start_y = SCREEN_HEIGHT - (len(layout) * (KEY_HEIGHT + PADDING)) - INPUT_HEIGHT - PADDING
    for row_index, row in enumerate(layout):
        total_units = sum([w for _, w in row])
        key_width_unit = (SCREEN_WIDTH - (len(row)+1)*PADDING) / total_units
        x_offset = PADDING
        y = keyboard_start_y + row_index*(KEY_HEIGHT + PADDING)
        for key, width_mult in row:
            width = key_width_unit * width_mult
            rect = pygame.Rect(x_offset, y, width, KEY_HEIGHT)
            buttons.append((key, rect))
            x_offset += width + PADDING
    return buttons

def get_current_layout():
    if is_symbols:
        return keys_layout_symbols
    else:
        return keys_layout_upper if is_shift else keys_layout_lower

def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def scroll_to_bottom():
    global scroll_offset
    total_lines = sum(len(wrap_text(msg, FONT, SCREEN_WIDTH - 20)) for _, msg in conversation_history)
    scroll_offset = -max(0, total_lines * 20 - (SCREEN_HEIGHT - INPUT_HEIGHT - len(get_current_layout())*(KEY_HEIGHT + PADDING) - 70))

def draw_chat():
    y_offset = 60 + scroll_offset
    max_height = SCREEN_HEIGHT - INPUT_HEIGHT - len(get_current_layout())*(KEY_HEIGHT + PADDING) - 70
    for speaker, msg in conversation_history:
        color = BOT_COLOR if speaker=="Kit" else USER_COLOR
        lines = wrap_text(msg, FONT, SCREEN_WIDTH-20)
        for line in lines:
            surf = FONT.render(f"{speaker}: {line}", True, color)
            screen.blit(surf, (PADDING, y_offset))
            y_offset += 20
            if y_offset > max_height:
                break

def draw_keyboard():
    layout = get_current_layout()
    for key, rect in create_keyboard_buttons(layout):
        # Draw solid backing
        backing_rect = pygame.Rect(rect.x - 2, rect.y - 2, rect.width + 4, rect.height + 4)
        pygame.draw.rect(screen, BG_COLOR, backing_rect)  # Darker base layer

        # Draw key surface
        pygame.draw.rect(screen, INPUT_BG_COLOR, rect, border_radius=5)

        # Draw key label
        display_key = " " if key == "SPACE" else key
        surf = FONT.render(display_key, True, TEXT_COLOR)
        surf_rect = surf.get_rect(center=rect.center)
        screen.blit(surf, surf_rect)

def handle_key_press(key_label):
    global is_shift, is_symbols, user_input
    if key_label=="SHIFT":
        is_shift = not is_shift
    elif key_label=="123":
        is_symbols = True
        is_shift = False
    elif key_label=="ABC":
        is_symbols = False
        is_shift = False
    elif key_label=="BACK":
        user_input = user_input[:-1]
    elif key_label=="ENTER":
        if user_input.strip():
            conversation_history.append(("You", user_input))
            response = bot.respond(user_input)
            conversation_history.append(("Kit", response))
            user_input = ""
            is_shift = False
            scroll_to_bottom()
    elif key_label=="SPACE":
        user_input += " "
    else:
        user_input += key_label.upper() if is_shift and not is_symbols else key_label.lower()
        if is_shift and not is_symbols:
            is_shift = False

# --- Main Loop ---
running = True
scroll_dragging = False
last_drag_y = 0

while running:
    screen.fill(BG_COLOR)
    mouse_pos = pygame.mouse.get_pos()
    mouse_clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        topbar.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                user_input = user_input[:-1]
            elif event.key == pygame.K_RETURN:
                if user_input.strip():
                    conversation_history.append(("You", user_input))
                    response = bot.respond(user_input)
                    conversation_history.append(("Kit", response))
                    user_input = ""
                    scroll_to_bottom()
            else:
                user_input += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_clicked = True
                last_drag_y = event.pos[1]
                for key, rect in create_keyboard_buttons(get_current_layout()):
                    if rect.collidepoint(event.pos):
                        handle_key_press(key)
            elif event.button == 4:
                scroll_offset += 20
            elif event.button == 5:
                scroll_offset -= 20

        if event.type == pygame.MOUSEMOTION:
            if event.buttons[0]:
                dy = event.pos[1]-last_drag_y
                scroll_offset += dy
                last_drag_y = event.pos[1]

    draw_chat()

    input_rect = pygame.Rect(PADDING, SCREEN_HEIGHT-INPUT_HEIGHT-PADDING, SCREEN_WIDTH-2*PADDING, INPUT_HEIGHT)
    pygame.draw.rect(screen, INPUT_BG_COLOR, input_rect, border_radius=5)
    display_text = user_input + ("|" if cursor_visible else "")
    input_surf = FONT.render(display_text, True, TEXT_COLOR)
    screen.blit(input_surf, (input_rect.x+5, input_rect.y+5))

    draw_keyboard()
    topbar.update()
    topbar.draw(screen)

    cursor_timer += clock.get_time()
    if cursor_timer>=500:
        cursor_visible = not cursor_visible
        cursor_timer=0

    pygame.display.flip()
    clock.tick(60)

bot.save_memory()
pygame.quit()
sys.exit()
