"""Modelo 6: Monte Carlo con caché de posiciones.

Reutiliza estimaciones de estados ya vistos. La llave es `estado.clave`
(tablero, turno y puntos).
"""

import random
import time

from motor import Estado, reportar, simular_al_azar

RESERVA = 0.3
SIMULACIONES = 20

# Parámetros del modelo 6
MAX_TABLA = 20000  # tamaño máximo de la tabla
MIN_VISITAS = 3  # visitas mínimas para reutilizar una estimación
MAX_EDAD = 6  # jugadas nuestras desde la última actualización
# Política de reemplazo: menos visitas y, en empate, la entrada más vieja.


def preparar(config):
    global color, rng, reserva, tabla, turno_nuestro
    color = config.color
    rng = random.Random(config.semilla)
    reserva = RESERVA * config.reloj_s
    tabla = {}
    turno_nuestro = 0
    simular_al_azar(Estado.inicial(), 1, 0, para=color)


def _edad(entrada):
    return turno_nuestro - entrada["turno"]


def _confianza(entrada):
    """Más visitas y menos antigüedad → más confianza."""
    return entrada["visitas"] / (1.0 + _edad(entrada))


def _se_puede_reusar(entrada):
    return entrada["visitas"] >= MIN_VISITAS and _edad(entrada) <= MAX_EDAD


def _expulsar():
    peor = min(tabla.items(), key=lambda kv: (kv[1]["visitas"], kv[1]["turno"]))
    del tabla[peor[0]]


def _guardar(clave, valor):
    if clave in tabla:
        e = tabla[clave]
        n = e["visitas"]
        e["valor"] = (e["valor"] * n + valor) / (n + 1)
        e["visitas"] = n + 1
        e["turno"] = turno_nuestro
        return
    if len(tabla) >= MAX_TABLA:
        _expulsar()
    tabla[clave] = {"valor": valor, "visitas": 1, "turno": turno_nuestro}


def estimar(estado):
    """Consulta la caché o simula y guarda."""
    if estado.terminado():
        return 1.0 if estado.ganador() == color else 0.0
    clave = estado.clave
    entrada = tabla.get(clave)
    if entrada is not None and _se_puede_reusar(entrada):
        return entrada["valor"]
    valor = simular_al_azar(estado, SIMULACIONES, rng.randrange(2**31), para=color)
    _guardar(clave, valor)
    return tabla[clave]["valor"]


def jugar(estado, tiempo_restante):
    global turno_nuestro
    turno_nuestro += 1

    disponible = tiempo_restante - reserva
    limite = time.perf_counter() + max(0.0, disponible) / 25
    jugadas = estado.jugadas()

    for j in jugadas:
        if all(hijo.ganador() == color for _, hijo in estado.siguiente(j)):
            return j
    if disponible <= 0:
        return rng.choice(jugadas)

    total = {j: 0.0 for j in jugadas}
    muestras = {j: 0 for j in jugadas}
    reusos = 0
    hechas = 0

    while True:
        j = jugadas[hechas % len(jugadas)]
        probs, hijos = zip(*estado.siguiente(j), strict=True)
        hijo = rng.choices(hijos, weights=probs)[0]

        clave = hijo.clave
        entrada = tabla.get(clave)
        if entrada is not None and _se_puede_reusar(entrada):
            valor = entrada["valor"]
            reusos += 1
        else:
            valor = estimar(hijo)

        total[j] += valor
        muestras[j] += 1
        hechas += 1

        if hechas >= len(jugadas) and time.perf_counter() >= limite:
            break
        if hechas >= len(jugadas) * 40:
            break

    mejor = max(jugadas, key=lambda j: total[j] / max(1, muestras[j]))
    reportar(
        muestras=sum(muestras.values()),
        eval=total[mejor] / max(1, muestras[mejor]),
        cache=len(tabla),
        reusos=reusos,
        modelo="cache",
    )
    return mejor
