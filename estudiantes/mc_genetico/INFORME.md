# Informe — mc_genetico

## 1. Descripción del bot
`mc_genetico` es una variante del bot híbrido de Breakthrough. Mantiene la selección de jugadas mediante simulaciones y permite modificar los pesos de su evaluación heurística.

## 2. Objetivo
Explorar si ajustar los pesos de la evaluación mejora el rendimiento frente al bot de referencia `montecarlo`.

## 3. Representación del estado
El bot utiliza el estado proporcionado por el motor, incluyendo los puntos, las piezas de cada jugador y las jugadas legales disponibles.

## 4. Generación y selección de jugadas
El bot examina las jugadas legales y utiliza la lógica de búsqueda y simulación heredada de `mc_hibrido` para valorar sus consecuencias.

## 5. Evaluación heurística
La evaluación combina tres factores: diferencia de puntos, diferencia en el número de peones y diferencia en el avance de las piezas. Los pesos de estos factores son configurables.

## 6. Algoritmo genético
Un programa externo genera configuraciones de pesos, evalúa cada candidato mediante partidas y utiliza selección, cruce y mutación para producir nuevas configuraciones.

## 7. Función de aptitud
Durante el experimento se utiliza la proporción de resultados favorables frente a `montecarlo`, contando un empate como media victoria cuando el motor devuelve un resultado de empate.

## 8. Parámetros y experimentación
Los experimentos utilizan una población de candidatos, varias generaciones y partidas con colores alternados. Los parámetros concretos y los resultados deben documentarse después de ejecutar el experimento.

## 9. Limitaciones y trabajo futuro
Los resultados dependen del número de partidas y de las semillas utilizadas. Para comparar los pesos con mayor fiabilidad, conviene evaluarlos con más partidas y semillas distintas, y comprobar el rendimiento frente a varios bots.

