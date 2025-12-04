import pygame

# Etapas del pipeline segmentado RISC-V
STAGES = ["IF", "ID", "EX", "MEM", "WB"]

# Colores utilizados en la interfaz gráfica
COLOR_BG = (20, 20, 20)
COLOR_TEXT = (255, 255, 255)
COLOR_STAGE = (100, 100, 255)
COLOR_BOX = (80, 80, 80)

"""
Dibuja visualmente el estado actual del pipeline para un procesador RISC-V.

Esta función recorre las cinco etapas del pipeline segmentado ('IF', 'ID', 'EX', 'MEM', 'WB')
y muestra en pantalla qué instrucción se encuentra en cada etapa, con un formato legible,
resaltando la operación y sus operandos.
"""

def draw_pipeline(screen, pipeline_dict, pos_x, pos_y, processor_id=1):
    font = pygame.font.SysFont("consolas", 16)

    # Título del pipeline.
    title = font.render(f"Procesador {processor_id}: Pipeline", True, COLOR_STAGE)
    screen.blit(title, (pos_x, pos_y))

    # Recorrer cada etapa del pipeline y dibujar su contenido.
    for idx, stage in enumerate(STAGES):
        y = pos_y + 30 + idx * 40

        # Nombre de la etapa (ej. "IF", "ID", ...).
        label = font.render(stage, True, COLOR_TEXT)

        # Caja más angosta para que no ocupe todo el panel.
        # Antes: ancho 300; ahora 240.
        box_x = pos_x + 60
        box_y = y - 5
        box_w = 240
        box_h = 30
        pygame.draw.rect(screen, COLOR_BOX, (box_x, box_y, box_w, box_h))

        screen.blit(label, (pos_x + 10, y))

        # Obtener la instrucción correspondiente a la etapa.
        instr = pipeline_dict.get(stage)

        if instr:
            op = instr.get("op", "")
            if op in ["ADD", "SUB", "AND", "OR", "MUL", "SLT"]:
                text = f"{op} {instr['rd']}, {instr['rs1']}, {instr['rs2']}"
            elif op == "ADDI":
                text = f"{op} {instr['rd']}, {instr['rs1']}, {instr['imm']}"
            elif op == "LW":
                text = f"{op} {instr['rd']}, {instr['imm']}({instr['rs1']})"
            elif op == "SW":
                text = f"{op} {instr['rs2']}, {instr['imm']}({instr['rs1']})"
            elif op == "BEQ":
                text = f"{op} {instr['rs1']}, {instr['rs2']}, {instr['imm']}"
            else:
                text = op
        else:
            text = "--"

        instr_text = font.render(text, True, COLOR_TEXT)
        # Un poco de margen a la izquierda dentro de la caja angosta
        screen.blit(instr_text, (box_x + 8, y))
