# Catálogo de estrategias — Torneo IA Breakthrough

Este documento presenta las estrategias implementadas para el torneo de Breakthrough, sus principales características y los algoritmos utilizados para seleccionar jugadas.

## 1. Estrategias de referencia

| Bot | Algoritmo | Descripción |
|---|---|---|
| `random` | Selección aleatoria | Elige una jugada legal al azar, sin evaluar la posición. |
| `montecarlo` | Monte Carlo plano | Simula partidas desde cada jugada candidata y selecciona la que obtiene el mejor resultado promedio. |

## 2. Estrategias desarrolladas

| Bot | Técnica principal | Descripción |
|---|---|---|
| `mc_azar` | Expectativa matemática + Monte Carlo | Evalúa los posibles resultados de los ataques usando sus probabilidades y combina esa información con simulaciones. |
| `mc_cache` | Monte Carlo + caché | Almacena evaluaciones de estados para reutilizarlas y evitar simulaciones redundantes. |
| `mc_heuristica` | Monte Carlo guiado por heurísticas | Utiliza reglas estratégicas para orientar las jugadas durante las simulaciones. |
| `mc_hibrido` | Expectiminimax + Monte Carlo | Explora las jugadas propias y las respuestas del rival, considera los resultados probabilísticos de los ataques y evalúa las posiciones resultantes. |
| `mc_genetico` | Monte Carlo + heurística parametrizable | Utiliza la lógica de búsqueda y simulación de `mc_hibrido`; un programa externo optimiza los pesos de su evaluación mediante un algoritmo genético. |
| `mc_estrategico` | Evaluación posicional | Considera factores como protección de peones, exposición a ataques, amenaza de anotación y control del centro. |
| `mc_ucb1` | UCB1 + Monte Carlo | Distribuye las simulaciones entre las jugadas candidatas equilibrando exploración y aprovechamiento de las mejores alternativas. |
| `mc_aprendiz` | Arquitectura híbrida con aprendizaje | Combina UCB1, búsqueda expectiminimax, evaluación posicional, aprendizaje TD(0), optimización genética y caché de transposición. |
| `mc_hibrido_pesos` | Expectiminimax + evaluación heurística ponderada | Variante experimental de `mc_hibrido` que modifica los pesos de las características de evaluación. |

## 3. Conceptos algorítmicos principales

- **Monte Carlo:** estima la calidad de una jugada mediante múltiples simulaciones de posibles partidas.
- **Expectiminimax:** extiende la búsqueda minimax para considerar eventos aleatorios, como los resultados de los ataques.
- **UCB1:** selecciona alternativas utilizando tanto sus resultados promedio como la incertidumbre asociada a las que se han explorado menos.
- **Algoritmos genéticos:** optimizan parámetros mediante selección, cruce y mutación de candidatos.
- **Funciones heurísticas:** aproximan la calidad de una posición utilizando características estratégicas del tablero.
- **TD(0):** método de aprendizaje por diferencias temporales que actualiza estimaciones a partir de la diferencia entre predicciones sucesivas.
- **Caché de transposición:** permite reutilizar información de posiciones que ya fueron evaluadas.

## 4. Documentación técnica

Cada estrategia cuenta con su propio directorio dentro de `estudiantes/`, donde se encuentran su implementación (`strategy.py`), configuración (`equipo.toml`) e informe técnico (`INFORME.md`).

Para consultar los detalles de cada implementación, experimentos y parámetros, se recomienda revisar el informe correspondiente.

## 5. Consideraciones

Las descripciones de este catálogo resumen las arquitecturas declaradas en los informes de cada bot. La presencia de una técnica en una estrategia no implica por sí sola que tenga un mejor rendimiento.

La comparación entre estrategias debe realizarse mediante torneos controlados, alternando colores y utilizando distintas semillas para reducir el efecto del azar.

