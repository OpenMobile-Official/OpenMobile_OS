import os
import sys
import subprocess
import pygame
import time
import shutil
import zipfile

RESOLUTION = (480, 320)

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    return lines

def show_progress(screen, font, resolution, message):
    """Show a simple progress bar animation while repairing."""
    bar_rect = pygame.Rect(40, resolution[1]//2, resolution[0]-80, 30)
    for i in range(0, 101, 5):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((0, 100, 0))  # green background
        msg_surf = font.render(message, True, (255, 255, 255))
        msg_rect = msg_surf.get_rect(center=(resolution[0]//2, resolution[1]//2 - 50))
        screen.blit(msg_surf, msg_rect)

        # Draw progress bar outline
        pygame.draw.rect(screen, (255, 255, 255), bar_rect, 2)
        # Fill progress bar
        fill_width = int((i/100) * (bar_rect.width-4))
        pygame.draw.rect(screen, (0, 200, 0), (bar_rect.x+2, bar_rect.y+2, fill_width, bar_rect.height-4))

        percent_surf = font.render(f"{i}%", True, (255, 255, 255))
        percent_rect = percent_surf.get_rect(center=(resolution[0]//2, resolution[1]//2 + 50))
        screen.blit(percent_surf, percent_rect)

        pygame.display.flip()
        time.sleep(0.05)

def show_repair_menu(error_type, details, uimobile_dir, zip_path, resolution=RESOLUTION):
    """Touch-friendly repair menu with Repair and Restart buttons."""
    pygame.init()
    screen = pygame.display.set_mode(resolution)
    pygame.display.set_caption("Repair Menu")
    font_title = pygame.font.SysFont('Arial', 26, bold=True)
    font_msg = pygame.font.SysFont('Arial', 18)

    repair_button = pygame.Rect(resolution[0]//2 - 100, resolution[1]-100, 80, 40)
    restart_button = pygame.Rect(resolution[0]//2 + 20, resolution[1]-100, 100, 40)

    running = True
    repaired = False
    restart = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if repair_button.collidepoint(event.pos):
                    try:
                        # Show progress bar while repairing
                        show_progress(screen, font_msg, resolution, "Repairing uimobile...")
                        if os.path.exists(uimobile_dir):
                            shutil.rmtree(uimobile_dir)
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(os.path.dirname(uimobile_dir))
                        repaired = True
                        running = False
                    except Exception as e:
                        details = f"Repair failed: {e}"
                elif restart_button.collidepoint(event.pos):
                    restart = True
                    running = False

        screen.fill((150, 0, 0))  # dark red background

        title_surf = font_title.render("⚠️ REPAIR MENU ⚠️", True, (255, 255, 0))
        title_rect = title_surf.get_rect(center=(resolution[0]//2, 40))
        screen.blit(title_surf, title_rect)

        message = f"Type: {error_type}\nDetails: {details}"
        lines = []
        for part in message.split("\n"):
            lines.extend(wrap_text(part, font_msg, resolution[0]-40))

        y = 100
        for line in lines:
            msg_surf = font_msg.render(line, True, (255, 255, 255))
            msg_rect = msg_surf.get_rect(center=(resolution[0]//2, y))
            screen.blit(msg_surf, msg_rect)
            y += 25

        pygame.draw.rect(screen, (0, 200, 0), repair_button, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 200), restart_button, border_radius=6)

        repair_text = font_msg.render("Repair", True, (255, 255, 255))
        restart_text = font_msg.render("Restart", True, (255, 255, 255))

        screen.blit(repair_text, repair_text.get_rect(center=repair_button.center))
        screen.blit(restart_text, restart_text.get_rect(center=restart_button.center))

        pygame.display.flip()
        time.sleep(0.1)

    pygame.quit()
    return repaired, restart

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uimobile_dir = os.path.join(script_dir, "uimobile")
    target_script = os.path.join(uimobile_dir, "main.py")
    zip_path = os.path.join(script_dir, "backup.zip")

    if not os.path.exists(target_script):
        repaired, restart = show_repair_menu(
            error_type="File Not Found",
            details=f"{target_script} missing.",
            uimobile_dir=uimobile_dir,
            zip_path=zip_path
        )
        if repaired:
            print("✅ Repair complete. Relaunching launcher...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif restart:
            print("🔄 Restarting launcher...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            sys.exit(1)
    else:
        try:
            print(f"▶️ Launching {target_script}...")
            subprocess.Popen([sys.executable, target_script], cwd=uimobile_dir)
        except Exception as e:
            repaired, restart = show_repair_menu(
                error_type="Launch Failure",
                details=str(e),
                uimobile_dir=uimobile_dir,
                zip_path=zip_path
            )
            if repaired or restart:
                print("🔄 Relaunching launcher...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                sys.exit(1)

if __name__ == "__main__":
    main()
