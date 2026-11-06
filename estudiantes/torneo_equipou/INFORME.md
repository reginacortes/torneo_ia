# Informe técnico — torneo_equipou

## 1. Integrantes

- Iker Aboitiz
- Regina Cortes

## 2. Descripción general

`torneo_equipou` implementa una estrategia de Monte Carlo con selección adaptativa de jugadas mediante el algoritmo UCB1 (Upper Confidence Bound 1).

El objetivo es elegir movimientos que maximicen la probabilidad estimada de victoria. A diferencia del Monte Carlo plano, que distribuye las simulaciones uniformemente, esta implementación utiliza los resultados obtenidos para decidir qué jugadas conviene explorar con mayor frecuencia.

## 3. Algoritmo de selección de jugadas

Primero se generan todas las jugadas legales del estado actual.

Antes de iniciar las simulaciones, el bot comprueba si existe una jugada cuyos posibles resultados de combate conducen siempre a una victoria inmediata. Si encuentra una, la selecciona directamente.

En caso contrario, comienza el proceso de búsqueda:

1. Cada jugada legal recibe al menos una muestra.
2. Se selecciona un resultado posible de la jugada utilizando las probabilidades de los ataques proporcionadas por el motor.
3. Desde el estado resultante se ejecutan 20 partidas simuladas.
4. Se acumula el resultado obtenido y se actualiza el número de muestras de esa jugada.
5. Una vez exploradas todas las jugadas, se utiliza UCB1 para seleccionar las siguientes muestras.

La búsqueda continúa hasta alcanzar el límite de tiempo disponible.

## 4. Función de evaluación

La función de evaluación se basa en la fracción de partidas ganadas por el color del bot.

El motor proporciona la función `simular_al_azar`, que ejecuta partidas desde un estado determinado. Ambos jugadores seleccionan movimientos aleatoriamente y los ataques se resuelven según sus probabilidades correspondientes.

El resultado se encuentra entre 0 y 1:

- 1: todas las partidas simuladas fueron ganadas por nuestro color.
- 0: ninguna partida simulada fue ganada por nuestro color.
- Valores intermedios: proporción de victorias obtenidas.

El bot acumula estos resultados para calcular el promedio de cada jugada.

## 5. Selección mediante UCB1

UCB1 permite equilibrar dos objetivos:

- **Exploración:** probar jugadas que todavía tienen pocas muestras.
- **Explotación:** favorecer jugadas que han obtenido buenos resultados promedio.

La puntuación utilizada es:

\[
UCB1(j)=\frac{W_j}{N_j}+
\sqrt{\frac{2\ln(T)}{N_j}}
\]

Donde:

- \(W_j\): suma de los resultados de las simulaciones de la jugada.
- \(N_j\): número de muestras de esa jugada.
- \(T\): número total de muestras realizadas.

El primer término representa el rendimiento promedio y el segundo favorece alternativas menos exploradas.

Al finalizar la búsqueda, se selecciona la jugada con el mayor promedio de resultados, no necesariamente la que tenga el mayor valor UCB1.

## 6. Parámetros y manejo del tiempo

Los principales parámetros definidos en `strategy.py` son:

| Parámetro | Valor | Función |
|---|---:|---|
| `SIMULACIONES` | 20 | Partidas aleatorias por muestra. |
| `RESERVA` | 0.3 | Fracción del reloj inicial reservada. |
| Divisor del tiempo | 25 | Determina el presupuesto de búsqueda a partir del tiempo disponible. |

Durante `preparar`, se ejecuta una simulación inicial para calentar Numba y evitar que su primera compilación consuma tiempo durante la selección de movimientos.

En cada turno se calcula el tiempo disponible descontando la reserva. Si ya no queda tiempo para pensar, el bot selecciona una jugada legal aleatoria.

La búsqueda revisa el reloj después de cada muestra, una vez que todas las jugadas legales han sido exploradas al menos una vez.

## 7. Reproducibilidad

El bot inicializa un generador aleatorio con la semilla proporcionada por la configuración del torneo.

Las simulaciones también reciben semillas generadas a partir de dicho generador. Esto permite que una misma configuración inicial y las mismas condiciones de ejecución produzcan resultados reproducibles.

## 8. Limitaciones y trabajo futuro

La estrategia presenta algunas limitaciones:

- Las partidas simuladas utilizan decisiones aleatorias, por lo que no anticipan necesariamente respuestas estratégicas del oponente.
- La calidad de las estimaciones depende del número de simulaciones realizadas.
- El algoritmo UCB1 equilibra exploración y explotación, pero no garantiza encontrar la mejor jugada.
- El tiempo disponible puede limitar la cantidad de muestras y afectar la precisión de las estimaciones.
- No se ha realizado todavía una comparación experimental suficientemente amplia para afirmar que esta estrategia supera a otras implementaciones.

Como trabajo futuro se propone experimentar con distintas cantidades de simulaciones, mejorar la política de selección de movimientos durante las partidas simuladas y comparar el rendimiento frente a diferentes estrategias.

## 9. Fuentes y herramientas

- Browne et al. (2012). *A Survey of Monte Carlo Tree Search Methods*. IEEE Transactions on Computational Intelligence and AI in Games.
- Auer, P., Cesa-Bianchi, N. y Fischer, P. (2002). *Finite-time Analysis of the Multiarmed Bandit Problem*. Machine Learning.
- Motor del torneo Breakthrough: funciones de generación de jugadas, resolución probabilística de ataques y simulación de partidas aleatorias.

La implementación utiliza Python y las funciones proporcionadas por el motor del torneo.
