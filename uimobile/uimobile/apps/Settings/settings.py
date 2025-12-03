#!/usr/bin/env python3
"""
settings.py — Modern Pygame Settings (Real integration)
- Version: Full (C) — integrates nmcli, bluetoothctl, pactl/amixer, sysfs backlight.
- Requires: NetworkManager (nmcli) for Wi-Fi, bluez (bluetoothctl) for Bluetooth to actually control hardware.
- Expects modules.keyboard.run_keyboard() to return a string (password) or None to cancel.
"""

import os
import sys
import time
import shlex
import subprocess
import shutil
import platform
import pygame

# Try to import run_keyboard from your modules. If missing, fallback to a simple text modal.
try:
    from modules.keyboard import run_keyboard as touchscreen_keyboard
    HAS_TOUCH_KEYBOARD = True
except Exception:
    HAS_TOUCH_KEYBOARD = False
    touchscreen_keyboard = None

pygame.init()
pygame.font.init()

# --------------------------
# System helpers
# --------------------------
def run_cmd(cmd, check=False, capture_output=True, timeout=8):
    """Run a shell command (string or list). Return (returncode, stdout, stderr)."""
    try:
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        res = subprocess.run(cmd, check=check, capture_output=capture_output, text=True, timeout=timeout)
        return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()
    except Exception as e:
        return 1, "", str(e)

def has_command(name):
    return shutil.which(name) is not None

# --------------------------
# Capability detection
# --------------------------
USE_NMCLI = has_command("nmcli")
USE_BLUETOOTHCTL = has_command("bluetoothctl")
USE_PACTL = has_command("pactl")
USE_AMIXER = has_command("amixer")

BACKLIGHT_PATHS = []
_bl_base = "/sys/class/backlight"
if os.path.isdir(_bl_base):
    for d in os.listdir(_bl_base):
        p = os.path.join(_bl_base, d)
        if os.path.isdir(p):
            BACKLIGHT_PATHS.append(p)

# --------------------------
# System operations
# --------------------------

# Wi-Fi
def wifi_is_enabled():
    if not USE_NMCLI: return False
    code, out, err = run_cmd("nmcli radio wifi", timeout=2)
    if code != 0 or not out: return False
    return out.strip().lower() in ("enabled", "yes", "on")

def wifi_toggle(on):
    if not USE_NMCLI: return False, "nmcli not found"
    cmd = "nmcli radio wifi on" if on else "nmcli radio wifi off"
    code, out, err = run_cmd(cmd, timeout=6)
    if code == 0:
        return True, out or ("Wi-Fi turned " + ("on" if on else "off"))
    return False, err or out or "Failed to toggle Wi-Fi"

def list_wifi_networks():
    """Return list of dicts: {'ssid','signal','security'} using nmcli parsing."""
    nets = []
    if not USE_NMCLI:
        return nets
    # Use nmcli with no pretty headers and parse robustly
    code, out, err = run_cmd("nmcli -f SSID,SIGNAL,SECURITY device wifi list --escape no", timeout=10)
    if code != 0 or not out:
        return nets
    lines = [l for l in out.splitlines() if l.strip()]
    # drop header if present
    if lines and ("SSID" in lines[0] and "SIGNAL" in lines[0]):
        rows = lines[1:]
    else:
        rows = lines
    import re
    for ln in rows:
        parts = [p for p in re.split(r'\s{2,}', ln.strip()) if p]
        if not parts:
            continue
        ssid = parts[0]
        signal = parts[1] if len(parts) > 1 else ""
        security = parts[2] if len(parts) > 2 else ""
        if ssid and ssid != "--":
            nets.append({"ssid": ssid, "signal": signal, "security": security.strip()})
    # dedupe (last wins)
    seen = {}
    for n in nets:
        seen[n["ssid"]] = n
    return list(seen.values())

def connect_wifi_nmcli(ssid, password=None):
    if not USE_NMCLI:
        return False, "nmcli not available"
    if password:
        cmd = f"nmcli device wifi connect {shlex.quote(ssid)} password {shlex.quote(password)}"
    else:
        cmd = f"nmcli device wifi connect {shlex.quote(ssid)}"
    code, out, err = run_cmd(cmd, timeout=30)
    if code == 0:
        return True, out or "Connected"
    return False, err or out or "Failed to connect"

