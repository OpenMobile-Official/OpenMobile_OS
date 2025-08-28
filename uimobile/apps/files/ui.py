import pygame


class IconButton:
    def __init__(self, label, rect, callback):
        self.label = label
        self.rect = rect
        self.callback = callback
        self.font = pygame.font.SysFont(None, 16)
        self.color = (70, 130, 180)
        self.hovered = False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=6)
        text = self.font.render(self.label[:10], True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


def paginate_icons(icons, icons_per_page, columns, padding, icon_width, icon_height):
    pages = []
    page = []
    for idx, icon in enumerate(icons):
        row = (idx % icons_per_page) // columns
        col = (idx % icons_per_page) % columns

        icon.rect.x = padding + col * (icon_width + padding)
        icon.rect.y = 40 + padding + row * (icon_height + padding)

        page.append(icon)
        if len(page) == icons_per_page:
            pages.append(page)
            page = []

    if page:
        pages.append(page)

    return pages
