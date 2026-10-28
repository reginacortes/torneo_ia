"""Modelo 5: Monte Carlo híbrido con búsqueda de varios turnos.

Expectiminimax poco profundo: nuestras jugadas, respuestas del rival y nodos
de azar en los ataques. Las hojas se miden con heurística + simulaciones.
"""

import math
import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3

# Parámetros del modelo 5
PROFUNDIDAD = 2  # plies: 2 = nuestra jugada + respuesta rival
CANDIDATAS = 5  # jugadas que se exploran en cada turno
SIMS_HOJA = 10  # simulaciones por hoja
PESO_HEUR = 0.35  # peso de la evaluación heurística en la hoja


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


def candidatas(estado):
    jugadas = estado.jugadas()
    jugadas.sort(key=lambda j: _prioridad(estado, j), reverse=True)
    return jugadas[:CANDIDATAS]


def valor_hoja(estado, limite):
    if estado.terminado():
        return 1.0 if estado.ganador() == color else 0.0
    heur = evaluar(estado)
    if time.perf_counter() >= limite:
        return heur
    mc = simular_al_azar(estado, SIMS_HOJA, rng.randrange(2**31), para=color)
    return PESO_HEUR * heur + (1.0 - PESO_HEUR) * mc


def valor_estado(estado, prof, limite):
    if estado.terminado() or prof <= 0 or time.perf_counter() >= limite:
        return valor_hoja(estado, limite)
    jugadas = candidatas(estado)
    if not jugadas:
        return valor_hoja(estado, limite)

    valores = []
    for j in jugadas:
        valores.append(valor_jugada(estado, j, prof, limite))
        if time.perf_counter() >= limite:
            break
    if not valores:
        return valor_hoja(estado, limite)
    if estado.turno == color:
        return max(valores)
    return min(valores)


def valor_jugada(estado, j, prof, limite):
    """Nodo de azar: ganancia esperada de la jugada."""
    total = 0.0
    for p, hijo in estado.siguiente(j):
        total += p * valor_estado(hijo, prof - 1, limite)
        if time.perf_counter() >= limite:
            break
    return total


def jugar(estado, tiempo_restante):
    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 18
    jugadas = estado.jugadas()

    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j
    if disponible <= 0:
        return rng.choice(jugadas)

    raiz = candidatas(estado)
    # Si hay pocas jugadas, las vemos todas.
    if len(jugadas) <= CANDIDATAS:
        raiz = jugadas

    puntaje = {}
    for j in raiz:
        puntaje[j] = valor_jugada(estado, j, PROFUNDIDAD, limite)
        if time.perf_counter() >= limite:
            break
    for j in raiz:
        if j not in puntaje:
            puntaje[j] = sum(p * evaluar(s) for p, s in estado.siguiente(j))

    mejor = max(raiz, key=lambda j: puntaje[j])
    reportar(eval=puntaje[mejor], modelo="hibrido", prof=PROFUNDIDAD, cand=len(raiz))
    return mejor
