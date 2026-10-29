"""Preparación, validación y extracción homogénea de experiencias para aprendizaje.

Procesa `partidas.jsonl`, valida esquemas e integridad, descarta duplicados y extrae
transiciones (s, a, r, s') con vectores de características normalizados desde la perspectiva
fija de cada color.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from motor import Estado
from estudiantes.compartido.caracteristicas import extraer_caracteristicas

COLORES = ("blancas", "negras")


def validar_partida(partida: dict) -> tuple[bool, str]:
    """Verifica la integridad estructural y de reglas de un registro de partida."""
    campos_obligatorios = (
        "id_partida",
        "version_esquema",
        "ganador",
        "historial",
        "equipos",
    )
    for c in campos_obligatorios:
        if c not in partida:
            return False, f"Falta campo obligatorio: {c}"

    if partida["ganador"] not in COLORES:
        return False, f"Ganador inválido: {partida['ganador']}"

    historial = partida["historial"]
    if not isinstance(historial, list) or len(historial) == 0:
        return False, "Historial vacío o mal formado"

    return True, "OK"


def procesar_partidas_a_experiencias(
    archivo_partidas: Path,
    archivo_salida: Path,
) -> dict:
    """Extrae transiciones y características desde partidas válidas sin duplicados."""
    if not archivo_partidas.is_file():
        raise FileNotFoundError(f"No existe el archivo de partidas: {archivo_partidas}")

    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    partidas_vistas = set()
    total_leidas = 0
    total_validas = 0
    total_duplicadas = 0
    total_errores = 0
    total_transiciones = 0

    experiencias = []

    with archivo_partidas.open("r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            total_leidas += 1
            try:
                p = json.loads(linea)
            except json.JSONDecodeError:
                total_errores += 1
                continue

            id_p = p.get("id_partida")
            if not id_p or id_p in partidas_vistas:
                total_duplicadas += 1
                continue

            valida, razon = validar_partida(p)
            if not valida:
                total_errores += 1
                continue

            partidas_vistas.add(id_p)
            total_validas += 1

            # Procesamiento de la secuencia de estados
            ganador = p["ganador"]
            historial = p["historial"]
            
            # Reconstruimos la trayectoria de estados
            # Estado inicial
            estado_actual = Estado.inicial()
            estados_secuencia = [estado_actual]

            for paso in historial:
                st_dict = paso["estado_despues"]
                st_obj = Estado.desde_dict(st_dict)
                estados_secuencia.append(st_obj)

            # Generamos experiencias desde la perspectiva de cada jugador
            for pers in COLORES:
                recompensa_final = 1.0 if ganador == pers else -1.0
                
                # Para cada transición en la partida
                for idx in range(len(estados_secuencia) - 1):
                    s_t = estados_secuencia[idx]
                    s_sig = estados_secuencia[idx + 1]
                    es_ultimo = (idx == len(estados_secuencia) - 2)

                    # Recompensa intermedia 0.0, terminal recompensa_final
                    r = recompensa_final if es_ultimo else 0.0

                    feats_s = extraer_caracteristicas(s_t, pers)
                    feats_sig = extraer_caracteristicas(s_sig, pers)

                    exp = {
                        "id_partida": id_p,
                        "paso": idx,
                        "perspectiva": pers,
                        "features_s": [round(x, 5) for x in feats_s],
                        "features_sig": [round(x, 5) for x in feats_sig],
                        "recompensa": r,
                        "terminal": es_ultimo,
                    }
                    experiencias.append(exp)
                    total_transiciones += 1

    # Guardar en JSONL
    with archivo_salida.open("w", encoding="utf-8") as f:
        for exp in experiencias:
            f.write(json.dumps(exp) + "\n")

    resumen = {
        "total_leidas": total_leidas,
        "total_validas": total_validas,
        "total_duplicadas": total_duplicadas,
        "total_errores": total_errores,
        "total_transiciones": total_transiciones,
    }
    return resumen


def main():
    parser = argparse.ArgumentParser(description="Preparación de experiencias para TD(0).")
    parser.add_argument("--entrada", type=str, default="datos/partidas/partidas.jsonl")
    parser.add_argument("--salida", type=str, default="datos/experiencias/experiencias.jsonl")
    args = parser.parse_args()

    entrada = RAIZ / args.entrada
    salida = RAIZ / args.salida

    print(f"Procesando {entrada} -> {salida}...")
    resumen = procesar_partidas_a_experiencias(entrada, salida)
    print("Resumen de procesamiento:")
    for k, v in resumen.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