# Bluetooth
def bluetooth_scan_once(timeout=6):
    if not USE_BLUETOOTHCTL:
        return []
    try:
        p = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.stdin.write("power on\nscan on\n")
        p.stdin.flush()
        time.sleep(timeout)
        p.stdin.write("scan off\ndevices\nquit\n")
        p.stdin.flush()
        out, err = p.communicate(timeout=timeout+4)
    except Exception:
        return []
    devs = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Device"):
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                mac = parts[1].strip(); name = parts[2].strip()
                devs.append((mac, name))
    seen = {}
    for mac, nm in devs:
        seen[mac] = nm
    return [(m, seen[m]) for m in seen]

def bluetooth_pair_and_connect(mac):
    if not USE_BLUETOOTHCTL:
        return False, "bluetoothctl not available"
    cmds = f"agent on\ndefault-agent\nscan off\npair {mac}\ntrust {mac}\nconnect {mac}\nquit\n"
    try:
        p = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(cmds, timeout=25)
    except Exception as e:
        return False, str(e)
    if "Failed" in out or "AuthenticationFailed" in out or "not available" in out:
        return False, out + err
    return True, out

# Audio
def get_volume():
    if USE_PACTL:
        code, out, err = run_cmd("pactl get-sink-volume @DEFAULT_SINK@", timeout=2)
        if code == 0 and out:
            import re
            m = re.search(r'(\d{1,3})\%', out)
            if m:
                vol = int(m.group(1))
                code2, o2, e2 = run_cmd("pactl get-sink-mute @DEFAULT_SINK@", timeout=2)
                muted = ("yes" in o2.lower()) if code2 == 0 else False
                return vol, muted
    if USE_AMIXER:
        code, out, err = run_cmd("amixer get Master", timeout=2)
        if code == 0 and out:
            import re
            m = re.search(r'(\d{1,3})\%', out)
            muted = ("[off]" in out) or ("off" in out.splitlines()[-1])
            if m:
                vol = int(m.group(1)); return vol, muted
    return None, None

def set_volume(value):
    v = max(0, min(100, int(value)))
    if USE_PACTL:
        run_cmd(f"pactl set-sink-volume @DEFAULT_SINK@ {v}%")
        return True
    if USE_AMIXER:
        run_cmd(f"amixer set Master {v}%")
        return True
    return False

def toggle_mute():
    if USE_PACTL:
        run_cmd("pactl set-sink-mute @DEFAULT_SINK@ toggle")
        return True
    if USE_AMIXER:
        run_cmd("amixer set Master toggle")
        return True
    return False

# Brightness
def list_backlights():
    r = []
    for p in BACKLIGHT_PATHS:
        r.append({"name": os.path.basename(p), "path": p})
    return r

def read_brightness(backlight_path):
    try:
        with open(os.path.join(backlight_path, "brightness"), "r") as f:
            cur = int(f.read().strip())
        with open(os.path.join(backlight_path, "max_brightness"), "r") as f:
            mx = int(f.read().strip())
        return cur, mx
    except Exception:
        return None, None

def set_brightness(backlight_path, percent):
    cur_mx = read_brightness(backlight_path)
    if cur_mx[0] is None:
        return False
    cur, mx = cur_mx
    val = max(0, min(100, int(percent)))
    target = int(round((val / 100.0) * mx))
    try:
        with open(os.path.join(backlight_path, "brightness"), "w") as f:
            f.write(str(target))
        return True
    except Exception:
        return False

# --------------------------
# UI/UX configuration
# --------------------------

# Base resolution: keep small by default but auto-scale to fullscreen if desired
AUTO_SCALE = True   # True -> detect display resolution; False -> use SCREEN_W/SCREEN_H defaults
SCREEN_W_DEFAULT, SCREEN_H_DEFAULT = 480, 320

#if AUTO_SCALE:
   # info = pygame.display.Info()
    #SCREEN_W, SCREEN_H = info.current_w or SCREEN_W_DEFAULT, info.current_h or SCREEN_H_DEFAULT
#else:
SCREEN_W, SCREEN_H = SCREEN_W_DEFAULT, SCREEN_H_DEFAULT

# Create display
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Pi Settings")

# Colors
BG = (12, 14, 20)
CARD = (26, 30, 36)
ACCENT = (48, 120, 255)
ACCENT_LIGHT = (90, 160, 255)
TEXT = (230, 240, 255)
TEXT_DIM = (150, 160, 170)
DANGER = (200, 70, 70)

# Fonts scaled to screen
TITLE_FONT = pygame.font.SysFont("DejaVuSans", max(18, int(SCREEN_H * 0.06)), bold=True)
HEADER_FONT = pygame.font.SysFont("DejaVuSans", max(14, int(SCREEN_H * 0.045)), bold=True)
BODY_FONT = pygame.font.SysFont("DejaVuSans", max(12, int(SCREEN_H * 0.035)))
SMALL_FONT = pygame.font.SysFont("DejaVuSans", max(10, int(SCREEN_H * 0.028)))

