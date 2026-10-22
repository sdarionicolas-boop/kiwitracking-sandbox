"""Cálculo diario de GDD y horas de frío (spec 002, RF-10 y RF-11).

Las funciones suponen `Tmax >= Tmin` y datos ya validados (`clima_entrada.preparar_clima`). Un día con
una temperatura vacía da un resultado vacío, no cero: es un día faltante, no un día sin frío.
"""

import numpy as np
import pandas as pd


def _como_arreglos(tmax, tmin):
    indice = tmax.index if isinstance(tmax, pd.Series) else (tmin.index if isinstance(tmin, pd.Series) else None)
    return np.asarray(tmax, dtype=float), np.asarray(tmin, dtype=float), indice


def _devolver(valores: np.ndarray, indice):
    return pd.Series(valores, index=indice) if indice is not None else valores


def gdd_diario(tmax, tmin, tbase: float = 10):
    """`GDD_diario = max(Tmedia - tbase, 0)` con `Tmedia = (Tmax + Tmin) / 2` (RF-10)."""
    maxima, minima, indice = _como_arreglos(tmax, tmin)
    tmedia = (maxima + minima) / 2
    return _devolver(np.maximum(tmedia - tbase, 0), indice)


def horas_frio_diarias(tmax, tmin, umbral: float = 7):
    """Horas del día con temperatura por debajo del umbral, con el modelo de coseno (RF-11).

    24 si `Tmax <= umbral` (se evalúa primero, como en el notebook); 0 si `Tmin >= umbral`; en otro
    caso `(24 / pi) x (pi - theta)` con `theta = arccos(clip((umbral - Tmedia) / amp, -1, 1))`.
    """
    maxima, minima, indice = _como_arreglos(tmax, tmin)
    tmedia = (maxima + minima) / 2
    amplitud = (maxima - minima) / 2

    with np.errstate(divide="ignore", invalid="ignore"):
        razon = (umbral - tmedia) / amplitud  # con amplitud 0 no llega a usarse: lo cubren las dos reglas de arriba
    theta = np.arccos(np.clip(razon, -1.0, 1.0))
    parcial = (24.0 / np.pi) * (np.pi - theta)

    horas = np.where(maxima <= umbral, 24.0, np.where(minima >= umbral, 0.0, parcial))
    horas = np.where(np.isnan(maxima) | np.isnan(minima), np.nan, horas)
    return _devolver(horas, indice)
