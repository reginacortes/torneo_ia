"""Entrenamiento de función de valor mediante TD(0) incremental sobre experiencias.

Aprende los pesos óptimos de las características estratégicas sin redes neuronales,
respetando la perspectiva de cada jugador y manteniendo estabilidad numérica con clipping
y regularización L2.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from estudiantes.compartido.caracteristicas import NOMBRES_CARACTERISTICAS
from estudiantes.compartido.evaluacion import PESOS_DEFECTO

# Límites de búsqueda física para cada peso
LIMITES_PESOS = {
    "dif_puntos": (0.8, 4.5),
    "dif_peones": (0.03, 0.4),
    "avance_promedio": (0.2, 1.2),
    "avance_maximo": (0.1, 0.8),
    "amenaza_anotacion": (0.15, 1.0),
    "movilidad_relativa": (0.05, 0.4),
    "apoyo_mutuo": (0.08, 0.4),
    "vulnerabilidad": (0.10, 0.5),
    "bloqueo_rival": (0.15, 0.6),
    "control_centro": (0.02, 0.3),
}


def cargar_experiencias(ruta_exp: Path) -> list[dict]:
    experiencias = []
    with ruta_exp.open("r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                experiencias.append(json.loads(linea))
    return experiencias


def estimar_v(w_vec: list[float], x_vec: list[float]) -> float:
    score = sum(w * x for w, x in zip(w_vec, x_vec))
    # Acotamos linealmente en [-1.0, 1.0]
    return max(-1.0, min(1.0, score))


def entrenar_td0(
    experiencias: list[dict],
    pesos_iniciales: dict[str, float] | None = None,
    alpha: float = 0.01,
    gamma: float = 0.98,
    epocas: int = 5,
    l2_reg: float = 0.0001,
) -> tuple[dict[str, float], dict]:
    """Entrena pesos mediante TD(0) con regularización L2 y clipping."""
    pesos = dict(PESOS_DEFECTO)
    if pesos_iniciales:
        pesos.update(pesos_iniciales)

    w_vec = [pesos[k] for k in NOMBRES_CARACTERISTICAS]

    errores_por_epoca = []

    for epoca in range(epocas):
        suma_error_cuad = 0.0
        n_muestras = 0

        for exp in experiencias:
            x_s = exp["features_s"]
            x_sig = exp["features_sig"]
            r = exp["recompensa"]
            terminal = exp["terminal"]

            v_s = estimar_v(w_vec, x_s)

            if terminal:
                target = r
            else:
                target = r + gamma * estimar_v(w_vec, x_sig)

            delta = target - v_s
            suma_error_cuad += delta**2
            n_muestras += 1

            # Actualización TD(0) con decaimiento de pesos
            for i in range(len(w_vec)):
                grad = delta * x_s[i] - l2_reg * w_vec[i]
                w_vec[i] += alpha * grad

                # Clipping a los límites razonables
                nom = NOMBRES_CARACTERISTICAS[i]
                min_w, max_w = LIMITES_PESOS.get(nom, (0.0, 5.0))
                w_vec[i] = max(min_w, min(max_w, w_vec[i]))

        mse = suma_error_cuad / max(1, n_muestras)
        errores_por_epoca.append(round(mse, 6))

    pesos_resultado = {
        NOMBRES_CARACTERISTICAS[i]: round(w_vec[i], 6)
        for i in range(len(NOMBRES_CARACTERISTICAS))
    }

    metadatos = {
        "fecha": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "algoritmo": "TD(0)",
        "alpha": alpha,
        "gamma": gamma,
        "epocas": epocas,
        "l2_reg": l2_reg,
        "muestras": len(experiencias),
        "mse_por_epoca": errores_por_epoca,
        "mse_inicial": errores_por_epoca[0] if errores_por_epoca else 0.0,
        "mse_final": errores_por_epoca[-1] if errores_por_epoca else 0.0,
        "pesos_iniciales": pesos_iniciales or PESOS_DEFECTO,
        "pesos_nuevos": pesos_resultado,
    }

    return pesos_resultado, metadatos


def main():
    parser = argparse.ArgumentParser(description="Entrenador TD(0) para Breakthrough.")
    parser.add_argument("--experiencias", type=str, default="datos/experiencias/experiencias.jsonl")
    parser.add_argument("--pesos-base", type=str, default="")
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--gamma", type=float, default=0.98)
    parser.add_argument("--epocas", type=int, default=5)
    parser.add_argument("--salida", type=str, default="datos/modelos/modelo_candidato.json")
    args = parser.parse_args()

    ruta_exp = RAIZ / args.experiencias
    print(f"Cargando experiencias de {ruta_exp}...")
    exps = cargar_experiencias(ruta_exp)
    print(f"Total experiencias cargadas: {len(exps)}")

    pesos_base = None
    if args.pesos_base:
        p_base = RAIZ / args.pesos_base
        if p_base.is_file():
            pesos_base = json.loads(p_base.read_text())

    print(f"Iniciando TD(0) por {args.epocas} épocas (alpha={args.alpha}, gamma={args.gamma})...")
    pesos_nuevos, meta = entrenar_td0(
        exps,
        pesos_iniciales=pesos_base,
        alpha=args.alpha,
        gamma=args.gamma,
        epocas=args.epocas,
    )

    salida_path = RAIZ / args.salida
    salida_path.parent.mkdir(parents=True, exist_ok=True)
    salida_path.write_text(json.dumps(pesos_nuevos, indent=2) + "\n")

    # Guardar metadatos en checkpoints
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chk_dir = RAIZ / "datos/modelos/checkpoints"
    chk_dir.mkdir(parents=True, exist_ok=True)
    chk_meta = chk_dir / f"checkpoint_{now_str}.json"
    chk_meta.write_text(json.dumps(meta, indent=2) + "\n")

    print(f"Modelo candidato guardado en: {salida_path}")
    print(f"Metadatos y checkpoint en: {chk_meta}")
    print(f"MSE inicial: {meta['mse_inicial']} -> final: {meta['mse_final']}")


if __name__ == "__main__":
    main()
