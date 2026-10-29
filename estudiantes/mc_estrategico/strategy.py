"""Bot «mc_estrategico»: Monte Carlo guiado por evaluación estratégica multidimensional.

Combina simulaciones de rollouts con una función de evaluación posicional enriquecida que mide
puntos, peones, avance medio y máximo, amenazas inmediatas, apoyo mutuo, vulnerabilidad
y control territorial. Trata el azar de ataques mediante expectativa matemática exacta.
"""

from __future__ import annotations

import math
import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3  # fracción de seguridad
SIMS_HOJA = 12  # simulaciones rápidas por hoja de evaluación
PESO_HEUR = 0.45  # balance entre evaluación heurística posicional y simulaciones azarosas

# Pesos de las dimensiones estratégicas (calibrados para Breakthrough)
W_PUNTOS = 2.10
W_PEONES = 0.08
W_AVANCE_PROM = 0.50
W_AVANCE_MAX = 0.35
W_AMENAZA = 0.40
W_APOYO = 0.15
W_VULNERABILIDAD = 0.20
W_CENTRO = 0.10


def preparar(config):
    global color, rival, rng, reserva
    color = config.color
    rival = "negras" if color == "blancas" else "blancas"
    rng = random.Random(config.semilla)
    reserva = RESERVA * config.reloj_s
    simular_al_azar(Estado.inicial(), 1, 0, para=color)


def _fila_col(casilla: str) -> tuple[int, int]:
    return int(casilla[1]), ord(casilla[0]) - ord("a")


def _avance_peon(fila: int, col_jugador: str) -> int:
    return (fila - 1) if col_jugador == "blancas" else (9 - fila)


def evaluacion_estrategica(estado: Estado) -> float:
    """Retorna una evaluación de la posición en [0.0, 1.0] desde la perspectiva de `color`."""
    ganador = estado.ganador()
    if ganador == color:
        return 1.0
    if ganador is not None:
        return 0.0

    pts = estado.puntos
    mias = estado.piezas(color)
    suyas = estado.piezas(rival)
    n_mias = len(mias)
    n_suyas = len(suyas)

    # 1. Material y puntos
    dif_pts = pts[color] - pts[rival]
    dif_peones = n_mias - n_suyas

    # 2. Avances
    av_mios = [_avance_peon(_fila_col(c)[0], color) for c in mias] if n_mias else [0]
    av_suyos = [_avance_peon(_fila_col(c)[0], rival) for c in suyas] if n_suyas else [0]

    prom_yo = sum(av_mios) / max(1, n_mias)
    prom_el = sum(av_suyos) / max(1, n_suyas)
    dif_prom = prom_yo - prom_el

    max_yo = max(av_mios) if av_mios else 0
    max_el = max(av_suyos) if av_suyos else 0
    dif_max = max_yo - max_el

    # 3. Amenazas directas de meta (avance >= 7)
    amenazas_yo = sum(1 for a in av_mios if a >= 7)
    amenazas_el = sum(1 for a in av_suyos if a >= 7)
    dif_amenaza = amenazas_yo - amenazas_el

    # 4. Estructura de peones: apoyo diagonal
    pos_mias = {_fila_col(c) for c in mias}
    pos_suyas = {_fila_col(c) for c in suyas}

    def _contar_apoyo(posiciones, col_j):
        df = 1 if col_j == "blancas" else -1
        apoyados = 0
        for f, c in posiciones:
            f_detras = f - df
            if (f_detras, c - 1) in posiciones or (f_detras, c + 1) in posiciones:
                apoyados += 1
        return apoyados

    apoyo_yo = _contar_apoyo(pos_mias, color) / max(1, n_mias)
    apoyo_el = _contar_apoyo(pos_suyas, rival) / max(1, n_suyas)
    dif_apoyo = apoyo_yo - apoyo_el

    # 5. Vulnerabilidad a ataques frontales
    def _contar_amenazados(propias, rivales, col_j):
        df_rival = -1 if col_j == "blancas" else 1
        amenazados = 0
        for f, c in propias:
            f_riv = f - df_rival
            if (f_riv, c - 1) in rivales or (f_riv, c + 1) in rivales:
                amenazados += 1
        return amenazados

    amenazados_yo = _contar_amenazados(pos_mias, pos_suyas, color) / max(1, n_mias)
    amenazados_el = _contar_amenazados(pos_suyas, pos_mias, rival) / max(1, n_suyas)
    dif_vulnerabilidad = amenazados_el - amenazados_yo

    # 6. Control de centro (columnas c-g: 2 a 6)
    centro_yo = sum(1 for _, c in pos_mias if 2 <= c <= 6) / max(1, n_mias)
    centro_el = sum(1 for _, c in pos_suyas if 2 <= c <= 6) / max(1, n_suyas)
    dif_centro = centro_yo - centro_el

    x = (
        W_PUNTOS * dif_pts
        + W_PEONES * dif_peones
        + W_AVANCE_PROM * (dif_prom / 8.0)
        + W_AVANCE_MAX * (dif_max / 8.0)
        + W_AMENAZA * dif_amenaza
        + W_APOYO * dif_apoyo
        + W_VULNERABILIDAD * dif_vulnerabilidad
        + W_CENTRO * dif_centro
    )

    # Sigmoide logística para obtener probabilidad estimada [0, 1]
    return 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, x))))


def valor_hoja(estado: Estado, limite: float) -> float:
    if estado.terminado():
        return 1.0 if estado.ganador() == color else 0.0
    heur = evaluacion_estrategica(estado)
    if time.perf_counter() >= limite:
        return heur
    mc = simular_al_azar(estado, SIMS_HOJA, rng.randrange(2**31), para=color)
    return PESO_HEUR * heur + (1.0 - PESO_HEUR) * mc


def valor_esperado_jugada(estado: Estado, j, limite: float) -> float:
    """Calcula el valor esperado ponderando los resultados probabilísticos del motor."""
    siguientes = estado.siguiente(j)
    return sum(prob * valor_hoja(hijo, limite) for prob, hijo in siguientes)


def jugar(estado: Estado, tiempo_restante: float):
    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 25.0
    jugadas = estado.jugadas()

    if not jugadas:
        return None

    # Táctica inmediata: victoria garantizada en un movimiento
    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j

    if disponible <= 0.0:
        return rng.choice(jugadas)

    # Ordenamiento previo de jugadas candidatas por avance y potencial de captura
    def prioridad_rapida(j):
        dest_fila = j.destino // 9 + 1
        anota = (dest_fila == 9) if color == "blancas" else (dest_fila == 1)
        es_atq = estado.es_ataque(j)
        p = estado.prob_ataque(j) if es_atq else 1.0
        av = dest_fila if color == "blancas" else (10 - dest_fila)
        return (anota, p > 0.5, av)

    candidatas = sorted(jugadas, key=prioridad_rapida, reverse=True)

    valores = {}
    for j in candidatas:
        valores[j] = valor_esperado_jugada(estado, j, limite)
        if time.perf_counter() >= limite:
            break

    # Si se agotó el tiempo antes de evaluar todas, las restantes usan solo heurística directa
    for j in jugadas:
        if j not in valores:
            valores[j] = sum(p * evaluacion_estrategica(s) for p, s in estado.siguiente(j))

    mejor = max(jugadas, key=lambda j: valores[j])
    reportar(eval=valores[mejor], modelo="mc_estrategico")
    return mejor
