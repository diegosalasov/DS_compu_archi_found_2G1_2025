import re

"""
Parsea una línea de código ensamblador RISC-V y la convierte
en un diccionario estructurado con los campos relevantes.

Soporta las siguientes instrucciones:
    - R-type : ADD, SUB, AND, OR, MUL, SLT
    - I-type : ADDI
    - Load   : LW  (ej. LW x1, 0(x2))
    - Store  : SW  (ej. SW x1, 0(x2))
    - Branch : BEQ, BNE (ej. BEQ x1, x2, -4)
"""


def parse_riscv_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None  # Ignorar líneas vacías o comentarios.

    # Quitar comas y separar por espacios.
    tokens = line.replace(",", "").split()
    op = tokens[0].upper()

    # Instrucciones tipo R (formato: op rd, rs1, rs2).
    if op in ["ADD", "SUB", "AND", "OR", "MUL", "SLT"]:
        return {"op": op, "rd": tokens[1], "rs1": tokens[2], "rs2": tokens[3]}

    # Instrucciones tipo I (formato: op rd, rs1, imm).
    elif op in ["ADDI"]:
        return {"op": op, "rd": tokens[1], "rs1": tokens[2], "imm": int(tokens[3])}

    # Instrucción de carga tipo LW (formato: LW rd, offset(rs1)).
    elif op == "LW":
        rd = tokens[1]
        match = re.match(r"(-?\d+)\((x\d+)\)", tokens[2])
        if match:
            imm, rs1 = int(match.group(1)), match.group(2)
            return {"op": op, "rd": rd, "rs1": rs1, "imm": imm}

    # Instrucción de almacenamiento tipo SW (formato: SW rs2, offset(rs1)).
    elif op == "SW":
        rs2 = tokens[1]
        match = re.match(r"(-?\d+)\((x\d+)\)", tokens[2])
        if match:
            imm, rs1 = int(match.group(1)), match.group(2)
            return {"op": op, "rs1": rs1, "rs2": rs2, "imm": imm}

    # Instrucciones de salto condicional tipo BEQ/BNE (formato: BEQ rs1, rs2, imm).
    elif op in ["BEQ", "BNE"]:
        return {"op": op, "rs1": tokens[1], "rs2": tokens[2], "imm": int(tokens[3])}

    return None  # Si no se reconoce el formato, devolver None.


def load_assembly_file(path):
    """
    Carga un archivo de texto que contiene instrucciones RISC-V y
    las convierte en una lista de diccionarios estructurados.
    """
    with open(path, "r") as f:
        lines = f.readlines()

    instructions = []
    for line in lines:
        instr = parse_riscv_line(line)
        if instr:
            instructions.append(instr)

    return instructions
