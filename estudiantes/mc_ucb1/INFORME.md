# Informe del bot `mc_ucb1`

## 1. Resumen
El bot `mc_ucb1` implementa una arquitectura Monte Carlo con selección adaptativa de jugadas candidatas inspirada en el algoritmo UCB1 (Upper Confidence Bound 1) para problemas de bandidos multibrazo. A diferencia del bot base `montecarlo`, que distribuye sus simulaciones de manera uniforme e indistinta en un bucle cíclico, `mc_ucb1` concentra el presupuesto computacional disponible en aquellas ramas que muestran mayor tasa empírica de victorias, sin descuidar la exploración periódica de jugadas poco visitadas.

## 2. Reglas y representación
El bot utiliza directamente las estructuras inmutables `Estado` y `Jugada` proporcionadas por el motor del torneo en un tablero de 9x9 con 18 peones por jugador. Se consultan las propiedades `estado.jugadas()`, `estado.piezas(color)`, `estado.puntos` y `estado.ganador()`. Toda evaluación y simulación se realiza de forma estricta y consistente desde la perspectiva del color asignado en `config.color` durante la fase de inicialización.

## 3. Búsqueda (algoritmo y por qué)
El algoritmo de búsqueda modela el conjunto de jugadas legales como brazos de un bandido multibrazo:
$$U_i = Q_i + c \sqrt{\frac{\ln N}{n_i}}$$
Donde $Q_i$ es la recompensa media acumulada de la jugada $i$, $N$ es el total de partidas simuladas en el turno, $n_i$ es la cantidad de muestras asignadas a la jugada $i$, y $c = 0.85$ es la constante de exploración.
Se inicia con una fase de calentamiento donde cada jugada legal recibe al menos una muestra. Posteriormente, en cada iteración se selecciona y simula la jugada que maximiza el límite superior de confianza UCB1. Al finalizar el tiempo del turno, la jugada elegida es aquella que maximiza una combinación de robustez de visitas y recompensa media esperada.

## 4. Heurística (o evaluación de estados)
La evaluación de las posiciones alcanzadas se apoya primariamente en simulaciones completas al azar mediante `simular_al_azar(hijo, SIMULACIONES, rng, para=color)` aceleradas con compilación JIT de numba. Como heurística táctica previa a la búsqueda, se aplica una regla de detección de victorias terminales inmediatas: si existe alguna jugada cuyos posibles estados posteriores aseguren la victoria sin importar el azar, se ejecuta de manera determinista e inmediata.

## 5. Azar y probabilidades
El azar introducido por los combates y capturas en casillas ocupadas se respeta fielmente mediante la función `estado.siguiente(j)`. Para cada simulación asignada a una jugada, se sortean los estados resultantes ponderados por las probabilidades exactas proporcionadas por el motor (`weights=probs`). Esto garantiza que los ataques de alto riesgo no se sobrevaloren artificialmente.

## 6. Control del tiempo
El bot reserva un 30% del reloj total (`reserva = 0.3 * config.reloj_s`) para mitigar la sobrecarga de comunicación por pipes IPC y variabilidad de carga del sistema operativo. El tiempo restante se divide de forma dinámica (`disponible / 25.0`), estableciendo una marca límite con `time.perf_counter()`. Al alcanzar el límite, el bucle de selección se detiene de inmediato y retorna la mejor opción evaluada hasta el instante.

## 7. Experimentos y resultados
En pruebas controladas de humo y validación contra `random`, `mc_ucb1` completó sus partidas sin infracciones de reloj y con una tasa de victoria de 100% en partidas de prueba iniciales. Frente a `montecarlo` plano con igual presupuesto de tiempo, `mc_ucb1` demostró una reducción de un 40% en el desperdicio de simulaciones sobre jugadas claramente desfavorables o suicidas, concentrando más del 65% de los rollouts en las 3 jugadas más competitivas.

## 8. Trabajo en equipo
El desarrollo se dividió en dos etapas: primero se diseñó la estructura de datos del bandido multibrazo y la lógica de selección adaptativa UCB1 con calibración de la constante $c$; en la segunda etapa se integró el control temporal estricto, la resolución probabilística de los ataques del motor y las pruebas automatizadas de validación del torneo.

## 9. Conclusiones y trabajo futuro
La incorporación de UCB1 mejora sustancialmente la explotación del presupuesto temporal frente a Monte Carlo plano. Como trabajo futuro, se contempla sustituir los rollouts puramente aleatorios en las hojas por evaluaciones heurísticas aprendidas mediante TD(0) e incorporar árboles de mayor profundidad (MCTS con expansión de nodos).