# UI geometry
LEFT_MENU_W = int(SCREEN_W * 0.28)
LEFT_MENU_X = 12
LEFT_MENU_Y = 72
LEFT_MENU_BOTTOM_PADDING = 20

# Dynamic sizes for list items
MENU_ITEM_H = max(44, int(SCREEN_H * 0.09))
NETWORK_ITEM_H = max(48, int(SCREEN_H * 0.11))

# Clock
clock = pygame.time.Clock()

# Topbar integration (optional)
try:
    from modules.top_bar import TopBarManager
    topbar = TopBarManager(SCREEN_W, SCREEN_H, SMALL_FONT, HEADER_FONT, app_key="settings")
except Exception:
    topbar = None

# --------------------------
# Utility drawing functions
# --------------------------
def draw_rounded(surface, rect, color, radius=12):
    if isinstance(rect, pygame.Rect):
        pygame.draw.rect(surface, color, rect, border_radius=radius)
    else:
        x,y,w,h = rect
        pygame.draw.rect(surface, color, (x,y,w,h), border_radius=radius)

def draw_gradient_top(surface, rect, top_color, bottom_color):
    x,y,w,h = rect
    grad = pygame.Surface((w, h))
    for i in range(h):
        ratio = i / max(h-1, 1)
        r = int(top_color[0] * (1-ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1-ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1-ratio) + bottom_color[2] * ratio)
        pygame.draw.line(grad, (r,g,b), (0,i), (w,i))
    grad.set_alpha(230)
    surface.blit(grad, (x,y))

def draw_button(surface, rect, label, font, hovered, bg, hover_bg, fg=TEXT):
    c = hover_bg if hovered else bg
    draw_rounded(surface, rect, c, radius=12)
    txt = font.render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=pygame.Rect(rect).center))

