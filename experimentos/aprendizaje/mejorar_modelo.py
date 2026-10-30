"""Orquestador automático del ciclo de mejora y promoción para `mc_aprendiz`.

Integra las fases de generación de partidas, preparación de experiencias,
entrenamiento TD(0), validación de legalidad, evaluación emparejada con intervalos Wilson,
y promoción condicionada a superación estadística del umbral de rendimiento.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SISTEMA = RAIZ / "sistema"
sys.path.insert(0, str(SISTEMA))
sys.path.insert(0, str(RAIZ))

from experimentos.aprendizaje.entrenar import entrenar_td0, cargar_experiencias
from experimentos.aprendizaje.evaluar import evaluar_enfrentamiento
from experimentos.aprendizaje.preparar_datos import procesar_partidas_a_experiencias
from experimentos.aprendizaje.registrar_partidas import registrar_serie


def registrar_historial_modelo(registro: dict):
    ruta_historial = RAIZ / "datos/modelos/historial_modelos.jsonl"
    ruta_historial.parent.mkdir(parents=True, exist_ok=True)
    with ruta_historial.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro) + "\n")


def ejecutar_ciclo_completo(
    partidas_generar: int,
    partidas_evaluar: int,
    reloj_s: float,
    semilla: int,
    alpha: float,
    gamma: float,
    epocas: int,
    adversario: str,
    umbral_promocion: float,
) -> dict:
    print("=================================================================")
    print("INICIO DEL CICLO AUTOMÁTICO DE MEJORA PARA MC_APRENDIZ")
    print("=================================================================")
    t_inicio = datetime.datetime.now(datetime.timezone.utc).isoformat()

    ruta_partidas = RAIZ / "datos/partidas/partidas.jsonl"
    ruta_experiencias = RAIZ / "datos/experiencias/experiencias.jsonl"
    ruta_candidato = RAIZ / "datos/modelos/modelo_candidato.json"
    ruta_estable = RAIZ / "estudiantes/mc_aprendiz/pesos.json"
    ruta_actual = RAIZ / "datos/modelos/modelo_actual.json"

    # FASE 1: Generación de partidas
    if partidas_generar > 0:
        print(f"\n[Fase 1/5] Generando {partidas_generar} partidas ({adversario} vs mc_aprendiz)...")
        registrar_serie(
            (adversario, "mc_aprendiz"),
            partidas_generar,
            reloj_s,
            semilla,
            ruta_partidas,
        )
    else:
        print("\n[Fase 1/5] Omitiendo generación de partidas (usando partidas preexistentes)...")

    # FASE 2: Preparación y validación de experiencias
    print(f"\n[Fase 2/5] Validando datos y extrayendo experiencias a {ruta_experiencias.name}...")
    res_prep = procesar_partidas_a_experiencias(ruta_partidas, ruta_experiencias)
    print(f"  Experiencias generadas: {res_prep['total_transiciones']} (Partidas válidas: {res_prep['total_validas']})")

    # FASE 3: Entrenamiento TD(0)
    print(f"\n[Fase 3/5] Entrenando pesos con TD(0) ({epocas} épocas, alpha={alpha})...")
    exps = cargar_experiencias(ruta_experiencias)
    pesos_base = json.loads(ruta_estable.read_text()) if ruta_estable.is_file() else None
    pesos_candidatos, meta_entrenamiento = entrenar_td0(
        exps,
        pesos_iniciales=pesos_base,
        alpha=alpha,
        gamma=gamma,
        epocas=epocas,
    )
    ruta_candidato.parent.mkdir(parents=True, exist_ok=True)
    ruta_candidato.write_text(json.dumps(pesos_candidatos, indent=2) + "\n")
    print(f"  MSE inicial: {meta_entrenamiento['mse_inicial']} -> final: {meta_entrenamiento['mse_final']}")

    # FASE 4: Validación y Evaluación frente a la línea base
    print(f"\n[Fase 4/5] Evaluando candidato frente a {adversario} en {partidas_evaluar} partidas...")
    
    # Creamos un respaldo temporal del peso estable antes de evaluar el candidato en mc_aprendiz
    backup_estable = ruta_estable.read_text() if ruta_estable.is_file() else None
    try:
        # Colocamos temporalmente los pesos candidatos en mc_aprendiz para la prueba
        ruta_estable.write_text(json.dumps(pesos_candidatos, indent=2) + "\n")
        
        # Evaluamos
        semilla_eval = semilla + 999
        res_eval = evaluar_enfrentamiento(
            "mc_aprendiz",
            adversario,
            partidas=partidas_evaluar,
            reloj_s=reloj_s,
            semilla=semilla_eval,
        )
    finally:
        # Restauramos el peso estable original antes de decidir promoción
        if backup_estable is not None:
            ruta_estable.write_text(backup_estable)

    winrate = res_eval["tasa_a"]
    ci = res_eval["ci_95"]
    print(f"  Resultado evaluación: {res_eval['victorias_a']}/{partidas_evaluar} ({winrate * 100:.1f}%)")
    print(f"  Intervalo Wilson 95%: [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]")

    # FASE 5: Decisión de promoción
    promovido = False
    motivo = ""
    if winrate >= umbral_promocion:
        promovido = True
        motivo = f"Superó umbral de promoción ({winrate:.2f} >= {umbral_promocion:.2f})"
        print(f"\n[Fase 5/5] ¡CANDIDATO PROMOVIDO! {motivo}")
        # Promoción atómica
        ruta_estable.write_text(json.dumps(pesos_candidatos, indent=2) + "\n")
        ruta_actual.write_text(json.dumps(pesos_candidatos, indent=2) + "\n")
    else:
        promovido = False
        motivo = f"No superó umbral de promoción ({winrate:.2f} < {umbral_promocion:.2f})"
        print(f"\n[Fase 5/5] Candidato NO promovido. {motivo}. Se conserva modelo estable.")

    # Registro en historial
    id_registro = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    registro_modelo = {
        "id_evaluacion": id_registro,
        "fecha": t_inicio,
        "semilla": semilla,
        "adversario": adversario,
        "partidas_evaluadas": partidas_evaluar,
        "victorias": res_eval["victorias_a"],
        "winrate": winrate,
        "ci_95": ci,
        "promovido": promovido,
        "motivo": motivo,
        "pesos_candidatos": pesos_candidatos,
        "mse_entrenamiento": meta_entrenamiento["mse_final"],
    }
    registrar_historial_modelo(registro_modelo)

    informe_resumen = {
        "id": id_registro,
        "promovido": promovido,
        "motivo": motivo,
        "winrate": winrate,
        "evaluacion": res_eval,
        "entrenamiento": meta_entrenamiento,
    }
    return informe_resumen


def main():
    parser = argparse.ArgumentParser(description="Script para mejorar automáticamente mc_aprendiz.")
    parser.add_argument(
        "--modo",
        type=str,
        default="completo",
        choices=["completo", "generar", "preparar", "entrenar", "evaluar"],
    )
    parser.add_argument("--partidas", type=int, default=4, help="Partidas a generar")
    parser.add_argument("--partidas-eval", type=int, default=4, help="Partidas para evaluar candidato")
    parser.add_argument("--reloj", type=float, default=2.0)
    parser.add_argument("--semilla", type=int, default=None, help="Semilla base (por defecto: dinámica según reloj)")
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--gamma", type=float, default=0.98)
    parser.add_argument("--epocas", type=int, default=5)
    parser.add_argument("--adversario", type=str, default="montecarlo")
    parser.add_argument("--umbral", type=float, default=0.50)
    args = parser.parse_args()

    semilla_usada = args.semilla if args.semilla is not None else int(time.time()) % 10000000

    if args.modo == "completo":
        res = ejecutar_ciclo_completo(
            partidas_generar=args.partidas,
            partidas_evaluar=args.partidas_eval,
            reloj_s=args.reloj,
            semilla=semilla_usada,
            alpha=args.alpha,
            gamma=args.gamma,
            epocas=args.epocas,
            adversario=args.adversario,
            umbral_promocion=args.umbral,
        )
        print("\n=================================================================")
        print(f"Resumen del ciclo: Promovido = {res['promovido']} ({res['motivo']})")
        print("=================================================================")
    elif args.modo == "generar":
        p = RAIZ / "datos/partidas/partidas.jsonl"
        registrar_serie((args.adversario, "mc_aprendiz"), args.partidas, args.reloj, args.semilla, p)
    elif args.modo == "preparar":
        p = RAIZ / "datos/partidas/partidas.jsonl"
        e = RAIZ / "datos/experiencias/experiencias.jsonl"
        procesar_partidas_a_experiencias(p, e)
    elif args.modo == "entrenar":
        e = RAIZ / "datos/experiencias/experiencias.jsonl"
        exps = cargar_experiencias(e)
        pesos, _ = entrenar_td0(exps, alpha=args.alpha, gamma=args.gamma, epocas=args.epocas)
        print("Pesos entrenados:", pesos)
    elif args.modo == "evaluar":
        res = evaluar_enfrentamiento("mc_aprendiz", args.adversario, args.partidas_eval, args.reloj, args.semilla)
        print(res)


if __name__ == "__main__":
    main()
