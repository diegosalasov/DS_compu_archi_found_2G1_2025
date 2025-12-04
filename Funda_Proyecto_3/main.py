import pygame
import sys
import time
from pipeline import Pipeline
from hazard_unit import HazardUnit
from render_pipeline import draw_pipeline
from render_hazard_unit import draw_hazard_info
from parser import parse_riscv_line
from text_editor import TextEditor
import tkinter as tk
from tkinter import messagebox

pygame.init()
pygame.key.set_repeat(300, 30)
tk_root = tk.Tk()
tk_root.withdraw()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Simulador Pipeline Dual RISC-V")
clock = pygame.time.Clock()

# Fuentes
font = pygame.font.SysFont("consolas", 18)
small_font = pygame.font.SysFont("consolas", 14)
tiny_font = pygame.font.SysFont("consolas", 12)   # para historial y registros

instructions = []

editor = TextEditor(50, 60, WIDTH // 2 - 60, 270, font)
proc1 = Pipeline([], HazardUnit(enable_forwarding=False))
proc2 = Pipeline([], HazardUnit(enable_forwarding=True))
mode = None
program_loaded = False
execution_active = False
execution_finished = False
execution_start_time = 0
execution_elapsed = 0
history = []
stall_count_1 = 0
stall_count_2 = 0
start_time = None
run_count = 0
running = True

config_mode_p1 = "hazard"
config_mode_p2 = "hazard_branch"

LATENCIES = {"IF": 0.1, "ID": 0.15, "EX": 0.2, "MEM": 0.25, "WB": 0.1}

CLOCK_FREQUENCY_HZ = 1_000_000_000  # 1 GHz
CYCLE_DURATION_NS = 1_000_000_000 / CLOCK_FREQUENCY_HZ  # 1 ns por ciclo


def calculate_simulated_time_ns(cycles):
    return cycles * CYCLE_DURATION_NS


def format_time_ns(nanoseconds):
    if nanoseconds < 1_000:
        return f"{nanoseconds:.0f} ns"
    elif nanoseconds < 1_000_000:
        return f"{nanoseconds / 1_000:.2f} μs"
    elif nanoseconds < 1_000_000_000:
        return f"{nanoseconds / 1_000_000:.2f} ms"
    else:
        return f"{nanoseconds / 1_000_000_000:.2f} s"


def get_mode_description(mode_key):
    return {
        "no_hazard": "Sin Unidad de Riesgos",
        "hazard": "Unidad de Riesgos",
        "branch": "Predicción de Saltos",
        "hazard_branch": "Riesgos + Predicción"
    }.get(mode_key, "Desconocido")


#  PANELES (dashboard))

def draw_panel(x, y, w, h, title=None):
    pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h), border_radius=10)
    pygame.draw.rect(screen, (100, 100, 100), (x, y, w, h), 2, border_radius=10)
    if title:
        txt = small_font.render(title, True, (255, 255, 0))
        screen.blit(txt, (x + 10, y + 5))


# Layout base
EDITOR_PANEL_X = 40
EDITOR_PANEL_Y = 20
EDITOR_PANEL_W = WIDTH // 2 - 40
EDITOR_PANEL_H = 320

INFO_PANEL_X = WIDTH // 2 + 20
INFO_PANEL_Y = 20
INFO_PANEL_W = WIDTH - INFO_PANEL_X - 20
INFO_PANEL_H = 90

CONTROLS_PANEL_X = 40
CONTROLS_PANEL_Y = EDITOR_PANEL_Y + EDITOR_PANEL_H + 10
CONTROLS_PANEL_W = 200
CONTROLS_PANEL_H = 260

