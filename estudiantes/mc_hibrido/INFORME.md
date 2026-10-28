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
la heurística.

## 7. Resultados vs random y montecarlo
Todavía no hay serie estadística. Comando de prueba: `./torneo jugar mc_hibrido montecarlo`.

## 8. Qué intentamos y no funcionó
Profundidad 3 con muchas candidatas explota el árbol por los nodos de azar. Por eso recortamos
a 5 jugadas por nodo y profundidad 2.

## 9. Fuentes y uso de IA
Expectiminimax (Russell y Norvig). Monte Carlo en las hojas como en el participante
`montecarlo` del curso. Implementado con un agente de IA según la idea del equipo.
