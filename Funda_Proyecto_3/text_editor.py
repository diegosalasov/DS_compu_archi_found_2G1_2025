import pygame
import pyperclip  # Para usar el portapapeles del sistema

"""
Editor de texto básico en Pygame.

Soporta:
    - Escritura normal
    - Enter, Backspace, Tab
    - Ctrl + C: copiar todo el texto
    - Ctrl + V: pegar desde portapapeles
    - Ctrl + X: cortar todo el texto
    - Ctrl + A: seleccionar todo (para borrar / reemplazar)
"""


class TextEditor:
    def __init__(self, x, y, w, h, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = ""
        self.cursor_visible = True
        self.cursor_counter = 0
        self.active = True
        self.placeholder = "Escriba instrucciones aquí"
        self.selection_all = False  # True cuando se hace Ctrl+A

    def handle_event(self, event):
        if not self.active:
            return

        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            # SELECCIONAR TODO: Ctrl + A
            if mods & pygame.KMOD_CTRL and event.key == pygame.K_a:
                if self.text:
                    self.selection_all = True
                return

            # Copiar: Ctrl + C (copia todo el texto actual)
            if mods & pygame.KMOD_CTRL and event.key == pygame.K_c:
                if self.text:
                    pyperclip.copy(self.text)
                return

            # Pegar: Ctrl + V
            if mods & pygame.KMOD_CTRL and event.key == pygame.K_v:
                paste_text = pyperclip.paste()
                if paste_text:
                    if self.selection_all:
                        self.text = paste_text
                        self.selection_all = False
                    else:
                        self.text += paste_text
                return

            # Cortar: Ctrl + X (corta todo el texto)
            if mods & pygame.KMOD_CTRL and event.key == pygame.K_x:
                if self.text:
                    pyperclip.copy(self.text)
                    self.text = ""
                    self.selection_all = False
                return

            # Teclas normales
            if event.key == pygame.K_BACKSPACE:
                if self.selection_all:
                    # Borrar todo si estaba "seleccionado"
                    self.text = ""
                    self.selection_all = False
                else:
                    self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                # Si hay selección, reemplazar todo por salto de línea
                if self.selection_all:
                    self.text = "\n"
                    self.selection_all = False
                else:
                    self.text += "\n"
            elif event.key == pygame.K_TAB:
                if self.selection_all:
                    self.text = "    "
                    self.selection_all = False
                else:
                    self.text += "    "
            elif event.key == pygame.K_ESCAPE:
                # Ignorar ESC
                pass
            else:
                # Caracter normal
                if event.unicode:
                    if self.selection_all:
                        # Reemplaza todo el contenido
                        self.text = event.unicode
                        self.selection_all = False
                    else:
                        self.text += event.unicode

    def draw(self, screen):
        # Fondo
        pygame.draw.rect(screen, (50, 50, 50), self.rect)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2)

        # Texto o placeholder
        display_text = self.text if self.text.strip() else self.placeholder
        color = (255, 255, 255) if self.text.strip() else (150, 150, 150)

        lines = display_text.split("\n")
        for i, line in enumerate(lines):
            txt_surface = self.font.render(line, True, color)
            screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 5 + i * 20))

        # Cursor intermitente SIEMPRE (aunque esté vacío)
        if self.active and self.cursor_visible:
            # Usar el contenido real, no el placeholder, para la posición
            real_lines = self.text.split("\n") if self.text else [""]
            last_line = real_lines[-1]
            cursor_x = self.rect.x + 5 + self.font.size(last_line)[0]
            cursor_y = self.rect.y + 5 + (len(real_lines) - 1) * 20
            pygame.draw.line(screen, (255, 255, 255),
                             (cursor_x, cursor_y),
                             (cursor_x, cursor_y + 18), 2)

        # Parpadeo del cursor
        self.cursor_counter += 1
        if self.cursor_counter >= 30:
            self.cursor_visible = not self.cursor_visible
            self.cursor_counter = 0

    def get_text(self):
        return self.text.strip()

    def clear(self):
        self.text = ""
        self.selection_all = False
