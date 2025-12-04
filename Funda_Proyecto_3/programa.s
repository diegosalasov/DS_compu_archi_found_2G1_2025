############################################################
# PROGRAMA A – Data hazards + forwarding (R-type + LW/RAW)
# P1 modo GUI: Con Unidad de Riesgos
# P2 modo GUI: Sin Unidad de Riesgos
# Ver:
#   P1 -> menos stalls y menos ciclos.
#   P2 -> más stalls por dependencias RAW.
############################################################

addi x1, x0, 10       # base
lw   x2, 0(x1)        # x2 <- MEM[10] (0 al inicio)
add  x3, x2, x1       # depende de x2 (RAW con lw)
sub  x4, x3, x1       # depende de x3 (RAW encadenado)
sw   x4, 4(x1)        # depende de x4

# Esperado:
# x1 = 10, x2 = 0, x3 = 10, x4 = 0
# MEM[10] = 0, MEM[14] = 0


############################################################
# PROGRAMA B2 – Branches fáciles, sin data hazards
# P1 modo GUI: Predicción de Saltos
# P2 modo GUI: Sin Unidad de Riesgos
# Ver:
#   - Ambos dan los mismos registros.
#   - P2 tiene +3 stalls (uno por cada BEQ/BNE).
############################################################

addi x1, x0, 1        # x1 = 1
addi x2, x0, 1        # x2 = 1

beq  x1, x2, 1        # tomado
addi x3, x0, 99       # se salta si el branch se toma
addi x3, x0, 5        # x3 = 5

bne  x3, x1, 1        # tomado (5 != 1)
addi x4, x0, 99       # se salta si el branch se toma
addi x4, x0, 7        # x4 = 7

beq  x4, x3, 1        # no tomado (7 != 5)
addi x5, x0, 9        # x5 = 9

# Esperado:
# x1 = 1, x2 = 1, x3 = 5, x4 = 7, x5 = 9
# P2 debe tener 3 stalls más que P1 por las 3 branches.


############################################################
# PROGRAMA C2 – Data + varios branches
# P1 modo GUI: Riesgos + Predicción
# P2 modo GUI: Con Unidad de Riesgos
# Ver:
#   - Ningún problema fuerte de datos (no hay RAW críticos).
#   - P2 tiene +3 stalls por branches; P1 no.
############################################################

addi x1, x0, 2        # x1 = 2
addi x2, x0, 2        # x2 = 2
add  x3, x1, x2       # x3 = 4

beq  x1, x2, 1        # tomado
addi x4, x0, 99       # se salta si el branch se toma
addi x4, x0, 10       # x4 = 10

bne  x3, x4, 1        # tomado (4 != 10)
addi x5, x0, 99       # se salta si el branch se toma
addi x5, x0, 20       # x5 = 20

beq  x5, x4, 1        # no tomado
addi x6, x0, 30       # x6 = 30

# Esperado:
# x1 = 2, x2 = 2, x3 = 4, x4 = 10, x5 = 20, x6 = 30
# P2 debería mostrar 3 stalls más que P1 (uno por cada branch).


############################################################
# PROGRAMA E2 – Comparar solo estrategia de branch
# P1 modo GUI: Sin Unidad de Riesgos
# P2 modo GUI: Predicción de Saltos
# Ver:
#   - Mismos registros al final.
#   - P1 tiene +2 stalls por branches que P2 no tiene.
############################################################

addi x1, x0, 4        # x1 = 4
addi x2, x0, 4        # x2 = 4

beq  x1, x2, 1        # tomado
addi x3, x0, 99       # se salta si el branch se toma
addi x3, x0, 1        # x3 = 1

bne  x3, x2, 1        # tomado (1 != 4)
addi x4, x0, 99       # se salta si el branch se toma
addi x4, x0, 2        # x4 = 2

# Esperado:
# x1 = 4, x2 = 4, x3 = 1, x4 = 2
# P1: 2 stalls adicionales (por BEQ y por BNE).
# P2: sin esos 2 stalls extra.
