"""Registrador homogéneo y canónico de partidas para Breakthrough.

Ejecuta partidas entre dos bots utilizando el motor oficial, los dados del árbitro y
las reglas del torneo, serializando la información completa a formato JSONL sin alterar
las reglas ni las probabilidades del juego.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from arbitro.azar import Dados, semilla_bots, semilla_de_color
from arbitro.runner import Config
from motor import Estado, Jugada

COLORES = ("blancas", "negras")
ESQUEMA_VERSION = "1.0.0"


def cargar_bot(equipo: str, instancia: int) -> ModuleType:
    """Carga `estudiantes/<equipo>/strategy.py` de forma aislada."""
    ruta = RAIZ / "estudiantes" / equipo / "strategy.py"
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el bot {equipo} en {ruta}")
    spec = importlib.util.spec_from_file_location(f"bot_{equipo}_{instancia}", ruta)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def jugar_y_registrar_partida(
    equipos: tuple[str, str],
    reloj_s: float,
    semilla_base: int,
    numero_partida: int,
    configuraciones: dict[str, dict] | None = None,
) -> dict:
    """Ejecuta una partida y genera el registro canónico detallado."""
    id_crudo = f"{equipos[0]}_{equipos[1]}_{semilla_base}_{numero_partida}_{reloj_s}"
    id_partida = hashlib.sha256(id_crudo.encode()).hexdigest()[:16]

    bots = {c: cargar_bot(e, i) for i, (c, e) in enumerate(zip(COLORES, equipos, strict=True))}
    base = semilla_bots(semilla_base, 0, numero_partida)

    for color, bot in bots.items():
        equipo = equipos[COLORES.index(color)]
        carpeta = RAIZ / "estudiantes" / equipo / "data"
        if hasattr(bot, "preparar"):
            bot.preparar(Config(color, semilla_de_color(base, color), carpeta, reloj_s))

    dados = Dados(semilla_base, 0, numero_partida)
    usado = {c: 0.0 for c in COLORES}
    estado = Estado.inicial()
    
    registro_jugadas = []
    ataques_totales = 0
    turno_num = 0

    while (ganador := estado.ganador()) is None:
        color_turno = estado.turno
        t0 = time.perf_counter()
        j = bots[color_turno].jugar(estado, max(0.0, reloj_s - usado[color_turno]))
        duracion = time.perf_counter() - t0
        usado[color_turno] += duracion

        if usado[color_turno] > reloj_s:
            rival = COLORES[1 - COLORES.index(color_turno)]
            return {
                "id_partida": id_partida,
                "version_esquema": ESQUEMA_VERSION,
                "fecha": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "semilla": semilla_base,
                "numero_partida": numero_partida,
                "equipos": {"blancas": equipos[0], "negras": equipos[1]},
                "configuraciones": configuraciones or {},
                "reloj_inicial_s": reloj_s,
                "reloj_consumido": usado,
                "ganador": rival,
                "motivo": "reloj",
                "jugadas_totales": len(registro_jugadas),
                "ataques_totales": ataques_totales,
                "historial": registro_jugadas,
            }

        jugada_obj = Jugada.desde_texto(str(j))
        es_ataque = estado.es_ataque(jugada_obj)
        prob_ataque = float(estado.prob_ataque(jugada_obj)) if es_ataque else 1.0
        dado_obtenido = None
        gana_ataque = None

        if es_ataque:
            ataques_totales += 1
            dado_obtenido = float(dados.tirar(color_turno))
            gana_ataque = dado_obtenido < prob_ataque
            nuevo_estado = estado.aplicar(jugada_obj, gana_ataque=gana_ataque)
        else:
            nuevo_estado = estado.aplicar(jugada_obj)

        registro_jugadas.append(
            {
                "paso": turno_num,
                "color": color_turno,
                "jugada": str(jugada_obj),
                "es_ataque": es_ataque,
                "prob_ataque": prob_ataque,
                "dado": dado_obtenido,
                "gana_ataque": gana_ataque,
                "tiempo_s": round(duracion, 5),
                "estado_despues": nuevo_estado.a_dict(),
            }
        )

        estado = nuevo_estado
        turno_num += 1

    return {
        "id_partida": id_partida,
        "version_esquema": ESQUEMA_VERSION,
        "fecha": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "semilla": semilla_base,
        "numero_partida": numero_partida,
        "equipos": {"blancas": equipos[0], "negras": equipos[1]},
        "configuraciones": configuraciones or {},
        "reloj_inicial_s": reloj_s,
        "reloj_consumido": usado,
        "ganador": ganador,
        "motivo": "juego",
        "jugadas_totales": len(registro_jugadas),
        "ataques_totales": ataques_totales,
        "historial": registro_jugadas,
    }


def registrar_serie(
    equipos: tuple[str, str],
    cantidad_partidas: int,
    reloj_s: float,
    semilla_base: int,
    archivo_destino: Path,
) -> list[dict]:
    """Genera una serie alternando colores y escribe línea por línea en JSONL."""
    archivo_destino.parent.mkdir(parents=True, exist_ok=True)
    partidas = []

    # Determinar offset para no colisionar con partidas existentes
    offset = 0
    if archivo_destino.is_file():
        with archivo_destino.open("r", encoding="utf-8") as f:
            offset = sum(1 for line in f if line.strip())

    # Abrimos en modo append para no destruir partidas previas
    with archivo_destino.open("a", encoding="utf-8") as f:
        for i in range(cantidad_partidas):
            num_global = offset + i
            semilla_partida = (semilla_base + num_global * 10007) % (2**31)
            # Alternar colores: pares (botA, botB), impares (botB, botA)
            orden = equipos if i % 2 == 0 else equipos[::-1]
            reg = jugar_y_registrar_partida(orden, reloj_s, semilla_partida, num_global)
            f.write(json.dumps(reg) + "\n")
            f.flush()
            partidas.append(reg)

    return partidas


def main():
    parser = argparse.ArgumentParser(description="Registrador de partidas Breakthrough.")
    parser.add_argument("--bot1", type=str, default="montecarlo")
    parser.add_argument("--bot2", type=str, default="random")
    parser.add_argument("--partidas", type=int, default=4)
    parser.add_argument("--reloj", type=float, default=2.0)
    parser.add_argument("--semilla", type=int, default=20261029)
    parser.add_argument("--salida", type=str, default="datos/partidas/partidas.jsonl")
    args = parser.parse_args()

    destino = RAIZ / args.salida
    print(f"Registrando {args.partidas} partidas entre {args.bot1} y {args.bot2} en {destino}...")
    partidas = registrar_serie(
        (args.bot1, args.bot2),
        args.partidas,
        args.reloj,
        args.semilla,
        destino,
    )
    victorias_b1 = sum(
        1
        for p in partidas
        if (p["ganador"] == "blancas" and p["equipos"]["blancas"] == args.bot1)
        or (p["ganador"] == "negras" and p["equipos"]["negras"] == args.bot1)
    )
    print(f"Completado: {victorias_b1}/{len(partidas)} victorias para {args.bot1}")


if __name__ == "__main__":
    main()
