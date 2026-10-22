"""Estabilidad, umbrales, ambientes y recomendaciones."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from kiwitracking.resultado import Advertencia
from kiwitracking.validacion import validar_parametros


def calcular_estabilidad(
    tabla: pd.DataFrame, escalar_std: bool = True
) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Agrega `estabilidad` = KVPI_corregido / KVPI_std (RF-20, RF-21, RF-27).

    Por defecto (`escalar_std` verdadero) el desvío se escala con el mismo FC que la media: como
    KVPI_corregido es KVPI_mean x FC en las plantas corregidas (y KVPI_mean en las demás), la
    estabilidad resulta KVPI_mean / KVPI_std. Con `escalar_std` falso el KVPI_std se usa sin
    corregir, como en el análisis publicado (v1.1). Con KVPI_std = 0 la estabilidad queda vacía y
    se avisa.
    """
    resultado = tabla.copy()
    std_cero = resultado["KVPI_std"] == 0
    divisor = resultado["KVPI_std"].mask(std_cero)  # el 0 pasa a vacío: nunca hay infinito
    numerador = resultado["KVPI_mean"] if escalar_std else resultado["KVPI_corregido"]
    resultado["estabilidad"] = numerador / divisor

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


def asignar_ambiente(tabla: pd.DataFrame, umbrales: Umbrales) -> pd.DataFrame:
    """Agrega `ambiente` (RF-23): >= p66 Alto Potencial, < p33 Limitante, el resto Transicional."""
    resultado = tabla.copy()
    kvpi = resultado["KVPI_corregido"]
    resultado["ambiente"] = np.select(
        [kvpi >= umbrales.p66, kvpi < umbrales.p33],
        ["Alto Potencial", "Limitante"],
        default="Transicional",
    )
    return resultado


def asignar_recomendacion(tabla: pd.DataFrame, umbrales: Umbrales) -> pd.DataFrame:
    """Agrega `recomendacion` (RF-24): Mantener, Intervenir u Observar.

    Los bordes son los de `asignar_ambiente`: Mantener desde p66 e Intervenir por debajo de p33, así
    que toda "Mantener" es "Alto Potencial" y toda "Intervenir" es "Limitante".

    Sin estabilidad (vacía) o sin p75 de estabilidad, ninguna planta califica: Observar (RF-21).
    """
    resultado = tabla.copy()
    kvpi = resultado["KVPI_corregido"]
    if umbrales.p75_estabilidad is None:
        estable = pd.Series(False, index=resultado.index)
    else:
        estable = resultado["estabilidad"] >= umbrales.p75_estabilidad  # un vacío da False

    resultado["recomendacion"] = np.select(
        [estable & (kvpi >= umbrales.p66), estable & (kvpi < umbrales.p33)],
        ["Mantener", "Intervenir"],
        default="Observar",
    )
    return resultado


def ajustar_por_frio(
    tabla: pd.DataFrame, estado_frio_ultima_campana: str | None
) -> tuple[pd.DataFrame, list[Advertencia]]:
    """Con frío "Deficiente" en la última campaña, las "Mantener" pasan a "Observar" (RF-25).

    Sin el dato no se ajusta nada y se avisa (SIN_ESTADO_FRIO).
    """
    validar_parametros(estado_frio_ultima_campana=estado_frio_ultima_campana)
    resultado = tabla.copy()

    if estado_frio_ultima_campana is None:
        aviso = "No se informó el estado de horas de frío de la última campaña: no se aplicó el ajuste."
        return resultado, [Advertencia("SIN_ESTADO_FRIO", aviso)]

    if estado_frio_ultima_campana == "Deficiente":
        resultado.loc[resultado["recomendacion"] == "Mantener", "recomendacion"] = "Observar"
    return resultado, []
