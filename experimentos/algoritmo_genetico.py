
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "sistema"))

from herramientas.calibrar import serie

ARCHIVO_PESOS = RAIZ / "estudiantes/mc_genetico/pesos.json"
ARCHIVO_MEJOR = RAIZ / "experimentos/mejores_pesos.json"

# Primera búsqueda: pequeña y relativamente económica.
POBLACION = 8
GENERACIONES = 4
PARTIDAS_POR_CANDIDATO = 4
RELOJ_S = 2.0
SEMILLA = 20261028

# Límites de búsqueda de cada peso.
LIMITES = (
    (0.5, 4.0),    # Diferencia de puntos
    (0.0, 0.25),   # Diferencia de peones
    (0.0, 0.60),   # Diferencia de avance
)

INICIAL = (1.7, 0.07, 0.22)


def guardar_pesos(individuo, ruta=ARCHIVO_PESOS):
    datos = {
        "puntos": round(individuo[0], 6),
        "peones": round(individuo[1], 6),
        "avance": round(individuo[2], 6),
    }
    ruta.write_text(json.dumps(datos, indent=2) + "\n")


def individuo_aleatorio(rng):
    return tuple(rng.uniform(a, b) for a, b in LIMITES)


def limitar(individuo):
    return tuple(
        max(a, min(b, x))
        for x, (a, b) in zip(individuo, LIMITES)
    )


def evaluar(individuo, semilla):
    guardar_pesos(individuo)

    resultados = serie(
        ("mc_genetico", "montecarlo"),
        PARTIDAS_POR_CANDIDATO,
        RELOJ_S,
        semilla,
    )

    victorias = 0
    empates = 0

    for i, resultado in enumerate(resultados):
        # El candidato juega con blancas en partidas pares
        # y con negras en partidas impares.
        color_candidato = "blancas" if i % 2 == 0 else "negras"

        if resultado.ganador == color_candidato:
            victorias += 1
        elif resultado.ganador not in ("blancas", "negras"):
            empates += 1

    # El motor normalmente termina con un ganador.
    # Las victorias pesan más que cualquier criterio secundario.
    fitness = (victorias + 0.5 * empates) / len(resultados)
    return fitness, victorias, len(resultados)


def seleccion_torneo(poblacion, fitnesses, rng, k=3):
    indices = rng.sample(range(len(poblacion)), min(k, len(poblacion)))
    mejor = max(indices, key=lambda i: fitnesses[i])
    return poblacion[mejor]


def cruzar(a, b, rng):
    hijo = []
    for x, y in zip(a, b):
        alpha = rng.random()
        hijo.append(alpha * x + (1.0 - alpha) * y)
    return limitar(hijo)


def mutar(individuo, rng, prob=0.30):
    hijo = list(individuo)

    for i, (a, b) in enumerate(LIMITES):
        if rng.random() < prob:
            sigma = 0.12 * (b - a)
            hijo[i] += rng.gauss(0.0, sigma)

    return limitar(hijo)


def main():
    rng = random.Random(SEMILLA)

    poblacion = [INICIAL]
    poblacion.extend(
        individuo_aleatorio(rng)
        for _ in range(POBLACION - 1)
    )

    mejor_global = None
    fitness_global = -1.0

    for generacion in range(GENERACIONES):
        print(f"\nGeneración {generacion + 1}/{GENERACIONES}")
        fitnesses = []

        # Mismas semillas dentro de una generación para comparar
        # candidatos en condiciones similares.
        semilla = SEMILLA + generacion * 10000

        for i, individuo in enumerate(poblacion):
            fitness, ganadas, total = evaluar(individuo, semilla)
            fitnesses.append(fitness)

            print(
                f"  {i + 1:02d}: pesos={tuple(round(x, 4) for x in individuo)}"
                f" | victorias={ganadas}/{total}"
                f" | fitness={fitness:.3f}"
            )

            if fitness > fitness_global:
                fitness_global = fitness
                mejor_global = individuo

                guardar_pesos(mejor_global, ARCHIVO_MEJOR)
                guardar_pesos(mejor_global)

        # Elitismo: conservar el mejor individuo de esta generación.
        indice_mejor = max(
            range(len(poblacion)),
            key=lambda i: fitnesses[i],
        )
        nueva = [poblacion[indice_mejor]]

        while len(nueva) < POBLACION:
            padre1 = seleccion_torneo(poblacion, fitnesses, rng)
            padre2 = seleccion_torneo(poblacion, fitnesses, rng)
            hijo = cruzar(padre1, padre2, rng)
            hijo = mutar(hijo, rng)
            nueva.append(hijo)

        poblacion = nueva

    # Dejar cargados los mejores pesos encontrados.
    guardar_pesos(mejor_global)
    guardar_pesos(mejor_global, ARCHIVO_MEJOR)

    print("\nMejores pesos encontrados:")
    print(json.dumps({
        "puntos": round(mejor_global[0], 6),
        "peones": round(mejor_global[1], 6),
        "avance": round(mejor_global[2], 6),
        "fitness_entrenamiento": fitness_global,
    }, indent=2))
    print(f"\nGuardados en: {ARCHIVO_MEJOR}")


if __name__ == "__main__":
    main()

