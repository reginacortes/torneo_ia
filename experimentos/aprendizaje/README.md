# Sistema de Aprendizaje y Optimización para `mc_aprendiz`

Este directorio contiene el pipeline reproducible de registro de partidas, extracción de experiencias, entrenamiento incremental con diferencias temporales (TD(0)), optimización genética y evaluación estadística emparejada para el bot `mc_aprendiz`.

## 1. Estructura de componentes

- `registrar_partidas.py`: Ejecuta partidas reales utilizando el motor del torneo y los generadores de azar del árbitro, serializando las trayectorias completas a `datos/partidas/partidas.jsonl`.
- `preparar_datos.py`: Valida el esquema canónico, elimina partidas duplicadas deterministamente y extrae transiciones $(s, a, r, s')$ con vectores de características normalizados desde la perspectiva fija de cada jugador en `datos/experiencias/experiencias.jsonl`.
- `entrenar.py`: Algoritmo TD(0) incremental con regularización L2 y acotación de pesos para optimizar la función de valor posicional sin redes neuronales. Genera checkpoints y metadatos en `datos/modelos/checkpoints/`.
- `evaluar.py`: Enfrentamientos controlados entre variantes alternando colores (blancas y negras) con cálculo de intervalos de confianza binomiales de Wilson (95%) y métricas de reloj.
- `analizar.py`: Diagnóstico estadístico de partidas (balance de victorias por color, duración promedio, efectividad de ataques) y seguimiento de evolución de pesos.
- `optimizacion_genetica.py`: Refinamiento evolutivo (selección por torneo, cruce aritmético, mutación y elitismo) inicializado desde los pesos aprendidos por TD(0).
- `mejorar_modelo.py`: Orquestador CLI principal que ejecuta el ciclo integral de auto-mejora:
  1. Generación de partidas contra adversarios de referencia.
  2. Preparación y validación de experiencias.
  3. Entrenamiento de candidato TD(0).
  4. Evaluación emparejada contra `montecarlo`.
  5. Decisión de promoción atómica condicionada al umbral de rendimiento.

## 2. Instrucciones de uso

Todos los comandos se ejecutan desde la raíz del repositorio con el entorno virtual `.venv/` activo (`source .venv/bin/activate`).

### Ciclo completo automático
```bash
python experimentos/aprendizaje/mejorar_modelo.py --modo completo --partidas 10 --partidas-eval 10 --reloj 2.0 --semilla 20261029 --umbral 0.50
```

### Ejecución de fases individuales

1. **Registrar partidas:**
```bash
python experimentos/aprendizaje/registrar_partidas.py --bot1 montecarlo --bot2 random --partidas 10 --reloj 2.0 --salida datos/partidas/partidas.jsonl
```

2. **Preparar experiencias:**
```bash
python experimentos/aprendizaje/preparar_datos.py --entrada datos/partidas/partidas.jsonl --salida datos/experiencias/experiencias.jsonl
```

3. **Entrenar candidato TD(0):**
```bash
python experimentos/aprendizaje/entrenar.py --experiencias datos/experiencias/experiencias.jsonl --epocas 5 --alpha 0.01 --salida datos/modelos/modelo_candidato.json
```

4. **Evaluar candidato vs Monte Carlo:**
```bash
python experimentos/aprendizaje/evaluar.py --bot-a mc_aprendiz --bot-b montecarlo --partidas 8 --reloj 2.0
```

5. **Análisis exploratorio:**
```bash
python experimentos/aprendizaje/analizar.py
```

6. **Optimización genética:**
```bash
python experimentos/aprendizaje/optimizacion_genetica.py --poblacion 6 --generaciones 3 --partidas 4 --reloj 1.5
```

## 3. Política de promoción y versionado

Para evitar que el aprendizaje degrade la fuerza de juego del bot:
1. Ningún entrenamiento modifica directamente los archivos en producción durante la partida (en `jugar(...)` la carpeta es de solo lectura).
2. Todo nuevo entrenamiento produce un artefacto candidato independiente (`modelo_candidato.json`).
3. La promoción a modelo estable (`estudiantes/mc_aprendiz/pesos.json`) exige superar una serie de evaluación emparejada frente a la línea base con alternancia rigurosa de colores y sin fallos de reloj.
4. Cada ciclo queda auditado con fecha, semillas y métricas en `datos/modelos/historial_modelos.jsonl`.
