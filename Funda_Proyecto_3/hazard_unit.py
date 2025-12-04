"""
Clase que representa la unidad de Riesgos (Hazard Unit) en un procesador segmentado.

Esta unidad es responsable de detectar posibles riesgos de datos en el pipeline y aplicar
políticas como stalling o reenvío (forwarding) para resolverlos.

Atributos:
    enable_forwarding (bool): Indica si el reenvío está habilitado.
    enable_branch_prediction (bool): Indica si la predicción de saltos está habilitada
        (se usa como flag para el procesador; aquí solo manejamos riesgos de datos).
"""

class HazardUnit:
    """
    Inicializa la unidad de riesgos.

    Args:
        enable_forwarding (bool): Activa el reenvío de datos si es True.
        enable_branch_prediction (bool): Activa la predicción de saltos si es True.
    """

    def __init__(self, enable_forwarding=True, enable_branch_prediction=False):
        self.enable_forwarding = enable_forwarding
        self.enable_branch_prediction = enable_branch_prediction

    def detect_hazard(self, pipeline, id_instr):
        """
        Detecta posibles riesgos de datos en la etapa de ID del pipeline.

        Analiza si las instrucciones en etapas posteriores (EX, MEM, WB) tienen conflictos
        con la instrucción en la etapa de ID.

        Args:
            pipeline (dict): Estado actual del pipeline con claves "IF", "ID", "EX", "MEM", "WB".
            id_instr (dict or None): Instrucción actual en la etapa de decodificación (ID).

        Returns:
            dict: Diccionario con las claves:
                - 'stall' (bool): True si requiere detener el pipeline (solo por datos).
                - 'forwardA' (str): Fuente de reenvío para rs1 ("EX", "MEM", "WB", "NO").
                - 'forwardB' (str): Fuente de reenvío para rs2 ("EX", "MEM", "WB", "NO").
        """
        if id_instr is None:
            return {"stall": False, "forwardA": "NO", "forwardB": "NO"}

        rs1 = id_instr.get("rs1")
        rs2 = id_instr.get("rs2")

        hazard = {"stall": False, "forwardA": "NO", "forwardB": "NO"}

        # ------------------------------------------------------------------
        # Riesgo load-use: EX contiene LW y su resultado es usado de inmediato.
        # Si hay LW en EX y su rd es igual a rs1/rs2 de la instrucción en ID,
        # se genera un stall de un ciclo (incluso con forwarding).
        # ------------------------------------------------------------------
        ex_instr = pipeline.get("EX")
        if ex_instr and ex_instr.get("op") == "LW" and ex_instr.get("rd"):
            if ex_instr["rd"] == rs1 or ex_instr["rd"] == rs2:
                hazard["stall"] = True
                return hazard

        # ------------------------------------------------------------------
        # Riesgo de datos con EX (RAW) -> posible forwarding o stall
        # ------------------------------------------------------------------
        if ex_instr and ex_instr.get("rd"):
            if ex_instr["rd"] == rs1:
                hazard["forwardA"] = "EX" if self.enable_forwarding else "NO"
                if not self.enable_forwarding:
                    hazard["stall"] = True
            if ex_instr["rd"] == rs2:
                hazard["forwardB"] = "EX" if self.enable_forwarding else "NO"
                if not self.enable_forwarding:
                    hazard["stall"] = True

        # ------------------------------------------------------------------
        # Riesgo de datos con MEM -> forwarding desde MEM si es necesario
        # ------------------------------------------------------------------
        mem_instr = pipeline.get("MEM")
        if mem_instr and mem_instr.get("rd"):
            if mem_instr["rd"] == rs1 and hazard["forwardA"] == "NO":
                hazard["forwardA"] = "MEM"
            if mem_instr["rd"] == rs2 and hazard["forwardB"] == "NO":
                hazard["forwardB"] = "MEM"

        # ------------------------------------------------------------------
        # Riesgo de datos con WB -> forwarding desde WB si aún no se resolvió
        # ------------------------------------------------------------------
        wb_instr = pipeline.get("WB")
        if wb_instr and wb_instr.get("rd"):
            if wb_instr["rd"] == rs1 and hazard["forwardA"] == "NO":
                hazard["forwardA"] = "WB"
            if wb_instr["rd"] == rs2 and hazard["forwardB"] == "NO":
                hazard["forwardB"] = "WB"

        return hazard
