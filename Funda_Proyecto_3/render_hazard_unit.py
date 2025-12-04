import pygame

def draw_hazard_info(screen, hazard_info, pos_x, pos_y, processor_id=1, mode_desc=""):
    font = pygame.font.SysFont("consolas", 16)

    # Encabezado del procesador y configuración seleccionada
    title = font.render(f"Procesador {processor_id}: {mode_desc}", True, (255, 255, 0))
    screen.blit(title, (pos_x, pos_y))

    # Mensaje de error si no hay datos disponibles
    if hazard_info is None:
        msg = font.render("Sin datos", True, (200, 200, 200))
        screen.blit(msg, (pos_x, pos_y + 20))
        return

    # STALL: mostrar si se detectó y en qué color
    stall_text = "STALL detectado" if hazard_info.get("stall") else "Sin STALL"
    stall_color = (255, 0, 0) if hazard_info.get("stall") else (0, 200, 0)
    stall = font.render(stall_text, True, stall_color)
    screen.blit(stall, (pos_x, pos_y + 20))

    # Forward A
    fA = hazard_info.get("forwardA", "NO")
    fA_color = (0, 255, 0) if fA != "NO" else (180, 180, 180)
    fA_text = font.render(f"Forward A: {fA}", True, fA_color)
    screen.blit(fA_text, (pos_x, pos_y + 40))

    # Forward B
    fB = hazard_info.get("forwardB", "NO")
    fB_color = (0, 255, 0) if fB != "NO" else (180, 180, 180)
    fB_text = font.render(f"Forward B: {fB}", True, fB_color)
    screen.blit(fB_text, (pos_x, pos_y + 60))
