"""Extracción homogénea de características estratégicas para Breakthrough.

Diseñado para ser invariante a la perspectiva y compatible tanto con
heurísticas lineales fijas como con modelos aprendidos (TD(0), TD(lambda), GA).
"""

from __future__ import annotations

import math
from typing import Sequence
from motor import Estado, Jugada

COLORES = ("blancas", "negras")
NOMBRES_CARACTERISTICAS = (
    "dif_puntos",
    "dif_peones",
    "avance_promedio",
    "avance_maximo",
    "amenaza_anotacion",
    "movilidad_relativa",
    "apoyo_mutuo",
    "vulnerabilidad",
    "bloqueo_rival",
    "control_centro",
)


def _fila_col(casilla: str) -> tuple[int, int]:
    col = ord(casilla[0]) - ord("a")  # 0 a 8
    fila = int(casilla[1])  # 1 a 9
    return fila, col


def _avance_peon(fila: int, color: str) -> int:
    """Avance de 0 (salida) a 8 (meta alcanzada)."""
    return (fila - 1) if color == "blancas" else (9 - fila)


def extraer_caracteristicas(estado: Estado, perspectiva: str) -> list[float]:
    """Extrae un vector de características normalizadas en [-1, 1] desde `perspectiva`.
    
    Valores positivos favorecen a `perspectiva`; valores negativos al rival.
    Si el estado es terminal, refleja victoria (+1) o derrota (-1).
    """
    ganador = estado.ganador()
    if ganador is not None:
        val = 1.0 if ganador == perspectiva else -1.0
        return [val] * len(NOMBRES_CARACTERISTICAS)

    rival = "negras" if perspectiva == "blancas" else "blancas"
    pts = estado.puntos
    mias = estado.piezas(perspectiva)
    suyas = estado.piezas(rival)

    n_mias = len(mias)
    n_suyas = len(suyas)

    # 1. Diferencia de puntos normalizada (-1 a 1, pues para ganar son 3 puntos)
    dif_pts = (pts[perspectiva] - pts[rival]) / 3.0

    # 2. Diferencia de peones normalizada (-1 a 1, max 18)
    dif_peones = (n_mias - n_suyas) / 18.0

    # Avances individuales
    avances_mios = [_avance_peon(_fila_col(c)[0], perspectiva) for c in mias] if n_mias else [0]
    avances_suyos = [_avance_peon(_fila_col(c)[0], rival) for c in suyas] if n_suyas else [0]

    # 3. Avance promedio normalizado (-1 a 1)
    prom_yo = sum(avances_mios) / max(1, n_mias)
    prom_el = sum(avances_suyos) / max(1, n_suyas)
    dif_avance_prom = (prom_yo - prom_el) / 8.0

    # 4. Avance máximo y proximidad a la meta (-1 a 1)
    max_yo = max(avances_mios) if avances_mios else 0
    max_el = max(avances_suyos) if avances_suyos else 0
    dif_avance_max = (max_yo - max_el) / 8.0

    # 5. Amenaza de conseguir punto en el próximo movimiento (avance >= 7)
    amenazas_yo = sum(1 for av in avances_mios if av >= 7)
    amenazas_el = sum(1 for av in avances_suyos if av >= 7)
    amenaza_anotacion = max(-1.0, min(1.0, (amenazas_yo - amenazas_el) / 3.0))

    # 6. Movilidad relativa: número de jugadas legales
    # Nota: estado.jugadas() es del turno actual. Si es mi turno, conozco mis jugadas;
    # si es el turno rival, conozco las del rival.
    if estado.turno == perspectiva:
        n_jugadas_yo = len(estado.jugadas())
        n_jugadas_el = max(1, n_suyas)  # estimación aproximada sin cambiar turno
    else:
        n_jugadas_el = len(estado.jugadas())
        n_jugadas_yo = max(1, n_mias)
    movilidad_rel = max(-1.0, min(1.0, (n_jugadas_yo - n_jugadas_el) / 25.0))

    # 7. Apoyo y protección entre peones (peones con defensor diagonal detrás)
    pos_mias = {_fila_col(c) for c in mias}
    pos_suyas = {_fila_col(c) for c in suyas}

    def _peones_apoyados(posiciones: set[tuple[int, int]], color_p: str) -> int:
        apoyados = 0
        df = 1 if color_p == "blancas" else -1
        for fila, col in posiciones:
            # ¿Tiene un peón defensor diagonalmente detrás?
            # Si blancas avanzan fila+1, detrás es fila-1
            f_detras = fila - df
            if (f_detras, col - 1) in posiciones or (f_detras, col + 1) in posiciones:
                apoyados += 1
        return apoyados

    apoyo_yo = _peones_apoyados(pos_mias, perspectiva) / max(1, n_mias)
    apoyo_el = _peones_apoyados(pos_suyas, rival) / max(1, n_suyas)
    apoyo_mutuo = apoyo_yo - apoyo_el

    # 8. Vulnerabilidad / exposición: peones que están bajo ataque diagonal frontal rival
    def _peones_amenazados(
        propias: set[tuple[int, int]], rivales: set[tuple[int, int]], color_p: str
    ) -> int:
        amenazados = 0
        df_rival = -1 if color_p == "blancas" else 1
        for fila, col in propias:
            # Un rival en fila - df_rival y col +/- 1 nos amenaza
            f_rival = fila - df_rival
            if (f_rival, col - 1) in rivales or (f_rival, col + 1) in rivales:
                amenazados += 1
        return amenazados

    amenazados_yo = _peones_amenazados(pos_mias, pos_suyas, perspectiva) / max(1, n_mias)
    amenazados_el = _peones_amenazados(pos_suyas, pos_mias, rival) / max(1, n_suyas)
    vulnerabilidad = amenazados_el - amenazados_yo  # Favorable si el rival está más amenazado

    # 9. Bloqueo de corredores rivales: si el rival tiene peones en avance 6 o 7,
    # ¿tenemos defensores en su columna o diagonales?
    bloqueo = 0.0
    for fila, col in pos_suyas:
        if _avance_peon(fila, rival) >= 6:
            df = 1 if perspectiva == "blancas" else -1
            # Bloqueador directo en frente
            f_bloq = fila + df
            if (f_bloq, col) in pos_mias or (f_bloq, col - 1) in pos_mias or (f_bloq, col + 1) in pos_mias:
                bloqueo += 0.5
            else:
                bloqueo -= 0.5
    bloqueo_rival = max(-1.0, min(1.0, bloqueo))

    # 10. Control del centro (columnas c, d, e, f, g -> 2, 3, 4, 5, 6)
    centro_yo = sum(1 for _, col in pos_mias if 2 <= col <= 6) / max(1, n_mias)
    centro_el = sum(1 for _, col in pos_suyas if 2 <= col <= 6) / max(1, n_suyas)
    control_centro = centro_yo - centro_el

    return [
        float(dif_pts),
        float(dif_peones),
        float(dif_avance_prom),
        float(dif_avance_max),
        float(amenaza_anotacion),
        float(movilidad_rel),
        float(apoyo_mutuo),
        float(vulnerabilidad),
        float(bloqueo_rival),
        float(control_centro),
    ]
