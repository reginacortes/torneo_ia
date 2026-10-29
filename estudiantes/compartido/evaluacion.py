"""Módulo de evaluación posicional y modelos lineales para Breakthrough.

Integra la evaluación heurística clásica con modelos de valor parametrizados.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from motor import Estado
from estudiantes.compartido.caracteristicas import (
    NOMBRES_CARACTERISTICAS,
    extraer_caracteristicas,
)

# Pesos por defecto basados en mc_genetico y calibración
PESOS_DEFECTO: dict[str, float] = {
    "dif_puntos": 2.107807,
    "dif_peones": 0.058300,
    "avance_promedio": 0.496565,
    "avance_maximo": 0.350000,
    "amenaza_anotacion": 0.400000,
    "movilidad_relativa": 0.150000,
    "apoyo_mutuo": 0.120000,
    "vulnerabilidad": 0.180000,
    "bloqueo_rival": 0.250000,
    "control_centro": 0.080000,
}


class EvaluadorLineal:
    """Evaluador lineal acotado en [-1.0, 1.0]."""

    def __init__(self, pesos: dict[str, float] | None = None):
        self.pesos = dict(PESOS_DEFECTO)
        if pesos:
            self.pesos.update(pesos)
        self._vector_pesos = [self.pesos.get(k, 0.0) for k in NOMBRES_CARACTERISTICAS]

    def evaluar(self, estado: Estado, perspectiva: str) -> float:
        """Devuelve una valoración en [-1.0, 1.0] desde `perspectiva`.
        
        +1.0 es victoria segura; -1.0 es derrota segura.
        """
        ganador = estado.ganador()
        if ganador is not None:
            return 1.0 if ganador == perspectiva else -1.0

        feats = extraer_caracteristicas(estado, perspectiva)
        score = sum(w * x for w, x in zip(self._vector_pesos, feats))
        # Acotamos con tanh para mapear suavemente a [-1, 1]
        return math.tanh(score)

    def evaluar_probabilidad(self, estado: Estado, perspectiva: str) -> float:
        """Devuelve una probabilidad estimada de victoria en [0.0, 1.0]."""
        v = self.evaluar(estado, perspectiva)
        return (v + 1.0) / 2.0

    def guardar(self, ruta: Path) -> None:
        ruta.write_text(json.dumps(self.pesos, indent=2) + "\n")

    @classmethod
    def cargar(cls, ruta: Path) -> EvaluadorLineal:
        try:
            datos = json.loads(ruta.read_text())
            # Soporta formato tradicional de 3 pesos o nuevo de 10 pesos
            pesos = {}
            if "puntos" in datos:
                pesos["dif_puntos"] = float(datos["puntos"])
            if "peones" in datos:
                pesos["dif_peones"] = float(datos["peones"])
            if "avance" in datos:
                pesos["avance_promedio"] = float(datos["avance"])
            for k in NOMBRES_CARACTERISTICAS:
                if k in datos:
                    pesos[k] = float(datos[k])
            return cls(pesos)
        except Exception:
            return cls()