CONFIG_PANEL_X = CONTROLS_PANEL_X + CONTROLS_PANEL_W + 20
CONFIG_PANEL_Y = CONTROLS_PANEL_Y 
CONFIG_PANEL_W = (WIDTH // 2 + 20) - CONFIG_PANEL_X - 20
CONFIG_PANEL_H = 260

# BAJO un poco el panel de métricas
METRICS_PANEL_X = 40
METRICS_PANEL_Y = CONTROLS_PANEL_Y + CONTROLS_PANEL_H + 10
METRICS_PANEL_W = WIDTH // 2 - 40
METRICS_PANEL_H = HEIGHT - METRICS_PANEL_Y - 40

PIPELINE_PANEL_Y = 130
PIPELINE_PANEL_H = 320   # panel pipelines
PIPELINE_PANEL_W = (WIDTH - (WIDTH // 2 + 20) - 40) // 2
PIPELINE_PANEL_X_P1 = WIDTH // 2 + 20
PIPELINE_PANEL_X_P2 = PIPELINE_PANEL_X_P1 + PIPELINE_PANEL_W + 20

MEM_PANEL_Y = PIPELINE_PANEL_Y + PIPELINE_PANEL_H + 20
MEM_PANEL_H = HEIGHT - MEM_PANEL_Y - 40
MEM_PANEL_W = PIPELINE_PANEL_W
MEM_PANEL_X_P1 = PIPELINE_PANEL_X_P1
MEM_PANEL_X_P2 = PIPELINE_PANEL_X_P2


#  Info en paneles 

def draw_info(panel_x, panel_y):
    y0 = panel_y + 25
    x0 = panel_x + 10

    info1 = font.render(f"Ciclo actual: {proc1.cycle}", True, (255, 255, 255))
    info2 = font.render(f"PC1: {proc1.pc} | PC2: {proc2.pc}", True, (255, 255, 255))
    screen.blit(info1, (x0, y0))
    screen.blit(info2, (x0, y0 + 22))

    if execution_active:
        elapsed = time.time() - execution_start_time
        time_txt = small_font.render(f"Tiempo transcurrido: {elapsed:.2f} s", True, (255, 255, 0))
        screen.blit(time_txt, (x0, y0 + 45))
    elif execution_finished:
        time_txt = small_font.render(f"Tiempo total: {execution_elapsed:.2f} s", True, (0, 255, 0))
        screen.blit(time_txt, (x0, y0 + 45))


def draw_metric_history(panel_x, panel_y):
    base_y = panel_y + 30
    base_x = panel_x + 10

    labels = ["Run", "Ciclos P1", "Stalls P1", "Ciclos P2", "Stalls P2"]
    for i, label in enumerate(labels):
        txt = tiny_font.render(label, True, (200, 200, 200))
        screen.blit(txt, (base_x + i * 80, base_y))

    for idx, item in enumerate(history[-20:]):
        run, c1, s1, c2, s2 = item
        values = [str(run), str(c1), str(s1), str(c2), str(s2)]
        for i, val in enumerate(values):
            txt = tiny_font.render(val, True, (180, 180, 180))
            screen.blit(txt, (base_x + i * 80, base_y + 18 + idx * 16))


def draw_memory_content(memory, x, y, last_write_addr=None):
    # 4 columnas
    header = tiny_font.render("Memoria (dirección : valor)", True, (255, 255, 255))
    screen.blit(header, (x, y))

    columnas = 4
    filas_por_col = (len(memory) + columnas - 1) // columnas
    col_width = 80
    row_step = 16

    for i in range(len(memory)):
        value = memory[i]
        col = i // filas_por_col
        row = i % filas_por_col

        val_color = (255, 80, 80) if last_write_addr == i else (255, 255, 0)

        addr_text = tiny_font.render(f"{i:04d}:", True, (180, 180, 180))
        val_text = tiny_font.render(str(value), True, val_color)

        dx = x + col * col_width
        dy = y + 20 + row * row_step

        screen.blit(addr_text, (dx, dy))
        screen.blit(val_text, (dx + 42, dy))


def draw_config_buttons(panel_x, panel_y, panel_w):
    titles = ["Procesador 1", "Procesador 2"]
    configs = [[("Sin Unidad de Riesgos", "no_hazard"),
                ("Con Unidad de Riesgos", "hazard"),
                ("Predicción de Saltos", "branch"),
                ("Riesgos + Predicción", "hazard_branch")]] * 2

    half_w = panel_w // 2
    base_xs = [panel_x + 10, panel_x + half_w + 10]
    selected_modes = [config_mode_p1, config_mode_p2]

    for p in range(2):
        label = small_font.render(titles[p], True, (255, 255, 255))
        screen.blit(label, (base_xs[p], panel_y + 30))
        for i, (text, mode) in enumerate(configs[p]):
            btn_y = panel_y + 55 + i * 45
            color = (100, 200, 100) if selected_modes[p] == mode else (60, 60, 60)
            pygame.draw.rect(screen, color, (base_xs[p], btn_y, half_w - 20, 35), border_radius=6)
            rendered_text = tiny_font.render(text, True, (255, 255, 255))
            screen.blit(rendered_text, (base_xs[p] + 5, btn_y + 9))


def draw_buttons(panel_x, panel_y):
    btn_width = 160
    btn_height = 40
    start_y = panel_y + 35
    start_x = panel_x + 10

    button_labels = [
        ("Run", "load"),
        ("Paso a Paso", "step"),
        ("Auto", "auto"),
        ("Completa", "fast"),
    ]

    buttons_local = []
    for i, (text, mode_label) in enumerate(button_labels):
        y = start_y + i * 50
        color = (100, 100, 200) if program_loaded else (80, 80, 80)
        pygame.draw.rect(screen, color, (start_x+10, y, btn_width, btn_height), border_radius=6)
        label_color = (255, 255, 255) if program_loaded else (120, 120, 120)
        rendered_text = small_font.render(text, True, label_color)
        text_rect = rendered_text.get_rect(center=(start_x + btn_width // 2, y + btn_height // 2))
        screen.blit(rendered_text, text_rect)
        buttons_local.append({"label": text, "x": start_x, "y": y, "mode": mode_label})

    quit_button = {"label": "Salir", "x": WIDTH - 75, "y": 5, "mode": "quit"}
    pygame.draw.rect(screen, (200, 50, 50), (quit_button["x"], quit_button["y"], 70, 40), border_radius=6)
    label = font.render(quit_button["label"], True, (255, 255, 255))
    screen.blit(label, (quit_button["x"] + 10, quit_button["y"] + 10))

    buttons_local.append(quit_button)
    return buttons_local


def check_button_click(pos, buttons_list):
    for b in buttons_list:
        w = 180 if b["mode"] != "quit" else 100
        h = 40
        rect = pygame.Rect(b["x"], b["y"], w, h)
        if rect.collidepoint(pos):
            return b["mode"]

    half_w = CONFIG_PANEL_W // 2
    base_xs = [CONFIG_PANEL_X + 10, CONFIG_PANEL_X + half_w + 10]
    for proc_id, base_x in enumerate(base_xs):
        for i, (_, mode_key) in enumerate([
            ("no hazard", "no_hazard"), ("hazard", "hazard"),
            ("branch", "branch"), ("hazard + branch", "hazard_branch")
        ]):
            rect = pygame.Rect(base_x, CONFIG_PANEL_Y + 55 + i * 45, half_w - 20, 35)
            if rect.collidepoint(pos):
                return f"config:{proc_id}:{mode_key}"
    return None


def draw_processor_status(proc, x, y, processor_id):
    # Estado del procesador (dentro del panel de MEMORIA)
    font_status = tiny_font

    title = font_status.render(f"Estado P{processor_id}", True, (255, 255, 0))
    screen.blit(title, (x, y))

    y += 16
    cycle_text = font_status.render(f"Ciclo: {proc.cycle}", True, (255, 255, 255))
    screen.blit(cycle_text, (x, y))

    y += 16
    sim_time = calculate_simulated_time_ns(proc.cycle)
    time_text = font_status.render(f"Tiempo sim.: {format_time_ns(sim_time)}", True, (255, 255, 255))
    screen.blit(time_text, (x, y))

    y += 16
    pc_text = font_status.render(f"PC: {proc.pc}", True, (255, 255, 255))
    screen.blit(pc_text, (x, y))


def draw_registers(proc, x, y, processor_id):
    """
    Ahora se dibujan dentro del panel de métricas:
    - fuente pequeña 
    - posición ajustada para no salir del contenedor
    """
    font_status = tiny_font
    title = font_status.render(f"Registros P{processor_id}:", True, (200, 200, 200))
    screen.blit(title, (x, y))
    line_height = 14
    for i in range(0, 32, 4):
        row_text = "  ".join([f"x{j:02d}: {proc.registers[j]}" for j in range(i, i + 4)])
        y += line_height
        reg_line = font_status.render(row_text, True, (180, 255, 180))
        screen.blit(reg_line, (x, y))


#  BUCLE PRINCIPAL 

while running:
    screen.fill((50, 100, 200))

    # Paneles
    draw_panel(EDITOR_PANEL_X, EDITOR_PANEL_Y, EDITOR_PANEL_W, EDITOR_PANEL_H, "Editor de instrucciones")
    draw_panel(INFO_PANEL_X, INFO_PANEL_Y, INFO_PANEL_W, INFO_PANEL_H, "Información general")
    draw_panel(CONTROLS_PANEL_X, CONTROLS_PANEL_Y, CONTROLS_PANEL_W, CONTROLS_PANEL_H, "Funcionalidades")
    draw_panel(CONFIG_PANEL_X, CONFIG_PANEL_Y, CONFIG_PANEL_W, CONFIG_PANEL_H, "Configuración de procesadores")
    draw_panel(METRICS_PANEL_X, METRICS_PANEL_Y, METRICS_PANEL_W, METRICS_PANEL_H, "Historial de métricas")
    draw_panel(PIPELINE_PANEL_X_P1, PIPELINE_PANEL_Y, PIPELINE_PANEL_W, PIPELINE_PANEL_H, "Pipeline P1")
    draw_panel(PIPELINE_PANEL_X_P2, PIPELINE_PANEL_Y, PIPELINE_PANEL_W, PIPELINE_PANEL_H, "Pipeline P2")
    draw_panel(MEM_PANEL_X_P1, MEM_PANEL_Y, MEM_PANEL_W, MEM_PANEL_H, "Memoria P1")
    draw_panel(MEM_PANEL_X_P2, MEM_PANEL_Y, MEM_PANEL_W, MEM_PANEL_H, "Memoria P2")

    # Editor
    editor.draw(screen)

    # Controles & paneles de info
    buttons = draw_buttons(CONTROLS_PANEL_X, CONTROLS_PANEL_Y)
    draw_config_buttons(CONFIG_PANEL_X, CONFIG_PANEL_Y, CONFIG_PANEL_W)
    draw_info(INFO_PANEL_X, INFO_PANEL_Y)

    # Historial
    draw_metric_history(METRICS_PANEL_X, METRICS_PANEL_Y)

    # REGISTROS DENTRO DEL PANEL DE MÉTRICAS
    # x a la derecha pero dentro del borde; y un poco más arriba para no salirse
    regs_x = METRICS_PANEL_X + 460
    regs_y_p1 = METRICS_PANEL_Y + 20
    # 8 líneas de registros + título ≈ 9*14px -> calculo altura para la segunda tabla
    regs_y_p2 = regs_y_p1 + 9 * 14 + 20

    draw_registers(proc1, regs_x, regs_y_p1, processor_id=1)
    draw_registers(proc2, regs_x, regs_y_p2, processor_id=2)

    # Eventos
    for event in pygame.event.get():
        editor.handle_event(event)
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            clicked_mode = check_button_click(event.pos, buttons)
            if clicked_mode == "quit":
                running = False
            elif clicked_mode and clicked_mode.startswith("config") and not program_loaded:
                _, proc_id, mode_val = clicked_mode.split(":")
                if proc_id == "0":
                    config_mode_p1 = mode_val
                elif proc_id == "1":
                    config_mode_p2 = mode_val
            elif clicked_mode == "load":
                try:
                    input_text = editor.get_text()
                    lines = input_text.strip().split("\n")
                    new_instructions = [parse_riscv_line(line) for line in lines if parse_riscv_line(line)]
                    if not new_instructions:
                        raise ValueError("No se detectaron instrucciones válidas.")

                    def create_unit(mode):
                        return HazardUnit(
                            mode in ("hazard", "hazard_branch"),
                            mode in ("branch", "hazard_branch")
                        )

                    instructions = new_instructions
                    proc1 = Pipeline(instructions.copy(), create_unit(config_mode_p1))
                    proc2 = Pipeline(instructions.copy(), create_unit(config_mode_p2))

                    stall_count_1 = stall_count_2 = 0
                    program_loaded = True
                    execution_finished = False
                    execution_elapsed = 0
                except Exception as e:
                    messagebox.showerror("Error de sintaxis", str(e))
            elif clicked_mode in ("step", "auto", "fast") and program_loaded:
                mode = clicked_mode
                execution_active = True
                execution_start_time = time.time()

    # Modos de ejecución
    if mode in ("auto", "fast") and not (proc1.finished and proc2.finished):
        if mode == "auto":
            pygame.time.delay(400)
        h1, h2 = proc1.step(), proc2.step()
        if h1 and h1.get("stall"):
            stall_count_1 += 1
        if h2 and h2.get("stall"):
            stall_count_2 += 1
    elif mode == "step":
        h1, h2 = proc1.step(), proc2.step()
        if h1 and h1.get("stall"):
            stall_count_1 += 1
        if h2 and h2.get("stall"):
            stall_count_2 += 1
        if proc1.finished and proc2.finished:
            run_count += 1
            history.append((run_count, proc1.cycle, stall_count_1, proc2.cycle, stall_count_2))
            history = history[-10:]
            program_loaded = False
            execution_active = False
            execution_elapsed = time.time() - execution_start_time
        mode = None

    if proc1.finished and proc2.finished and mode is not None:
        run_count += 1
        history.append((run_count, proc1.cycle, stall_count_1, proc2.cycle, stall_count_2))
        history = history[-20:]
        mode = None
        program_loaded = False
        execution_active = False
        execution_elapsed = time.time() - execution_start_time

    #  Pipelines (solo las etapas) 
    pipeline_y = PIPELINE_PANEL_Y + 25
    draw_pipeline(screen, proc1.pipeline, PIPELINE_PANEL_X_P1 + 10, pipeline_y, processor_id=1)
    draw_pipeline(screen, proc2.pipeline, PIPELINE_PANEL_X_P2 + 10, pipeline_y, processor_id=2)

    #  Hazard + ESTADO DENTRO DE MEMORIA P1 / P2 
    hazard_y_p1 = MEM_PANEL_Y + 30
    status_y_p1 = hazard_y_p1 + 80
    mem_y_p1 = status_y_p1 + 60

    hazard_y_p2 = MEM_PANEL_Y + 30
    status_y_p2 = hazard_y_p2 + 80
    mem_y_p2 = status_y_p2 + 60

    # P1
    draw_hazard_info(
        screen,
        proc1.hazard_unit.detect_hazard(proc1.pipeline, proc1.pipeline["ID"]),
        MEM_PANEL_X_P1 + 10,
        hazard_y_p1,
        processor_id=1,
        mode_desc=get_mode_description(config_mode_p1)
    )
    draw_processor_status(proc1, MEM_PANEL_X_P1 + 10, status_y_p1, processor_id=1)
    draw_memory_content(proc1.memory, MEM_PANEL_X_P1 + 10, mem_y_p1, proc1.last_mem_write)

    # P2
    draw_hazard_info(
        screen,
        proc2.hazard_unit.detect_hazard(proc2.pipeline, proc2.pipeline["ID"]),
        MEM_PANEL_X_P2 + 10,
        hazard_y_p2,
        processor_id=2,
        mode_desc=get_mode_description(config_mode_p2)
    )
    draw_processor_status(proc2, MEM_PANEL_X_P2 + 10, status_y_p2, processor_id=2)
    draw_memory_content(proc2.memory, MEM_PANEL_X_P2 + 10, mem_y_p2, proc2.last_mem_write)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
