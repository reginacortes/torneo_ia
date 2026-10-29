"""Evaluador estadístico riguroso de bots para Breakthrough.

Ejecuta series emparejadas alternando colores, semillas independientes, midiendo tiempos
y calculando tasas de victoria con intervalos de confianza de Wilson (95%).
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from arbitro.azar import Dados, semilla_bots, semilla_de_color
from arbitro.runner import Config
from motor import Estado, Jugada

COLORES = ("blancas", "negras")


def cargar_bot(equipo: str, instancia: int):
    ruta = RAIZ / "estudiantes" / equipo / "strategy.py"
    spec = importlib.util.spec_from_file_location(f"eval_{equipo}_{instancia}", ruta)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def intervalo_wilson(exitos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Calcula el intervalo de confianza de Wilson para una proporción binomial."""
    if total == 0:
        return 0.0, 1.0
    p = exitos / total
    den = 1.0 + (z**2) / total
    centro = (p + (z**2) / (2 * total)) / den
    margen = (z * math.sqrt((p * (1.0 - p) + (z**2) / (4 * total)) / total)) / den
    return max(0.0, centro - margen), min(1.0, centro + margen)


def partida_evaluacion(
    equipos: tuple[str, str], reloj_s: float, semilla_base: int, n: int
) -> dict:
    bots = {c: cargar_bot(e, i) for i, (c, e) in enumerate(zip(COLORES, equipos, strict=True))}
    base = semilla_bots(semilla_base, 0, n)
    for color, bot in bots.items():
        carp = RAIZ / "estudiantes" / equipos[COLORES.index(color)] / "data"
        if hasattr(bot, "preparar"):
            bot.preparar(Config(color, semilla_de_color(base, color), carp, reloj_s))

    dados = Dados(semilla_base, 0, n)
    usado = {c: 0.0 for c in COLORES}
    estado = Estado.inicial()
    jugadas = 0

    while (ganador := estado.ganador()) is None:
        color = estado.turno
        t0 = time.perf_counter()
        j = bots[color].jugar(estado, max(0.0, reloj_s - usado[color]))
        dur = time.perf_counter() - t0
        usado[color] += dur

        if usado[color] > reloj_s:
            otro = COLORES[1 - COLORES.index(color)]
            return {
                "ganador": otro,
                "ganador_bot": equipos[COLORES.index(otro)],
                "motivo": "reloj",
                "jugadas": jugadas,
                "tiempos": usado,
            }

        j_obj = Jugada.desde_texto(str(j))
        if estado.es_ataque(j_obj):
            gana = float(dados.tirar(color)) < estado.prob_ataque(j_obj)
            estado = estado.aplicar(j_obj, gana_ataque=gana)
        else:
            estado = estado.aplicar(j_obj)
        jugadas += 1

    ganador_bot = equipos[COLORES.index(ganador)]
    return {
        "ganador": ganador,
        "ganador_bot": ganador_bot,
        "motivo": "juego",
        "jugadas": jugadas,
        "tiempos": usado,
    }


def evaluar_enfrentamiento(
    bot_a: str,
    bot_b: str,
    partidas: int = 10,
    reloj_s: float = 2.0,
    semilla: int = 20261029,
) -> dict:
    """Evalúa bot_a vs bot_b en `partidas` alternando colores."""
    victorias_a = 0
    victorias_b = 0
    victorias_a_blancas = 0
    victorias_a_negras = 0
    fallos_reloj_a = 0
    fallos_reloj_b = 0
    total_jugadas = 0

    equipos = (bot_a, bot_b)

    for i in range(partidas):
        orden = equipos if i % 2 == 0 else equipos[::-1]
        res = partida_evaluacion(orden, reloj_s, semilla, i)
        total_jugadas += res["jugadas"]

        if res["ganador_bot"] == bot_a:
            victorias_a += 1
            if res["ganador"] == "blancas":
                victorias_a_blancas += 1
            else:
                victorias_a_negras += 1
        else:
            victorias_b += 1

        if res["motivo"] == "reloj":
            if res["ganador_bot"] == bot_b:
                fallos_reloj_a += 1
            else:
                fallos_reloj_b += 1

    tasa_a = victorias_a / max(1, partidas)
    ci_inf, ci_sup = intervalo_wilson(victorias_a, partidas)

    return {
        "bot_a": bot_a,
        "bot_b": bot_b,
        "partidas": partidas,
        "reloj_s": reloj_s,
        "victorias_a": victorias_a,
        "victorias_b": victorias_b,
        "tasa_a": round(tasa_a, 4),
        "ci_95": (round(ci_inf, 4), round(ci_sup, 4)),
        "victorias_a_blancas": victorias_a_blancas,
        "victorias_a_negras": victorias_a_negras,
        "fallos_reloj_a": fallos_reloj_a,
        "fallos_reloj_b": fallos_reloj_b,
        "promedio_jugadas": round(total_jugadas / max(1, partidas), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluación comparativa de bots.")
    parser.add_argument("--bot-a", type=str, default="mc_aprendiz")
    parser.add_argument("--bot-b", type=str, default="montecarlo")
    parser.add_argument("--partidas", type=int, default=6)
    parser.add_argument("--reloj", type=float, default=2.0)
    parser.add_argument("--semilla", type=int, default=20261029)
    args = parser.parse_args()

    print(f"Evaluando {args.bot_a} vs {args.bot_b} ({args.partidas} partidas, reloj {args.reloj}s)...")
    res = evaluar_enfrentamiento(args.bot_a, args.bot_b, args.partidas, args.reloj, args.semilla)
    print("--------------------------------------------------")
    print(f"Resultado: {res['bot_a']} {res['victorias_a']} - {res['victorias_b']} {res['bot_b']}")
    print(f"Tasa de victorias {res['bot_a']}: {res['tasa_a'] * 100:.1f}%")
    print(f"Intervalo Wilson (95%): [{res['ci_95'][0]*100:.1f}%, {res['ci_95'][1]*100:.1f}%]")
    print(f"Blancas: {res['victorias_a_blancas']}, Negras: {res['victorias_a_negras']}")
    print(f"Promedio de jugadas: {res['promedio_jugadas']}")
    print(f"Fallos de reloj: {res['bot_a']}={res['fallos_reloj_a']}, {res['bot_b']}={res['fallos_reloj_b']}")
    print("--------------------------------------------------")


if __name__ == "__main__":
    main()
