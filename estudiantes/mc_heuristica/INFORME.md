# Informe: mc_heuristica

## 1. Integrantes
Iker Aboitiz (000294939) y Regina Cortes (000206138). Variante experimental del equipo `torneo_equipou`.

## 2. Idea en un párrafo
Las rollouts no juegan con probabilidad uniforme. Durante unos plies, cada lado elige con una
política de reglas simples (avanzar, atacar con p alta, no suicidarse, no desarmar apoyos,
impedir que el rival anote). Después se deja el resto de la partida a `simular_al_azar`.

## 3. Búsqueda (algoritmo y por qué)
En la raíz recorremos las legales (priorizadas por la misma política). Para cada muestra
sorteamos el resultado del ataque y hacemos un rollout guiado de `PLIES_POLITICA` turnos.
Cada regla tiene un peso y una probabilidad de aplicarse (parámetros tipo genéticos): así se
puede variar el estilo sin reescribir el algoritmo. Elegimos la jugada con mejor promedio de
esas muestras.

## 4. Función de evaluación
El promedio de rollouts. Dentro de la política: avance hacia la meta, bonus si `p` del ataque
es alta, penalización si `p < 0.5`, penalización por mover un peón que sostiene a otro, y un
bonus fuerte si la jugada quita al rival un avance seguro a la última fila.

## 5. Precomputación (qué y cómo regenerarla)
Nada en `data/` todavía. Los pesos (`W_*`) y las `P_*` están en `strategy.py`; se podrían
ajustar offline (por ejemplo un algoritmo genético en `herramientas/`) y entonces sí
guardarlos en `data/`.

## 6. Manejo del reloj
Reserva del 30 % y `1/25` del disponible. Cada muestra es más cara que un Monte Carlo plano
porque los primeros plies corren en Python; por eso el rollout guiado es corto y la cola va
a numba.

## 7. Resultados vs random y montecarlo
Pendiente de una serie. Comparar con `./torneo jugar mc_heuristica montecarlo`.

## 8. Qué intentamos y no funcionó
Hacer toda la partida con la política en Python es demasiado lento para 30 s. Por eso cortamos
a cinco plies y el resto lo simula el motor.

## 9. Fuentes y uso de IA
Rollouts sesgados y políticas heurísticas en Monte Carlo (Browne et al., 2012). Reglas
propuestas por el equipo. Implementación con un agente de IA.
