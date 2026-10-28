import csv
import json
from pathlib import Path

raiz = Path("resultados")
salida = Path("experimentos")
partidas = []
jugadas = []

for archivo in sorted(raiz.rglob("*.json")):
    # Ignorar JSON auxiliares que no sean registros de partidas.
    try:
        with archivo.open(encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        continue

    meta = datos.get("meta")
    movimientos = datos.get("jugadas")

    if not isinstance(meta, dict) or not isinstance(movimientos, list):
        continue
    if "blancas" not in meta or "negras" not in meta:
        continue

    blancos = meta["blancas"]
    negros = meta["negras"]
    ganador_color = datos.get("ganador")

    ganador_bot = {
        "blancas": blancos,
        "negras": negros,
    }.get(ganador_color, "")

    motivo = datos.get("motivo", "")
    puntos = datos.get("puntos") or {}
    relojes = datos.get("reloj_usado") or {}

    id_partida = str(archivo.relative_to(raiz))

    partidas.append({
        "id_partida": id_partida,
        "sesion": archivo.parent.name,
        "grupo": archivo.parent.parent.name,
        "blancas": blancos,
        "negras": negros,
        "ganador_color": ganador_color or "",
        "ganador_bot": ganador_bot,
        "motivo": motivo,
        "puntos_blancas": puntos.get("blancas", ""),
        "puntos_negras": puntos.get("negras", ""),
        "tiempo_blancas": relojes.get("blancas", ""),
        "tiempo_negras": relojes.get("negras", ""),
        "numero_jugadas": len(movimientos),
        "semilla": meta.get("semilla_maestra", ""),
        "pareja": meta.get("pareja", ""),
        "juego": meta.get("juego", ""),
    })

    for mov in movimientos:
        color = mov.get("color", "")
        info = mov.get("info") or {}

        bot = {
            "blancas": blancos,
            "negras": negros,
        }.get(color, "")

        jugadas.append({
            "id_partida": id_partida,
            "numero": mov.get("n", ""),
            "color": color,
            "bot": bot,
            "jugada": mov.get("jugada", ""),
            "tiempo_segundos": mov.get("tiempo", ""),
            "reloj_segundos": mov.get("reloj", ""),
            "evaluacion": info.get("eval", ""),
            "muestras": info.get("muestras", ""),
            "modelo_info": info.get("modelo", ""),
            "combate": json.dumps(
                mov.get("combate"), ensure_ascii=False
            ),
        })

def guardar_csv(nombre, filas):
    if not filas:
        print(f"Sin datos para {nombre}")
        return

    with (salida / nombre).open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)

guardar_csv("partidas.csv", partidas)
guardar_csv("jugadas.csv", jugadas)

print(f"Partidas procesadas: {len(partidas)}")
print(f"Jugadas procesadas: {len(jugadas)}")
print(f"Archivos creados en: {salida.resolve()}")
print("\nResultados por partida:")
for p in partidas:
    print(
        f'{p["blancas"]} vs {p["negras"]}: '
        f'ganador={p["ganador_bot"] or "sin dato"}, '
        f'motivo={p["motivo"] or "sin dato"}'
    )
