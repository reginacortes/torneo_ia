# Informe: mc_azar

## 1. Integrantes
Iker Aboitiz (000294939) y Regina Cortes (000206138). Variante experimental del equipo `torneo_equipou`.

## 2. Idea en un párrafo
Cuando una jugada es un ataque, no sorteamos un único resultado. Pedimos al motor las dos
continuaciones (ganar y perder) con su probabilidad real, evaluamos cada una y las combinamos
en un valor esperado. Esa estimación se mezcla con una tanda de partidas completas desde un
hijo sorteado, para no perder la señal de simulaciones largas.

## 3. Búsqueda (algoritmo y por qué)
Monte Carlo de un ply sobre la lista legal, pero el nodo de azar se trata de forma explícita:
`estado.siguiente(j)` da `[(p, gana), (1-p, pierde)]`. Cada hoja se mide con una heurística
(opcionalmente un ply extra) y con `simular_al_azar`. Elegimos la jugada de mayor puntaje
mezclado. Si una jugada gana con los dos resultados del dado, la tomamos al instante.

## 4. Función de evaluación
Sigmoide de (diferencia de puntos, material y avance medio hacia la última fila). En las hojas
se mezcla con la fracción de victorias de las simulaciones posteriores al ataque
(`PESO_EVAL_POST`). `PESO_EV` controla cuánto cuenta ese valor esperado frente a partidas
completas desde un resultado sorteado.

## 5. Precomputación (qué y cómo regenerarla)
Nada en `data/`. En `preparar` solo se calienta numba con una simulación de prueba.

## 6. Manejo del reloj
Reserva del 30 % del reloj inicial. El resto se reparte como `1/25` del tiempo disponible por
turno. Si se acaba el presupuesto, las jugadas que faltan se puntúan solo con el valor esperado
heurístico, sin más simulaciones.

## 7. Resultados vs random y montecarlo
Aún no medimos esta variante en serie larga. Para comparar: `./torneo jugar mc_azar montecarlo`
y `./torneo jugar mc_azar random`.

## 8. Qué intentamos y no funcionó
Es la primera versión del modelo. El ply extra de evaluación puede ser caro si hay muchos
ataques; por eso limitamos candidatas en profundidad.

## 9. Fuentes y uso de IA
Russell y Norvig, expectiminimax en juegos con azar. Motor del curso (`estado.siguiente`).
Código escrito con ayuda de un agente de IA a partir de la especificación del equipo.
