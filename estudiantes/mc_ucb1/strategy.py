"""Bot «mc_ucb1»: Monte Carlo con selección adaptativa mediante UCB1 (Multi-Armed Bandit).

Reemplaza la asignación cíclica/uniforme de simulaciones por una selección orientada por el
límite superior de confianza: UCB1 = Q_i + c * sqrt(ln(N) / n_i).
"""

from __future__ import annotations

import math
import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3  # fracción de seguridad del reloj
SIMULACIONES_POR_MUESTRA = 15  # rollouts rápidos por cada visita seleccionada por UCB
CONSTANTE_C = 0.85  # factor de exploración de UCB1 adaptado al rango [0, 1]


def preparar(config):
    global color, rng, reserva
    color = config.color
    rng = random.Random(config.semilla)
    reserva = RESERVA * config.reloj_s
    # Calentamos la compilación JIT de numba
    simular_al_azar(Estado.inicial(), 1, 0, para=color)


def jugar(estado: Estado, tiempo_restante: float):
    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 25.0
    jugadas = estado.jugadas()

    if not jugadas:
        return None

    # 1. Victoria inmediata confirmada en un ply sin importar el dado
    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j

    if disponible <= 0.0:
        return rng.choice(jugadas)

    # 2. Inicialización de estadísticas del bandit para cada jugada
    recompensas = {j: 0.0 for j in jugadas}
    visitas = {j: 0 for j in jugadas}
    total_visitas = 0

    # Fase de calentamiento: garantizar al menos 1 visita por jugada
    for j in jugadas:
        probs, hijos = zip(*estado.siguiente(j), strict=True)
        hijo = rng.choices(hijos, weights=probs)[0]
        r = simular_al_azar(hijo, SIMULACIONES_POR_MUESTRA, rng.randrange(2**31), para=color)
        recompensas[j] += r
        visitas[j] += 1
        total_visitas += 1
        if time.perf_counter() >= limite:
            break

    # Fase adaptativa UCB1: mientras quede tiempo en el presupuesto del turno
    while time.perf_counter() < limite:
        # Selección de la jugada con mayor UCB1
        log_n = math.log(max(1, total_visitas))
        mejor_j = None
        mejor_ucb = -float("inf")

        for j in jugadas:
            n_j = visitas[j]
            if n_j == 0:
                mejor_j = j
                break
            q_j = recompensas[j] / n_j
            ucb = q_j + CONSTANTE_C * math.sqrt(log_n / n_j)
            if ucb > mejor_ucb:
                mejor_ucb = ucb
                mejor_j = j

        if mejor_j is None:
            mejor_j = rng.choice(jugadas)

        # Simulación probabilística desde la jugada seleccionada
        probs, hijos = zip(*estado.siguiente(mejor_j), strict=True)
        hijo = rng.choices(hijos, weights=probs)[0]
        r = simular_al_azar(hijo, SIMULACIONES_POR_MUESTRA, rng.randrange(2**31), para=color)

        recompensas[mejor_j] += r
        visitas[mejor_j] += 1
        total_visitas += 1

    # Selección final: la jugada más visitada (o con mayor tasa de éxito comprobada)
    def criterio_final(j):
        n = visitas[j]
        if n == 0:
            return 0.0
        # Ponderación principal por robustez (visitas) y secundaria por promedio
        return (recompensas[j] / n) + 0.01 * math.log(1 + n)

    mejor_jugada = max(jugadas, key=criterio_final)
    q_mejor = (recompensas[mejor_jugada] / max(1, visitas[mejor_jugada]))
    reportar(muestras=total_visitas, eval=q_mejor, modelo="mc_ucb1")
    return mejor_jugada
