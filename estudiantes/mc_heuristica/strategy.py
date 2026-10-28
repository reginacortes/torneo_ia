"""Modelo 7: Monte Carlo con política de jugadas heurística.

Las simulaciones no eligen al azar uniforme: aplican reglas simples con pesos
(parámetros genéticos) y una probabilidad de aplicar cada regla.
"""

import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3
SIMS_COLA = 12  # partidas al azar después de los plies guiados
PLIES_POLITICA = 5  # cuántos turnos se juegan con la heurística
MUESTRAS_MIN = 1

# Parámetros genéticos: peso de cada regla y probabilidad de aplicarla.
W_AVANCE = 1.10
P_AVANCE = 0.90

W_ATAQUE = 1.40
P_ATAQUE = 0.85

W_VULNERABLE = 1.00
P_VULNERABLE = 0.80

W_APOYO = 0.70
P_APOYO = 0.75

W_BLOQUEAR = 2.20
P_BLOQUEAR = 0.95


def preparar(config):
    global color, rival, rng, reserva
    color = config.color
    rival = "negras" if color == "blancas" else "blancas"
    rng = random.Random(config.semilla)
    reserva = RESERVA * config.reloj_s
    simular_al_azar(Estado.inicial(), 1, 0, para=color)


def _fila(idx):
    return idx // 9 + 1


def _col(idx):
    return idx % 9


def _meta(quien):
    return 9 if quien == "blancas" else 1


def _avance(idx, quien):
    fila = _fila(idx)
    return fila if quien == "blancas" else 10 - fila


def _indice(casilla):
    return (int(casilla[1]) - 1) * 9 + "abcdefghi".index(casilla[0])


def _apoya_a_alguien(estado, origen, quien):
    """True si el peón en origen está en diagonal detrás de otro propio."""
    propios = {_indice(c) for c in estado.piezas(quien)}
    c, f = _col(origen), origen // 9
    if quien == "blancas":
        destinos = ((c - 1, f + 1), (c + 1, f + 1))
    else:
        destinos = ((c - 1, f - 1), (c + 1, f - 1))
    for dc, df in destinos:
        if 0 <= dc < 9 and 0 <= df < 9 and (df * 9 + dc) in propios:
            return True
    return False


def _anota(j, quien):
    return _fila(j.destino) == _meta(quien)


def _rival_anota_seguro(estado):
    """El jugador en turno puede caminar a su última fila (sin ataque)."""
    quien = estado.turno
    for j in estado.jugadas():
        if _anota(j, quien) and not estado.es_ataque(j):
            return True
    return False


def _bloquea_anotacion(estado, j):
    """Tras esta jugada, el rival ya no tiene un avance seguro a meta."""
    if estado.terminado():
        return False
    # Si no es ataque, hay un solo hijo; si es ataque, miramos el caso en que ganamos.
    if estado.es_ataque(j):
        hijo = estado.aplicar(j, gana_ataque=True)
    else:
        hijo = estado.aplicar(j)
    if hijo.terminado():
        return hijo.ganador() == estado.turno
    return not _rival_anota_seguro(hijo)


def puntaje_regla(estado, j):
    """Suma contribuciones de reglas, cada una con probabilidad de aplicarse."""
    s = 0.08  # suelo para que ninguna jugada tenga peso 0
    quien = estado.turno

    if rng.random() < P_AVANCE:
        s += W_AVANCE * (_avance(j.destino, quien) / 9.0)

    if estado.es_ataque(j) and rng.random() < P_ATAQUE:
        p = estado.prob_ataque(j)
        s += W_ATAQUE * (p - 0.35)

    if estado.es_ataque(j) and rng.random() < P_VULNERABLE:
        p = estado.prob_ataque(j)
        if p < 0.5:
            s -= W_VULNERABLE * (0.5 - p)

    if rng.random() < P_APOYO and _apoya_a_alguien(estado, j.origen, quien):
        s -= W_APOYO

    if rng.random() < P_BLOQUEAR and _bloquea_anotacion(estado, j):
        s += W_BLOQUEAR

    if _anota(j, quien) and not estado.es_ataque(j):
        s += 3.0
    return max(s, 1e-6)


def elegir_politica(estado):
    jugadas = estado.jugadas()
    if not jugadas:
        return None
    pesos = [puntaje_regla(estado, j) for j in jugadas]
    return rng.choices(jugadas, weights=pesos)[0]


def rollout_guiado(estado):
    """Juega unos turnos con la política y termina con simulaciones al azar."""
    actual = estado
    for _ in range(PLIES_POLITICA):
        if actual.terminado():
            return 1.0 if actual.ganador() == color else 0.0
        j = elegir_politica(actual)
        if j is None:
            break
        probs, hijos = zip(*actual.siguiente(j), strict=True)
        actual = rng.choices(hijos, weights=probs)[0]
    if actual.terminado():
        return 1.0 if actual.ganador() == color else 0.0
    return simular_al_azar(actual, SIMS_COLA, rng.randrange(2**31), para=color)


def jugar(estado, tiempo_restante):
    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 25
    jugadas = estado.jugadas()

    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j
    if disponible <= 0:
        return elegir_politica(estado) or rng.choice(jugadas)

    # Orden: primero las que la política considera fuertes.
    orden = sorted(jugadas, key=lambda j: puntaje_regla(estado, j), reverse=True)

    total = {j: 0.0 for j in jugadas}
    muestras = {j: 0 for j in jugadas}
    hechas = 0
    while True:
        j = orden[hechas % len(orden)]
        probs, hijos = zip(*estado.siguiente(j), strict=True)
        hijo = rng.choices(hijos, weights=probs)[0]
        total[j] += rollout_guiado(hijo)
        muestras[j] += 1
        hechas += 1
        if hechas >= len(jugadas) * MUESTRAS_MIN and time.perf_counter() >= limite:
            break
        if hechas >= len(jugadas) * 30:
            break

    mejor = max(jugadas, key=lambda j: total[j] / max(1, muestras[j]))
    reportar(
        muestras=sum(muestras.values()),
        eval=total[mejor] / max(1, muestras[mejor]),
        modelo="politica_heuristica",
    )
    return mejor
