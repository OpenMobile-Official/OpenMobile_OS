# settings.py
# Pygame Settings UI (480x320) — integrated TopBarManager, Wi-Fi toggles + networks
# Run as root (sudo) on the Pi for full functionality.

import pygame
import sys
import os
import time
import platform
import subprocess
import shlex
import shutil
from modules.top_bar import TopBarManager

# --------------------------
# Paths
# --------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
USER_FILE = os.path.join(CONFIG_DIR, "user.enc")
KEY_FILE = os.path.join(CONFIG_DIR, "key.key")
MAIN_FILE = os.path.join(BASE_DIR, "main.py")

# --------------------------
# Helper utilities
# --------------------------
def run_cmd(cmd, check=False, capture_output=True, timeout=8):
    """Run a shell command (list or string). Returns (returncode, stdout, stderr)."""
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
# System-capability detection
# --------------------------
USE_NMCLI = has_command("nmcli")
USE_BLUETOOTHCTL = has_command("bluetoothctl")
USE_AMIXER = has_command("amixer")
USE_PACTL = has_command("pactl")
# For brightness we check sysfs
BACKLIGHT_PATHS = []
bl_base = "/sys/class/backlight"
if os.path.isdir(bl_base):
    for d in os.listdir(bl_base):
        p = os.path.join(bl_base, d)
        if os.path.isdir(p):
            BACKLIGHT_PATHS.append(p)

# --------------------------
# System operations (WiFi, Bluetooth, Sound, Brightness)
# --------------------------

# --- Wi-Fi helpers via nmcli ---
def wifi_is_enabled():
    """Return True if Wi-Fi radio is enabled (nmcli available)."""
    if not USE_NMCLI:
        return False
    code, out, err = run_cmd("nmcli radio wifi", timeout=2)
    if code != 0 or not out:
        return False
    return out.strip().lower() in ("enabled", "yes", "on")

def wifi_toggle(on):
    """Turn Wi-Fi radio on/off. on=True to enable, False to disable."""
    if not USE_NMCLI:
        return False, "nmcli not found"
    cmd = "nmcli radio wifi on" if on else "nmcli radio wifi off"
    code, out, err = run_cmd(cmd, timeout=5)
    if code == 0:
        return True, out or ("Wi-Fi turned " + ("on" if on else "off"))
    else:
        return False, err or out or "Failed to toggle Wi-Fi"

def list_wifi_networks():
    """Return list of dicts: {'ssid':..., 'signal':..., 'security':...}"""
    networks = []
    if not USE_NMCLI:
        return networks
    code, out, err = run_cmd("nmcli -f SSID,SIGNAL,SECURITY device wifi list", timeout=10)
    if code != 0 or not out:
        return networks
    lines = [l for l in out.splitlines() if l.strip()]
    # If header present (contains SSID), drop it
    if lines and ("SSID" in lines[0] and "SIGNAL" in lines[0]):
        rows = lines[1:]
    else:
        rows = lines
    for ln in rows:
        # split on two or more spaces to preserve SSIDs with single spaces
        import re
        parts = [p for p in re.split(r'\s{2,}', ln.strip()) if p]
        if not parts:
            continue
        ssid = parts[0]
        signal = parts[1] if len(parts) > 1 else ""
        security = parts[2] if len(parts) > 2 else ""
        # clean up placeholder entries
        if ssid and ssid != "--":
            networks.append({"ssid": ssid, "signal": signal, "security": security})
    # dedupe by ssid (last wins)
    seen = {}
    for n in networks:
        seen[n["ssid"]] = n
    return list(seen.values())

def connect_wifi_nmcli(ssid, password=None):
    """Connect to SSID using nmcli. Returns (ok, msg)."""
    if not USE_NMCLI:
        return False, "nmcli not found"
    if password:
        cmd = f"nmcli device wifi connect {shlex.quote(ssid)} password {shlex.quote(password)}"
    else:
        cmd = f"nmcli device wifi connect {shlex.quote(ssid)}"
    code, out, err = run_cmd(cmd, timeout=25)
    if code == 0:
        return True, out or "Connected"
    else:
        # nmcli prints useful stderr sometimes
        return False, err or out or "Failed to connect"

# --- Bluetooth via bluetoothctl ---
def bluetooth_scan_once(timeout=6):
    """Start a scan and return list of (mac, name)."""
    if not USE_BLUETOOTHCTL:
        return []
    cmds = "power on\nscan on\n"
    try:
        p = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.stdin.write(cmds)
        p.stdin.flush()
        time.sleep(timeout)
        p.stdin.write("scan off\ndevices\nquit\n")
        p.stdin.flush()
        out, err = p.communicate(timeout=timeout + 4)
    except Exception:
        return []
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Device"):
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                mac = parts[1].strip()
                name = parts[2].strip()
                devices.append((mac, name))
    # dedupe by mac
    seen = {}
    for mac, name in devices:
        seen[mac] = name
    return [(m, seen[m]) for m in seen]

