"""Estabilidad, umbrales, ambientes y recomendaciones."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from kiwitracking.resultado import Advertencia


def calcular_estabilidad(tabla: pd.DataFrame) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Agrega `estabilidad` = KVPI_corregido / KVPI_std (RF-20, RF-21).

    El KVPI_std se usa sin corregir, como en el notebook de referencia (duda abierta de la spec).
    Con KVPI_std = 0 la estabilidad queda vacía y se avisa.
    """
    resultado = tabla.copy()
    std_cero = resultado["KVPI_std"] == 0
    divisor = resultado["KVPI_std"].mask(std_cero)  # el 0 pasa a vacío: nunca hay infinito
    resultado["estabilidad"] = resultado["KVPI_corregido"] / divisor

    advertencias = []
    cantidad = int(std_cero.sum())
    if cantidad:
        advertencias.append(
            Advertencia("STD_CERO", f"{cantidad} plantas tienen KVPI_std = 0: su estabilidad queda vacía.")
        )
    return resultado, advertencias


@dataclass(frozen=True)
class Umbrales:
    """Percentiles del lote. Los nombres son los de los valores por defecto (33, 66 y 75)."""

    p33: float
    p66: float
    p75_estabilidad: float | None


def calcular_umbrales(
    tabla: pd.DataFrame, p_ambiente: tuple[float, float] = (33, 66), p_estabilidad: float = 75
) -> Umbrales:
    """p33 y p66 de KVPI_corregido y p75 de estabilidad, con interpolación lineal (RF-22).

    La estabilidad vacía (KVPI_std = 0) no entra al percentil de estabilidad.
    """
    bajo, alto = np.percentile(tabla["KVPI_corregido"], p_ambiente, method="linear")

    estabilidad = tabla["estabilidad"].dropna()
    p_estab = float(np.percentile(estabilidad, p_estabilidad, method="linear")) if len(estabilidad) else None

    return Umbrales(p33=float(bajo), p66=float(alto), p75_estabilidad=p_estab)