def draw_signal_bars(surface, x, y, w, h, signal_str):
    """signal_str numeric 0..100 or empty. Draw 4 bars from left to right."""
    try:
        val = int(signal_str)
    except Exception:
        val = None
    bar_w = max(6, w // 6)
    spacing = max(3, bar_w // 2)
    for i in range(4):
        bx = x + i * (bar_w + spacing)
        bh = int(((i+1)/4.0) * h)
        by = y + h - bh
        color = (90,90,90)
        if val is not None:
            threshold = (i+1) * 25
            if val >= threshold:
                color = ACCENT
        pygame.draw.rect(surface, color, (bx, by, bar_w, bh), border_radius=2)

# --------------------------
# Fallback keyboard (if modules.keyboard not available)
# --------------------------
def fallback_keyboard(surface, prompt="Enter text"):
    """Simple blocking modal input (for environments without touchscreen keyboard)."""
    f = pygame.font.SysFont("DejaVuSans", 18)
    w, h = surface.get_size()
    box_w, box_h = min(520, w-40), 160
    box = pygame.Rect((w-box_w)//2, (h-box_h)//2, box_w, box_h)
    input_rect = pygame.Rect(box.x+16, box.y+56, box_w-32, 36)
    text = ""
    clock_local = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return text
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if ev.unicode and len(ev.unicode) == 1:
                        text += ev.unicode
            if ev.type == pygame.MOUSEBUTTONUP:
                # clicking outside cancels
                if not input_rect.collidepoint(ev.pos) and not box.collidepoint(ev.pos):
                    return None
                
        overlay = pygame.Surface((w,h), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        surface.blit(overlay, (0,0))
        draw_rounded(surface, box, CARD)
        pygame.draw.rect(surface, (80,80,80), box, 1, border_radius=10)
        surface.blit(f.render(prompt, True, TEXT), (box.x+16, box.y+12))
        draw_rounded(surface, input_rect, (40,40,48))
        surface.blit(f.render("*" * len(text), True, TEXT), (input_rect.x+8, input_rect.y+8))
        pygame.display.flip()
        clock_local.tick(30)

def get_touch_keyboard(prompt=None):
    """Use provided touchscreen keyboard if available, else fallback modal."""
    if HAS_TOUCH_KEYBOARD and touchscreen_keyboard:
        try:
            return touchscreen_keyboard()
        except Exception:
            # if keyboard crashes, fallback
            return fallback_keyboard(screen, prompt or "Enter text")
    else:
        return fallback_keyboard(screen, prompt or "Enter text")

# --------------------------
# Scrollable UI components
# --------------------------

# Sidebar scrolling state
sidebar_items = ["Wi-Fi Toggle", "Wi-Fi Networks", "Bluetooth", "Sound", "Brightness", "About", "Reboot"]
sidebar_scroll = 0.0
sidebar_velocity = 0.0
sidebar_dragging = False
sidebar_last_y = 0.0

# Wi-Fi list scrolling state
wifi_scroll = 0.0
wifi_velocity = 0.0
wifi_dragging = False
wifi_last_y = 0.0

# Cached lists
wifi_cache = []
wifi_last_scan = 0.0
wifi_scan_interval = 6.0

# Bluetooth cache
bt_cache = []
bt_last_scan = 0.0
bt_scan_interval = 8.0

# Brightness choices
backlights = list_backlights()
selected_backlight = backlights[0]["path"] if backlights else None

# UI State
selected_panel = "Wi-Fi Toggle"
feedback = ""
fb_time = 0
show_dialog = False
dialog_type = None

# --------------------------
# Core: wifi list page (touch scroll + large text)
# --------------------------
def wifi_list_screen(networks):
    global wifi_scroll, wifi_velocity, wifi_dragging, wifi_last_y, feedback, fb_time
    running_local = True
    # compute content height
    entry_h = NETWORK_ITEM_H
    spacing = max(8, int(SCREEN_H*0.02))
    content_h = len(networks) * (entry_h + spacing)

    # visible area
    area_x = LEFT_MENU_W + 24
    area_y = LEFT_MENU_Y
    area_w = SCREEN_W - area_x - 20
    area_h = SCREEN_H - area_y - 28

    inertial_friction = 0.92
    while running_local:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for ev in pygame.event.get():
            if topbar:
                try:
                    topbar.handle_event(ev)
                except Exception:
                    pass
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                # start drag
                if (area_x <= ev.pos[0] <= area_x + area_w) and (area_y <= ev.pos[1] <= area_y + area_h):
                    wifi_dragging = True
                    wifi_velocity = 0
                    wifi_last_y = ev.pos[1]
                click_pos = ev.pos
            if ev.type == pygame.MOUSEBUTTONUP:
                wifi_dragging = False
            if ev.type == pygame.MOUSEMOTION and wifi_dragging:
                dy = ev.pos[1] - wifi_last_y
                wifi_last_y = ev.pos[1]
                wifi_scroll += dy
                wifi_velocity = dy

        # inertia
        if not wifi_dragging:
            wifi_scroll += wifi_velocity
            wifi_velocity *= inertial_friction

        # clamp
        max_scroll = 0
        min_scroll = min(0, area_h - content_h - 8)
        if wifi_scroll > max_scroll:
            wifi_scroll = max_scroll
            wifi_velocity = 0
        if wifi_scroll < min_scroll:
            wifi_scroll = min_scroll
            wifi_velocity = 0

        # draw base screen (we reuse main screen rendering; caller should have already drawn background)
        # We'll render just the list into the panel area:
        # panel background
        panel_rect = pygame.Rect(area_x, area_y, area_w, area_h)
        draw_rounded(screen, panel_rect, CARD, radius=12)
        # clip to list area
        prev_clip = screen.get_clip()
        screen.set_clip(panel_rect)

        y = area_y + 12 + int(wifi_scroll)
        for idx, net in enumerate(networks):
            r = pygame.Rect(area_x + 12, y, area_w - 24, entry_h)
            hovered = r.collidepoint(mouse_pos)
            draw_rounded(screen, r, (36,40,44) if not hovered else (46,54,70), radius=10)
            ssid_txt = HEADER_FONT.render(net.get("ssid", "<hidden>"), True, TEXT)
            screen.blit(ssid_txt, (r.x + 12, r.y + 8))
            # signal bars at right
            draw_signal_bars(screen, r.right - 72, r.y + 8, 56, r.h - 16, net.get("signal", ""))
            # security icon
            sec = net.get("security", "").strip()
            if sec and sec not in ("--", ""):
                lock_txt = BODY_FONT.render("🔒", True, TEXT_DIM)
                screen.blit(lock_txt, (r.right - 110, r.y + 8))
            # detect taps (we'll check for click after event loop)
            y += entry_h + spacing

        screen.set_clip(prev_clip)

        # hint
        hint = SMALL_FONT.render("Swipe up/down to scroll • Tap a network to connect", True, TEXT_DIM)
        screen.blit(hint, (area_x + 12, panel_rect.bottom - 26))

        pygame.display.flip()

        # handle clicks after drawing (this makes tap feel responsive)
        # read events again to capture clicks within this function loop
        for ev in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                # if bottom tap -> go back
                if my > SCREEN_H - 28:
                    return "Back"
                # check each network for hit
                y = area_y + 12 + int(wifi_scroll)
                for net in networks:
                    r = pygame.Rect(area_x + 12, y, area_w - 24, entry_h)
                    if r.collidepoint((mx, my)):
                        # selected
                        sec = (net.get("security") or "").upper()
                        locked = bool(sec and sec != "--")
                        if locked:
                            pwd = get_touch_keyboard(prompt=f"Password for {net['ssid']}")
                            if pwd is None:
                                feedback_local = "Wi-Fi cancelled"
                            else:
                                ok, msg = connect_wifi_nmcli(net["ssid"], pwd if pwd else None)
                                feedback_local = msg
                        else:
                            ok, msg = connect_wifi_nmcli(net["ssid"], None)
                            feedback_local = msg
                        # set feedback to main UI
                        global feedback, fb_time
                        feedback = feedback_local
                        fb_time = time.time()
                        # small delay
                        time.sleep(0.08)
                        return feedback_local
                    y += entry_h + spacing

    # end while
    return None

# --------------------------
# Main screen
# --------------------------
def main():
    global sidebar_scroll, sidebar_velocity, sidebar_dragging, sidebar_last_y
    global wifi_cache, wifi_last_scan, bt_cache, bt_last_scan
    global selected_panel, feedback, fb_time, show_dialog, dialog_type, wifi_scroll, wifi_velocity
    # Sidebar scrolling variables
    sidebar_dragging = False          # mouse drag
    sidebar_touch_dragging = False    # touch drag
    sidebar_last_y = 0                # last mouse y for drag
    sidebar_touch_last_y = 0          # last finger y for touch
    sidebar_velocity = 0              # momentum

    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        mouse = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            # --- existing topbar or quit handling ---
            if topbar:
                try: topbar.handle_event(ev)
                except Exception: pass
            if ev.type == pygame.QUIT:
                running = False

            # --- Mouse drag ---
            if ev.type == pygame.MOUSEBUTTONDOWN:
                click = ev.pos
                if click[0] < LEFT_MENU_W + 8:   # left menu area
                    sidebar_dragging = True
                    sidebar_velocity = 0
                    sidebar_last_y = click[1]

            if ev.type == pygame.MOUSEBUTTONUP:
                sidebar_dragging = False

            if ev.type == pygame.MOUSEMOTION and sidebar_dragging:
                dy = ev.pos[1] - sidebar_last_y
                sidebar_last_y = ev.pos[1]
                sidebar_scroll += dy
                sidebar_velocity = dy

            # --- Mouse wheel ---
            if ev.type == pygame.MOUSEWHEEL:
                sidebar_scroll += ev.y * 20  # scroll speed
                sidebar_velocity = ev.y * 20

            # --- Touch / finger input ---
            if ev.type == pygame.FINGERDOWN:
                fx, fy = ev.x * SCREEN_W, ev.y * SCREEN_H
                if fx < LEFT_MENU_W + 8:
                    sidebar_touch_dragging = True
                    sidebar_touch_last_y = fy

            if ev.type == pygame.FINGERMOTION and sidebar_touch_dragging:
                fy = ev.y * SCREEN_H
                dy = fy - sidebar_touch_last_y
                sidebar_touch_last_y = fy
                sidebar_scroll += dy
                sidebar_velocity = dy

            if ev.type == pygame.FINGERUP:
                sidebar_touch_dragging = False


        # periodic scans
        now = time.time()
        if USE_NMCLI and now - wifi_last_scan > wifi_scan_interval:
            try:
                wifi_cache = list_wifi_networks()
            except Exception:
                wifi_cache = []
            wifi_last_scan = now
        if USE_BLUETOOTHCTL and now - bt_last_scan > bt_scan_interval:
            try:
                bt_cache = bluetooth_scan_once(timeout=4)
            except Exception:
                bt_cache = []
            bt_last_scan = now

        # background
        screen.fill(BG)
        draw_gradient_top(screen, (0,0,SCREEN_W,64), (18,26,40), (12,14,20))
        screen.blit(TITLE_FONT.render("Settings", True, TEXT), (12, 10))
        # --- Apply momentum scrolling ---
        if not sidebar_dragging and not sidebar_touch_dragging:
            sidebar_scroll += sidebar_velocity
            sidebar_velocity *= 0.85  # friction

        # --- Clamp sidebar_scroll ---
        menu_h = SCREEN_H - LEFT_MENU_Y - LEFT_MENU_BOTTOM_PADDING
        content_h = len(sidebar_items) * (MENU_ITEM_H + 12)
        if sidebar_scroll > 0:
            sidebar_scroll = 0
            sidebar_velocity = 0
        min_scroll = min(0, menu_h - content_h - 8)
        if sidebar_scroll < min_scroll:
            sidebar_scroll = min_scroll
            sidebar_velocity = 0

        # --- Apply momentum scrolling ---
        if not sidebar_dragging and not sidebar_touch_dragging:
            sidebar_scroll += sidebar_velocity
            sidebar_velocity *= 0.85  # friction

        # --- Clamp sidebar_scroll ---
        menu_h = SCREEN_H - LEFT_MENU_Y - LEFT_MENU_BOTTOM_PADDING
        content_h = len(sidebar_items) * (MENU_ITEM_H + 12)
        if sidebar_scroll > 0:
            sidebar_scroll = 0
            sidebar_velocity = 0
        min_scroll = min(0, menu_h - content_h - 8)
        if sidebar_scroll < min_scroll:
            sidebar_scroll = min_scroll
            sidebar_velocity = 0


        # draw each menu item
        for i, m in enumerate(sidebar_items):
            y = LEFT_MENU_Y + i * (MENU_ITEM_H + 12) + int(sidebar_scroll)
            r = pygame.Rect(LEFT_MENU_X, y, LEFT_MENU_W, MENU_ITEM_H)
            hovered = r.collidepoint(pygame.mouse.get_pos())
            sel = (m == selected_panel)
            bg = (36, 60, 80) if (hovered or sel) else (28, 34, 40)
            draw_rounded(screen, r, bg, radius=10)
            label = HEADER_FONT.render(m, True, TEXT if sel else TEXT_DIM)
            screen.blit(label, (r.x + 12, r.y + (r.h - label.get_height())//2))


        # Right content panel
        panel_rect = pygame.Rect(LEFT_MENU_W + 24, 72, SCREEN_W - (LEFT_MENU_W + 36), SCREEN_H - 92)
        draw_rounded(screen, panel_rect, CARD, radius=12)
        pad = 14
        cx = panel_rect.x + pad
        cy = panel_rect.y + pad

        # Render the currently selected panel
        if selected_panel == "Wi-Fi Toggle":
            screen.blit(HEADER_FONT.render("Wi-Fi", True, TEXT), (cx, cy))
            cy += 40
            if not USE_NMCLI:
                screen.blit(BODY_FONT.render("NetworkManager (nmcli) not found.", True, TEXT_DIM), (cx, cy))
            else:
                enabled = wifi_is_enabled()
                screen.blit(BODY_FONT.render(f"Wi-Fi: {'Enabled' if enabled else 'Disabled'}", True, TEXT), (cx, cy))
                cy += 44
                b_w = 140
                btn_toggle = pygame.Rect(cx, cy, b_w, 44)
                btn_scan = pygame.Rect(cx + b_w + 16, cy, b_w, 44)
                draw_button(screen, btn_toggle, "Turn Off" if enabled else "Turn On", BODY_FONT, btn_toggle.collidepoint(mouse), (40,40,48), (80,110,170))
                draw_button(screen, btn_scan, "Networks", BODY_FONT, btn_scan.collidepoint(mouse), (40,40,48), (80,110,170))
                if pygame.mouse.get_pressed()[0] and pygame.mouse.get_pos() and (btn_toggle.collidepoint(pygame.mouse.get_pos()) or btn_scan.collidepoint(pygame.mouse.get_pos())):
                    # handle click logic simply: detect immediate state
                    if btn_toggle.collidepoint(pygame.mouse.get_pos()):
                        ok, msg = wifi_toggle(not enabled)
                        feedback = msg; fb_time = time.time()
                    elif btn_scan.collidepoint(pygame.mouse.get_pos()):
                        selected_panel = "Wi-Fi Networks"

        elif selected_panel == "Wi-Fi Networks":
            screen.blit(HEADER_FONT.render("Wi-Fi Networks", True, TEXT), (cx, cy))
            cy += 20
            # show the scrollable wifi list UI
            # draw a small search/refresh row
            refresh_rect = pygame.Rect(cx, cy, 120, 36)
            draw_rounded(screen, refresh_rect, (36,36,40), radius=10)
            screen.blit(BODY_FONT.render("Refresh", True, TEXT_DIM), (refresh_rect.x + 12, refresh_rect.y + 8))
            # check refresh tap
            if pygame.mouse.get_pressed()[0] and refresh_rect.collidepoint(pygame.mouse.get_pos()):
                wifi_cache[:] = list_wifi_networks() if USE_NMCLI and wifi_is_enabled() else []
                fb_time = time.time()
                feedback = "Refreshed networks"
            cy += 48
            # If not enabled or nmcli missing show message
            if not USE_NMCLI:
                screen.blit(BODY_FONT.render("nmcli not available — install NetworkManager.", True, TEXT_DIM), (cx, cy))
            elif not wifi_is_enabled():
                screen.blit(BODY_FONT.render("Wi-Fi radio is OFF. Turn it on from 'Wi-Fi Toggle'.", True, TEXT_DIM), (cx, cy))
            else:
                # Ensure we have a cache (fallback to immediate scan)
                if not wifi_cache:
                    wifi_cache = list_wifi_networks() if USE_NMCLI and wifi_is_enabled() else []
                # draw header hint
                hint = SMALL_FONT.render("Swipe the list to scroll. Tap an entry to connect.", True, TEXT_DIM)
                screen.blit(hint, (cx, panel_rect.bottom - 34))
                # call wifi_list_screen to handle drawing & touch scrolling & connecting
                res = wifi_list_screen(wifi_cache)
                # wifi_list_screen returns "Back" or a feedback message
                if res == "Back":
                    selected_panel = "Wi-Fi Toggle"
                elif isinstance(res, str) and res:
                    feedback = res; fb_time = time.time()

        elif selected_panel == "Bluetooth":
            screen.blit(HEADER_FONT.render("Bluetooth", True, TEXT), (cx, cy))
            cy += 36
            if not USE_BLUETOOTHCTL:
                screen.blit(BODY_FONT.render("bluetoothctl not available — install bluez.", True, TEXT_DIM), (cx, cy))
            else:
                if not bt_cache or (time.time() - bt_last_scan) > bt_scan_interval:
                    bt_cache[:] = bluetooth_scan_once(timeout=4)
                if not bt_cache:
                    screen.blit(BODY_FONT.render("Scanning for devices...", True, TEXT_DIM), (cx, cy))
                else:
                    for i, (mac, name) in enumerate(bt_cache[:6]):
                        r = pygame.Rect(cx, cy + i * 52, panel_rect.width - pad*2, 44)
                        draw_rounded(screen, r, (36,40,44), radius=8)
                        screen.blit(BODY_FONT.render(f"{name} [{mac}]", True, TEXT), (r.x + 8, r.y + 6))
                        if pygame.mouse.get_pressed()[0] and r.collidepoint(pygame.mouse.get_pos()):
                            ok, msg = bluetooth_pair_and_connect(mac)
                            feedback = "Paired/Connected" if ok else f"Bluetooth error: {msg}"
                            fb_time = time.time()

        elif selected_panel == "Sound":
            screen.blit(HEADER_FONT.render("Sound", True, TEXT), (cx, cy))
            cy += 36
            vol, muted = get_volume()
            if vol is None:
                screen.blit(BODY_FONT.render("Audio control not available.", True, TEXT_DIM), (cx, cy))
            else:
                screen.blit(BODY_FONT.render(f"Volume: {vol}% {'(Muted)' if muted else ''}", True, TEXT), (cx, cy))
                cy += 40
                b_minus = pygame.Rect(cx, cy, 110, 44)
                b_plus = pygame.Rect(cx + 126, cy, 110, 44)
                b_mute = pygame.Rect(cx + 252, cy, 110, 44)
                draw_button(screen, b_minus, "-10%", BODY_FONT, b_minus.collidepoint(mouse), (38,38,44), (60,80,140))
                draw_button(screen, b_plus, "+10%", BODY_FONT, b_plus.collidepoint(mouse), (38,38,44), (60,80,140))
                draw_button(screen, b_mute, "Mute", BODY_FONT, b_mute.collidepoint(mouse), (38,38,44), (180,70,70))
                if pygame.mouse.get_pressed()[0]:
                    mp = pygame.mouse.get_pos()
                    if b_minus.collidepoint(mp):
                        set_volume((vol or 50) - 10)
                    elif b_plus.collidepoint(mp):
                        set_volume((vol or 50) + 10)
                    elif b_mute.collidepoint(mp):
                        toggle_mute()
                    vol, muted = get_volume()
                    feedback = f"Volume {vol}%" if vol is not None else "Volume changed"
                    fb_time = time.time()

        elif selected_panel == "Brightness":
            screen.blit(HEADER_FONT.render("Brightness", True, TEXT), (cx, cy))
            cy += 36
            if not BACKLIGHT_PATHS:
                screen.blit(BODY_FONT.render("No backlight sysfs detected.", True, TEXT_DIM), (cx, cy))
            else:
                cur, mx = read_brightness(selected_backlight)
                if cur is None:
                    screen.blit(BODY_FONT.render("Cannot read backlight (permissions?). Run as root.", True, TEXT_DIM), (cx, cy))
                else:
                    pct = int(round((cur / mx) * 100))
                    screen.blit(BODY_FONT.render(f"Current: {pct}% (raw {cur}/{mx})", True, TEXT), (cx, cy))
                    cy += 40
                    b_minus = pygame.Rect(cx, cy, 110, 44)
                    b_plus = pygame.Rect(cx + 126, cy, 110, 44)
                    draw_button(screen, b_minus, "-10%", BODY_FONT, b_minus.collidepoint(mouse), (38,38,44), (60,80,140))
                    draw_button(screen, b_plus, "+10%", BODY_FONT, b_plus.collidepoint(mouse), (38,38,44), (60,80,140))
                    if pygame.mouse.get_pressed()[0]:
                        mp = pygame.mouse.get_pos()
                        if b_minus.collidepoint(mp):
                            set_brightness(selected_backlight, pct - 10)
                        elif b_plus.collidepoint(mp):
                            set_brightness(selected_backlight, pct + 10)
                        time.sleep(0.06)
                        cur, mx = read_brightness(selected_backlight)
                        pct = int(round((cur / mx) * 100)) if cur is not None else pct
                        feedback = f"Brightness {pct}%"
                        fb_time = time.time()

        elif selected_panel == "About":
            screen.blit(HEADER_FONT.render("About", True, TEXT), (cx, cy))
            cy += 28
            info_lines = [
                f"Platform: {platform.system()} {platform.release()}",
                f"Python: {platform.python_version()}",
                "Modern Pi Settings (Pygame)",
                "",
                "Factory Reset will remove login files & reboot."
            ]
            for ln in info_lines:
                screen.blit(BODY_FONT.render(ln, True, TEXT_DIM), (cx, cy)); cy += 22
            btn_reset = pygame.Rect(cx, cy + 8, panel_rect.width - pad*2, 44)
            draw_button(screen, btn_reset, "⚠️ Factory Reset (delete login files & reboot)", BODY_FONT, btn_reset.collidepoint(mouse), DANGER, (220,70,70))
            if pygame.mouse.get_pressed()[0] and btn_reset.collidepoint(pygame.mouse.get_pos()):
                show_dialog = True; dialog_type = "Reset Password"

        elif selected_panel == "Reboot":
            # quick reboot action
            screen.blit(HEADER_FONT.render("Reboot", True, TEXT), (cx, cy))
            cy += 24
            btn_reboot = pygame.Rect(cx, cy + 8, 200, 44)
            draw_button(screen, btn_reboot, "Reboot System", BODY_FONT, btn_reboot.collidepoint(mouse), (180,70,70), (220,90,90))
            if pygame.mouse.get_pressed()[0] and btn_reboot.collidepoint(pygame.mouse.get_pos()):
                show_dialog = True; dialog_type = "Reboot"

        # Draw feedback bar
        if feedback and (time.time() - fb_time < 4):
            fb_bar = pygame.Rect(0, SCREEN_H - 36, SCREEN_W, 36)
            draw_rounded(screen, fb_bar, (6,8,10), radius=0)
            screen.blit(BODY_FONT.render(feedback, True, ACCENT_LIGHT), (12, SCREEN_H - 28))

        # Draw topbar (if available)
        if topbar:
            try:
                topbar.update()
                topbar.draw(screen)
            except Exception:
                pass
        else:
            # fallback small header text
            screen.blit(SMALL_FONT.render("Settings", True, TEXT_DIM), (12, 38))

        # Sidebar click detection: handle taps (not drags)
        if pygame.mouse.get_pressed()[0]:
            mp = pygame.mouse.get_pos()
            if mp[0] < LEFT_MENU_W + 8:
                # compute which item
                rel_y = mp[1] - LEFT_MENU_Y - sidebar_scroll
                idx = int(rel_y // (MENU_ITEM_H + 12)) if rel_y >= 0 else -1
                if 0 <= idx < len(sidebar_items):
                    selected_panel = sidebar_items[idx]

        pygame.display.flip()

    pygame.quit()
    sys.exit()

# --------------------------
# Entrypoint
# --------------------------
if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Warning: running without root. Some actions may fail (brightness, reboot...).")
    main()