def bluetooth_pair_and_connect(mac):
    """Pair + connect to device at MAC. Returns (ok,msg)."""
    if not USE_BLUETOOTHCTL:
        return False, "bluetoothctl not available"
    cmds = f"agent on\ndefault-agent\nscan off\npair {mac}\ntrust {mac}\nconnect {mac}\nquit\n"
    try:
        p = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(cmds, timeout=20)
    except Exception as e:
        return False, str(e)
    if "Failed" in out or "not available" in out or "Could not" in out or "AuthenticationFailed" in out:
        return False, out + err
    return True, out

# --- Sound via amixer (ALSA) or pactl (PulseAudio) ---
def get_volume():
    """Return volume (0-100) and muted boolean."""
    if USE_PACTL:
        code, out, err = run_cmd("pactl get-sink-volume @DEFAULT_SINK@", timeout=2)
        if code == 0 and out:
            import re
            m = re.search(r'(\d{1,3})\%', out)
            if m:
                try:
                    vol = int(m.group(1))
                    code2, o2, e2 = run_cmd("pactl get-sink-mute @DEFAULT_SINK@", timeout=2)
                    muted = ("yes" in o2.lower()) if code2 == 0 else False
                    return vol, muted
                except:
                    pass
    if USE_AMIXER:
        code, out, err = run_cmd("amixer get Master", timeout=2)
        if code == 0 and out:
            import re
            m = re.search(r'(\d{1,3})\%', out)
            muted = ("[off]" in out) or ("off" in out.splitlines()[-1])
            if m:
                try:
                    vol = int(m.group(1))
                    return vol, muted
                except:
                    pass
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

# --- Brightness via sysfs backlight ---
def list_backlights():
    result = []
    for p in BACKLIGHT_PATHS:
        name = os.path.basename(p)
        result.append({"name": name, "path": p})
    return result

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
    cur, mx = read_brightness(backlight_path)
    if cur is None:
        return False
    val = max(0, min(100, int(percent)))
    target = int(round((val / 100.0) * mx))
    try:
        with open(os.path.join(backlight_path, "brightness"), "w") as f:
            f.write(str(target))
        return True
    except Exception:
        return False

# --------------------------
# UI (Pygame)
# --------------------------
SCREEN_W, SCREEN_H = 480, 320

def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def draw_rounded(surface, rect, color, radius=8):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_button(surface, rect, label, font, hovered, bg, hover_bg, fg=(255,255,255)):
    c = hover_bg if hovered else bg
    draw_rounded(surface, rect, c, radius=8)
    txt = font.render(label, True, fg)
    surface.blit(txt, txt.get_rect(center=rect.center))

