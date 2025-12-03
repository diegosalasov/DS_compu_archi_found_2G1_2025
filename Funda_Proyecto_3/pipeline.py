from hazard_unit import HazardUnit

"""
Clase que representa un procesador segmentado (pipeline) de 5 etapas:
IF, ID, EX, MEM y WB.
"""


class Pipeline:
    """
    Procesador segmentado básico con manejo de riesgos de datos y saltos condicionales.
    """

    def __init__(self, instruction_memory, hazard_unit=None):
        """
        Args:
            instruction_memory (list[dict]): Lista de instrucciones a ejecutar.
            hazard_unit (HazardUnit, optional): Unidad de riesgos.
        """
        self.instruction_memory = instruction_memory or []
        self.hazard_unit = hazard_unit or HazardUnit(enable_forwarding=True)

        self.pipeline = {
            "IF": None,
            "ID": None,
            "EX": None,
            "MEM": None,
            "WB": None,
        }

        self.pc = 0        # Contador de programa (índice en instruction_memory)
        self.cycle = 0     # Ciclo actual
        self.stalled = False     # Stall que se aplicará en el PRÓXIMO ciclo
        self.finished = False

        self.memory = [0] * 64
        self.registers = [0] * 32
        self.last_mem_write = None

    # ----------------------------------------------------------------------
    # Utilidades internas
    # ----------------------------------------------------------------------

    def _reg_index(self, name: str) -> int:
        """
        Convierte 'x5' en 5. Asume nombres bien formados.
        """
        return int(name[1:])

    # ----------------------------------------------------------------------
    # Ejecución de un ciclo
    # ----------------------------------------------------------------------

    def step(self):
        """
        Ejecuta un ciclo de reloj del pipeline.

        Retorna:
            dict o None: Información de hazard para este ciclo (stall, forwarding).
        """
        if self.finished:
            return None

        self.cycle += 1

        # Stall del ciclo anterior: afecta cómo avanza el pipeline ahora
        stall_prev = self.stalled

        # ------------------------------------------------------------------
        # Etapa WB: escribir resultados en registros
        # ------------------------------------------------------------------
        if self.pipeline["WB"]:
            instr = self.pipeline["WB"]
            op = instr.get("op")

            if op in ["ADD", "SUB", "AND", "OR", "MUL", "SLT"]:
                rd = self._reg_index(instr["rd"])
                rs1 = self.registers[self._reg_index(instr["rs1"])]
                rs2 = self.registers[self._reg_index(instr["rs2"])]
                if rd != 0:
                    if op == "ADD":
                        self.registers[rd] = rs1 + rs2
                    elif op == "SUB":
                        self.registers[rd] = rs1 - rs2
                    elif op == "AND":
                        self.registers[rd] = rs1 & rs2
                    elif op == "OR":
                        self.registers[rd] = rs1 | rs2
                    elif op == "MUL":
                        self.registers[rd] = rs1 * rs2
                    elif op == "SLT":
                        self.registers[rd] = int(rs1 < rs2)

            elif op == "ADDI":
                rd = self._reg_index(instr["rd"])
                rs1 = self.registers[self._reg_index(instr["rs1"])]
                imm = instr["imm"]
                if rd != 0:
                    self.registers[rd] = rs1 + imm

            elif op == "LW":
                rd = self._reg_index(instr["rd"])
                if rd != 0:
                    self.registers[rd] = instr.get("loaded_value", 0)

            # Mantener x0 = 0
            self.registers[0] = 0

        # ------------------------------------------------------------------
        # Etapa MEM: accesos a memoria
        # ------------------------------------------------------------------
        if self.pipeline["MEM"]:
            instr = self.pipeline["MEM"]
            op = instr.get("op")

            if op == "SW":
                base = self.registers[self._reg_index(instr["rs1"])]
                offset = instr["imm"]
                addr = base + offset
                value = self.registers[self._reg_index(instr["rs2"])]
                if 0 <= addr < len(self.memory):
                    self.memory[addr] = value
                    self.last_mem_write = addr

            elif op == "LW":
                base = self.registers[self._reg_index(instr["rs1"])]
                offset = instr["imm"]
                addr = base + offset
                if 0 <= addr < len(self.memory):
                    instr["loaded_value"] = self.memory[addr]

        # ------------------------------------------------------------------
        # Etapa EX: resolución de saltos (BEQ/BNE) + cálculo de penalización
        # ------------------------------------------------------------------
        ex_instr = self.pipeline["EX"]
        branch_penalty = False  # penalización de 1 ciclo si NO hay predicción

        if ex_instr:
            op = ex_instr.get("op")
            if op in ["BEQ", "BNE"]:
                rs1_val = self.registers[self._reg_index(ex_instr["rs1"])]
                rs2_val = self.registers[self._reg_index(ex_instr["rs2"])]
                taken = False

                if op == "BEQ":
                    taken = (rs1_val == rs2_val)
                elif op == "BNE":
                    taken = (rs1_val != rs2_val)

                if taken:
                    base_pc = ex_instr.get("pc")
                    imm = ex_instr.get("imm", 0)
                    if base_pc is not None:
                        target_pc = base_pc + imm
                        if 0 <= target_pc < len(self.instruction_memory):
                            self.pc = target_pc
                        else:
                            # Si la dirección cae fuera, terminamos el programa.
                            self.pc = len(self.instruction_memory)

                    # Flush sencillo: limpiar IF e ID para simular penalización de salto tomado.
                    self.pipeline["IF"] = None
                    self.pipeline["ID"] = None

                # Si NO hay predicción de saltos, cada branch (tomado o no) paga 1 ciclo extra
                if not self.hazard_unit.enable_branch_prediction:
                    branch_penalty = True

        # ------------------------------------------------------------------
        # Avance del pipeline (usando stall_prev)
        # ------------------------------------------------------------------
        self.pipeline["WB"] = self.pipeline["MEM"]
        self.pipeline["MEM"] = self.pipeline["EX"]

        if not stall_prev:
            # Avanza normalmente
            self.pipeline["EX"] = self.pipeline["ID"]
            self.pipeline["ID"] = self.pipeline["IF"]
        else:
            # Insertar burbuja en EX y mantener ID/IF (la instrucción en ID se reevalúa)
            self.pipeline["EX"] = None
            # NO fijamos aquí self.stalled; se recalcula al final del ciclo

        # ------------------------------------------------------------------
        # Etapa IF: traer nueva instrucción solo si NO hubo stall previo
        # ------------------------------------------------------------------
        if not stall_prev:
            if self.pc < len(self.instruction_memory):
                # Copia superficial para poder adjuntar metadatos como 'pc'
                instr = dict(self.instruction_memory[self.pc])
                instr["pc"] = self.pc
                self.pipeline["IF"] = instr
                self.pc += 1
            else:
                self.pipeline["IF"] = None

        # ------------------------------------------------------------------
        # ¿Terminó el programa?
        # ------------------------------------------------------------------
        if all(stage is None for stage in self.pipeline.values()):
            self.finished = True
            return None

        # ------------------------------------------------------------------
        # Detección de hazards de datos (load-use, RAW) en la instrucción en ID.
        # ------------------------------------------------------------------
        hazard_info = self.hazard_unit.detect_hazard(self.pipeline, self.pipeline["ID"])

        # Stall por datos (tal como lo decide la HazardUnit)
        data_stall = hazard_info.get("stall", False)

        # ------------------------------------------------------------------
        # Integrar penalización por branch a las métricas:
        #   - Queremos que el main, que suma cuando hazard_info["stall"] es True,
        #     cuente también estos stalls de control.
        # ------------------------------------------------------------------
        if branch_penalty:
            hazard_info["branch_stall"] = True
            # Si ya había stall por datos, lo conservamos; si no, lo marcamos.
            hazard_info["stall"] = True or data_stall

        # Stall global que se usará en el PRÓXIMO ciclo
        self.stalled = bool(hazard_info.get("stall", False))

        return hazard_info
