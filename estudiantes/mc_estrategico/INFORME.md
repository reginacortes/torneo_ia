# Informe del bot `mc_estrategico`

## 1. Resumen
El bot `mc_estrategico` amplía el paradigma de Monte Carlo enriqueciendo la función de evaluación en las hojas del árbol mediante un vector multidimensional de características posicionales. Mientras que los modelos convencionales se limitan a contabilizar peones y avance lineal, `mc_estrategico` incorpora factores geométricos como la protección mutua en diagonal, la exposición a ataques frontales rivales, la amenaza directa de coronación y el dominio central del tablero.

## 2. Reglas y representación
Se opera directamente sobre las instancias inmutables de `Estado` y `Jugada` provistas por el motor del torneo. Las consultas de casillas y estados se realizan a través de `estado.piezas(color)` y `estado.puntos`. Las coordenadas se transforman internamente en tuplas `(fila, col)` para computar avances y diagonales relativas. Todas las evaluaciones y decisiones se anclan estrictamente al color asignado en `config.color` durante la llamada a `preparar`.

## 3. Búsqueda (algoritmo y por qué)
Se adopta una búsqueda de expectativa de un nivel (depth-1 expectiminimax) combinada con evaluación híbrida en los estados resultantes. Las jugadas legales son preordenadas según criterios tácticos primarios (anotación inmediata, probabilidad de captura favorable y avance neto). Para cada jugada candidata se recorren los desenlaces probabilísticos del motor, computando su valor esperado. Las hojas que no son terminales se evalúan mediante una combinación convexa:
$$V(s) = \lambda \cdot \text{Heur}(s) + (1 - \lambda) \cdot \text{MC}(s)$$
con $\lambda = 0.45$, unificando la intuición posicional con la robustez empírica de rollouts al azar.

## 4. Heurística (o evaluación de estados)
La función de evaluación estratégica evalúa de forma balanceada ocho dimensiones:
1. Diferencia de puntos anotados ($W = 2.10$).
2. Diferencia de peones supervivientes ($W = 0.08$).
3. Avance promedio hacia la fila meta ($W = 0.50$).
4. Avance máximo de los peones más adelantados ($W = 0.35$).
5. Amenaza inminente de anotación en fila 8/9 ($W = 0.40$).
6. Estructura de apoyo diagonal entre peones propios ($W = 0.15$).
7. Exposición y vulnerabilidad ante ataques rivales ($W = 0.20$).
8. Control territorial de las columnas centrales c a g ($W = 0.10$).
El puntaje combinado se proyecta al intervalo $[0, 1]$ mediante una transformación logística sigmoide.

## 5. Azar y probabilidades
Los ataques no se muestrean arbitrariamente; en su lugar, se invoca `estado.siguiente(j)`, la cual devuelve exactamente los pares `(probabilidad, estado_hijo)` calculados por las reglas del motor. El valor asignado a la jugada es la suma ponderada exacta de los valores de las hojas, respetando la expectativa matemática real del juego.

## 6. Control del tiempo
Se reserva un 30% del reloj asignado para mitigar fluctuaciones del sistema y costos de serialización de procesos. El tiempo disponible restante se distribuye asignando un límite por turno (`disponible / 25.0`). El ordenamiento previo de candidatas garantiza que, si el reloj interrumpe la iteración, las jugadas más prometedoras ya han sido simuladas exhaustivamente, y las restantes reciben una estimación rápida con la heurística directa.

## 7. Experimentos y resultados
En pruebas locales de validación contra el bot de referencia `random`, `mc_estrategico` superó ambas partidas de humo con un margen contundente y sin incidencias de tiempo. En series comparativas frente a `montecarlo`, la evaluación estratégica permitió al bot mantener cadenas de peones cohesivas y bloquear tempranamente incursiones veloces del adversario, demostrando una notable superioridad posicional en el juego medio.

## 8. Trabajo en equipo
El equipo estructuró el trabajo en dos vertientes: diseño y calibración analítica de los pesos heurísticos y métricas de soporte geométrico, seguido por la implementación de la búsqueda con expectation pooling y la verificación estricta contra las restricciones del validador del torneo.

## 9. Conclusiones y trabajo futuro
La evaluación estratégica multidimensional dota al bot de una dirección táctica mucho más coherente que el Monte Carlo puro. Las siguientes etapas contemplan la integración de pesos aprendidos dinámicamente mediante diferencias temporales (TD(0)) y la incorporación de tablas de transposición con sustitución temporal para reutilizar evaluaciones entre turnos consecutivos.
