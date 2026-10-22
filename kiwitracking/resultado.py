"""Tipos de salida del núcleo."""

from dataclasses import dataclass, field

import pandas as pd


class ErrorDeEntrada(ValueError):
    """La entrada no permite un análisis con sentido."""


@dataclass(frozen=True)
class Advertencia:
    """Aviso que no detiene el análisis. El código es estable; el mensaje es para personas."""

    codigo: str
    mensaje: str


@dataclass
class Resumen:
    fc: float | None = None
    p_valor: float | None = None
    n_bajo_malla: int | None = None
    n_fuera_malla: int | None = None
    correccion_aplicada: bool = False
    p33: float | None = None
    p66: float | None = None
    p75_estabilidad: float | None = None
    huella: str | None = None
    escalar_std: bool = False  # True solo si se pidió y hubo corrección (si no, no hay nada que escalar)
    prueba_t: str = "welch"


@dataclass
class Resultado:
    tabla: pd.DataFrame
    resumen: Resumen
    advertencias: list[Advertencia] = field(default_factory=list)
