"""Optimización genética de hiperparámetros y pesos estratégicos para `mc_aprendiz`.

Complementa el aprendizaje TD(0) explorando el espacio continuo de pesos
mediante algoritmos evolutivos (población, torneo, cruce aritmético, mutación y elitismo).
"""

from __future__ import annotations

import argparse
import datetime
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from estudiantes.compartido.caracteristicas import NOMBRES_CARACTERISTICAS
from experimentos.aprendizaje.entrenar import LIMITES_PESOS
from experimentos.aprendizaje.evaluar import evaluar_enfrentamiento

ARCHIVO_PESOS_APRENDIZ = RAIZ / "estudiantes/mc_aprendiz/pesos.json"


def cargar_pesos_base() -> dict[str, float]:
    if ARCHIVO_PESOS_APRENDIZ.is_file():
        try:
            return json.loads(ARCHIVO_PESOS_APRENDIZ.read_text())
        except Exception:
            pass
    from estudiantes.compartido.evaluacion import PESOS_DEFECTO
    return dict(PESOS_DEFECTO)


def individuo_a_dict(ind: list[float]) -> dict[str, float]:
    return {NOMBRES_CARACTERISTICAS[i]: round(ind[i], 6) for i in range(len(NOMBRES_CARACTERISTICAS))}


def dict_a_individuo(d: dict[str, float]) -> list[float]:
    return [d.get(k, 0.2) for k in NOMBRES_CARACTERISTICAS]


def limitar_individuo(ind: list[float]) -> list[float]:
    clipeado = []
    for i, val in enumerate(ind):
        nom = NOMBRES_CARACTERISTICAS[i]
        min_v, max_v = LIMITES_PESOS.get(nom, (0.0, 5.0))
        clipeado.append(max(min_v, min(max_v, val)))
    return clipeado


def mutar(ind: list[float], rng: random.Random, prob: float = 0.25, sigma_factor: float = 0.08) -> list[float]:
    hijo = list(ind)
    for i, val in enumerate(hijo):
        if rng.random() < prob:
            nom = NOMBRES_CARACTERISTICAS[i]
            min_v, max_v = LIMITES_PESOS.get(nom, (0.0, 5.0))
            sigma = (max_v - min_v) * sigma_factor
            hijo[i] = val + rng.gauss(0, sigma)
    return limitar_individuo(hijo)


def cruzar(ind1: list[float], ind2: list[float], rng: random.Random) -> list[float]:
    # Cruce BLX-alpha o interpolación lineal aleatoria
    alpha = rng.random()
    hijo = [alpha * a + (1.0 - alpha) * b for a, b in zip(ind1, ind2)]
    return limitar_individuo(hijo)


def seleccion_torneo(poblacion: list[list[float]], fitnesses: list[float], rng: random.Random, k: int = 3) -> list[float]:
    indices = rng.sample(range(len(poblacion)), min(k, len(poblacion)))
    mejor_idx = max(indices, key=lambda idx: fitnesses[idx])
    return list(poblacion[mejor_idx])


def evaluar_candidato(
    ind: list[float],
    adversario: str,
    partidas: int,
    reloj_s: float,
    semilla: int,
) -> float:
    # Escribimos temporalmente los pesos en mc_aprendiz para evaluarlo
    pesos_dict = individuo_a_dict(ind)
    backup = ARCHIVO_PESOS_APRENDIZ.read_text() if ARCHIVO_PESOS_APRENDIZ.is_file() else None
    try:
        ARCHIVO_PESOS_APRENDIZ.write_text(json.dumps(pesos_dict, indent=2) + "\n")
        res = evaluar_enfrentamiento(
            "mc_aprendiz",
            adversario,
            partidas=partidas,
            reloj_s=reloj_s,
            semilla=semilla,
        )
        return float(res["tasa_a"])
    finally:
        if backup is not None:
            ARCHIVO_PESOS_APRENDIZ.write_text(backup)


def optimizar(
    poblacion_tam: int = 4,
    generaciones: int = 2,
    partidas_por_eval: int = 2,
    reloj_s: float = 1.5,
    semilla: int = 20261029,
    adversario: str = "montecarlo",
) -> tuple[dict[str, float], float]:
    rng = random.Random(semilla)
    base_dict = cargar_pesos_base()
    base_ind = dict_a_individuo(base_dict)

    print(f"Inicializando población de {poblacion_tam} individuos alrededor del modelo base...")
    poblacion = [base_ind]
    for _ in range(poblacion_tam - 1):
        poblacion.append(mutar(base_ind, rng, prob=0.4, sigma_factor=0.15))

    mejor_global = base_ind
    mejor_fitness = -1.0

    for gen in range(generaciones):
        print(f"\n--- Generación {gen + 1}/{generaciones} ---")
        fitnesses = []
        for idx, ind in enumerate(poblacion):
            fit = evaluar_candidato(ind, adversario, partidas_por_eval, reloj_s, semilla + gen * 100 + idx)
            fitnesses.append(fit)
            print(f"  Individuo {idx + 1}: Winrate = {fit * 100:.1f}%")

            if fit > mejor_fitness:
                mejor_fitness = fit
                mejor_global = list(ind)

        # Elitismo: preservamos al mejor
        nueva_poblacion = [mejor_global]
        while len(nueva_poblacion) < poblacion_tam:
            p1 = seleccion_torneo(poblacion, fitnesses, rng)
            p2 = seleccion_torneo(poblacion, fitnesses, rng)
            hijo = cruzar(p1, p2, rng)
            hijo_mutado = mutar(hijo, rng)
            nueva_poblacion.append(hijo_mutado)

        poblacion = nueva_poblacion

    mejor_pesos = individuo_a_dict(mejor_global)
    return mejor_pesos, mejor_fitness


def main():
    parser = argparse.ArgumentParser(description="Algoritmo genético para afinar pesos de mc_aprendiz.")
    parser.add_argument("--poblacion", type=int, default=4)
    parser.add_argument("--generaciones", type=int, default=2)
    parser.add_argument("--partidas", type=int, default=2)
    parser.add_argument("--reloj", type=float, default=1.5)
    parser.add_argument("--semilla", type=int, default=20261029)
    parser.add_argument("--adversario", type=str, default="montecarlo")
    parser.add_argument("--salida", type=str, default="datos/modelos/modelo_genetico.json")
    args = parser.parse_args()

    print("Iniciando optimización genética...")
    pesos, fit = optimizar(
        poblacion_tam=args.poblacion,
        generaciones=args.generaciones,
        partidas_por_eval=args.partidas,
        reloj_s=args.reloj,
        semilla=args.semilla,
        adversario=args.adversario,
    )

    salida_p = RAIZ / args.salida
    salida_p.parent.mkdir(parents=True, exist_ok=True)
    salida_p.write_text(json.dumps(pesos, indent=2) + "\n")
    print(f"\nMejor individuo genético guardado en {salida_p} con fitness={fit:.2f}")


if __name__ == "__main__":
    main()
