# Informe: mc_cache

## 1. Integrantes
Iker Aboitiz (000294939) y Regina Cortes (000206138). Variante experimental del equipo `torneo_equipou`.

## 2. Idea en un párrafo
El Monte Carlo plano vuelve a simular posiciones que ya vio en el mismo turno o en turnos
anteriores. Guardamos un promedio por `estado.clave` (tablero, turno y puntos) y lo reutilizamos
cuando hay suficientes visitas y la entrada no está vieja.

## 3. Búsqueda (algoritmo y por qué)
Igual que el Monte Carlo de un ply: recorremos las legales, muestreando el resultado de cada
ataque. Antes de simular, consultamos la tabla. Si la entrada tiene al menos `MIN_VISITAS` y
su antigüedad es ≤ `MAX_EDAD` (en turnos nuestros), usamos el promedio guardado. Si no, simulamos
y actualizamos un promedio móvil. Si la tabla llega a `MAX_TABLA`, expulsamos la entrada con
menos visitas (y la más antigua si empatan).

## 4. Función de evaluación
Fracción de victorias de `simular_al_azar`, promediada en la caché. La confianza de una
entrada es `visitas / (1 + edad)`: sirve para decidir el reemplazo y para no fiarse de
estadísticas viejas.

## 5. Precomputación (qué y cómo regenerarla)
Nada en `data/`. La tabla vive en memoria durante la partida y se borra al terminar el
proceso. En `preparar` se crea vacía y se calienta numba.

## 6. Manejo del reloj
Reserva del 30 % y `1/25` del tiempo disponible por turno, como el bot de referencia. El
ahorro viene de no repetir simulaciones, no de pensar más tiempo.

## 7. Resultados vs random y montecarlo
Sin medición larga todavía. El visor reporta `cache` (tamaño de la tabla) y `reusos`.
Probar con `./torneo jugar mc_cache montecarlo`.

## 8. Qué intentamos y no funcionó
Reutilizar con una sola visita ahorra tiempo pero mete mucho ruido: por eso exigimos tres
visitas. No guardamos entre partidas: cada partida es un proceso nuevo.

## 9. Fuentes y uso de IA
Tablas de transposición en juegos (clave de 64 bits del motor). Monte Carlo plano del
participante `montecarlo`. Código con ayuda de un agente de IA.
