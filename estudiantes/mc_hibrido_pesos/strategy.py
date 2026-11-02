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

    mias = estado.piezas(color)
    suyas = estado.piezas(rival)
    pts = estado.puntos

    # 1. Diferencia de puntos
    dif_puntos = pts[color] - pts[rival]

    # 2. Diferencia de peones (normalizada)
    dif_peones = (len(mias) - len(suyas)) / 18

    # 3. Avance promedio (normalizado)
    avance_mio = [
        (_progreso(c, color) - 1) / 8 for c in mias
    ]
    avance_rival = [
        (_progreso(c, rival) - 1) / 8 for c in suyas
    ]

    avance_promedio = (
        sum(avance_mio) / max(1, len(avance_mio))
        - sum(avance_rival) / max(1, len(avance_rival))
    )

    # 4. Avance máximo (normalizado)
    avance_maximo = (
        max(avance_mio, default=0)
        - max(avance_rival, default=0)
    )

    # 5. Amenaza de anotación
    amenaza_mia = sum(
        _progreso(c, color) >= 8 for c in mias
    ) / 18

    amenaza_rival = sum(
        _progreso(c, rival) >= 8 for c in suyas
    ) / 18

    amenaza_anotacion = amenaza_mia - amenaza_rival

    # 6. Control del centro (columnas d, e, f)
    centro_mio = sum(c[0] in "def" for c in mias) / 18
    centro_rival = sum(c[0] in "def" for c in suyas) / 18

    control_centro = centro_mio - centro_rival

    # Evaluación ponderada
    x = (
        1.391 * dif_puntos
        + 0.400 * dif_peones
        + 0.586 * avance_promedio
        + 0.683 * avance_maximo
        + 0.495 * amenaza_anotacion
        + 0.217 * control_centro
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
        if time.perf_counter() >= limite:
            valor = sum(
                p * evaluar(hijo)
                for p, hijo in estado.siguiente(j)
            )
        else:
            valor = valor_jugada(estado, j, prof, limite)

        valores.append(valor)

    if estado.turno == color:
        return max(valores)
    return min(valores)

def valor_jugada(estado, j, prof, limite):
    """Nodo de azar: ganancia esperada de la jugada."""
    total = 0.0
    for p, hijo in estado.siguiente(j):
        if time.perf_counter() >= limite:
            valor = evaluar(hijo)
        else:
            valor = valor_estado(hijo, prof - 1, limite)

        total += p * valor

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
