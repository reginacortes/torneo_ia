"""Modelo 4: Monte Carlo con tratamiento explícito del azar.

En un ataque no se sortea un solo resultado: se evalúan ganar y perder con las
probabilidades reales del motor y se combina un valor esperado.
"""

import math
import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3

# Parámetros del modelo 4
PESO_EVAL_POST = 0.30  # mezcla heurística vs simulaciones tras el ataque
PROFUNDIDAD_EVAL = 1  # 0 = solo heurística; 1 = un ply extra de expectiminimax
SIMS_POST = 12  # simulaciones desde cada resultado posible
PESO_EV = 0.75  # valor esperado vs partidas completas desde un hijo sorteado
SIMS_COMPLETAS = 16
MAX_CANDIDATAS_PROF = 6


def preparar(config):
    global color, rival, rng, reserva
    color = config.color
    rival = "negras" if color == "blancas" else "blancas"
    rng = random.Random(config.semilla)
    reserva = RESERVA * config.reloj_s
    simular_al_azar(Estado.inicial(), 1, 0, para=color)


def _progreso(casilla, quien):
    fila = int(casilla[1])
    return fila if quien == "blancas" else 10 - fila


def evaluar(estado):
    """Estimación en [0, 1] de ganar, desde nuestro color."""
    g = estado.ganador()
    if g == color:
        return 1.0
    if g is not None:
        return 0.0
    pts = estado.puntos
    mias = estado.piezas(color)
    suyas = estado.piezas(rival)
    av_yo = sum(_progreso(c, color) for c in mias) / max(1, len(mias))
    av_el = sum(_progreso(c, rival) for c in suyas) / max(1, len(suyas))
    x = (
        1.7 * (pts[color] - pts[rival])
        + 0.07 * (len(mias) - len(suyas))
        + 0.22 * (av_yo - av_el)
    )
    return 1.0 / (1.0 + math.exp(-x))


def _prioridad(estado, j):
    dest_fila = j.destino // 9 + 1
    meta = 9 if estado.turno == "blancas" else 1
    anota = dest_fila == meta
    p = estado.prob_ataque(j) if estado.es_ataque(j) else 1.0
    avance = dest_fila if estado.turno == "blancas" else 10 - dest_fila
    return (anota, p, avance)


def evaluar_profundo(estado, prof, limite):
    if estado.terminado() or prof <= 0 or time.perf_counter() >= limite:
        return evaluar(estado)
    jugadas = estado.jugadas()
    if not jugadas:
        return evaluar(estado)
    jugadas = sorted(jugadas, key=lambda j: _prioridad(estado, j), reverse=True)
    jugadas = jugadas[:MAX_CANDIDATAS_PROF]
    valores = []
    for j in jugadas:
        v = sum(p * evaluar_profundo(s, prof - 1, limite) for p, s in estado.siguiente(j))
        valores.append(v)
        if time.perf_counter() >= limite:
            break
    if not valores:
        return evaluar(estado)
    if estado.turno == color:
        return max(valores)
    return min(valores)


def valor_hoja(estado, limite):
    if estado.terminado():
        return 1.0 if estado.ganador() == color else 0.0
    heur = evaluar_profundo(estado, PROFUNDIDAD_EVAL, limite)
    if time.perf_counter() >= limite:
        return heur
    mc = simular_al_azar(estado, SIMS_POST, rng.randrange(2**31), para=color)
    return PESO_EVAL_POST * heur + (1.0 - PESO_EVAL_POST) * mc


def valor_esperado(estado, j, limite):
    """Combina los resultados posibles con sus probabilidades reales."""
    return sum(p * valor_hoja(s, limite) for p, s in estado.siguiente(j))


def valor_partidas_completas(estado, j):
    probs, hijos = zip(*estado.siguiente(j), strict=True)
    hijo = rng.choices(hijos, weights=probs)[0]
    return simular_al_azar(hijo, SIMS_COMPLETAS, rng.randrange(2**31), para=color)


def jugar(estado, tiempo_restante):
    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 25
    jugadas = estado.jugadas()

    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j
    if disponible <= 0:
        return rng.choice(jugadas)

    puntaje = {}
    for j in jugadas:
        ev = valor_esperado(estado, j, limite)
        if time.perf_counter() >= limite:
            puntaje[j] = ev
            continue
        completas = valor_partidas_completas(estado, j)
        puntaje[j] = PESO_EV * ev + (1.0 - PESO_EV) * completas
        if time.perf_counter() >= limite:
            break

    for j in jugadas:
        if j not in puntaje:
            # Sin tiempo: al menos el valor esperado con heurística de profundidad 0.
            puntaje[j] = sum(p * evaluar(s) for p, s in estado.siguiente(j))

    mejor = max(jugadas, key=lambda j: puntaje[j])
    reportar(eval=puntaje[mejor], modelo="azar_explicito")
    return mejor