def text_input_modal(surface, prompt):
    """Simple blocking text input modal - returns string or None if cancelled."""
    pygame.font.init()
    f = pygame.font.SysFont("Arial", 16)
    w, h = surface.get_size()
    box = pygame.Rect((w-420)//2, (h-140)//2, 420, 140)
    input_rect = pygame.Rect(box.x+20, box.y+60, box.width-40, 30)
    text = ""
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    return text
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if ev.unicode and len(ev.unicode) == 1:
                        text += ev.unicode
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if not input_rect.collidepoint(ev.pos) and not box.collidepoint(ev.pos):
                    return None
        # draw overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        surface.blit(overlay, (0,0))
        draw_rounded(surface, box, (28,30,36))
        pygame.draw.rect(surface, (100,100,100), box, 1)
        surface.blit(f.render(prompt, True, (200,230,255)), (box.x+20, box.y+20))
        draw_rounded(surface, input_rect, (40,40,48))
        pygame.draw.rect(surface, (80,80,80), input_rect, 1)
        masked = "*" * len(text)
        surface.blit(f.render(masked, True, (230,230,230)), (input_rect.x+6, input_rect.y+6))
        pygame.display.flip()
        clock.tick(30)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Pi Settings (Real)")
    clock = pygame.time.Clock()
    font_s = pygame.font.SysFont("Arial", 14)
    font_m = pygame.font.SysFont("Arial", 18)
    font_l = pygame.font.SysFont("Arial", 22)

    # Top bar manager integration
    topbar = TopBarManager(SCREEN_W, SCREEN_H, font_s, font_m, app_key="settings")

    # Menu and state
    menu_items = ["Wi-Fi Toggle", "Wi-Fi Networks", "Bluetooth", "Sound", "Brightness", "About", "Reboot"]
    selected = "Wi-Fi Toggle"
    feedback = ""
    fb_time = 0
    show_dialog = False
    dialog_type = None

    # WiFi state cache
    wifi_list = []
    wifi_scan_time = 0

    # Bluetooth cached devices
    bt_devices = []
    bt_scan_time = 0

    # Brightness choices
    bks = list_backlights()
    selected_backlight = bks[0]["path"] if bks else None

    running = True
    while running:
        mouse = pygame.mouse.get_pos()
        click = None
        evs = pygame.event.get()
        for ev in evs:
            # pass events to topbar
            try:
                topbar.handle_event(ev)
            except Exception:
                pass
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                click = ev.pos
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                if ev.key == pygame.K_r:
                    show_dialog = True
                    dialog_type = "Reboot"

        screen.fill((12,14,20))
        topbar.update()

        # Draw left menu
        # Draw left menu (auto-fit vertically)
        menu_w = 140
        menu_x = 12
        menu_y = 56
        menu_h = SCREEN_H - menu_y - 40  # leave space at bottom

        # Dynamic height and spacing
        num_items = len(menu_items)
        total_spacing = 8 * (num_items - 1)
        btn_h = max(30, (menu_h - total_spacing) // num_items)

        for i, item in enumerate(menu_items):
            y = menu_y + i * (btn_h + 8)
            r = pygame.Rect(menu_x, y, menu_w, btn_h)
            hovered = r.collidepoint(mouse)
            is_sel = (item == selected)
            bg = (0, 110, 150) if hovered or is_sel else (0, 70, 100)
            draw_button(screen, r, item, font_m, hovered or is_sel, bg, (0, 170, 240))
            if click and r.collidepoint(click):
                if item == "Reboot":
                    show_dialog = True
                    dialog_type = "Reboot"
                else:
                    selected = item


        # Right panel
        panel_rect = pygame.Rect(menu_w + 24, 56, SCREEN_W - (menu_w + 36), SCREEN_H - 76)
        draw_rounded(screen, panel_rect, (26,30,36), radius=10)

        # Draw selected panel content
        if selected == "Wi-Fi Toggle":
            title = font_l.render("Wi-Fi", True, (180,255,255))
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + 8))
            y = panel_rect.y + 48
            if not USE_NMCLI:
                screen.blit(font_s.render("nmcli not available — install NetworkManager to control Wi-Fi.", True, (220,200,180)), (panel_rect.x + 12, y))
            else:
                enabled = wifi_is_enabled()
                status_txt = "ON" if enabled else "OFF"
                screen.blit(font_s.render(f"Wi-Fi: {status_txt}", True, (200,255,200)), (panel_rect.x + 12, y))
                y += 36
                btn_w = 120
                b_toggle = pygame.Rect(panel_rect.x + 12, y, btn_w, 34)
                b_scan = pygame.Rect(panel_rect.x + 12 + btn_w + 12, y, btn_w, 34)
                draw_button(screen, b_toggle, "Turn Off" if enabled else "Turn On", font_m, b_toggle.collidepoint(mouse), (40,40,48), (0,120,180))
                draw_button(screen, b_scan, "Go to Networks", font_m, b_scan.collidepoint(mouse), (40,40,48), (0,120,180))
                if click:
                    if b_toggle.collidepoint(click):
                        ok, msg = wifi_toggle(not enabled)
                        feedback = msg
                        fb_time = time.time()
                    elif b_scan.collidepoint(click):
                        selected = "Wi-Fi Networks"

        elif selected == "Wi-Fi Networks":
            title = font_l.render("Wi-Fi Networks", True, (180,255,255))
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + 8))

            # refresh networks at most every 6s
            if time.time() - wifi_scan_time > 6:
                wifi_scan_time = time.time()
                wifi_list = list_wifi_networks() if USE_NMCLI and wifi_is_enabled() else []
            y = panel_rect.y + 44
            if not USE_NMCLI:
                txt = font_s.render("nmcli not available — install NetworkManager to enable Wi-Fi control.", True, (220,200,180))
                screen.blit(txt, (panel_rect.x + 12, y))
                y += 28
            elif not wifi_is_enabled():
                screen.blit(font_s.render("Wi-Fi radio is OFF. Turn it on from 'Wi-Fi Toggle'.", True, (220,200,180)), (panel_rect.x + 12, y))
                y += 28
            elif not wifi_list:
                screen.blit(font_s.render("No networks found yet — scanning...", True, (200,200,200)), (panel_rect.x + 12, y))
                y += 28
            for net in wifi_list[:8]:
                r = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, 36)
                hovered = r.collidepoint(mouse)
                label = f"{net['ssid']}  ({net.get('signal','')})"
                draw_button(screen, r, label, font_s, hovered, (30,40,50), (0,120,180))
                if click and r.collidepoint(click):
                    # if secured ask for password
                    sec = (net.get("security") or "").upper()
                    if sec and sec != "--" and "WEP" in sec or "WPA" in sec or sec.strip():
                        pwd = text_input_modal(screen, f"Password for {net['ssid']} (blank to cancel):")
                        if pwd is None:
                            feedback = "Canceled"
                            fb_time = time.time()
                        else:
                            ok, msg = connect_wifi_nmcli(net["ssid"], pwd if pwd else None)
                            feedback = msg
                            fb_time = time.time()
                    else:
                        ok, msg = connect_wifi_nmcli(net["ssid"], None)
                        feedback = msg
                        fb_time = time.time()
                y += 44

        elif selected == "Bluetooth":
            title = font_l.render("Bluetooth", True, (180,255,255))
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + 8))
            y = panel_rect.y + 44
            if not USE_BLUETOOTHCTL:
                txt = font_s.render("bluetoothctl not available — install bluez to enable Bluetooth control.", True, (220,200,180))
                screen.blit(txt, (panel_rect.x + 12, y))
            else:
                if time.time() - bt_scan_time > 8:
                    bt_scan_time = time.time()
                    bt_devices = bluetooth_scan_once(timeout=5)
                if not bt_devices:
                    screen.blit(font_s.render("No devices found yet — scanning...", True, (200,200,200)), (panel_rect.x + 12, y))
                for mac, name in bt_devices[:8]:
                    r = pygame.Rect(panel_rect.x + 12, y, panel_rect.width - 24, 36)
                    draw_button(screen, r, f"{name} [{mac}]", font_s, r.collidepoint(mouse), (30,40,50), (0,120,180))
                    if click and r.collidepoint(click):
                        ok, msg = bluetooth_pair_and_connect(mac)
                        feedback = "Paired/Connected" if ok else f"Bluetooth error: {msg}"
                        fb_time = time.time()
                    y += 44

        elif selected == "Sound":
            title = font_l.render("Sound", True, (180,255,255))
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + 8))
            y = panel_rect.y + 48
            vol, muted = get_volume()
            if vol is None:
                screen.blit(font_s.render("Audio control not available (no amixer/pactl).", True, (220,200,180)), (panel_rect.x + 12, y))
            else:
                screen.blit(font_s.render(f"Volume: {vol}% {'(Muted)' if muted else ''}", True, (200,255,200)), (panel_rect.x + 12, y))
                y += 28
                btn_w = 84
                b_minus = pygame.Rect(panel_rect.x + 12, y, btn_w, 34)
                b_plus = pygame.Rect(panel_rect.x + 12 + btn_w + 12, y, btn_w, 34)
                b_mute = pygame.Rect(panel_rect.x + 12 + 2*(btn_w+12), y, btn_w, 34)
                draw_button(screen, b_minus, "-10%", font_m, b_minus.collidepoint(mouse), (40,40,48), (0,120,180))
                draw_button(screen, b_plus, "+10%", font_m, b_plus.collidepoint(mouse), (40,40,48), (0,120,180))
                draw_button(screen, b_mute, "Mute/Toggle", font_m, b_mute.collidepoint(mouse), (40,40,48), (0,120,180))
                if click:
                    if b_minus.collidepoint(click):
                        set_volume((vol or 50) - 10)
                    elif b_plus.collidepoint(click):
                        set_volume((vol or 50) + 10)
                    elif b_mute.collidepoint(click):
                        toggle_mute()
                    vol, muted = get_volume()
                    feedback = f"Volume {vol}%" if vol is not None else "Volume changed"
                    fb_time = time.time()

        elif selected == "Brightness":
            title = font_l.render("Brightness", True, (180,255,255))
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + 8))
            y = panel_rect.y + 44
            if not BACKLIGHT_PATHS:
                screen.blit(font_s.render("No backlight sysfs detected (/sys/class/backlight).", True, (220,200,180)), (panel_rect.x + 12, y))
            else:
                cur, mx = read_brightness(selected_backlight)
                if cur is None:
                    screen.blit(font_s.render("Cannot read backlight (permissions?). Try running as root.", True, (220,200,180)), (panel_rect.x + 12, y))
                else:
                    pct = int(round((cur / mx) * 100))
                    screen.blit(font_s.render(f"Current: {pct}% (raw {cur}/{mx})", True, (200,255,200)), (panel_rect.x + 12, y))
                    y += 28
                    b_w = 84
                    b_minus = pygame.Rect(panel_rect.x + 12, y, b_w, 34)
                    b_plus = pygame.Rect(panel_rect.x + 12 + b_w + 12, y, b_w, 34)
                    draw_button(screen, b_minus, "-10%", font_m, b_minus.collidepoint(mouse), (40,40,48), (0,120,180))
                    draw_button(screen, b_plus, "+10%", font_m, b_plus.collidepoint(mouse), (40,40,48), (0,120,180))
                    if click:
                        if b_minus.collidepoint(click):
                            set_brightness(selected_backlight, pct - 10)
                        elif b_plus.collidepoint(click):
                            set_brightness(selected_backlight, pct + 10)
                        time.sleep(0.06)
                        cur, mx = read_brightness(selected_backlight)
                        pct = int(round((cur / mx) * 100)) if cur is not None else pct
                        feedback = f"Brightness {pct}%"
                        fb_time = time.time()

        elif selected == "About":
            txts = [
                f"Platform: {platform.system()} {platform.release()}",
                f"Python: {platform.python_version()}",
                "Futuristic Pi Settings v1.0",
                "",
                "Factory Reset will delete login files and reboot."
            ]
            y = panel_rect.y + 20
            for t in txts:
                screen.blit(font_s.render(t, True, (200,220,255)), (panel_rect.x + 12, y))
                y += 20
            btn = pygame.Rect(panel_rect.x + 12, y + 8, panel_rect.width - 24, 42)
            draw_button(screen, btn, "⚠️ Factory Reset (delete login files & reboot)", font_s, btn.collidepoint(mouse), (180,60,60), (240,90,90))
            if click and btn.collidepoint(click):
                show_dialog = True
                dialog_type = "Reset Password"

        # Dialog modal area
        if show_dialog:
            dw, dh = 420, 160
            dr = pygame.Rect((SCREEN_W - dw)//2, (SCREEN_H - dh)//2, dw, dh)
            draw_rounded(screen, dr, (32,36,40), radius=10)
            pygame.draw.rect(screen, (80,80,80), dr, 1, border_radius=10)
            f = pygame.font.SysFont("Arial", 16)
            msg = f"Are you sure you want to {dialog_type.lower()}?"
            lines = wrap_text(msg, f, dw - 40)
            yy = dr.y + 18
            for ln in lines:
                screen.blit(f.render(ln, True, (230,230,230)), (dr.x + 20, yy))
                yy += 20
            yes = pygame.Rect(dr.x + 48, dr.bottom - 54, 120, 36)
            no = pygame.Rect(dr.right - 168, dr.bottom - 54, 120, 36)
            draw_button(screen, yes, "Yes", f, yes.collidepoint(mouse), (0,160,140), (0,200,180))
            draw_button(screen, no, "Cancel", f, no.collidepoint(mouse), (100,100,100), (160,160,160))
            if click:
                if yes.collidepoint(click):
                    if dialog_type == "Reset Password":
                        deleted = []
                        try:
                            for path in (USER_FILE, KEY_FILE):
                                if os.path.exists(path):
                                    os.remove(path)
                                    deleted.append(os.path.basename(path))
                        except Exception as e:
                            feedback = f"Reset failed: {e}"
                            fb_time = time.time()
                        else:
                            feedback = "Deleted: " + ", ".join(deleted) if deleted else "No files found"
                            fb_time = time.time()
                            time.sleep(0.5)
                            if os.path.exists(MAIN_FILE):
                                pygame.quit()
                                os.execv(sys.executable, [sys.executable, MAIN_FILE])
                        show_dialog = False
                    elif dialog_type == "Reboot":
                        feedback = "Rebooting..."
                        fb_time = time.time()
                        time.sleep(0.5)
                        if os.path.exists(MAIN_FILE):
                            pygame.quit()
                            os.execv(sys.executable, [sys.executable, MAIN_FILE])
                        show_dialog = False
                elif no.collidepoint(click):
                    show_dialog = False

        # Feedback bar
        if feedback and time.time() - fb_time < 4:
            bar = pygame.Rect(0, SCREEN_H - 28, SCREEN_W, 28)
            draw_rounded(screen, bar, (0,0,0))
            screen.blit(font_s.render(feedback, True, (120,255,180)), (12, SCREEN_H - 22))

        # Draw topbar (single call)
        try:
            topbar.draw(screen)
        except Exception:
            # fallback title
            screen.blit(font_l.render("Settings", True, (200,255,255)), (12,6))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Warning: running without root. Some actions may fail.")
    main()
