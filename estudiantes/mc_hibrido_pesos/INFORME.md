# Informe: mc_hibrido

## 1. Integrantes
Iker Aboitiz (000294939) y Regina Cortes (000206138). Variante experimental del equipo `torneo_equipou`.

## 2. Idea en un párrafo
Combinamos Monte Carlo con una búsqueda corta que mira nuestra jugada y la respuesta del
rival. Los ataques se tratan como nodos de azar (expectiminimax). Lo que queda fuera de esa
ventana se estima con heurística y simulaciones al azar.

## 3. Búsqueda (algoritmo y por qué)
Expectiminimax de profundidad 2 con ramificación limitada: en cada turno solo se expanden las
`CANDIDATAS` jugadas mejor ordenadas (anotar, ataques con p alta, avance). En un ataque el
valor es `p * V(gana) + (1-p) * V(pierde)`. En las hojas, `simular_al_azar`. Maximizamos
nuestro color y minimizamos el del rival. Sirve para no ignorar respuestas obvias que el Monte
Carlo plano tarda en ver.

## 4. Función de evaluación
En las hojas: mezcla `PESO_HEUR * heurística + (1-PESO_HEUR) * simulaciones`. La heurística es
una sigmoide de puntos, número de peones y avance medio. Ordena también las candidatas de cada
nodo.

## 5. Precomputación (qué y cómo regenerarla)
Nada en `data/`. En `preparar` se calienta numba.

## 6. Manejo del reloj
Reserva del 30 %. Cada turno usa `1/18` del tiempo disponible (la búsqueda es más pesada que
un Monte Carlo plano). Si el reloj se acaba a mitad del árbol, las hojas restantes usan solo
# Informe: mc_hibrido_pesos

## 1. Integrantes
Iker Aboitiz (000294939) y Regina Cortes (000206138). Variante experimental del equipo `torneo_equipou`.

## 2. Idea en un párrafo
Combinamos Monte Carlo con una búsqueda corta que mira nuestra jugada y la respuesta del rival. Los ataques se tratan como nodos de azar (expectiminimax). Lo que queda fuera de esa ventana se estima con heurística y simulaciones al azar.

## 3. Búsqueda (algoritmo y por qué)
Expectiminimax de profundidad 2 con ramificación limitada: en cada turno solo se expanden las `CANDIDATAS` jugadas mejor ordenadas (anotar, ataques con p alta, avance). En un ataque el valor es `p * V(gana) + (1-p) * V(pierde)`. En las hojas, `simular_al_azar`. Maximizamos nuestro color y minimizamos el del rival. Sirve para no ignorar respuestas obvias que el Monte Carlo plano tarda en ver.

## 4. Función de evaluación
Esta variante experimental utiliza seis características ponderadas:

| Característica | Peso |
|---|---:|
| Diferencia de puntos | 1.391 |
| Diferencia de peones | 0.400 |
| Avance promedio | 0.586 |
| Avance máximo | 0.683 |
| Amenaza de anotación | 0.495 |
| Control del centro | 0.217 |

Las características se calculan a partir de los puntos, cantidad de peones, progreso de las piezas, proximidad a la anotación y ocupación de las columnas centrales. La suma ponderada se transforma mediante una función sigmoide para obtener una evaluación entre 0 y 1.

Estos coeficientes se probaron como una alternativa a la heurística original. Las definiciones y normalizaciones de las características corresponden a esta implementación experimental.

## 5. Precomputación (qué y cómo regenerarla)
Nada en `data/`. En `preparar` se calienta numba.

## 6. Manejo del reloj
Reserva del 30 %. Cada turno usa `1/18` del tiempo disponible (la búsqueda es más pesada que un Monte Carlo plano). Si el reloj se acaba a mitad del árbol, las hojas restantes usan solo la heurística.

## 7. Resultados experimentales
Se comparó `mc_hibrido_pesos` contra `mc_hibrido`, alternando los colores en cada partida.

| Partidas | Semilla | mc_hibrido | mc_hibrido_pesos |
|---:|---:|---:|---:|
| 10 | 43853 | 6 | 4 |
| 30 | 839267 | 13 | 17 |
| 100 | 756657 | 48 | 52 |
| **Total** | — | **67** | **73** |

En las 140 partidas, la variante experimental obtuvo 73 victorias (52.1 %), mientras que la estrategia original obtuvo 67 (47.9 %).

Los resultados muestran una ventaja preliminar de la variante experimental, pero no son suficientes para afirmar que los nuevos pesos producen una mejora estadísticamente significativa.

Comando de prueba:

`./torneo jugar mc_hibrido mc_hibrido_pesos --sin-docker --partidas 100`

## 8. Qué intentamos y no funcionó
Profundidad 3 con muchas candidatas explota el árbol por los nodos de azar. Por eso recortamos a 5 jugadas por nodo y profundidad 2.

La primera prueba de los nuevos pesos, con 10 partidas, favoreció a la estrategia original. En las pruebas posteriores de 30 y 100 partidas, la variante experimental obtuvo más victorias.

## 9. Fuentes y uso de IA
Expectiminimax (Russell y Norvig). Monte Carlo en las hojas como en el participante `montecarlo` del curso. Implementado con un agente de IA según la idea del equipo.
