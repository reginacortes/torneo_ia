"""Análisis exploratorio y diagnóstico del repositorio de datos y modelos.

Analiza estadísticas de partidas, sesgo de color, porcentaje de capturas exitosas,
duración promedio y evolución de pesos aprendidos.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def analizar_partidas(ruta_partidas: Path) -> dict:
    if not ruta_partidas.is_file():
        return {"error": "Archivo no encontrado"}

    total = 0
    victorias_color = {"blancas": 0, "negras": 0}
    victorias_bot: dict[str, int] = {}
    motivos = {"juego": 0, "reloj": 0}
    ataques_totales = 0
    ataques_ganados = 0
    jugadas_totales = 0

    with ruta_partidas.open("r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            total += 1
            p = json.loads(linea)
            g = p.get("ganador", "")
            if g in victorias_color:
                victorias_color[g] += 1

            bot_ganador = p.get("equipos", {}).get(g, "desconocido")
            victorias_bot[bot_ganador] = victorias_bot.get(bot_ganador, 0) + 1

            mot = p.get("motivo", "juego")
            motivos[mot] = motivos.get(mot, 0) + 1

            jugadas_totales += p.get("jugadas_totales", 0)
            ataques_totales += p.get("ataques_totales", 0)

            for paso in p.get("historial", []):
                if paso.get("es_ataque"):
                    if paso.get("gana_ataque"):
                        ataques_ganados += 1

    return {
        "partidas_totales": total,
        "victorias_color": victorias_color,
        "victorias_bot": victorias_bot,
        "motivos": motivos,
        "promedio_jugadas": round(jugadas_totales / max(1, total), 2),
        "promedio_ataques": round(ataques_totales / max(1, total), 2),
        "tasa_ataques_exitosos": round(ataques_ganados / max(1, ataques_totales), 4),
    }


def analizar_pesos() -> dict:
    ruta_aprendiz = RAIZ / "estudiantes/mc_aprendiz/pesos.json"
    ruta_genetico = RAIZ / "estudiantes/mc_genetico/pesos.json"

    pesos_ap = json.loads(ruta_aprendiz.read_text()) if ruta_aprendiz.is_file() else {}
    pesos_gen = json.loads(ruta_genetico.read_text()) if ruta_genetico.is_file() else {}

    return {
        "pesos_mc_aprendiz": pesos_ap,
        "pesos_mc_genetico": pesos_gen,
    }


def main():
    parser = argparse.ArgumentParser(description="Análisis de datos y modelos.")
    parser.add_argument("--partidas", type=str, default="datos/partidas/partidas.jsonl")
    args = parser.parse_args()

    ruta = RAIZ / args.partidas
    print("==================================================")
    print("ANÁLISIS DE DATOS DE PARTIDAS")
    print("==================================================")
    stats = analizar_partidas(ruta)
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n==================================================")
    print("COMPARACIÓN DE PESOS ACTUALES")
    print("==================================================")
    pesos = analizar_pesos()
    for k, v in pesos.items():
        print(f"\n{k}:")
        for pk, pv in v.items():
            print(f"  {pk}: {pv}")


if __name__ == "__main__":
    main()
