"""
importar_resultados.py
======================
Importa partidas de los archivos HTML generados por el torneo (carpeta resultados/)
al formato JSONL canónico usado por preparar_datos.py.

Uso:
    python importar_resultados.py [--directorio DIR] [--salida ARCHIVO]

Ejemplos:
    python importar_resultados.py
    python importar_resultados.py --directorio resultados/2026-10-30_10-04-51
    python importar_resultados.py --directorio resultados/2026-10-30_10-04-51 --salida datos/partidas/partidas.jsonl
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
DATOS = RAIZ / "datos"
PARTIDAS_DEFAULT = DATOS / "partidas" / "partidas.jsonl"
RESULTADOS_DEFAULT = RAIZ / "resultados"

sys.path.insert(0, str(SISTEMA))

try:
    from motor import Estado, Jugada
except ImportError as e:
    print(f"ERROR: No se pudo importar el motor: {e}")
    print(f"  Asegúrate de correr desde la raíz del repo con .venv/bin/python")
    sys.exit(1)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _id_partida(equipos: dict, jugadas_texto: list[str]) -> str:
    """Genera ID determinístico SHA-256[:16] basado en equipos + secuencia de jugadas."""
    clave = json.dumps({
        "equipos": equipos,
        "jugadas": jugadas_texto,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(clave.encode()).hexdigest()[:16]


def _extraer_json_html(html: str) -> dict | None:
    """Extrae el JSON embebido en <script id='datos'>...</script>."""
    m = re.search(r'<script\s+id=["\']datos["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _equipos_desde_nombre(nombre_archivo: str) -> dict | None:
    """
    Extrae blancas y negras del nombre de archivo.
    Formato esperado: NNN_X_Y_botA_vs_botB.html  ó  NNN_botA_vs_botB.html
    """
    base = Path(nombre_archivo).stem
    # Intenta patrón NNN_X_Y_botA_vs_botB
    m = re.match(r'^\d+_\d+_\d+_(.+)_vs_(.+)$', base)
    if not m:
        # Intenta patrón NNN_botA_vs_botB
        m = re.match(r'^\d+_(.+)_vs_(.+)$', base)
    if not m:
        # Intenta solo botA_vs_botB
        m = re.match(r'^(.+)_vs_(.+)$', base)
    if not m:
        return None
    return {"blancas": m.group(1), "negras": m.group(2)}


def _reconstruir_historial(jugadas_raw: list[dict]) -> list[dict] | None:
    """
    Reconstruye el historial completo reproduciendo el juego desde Estado.inicial().
    Cada entrada contiene: paso, color, jugada, es_ataque, prob_ataque, dado, gana_ataque,
    tiempo_s, estado_despues.
    Devuelve None si ocurre un error (jugada ilegal, etc.).
    """
    estado = Estado.inicial()
    historial = []

    for i, jraw in enumerate(jugadas_raw):
        texto = jraw.get("jugada", "")
        color = jraw.get("color", "")
        combate = jraw.get("combate")        # None o {"p": float, "u": float, "gano": bool}
        tiempo_s = jraw.get("tiempo", 0.0)

        # Parsear la jugada
        try:
            jugada = Jugada.desde_texto(texto)
        except Exception:
            return None

        # Verificar que sea legal
        legales = estado.jugadas()
        if jugada not in legales:
            return None

        es_ataque = estado.es_ataque(jugada)
        prob_ataque = estado.prob_ataque(jugada) if es_ataque else None
        gana_ataque: bool | None = None
        dado: float | None = None

        if combate is not None:
            gana_ataque = bool(combate.get("gano", True))
            dado = combate.get("u")          # número aleatorio que usó el árbitro

        # Aplicar la jugada
        try:
            if es_ataque and gana_ataque is not None:
                estado_nuevo = estado.aplicar(jugada, gana_ataque=gana_ataque)
            else:
                estado_nuevo = estado.aplicar(jugada)
        except Exception:
            return None

        historial.append({
            "paso": i,
            "color": color,
            "jugada": texto,
            "es_ataque": es_ataque,
            "prob_ataque": prob_ataque,
            "dado": dado,
            "gana_ataque": gana_ataque,
            "tiempo_s": tiempo_s,
            "estado_despues": estado_nuevo.a_dict(),
        })

        estado = estado_nuevo

    return historial


def _procesar_html(path: Path) -> dict | None:
    """
    Procesa un archivo HTML y devuelve el registro en formato canónico,
    o None si falla.
    """
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    datos = _extraer_json_html(html)
    if datos is None:
        return None

    reg = datos.get("registro", {})
    jugadas_raw = reg.get("jugadas", [])
    if not jugadas_raw:
        return None

    # Equipos desde nombre de archivo
    equipos = _equipos_desde_nombre(path.name)
    if equipos is None:
        # Intentar extraer de meta si existe
        meta = reg.get("meta", {})
        equipos = meta.get("equipos") if meta else None
    if equipos is None:
        return None

    # Ganador y motivo
    ganador = reg.get("ganador", "desconocido")
    motivo_raw = reg.get("motivo", "juego")
    motivo = "juego" if motivo_raw == "puntos" else motivo_raw  # normalizar

    reloj_consumido = reg.get("reloj_usado", {"blancas": 0.0, "negras": 0.0}) or {}

    # Textos de jugadas para el ID
    jugadas_texto = [j.get("jugada", "") for j in jugadas_raw]

    id_partida = _id_partida(equipos, jugadas_texto)

    # Reconstruir historial con estados
    historial = _reconstruir_historial(jugadas_raw)
    if historial is None:
        return None

    # Conteos
    ataques = sum(1 for h in historial if h["es_ataque"])

    registro = {
        "id_partida": id_partida,
        "version_esquema": "1.0.0",
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "semilla": None,
        "numero_partida": 0,
        "equipos": equipos,
        "configuraciones": {},
        "reloj_inicial_s": 30.0,
        "reloj_consumido": reloj_consumido,
        "ganador": ganador,
        "motivo": motivo,
        "jugadas_totales": len(historial),
        "ataques_totales": ataques,
        "historial": historial,
    }

    return registro


# ── Carga de IDs existentes ────────────────────────────────────────────────────

def _cargar_ids_existentes(salida: Path) -> set[str]:
    ids = set()
    if not salida.exists():
        return ids
    with open(salida, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                obj = json.loads(linea)
                if "id_partida" in obj:
                    ids.add(obj["id_partida"])
            except json.JSONDecodeError:
                pass
    return ids


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Importa partidas HTML al formato JSONL canónico.")
    parser.add_argument(
        "--directorio", "-d",
        default=None,
        help="Carpeta con archivos HTML (default: busca en resultados/)",
    )
    parser.add_argument(
        "--salida", "-s",
        default=str(PARTIDAS_DEFAULT),
        help=f"Archivo JSONL de salida (default: {PARTIDAS_DEFAULT})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar detalles de cada archivo procesado",
    )
    args = parser.parse_args()

    # Resolver directorio
    if args.directorio:
        directorio = Path(args.directorio)
    else:
        # Buscar la carpeta más reciente en resultados/
        subdirs = sorted(RESULTADOS_DEFAULT.glob("*/"))
        if not subdirs:
            print(f"ERROR: No se encontraron subcarpetas en {RESULTADOS_DEFAULT}")
            sys.exit(1)
        directorio = subdirs[-1]
        print(f"→ Usando directorio más reciente: {directorio}")

    if not directorio.exists():
        print(f"ERROR: No existe el directorio: {directorio}")
        sys.exit(1)

    archivos = sorted(directorio.glob("*.html"))
    if not archivos:
        print(f"ERROR: No se encontraron archivos .html en {directorio}")
        sys.exit(1)

    print(f"→ {len(archivos)} archivos HTML encontrados en {directorio.name}")

    # Preparar salida
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    ids_existentes = _cargar_ids_existentes(salida)
    print(f"→ {len(ids_existentes)} partidas ya existentes en {salida.name}")

    # Procesar
    importadas = 0
    omitidas_dup = 0
    errores = 0

    with open(salida, "a", encoding="utf-8") as f_out:
        for i, archivo in enumerate(archivos):
            if args.verbose or (i % 50 == 0):
                print(f"  [{i+1}/{len(archivos)}] {archivo.name} ...", end="\r")

            registro = _procesar_html(archivo)

            if registro is None:
                errores += 1
                if args.verbose:
                    print(f"  ERROR: {archivo.name}")
                continue

            pid = registro["id_partida"]
            if pid in ids_existentes:
                omitidas_dup += 1
                if args.verbose:
                    print(f"  DUPLICADO: {archivo.name} ({pid})")
                continue

            f_out.write(json.dumps(registro, ensure_ascii=False) + "\n")
            ids_existentes.add(pid)
            importadas += 1

            if args.verbose:
                eq = registro["equipos"]
                print(f"  OK [{pid}] {eq['blancas']} vs {eq['negras']} → {registro['ganador']}")

    print()  # nueva línea tras el \r
    print("=" * 50)
    print(f"  Archivos HTML procesados : {len(archivos)}")
    print(f"  Partidas importadas      : {importadas}")
    print(f"  Omitidas (duplicadas)    : {omitidas_dup}")
    print(f"  Errores (no procesables) : {errores}")
    print(f"  Salida                   : {salida}")
    print("=" * 50)

    if importadas == 0:
        print("⚠  No se importó ninguna partida nueva.")
    else:
        print(f"✓  Listo. Ahora puedes correr preparar_datos.py para extraer transiciones.")


if __name__ == "__main__":
    main()
