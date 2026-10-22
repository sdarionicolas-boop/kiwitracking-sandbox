"""Corrección del KVPI por sesgo de malla de protección."""

from dataclasses import dataclass

import pandas as pd
from scipy import stats

from kiwitracking.huella import huella
from kiwitracking.resultado import Advertencia
from kiwitracking.validacion import validar_parametros


@dataclass(frozen=True)
class FactorMalla:
    """FC = media(fuera de malla) / media(bajo malla), con su prueba t y el tamaño de cada grupo.

    `fc` y `p_valor` son None cuando no se pueden calcular con sentido; qué hacer entonces
    lo decide la lógica de corrección, no este cálculo.
    """

    fc: float | None
    p_valor: float | None
    n_bajo: int
    n_fuera: int
    media_bajo: float | None = None


def calcular_factor(tabla: pd.DataFrame) -> FactorMalla:
    bajo = tabla.loc[tabla["bajo_malla"] == 1, "KVPI_mean"]
    fuera = tabla.loc[tabla["bajo_malla"] == 0, "KVPI_mean"]

    fc = None
    if len(bajo) > 0 and len(fuera) > 0 and bajo.mean() != 0:
        fc = float(fuera.mean() / bajo.mean())

    p_valor = None
    hay_variacion = bajo.var() > 0 or fuera.var() > 0
    if len(bajo) >= 2 and len(fuera) >= 2 and hay_variacion:
        p_valor = float(stats.ttest_ind(fuera, bajo, equal_var=True).pvalue)

    media_bajo = float(bajo.mean()) if len(bajo) > 0 else None
    return FactorMalla(fc=fc, p_valor=p_valor, n_bajo=len(bajo), n_fuera=len(fuera), media_bajo=media_bajo)


def evaluar_confirmacion(
    tabla: pd.DataFrame, huella_confirmada: str | None, huella_referencia: str | None = None
) -> Advertencia | None:
    """Verifica la confirmación visual. Devuelve None si la huella coincide con la tabla.

    `huella_referencia` es la huella contra la que se compara (por defecto, la de `tabla`); sirve
    cuando la tabla ya perdió plantas pero lo confirmado fue el mapa de la tabla completa.

    No depende del modo de corrección: sin confirmación válida no se corrige en ningún modo.
    """
    confirmada = (huella_confirmada or "").strip()
    if not confirmada:
        return Advertencia(
            "FALTA_CONFIRMACION",
            "Falta la validación visual de las plantas bajo malla: no se aplicó ninguna corrección.",
        )
    if confirmada != (huella_referencia or huella(tabla)):
        return Advertencia(
            "HUELLA_NO_COINCIDE",
            "La huella confirmada no corresponde a estos datos (cambió el conjunto de plantas "
            "bajo malla): no se aplicó ninguna corrección.",
        )
    return None


@dataclass(frozen=True)
class DecisionCorreccion:
    corregir: bool
    advertencia: Advertencia | None = None


def decidir_modo_auto(
    factor: FactorMalla, alfa: float = 0.05, min_plantas_grupo: int = 2
) -> DecisionCorreccion:
    """Decide si corregir en modo "auto" (RF-7, RF-10, RF-11). Revisa las causas en este orden."""
    if factor.n_bajo == 0 or factor.n_fuera == 0:
        return DecisionCorreccion(False)  # lote sin malla (o todo bajo malla): no es un error

    if factor.n_bajo < min_plantas_grupo or factor.n_fuera < min_plantas_grupo:
        return DecisionCorreccion(
            False,
            Advertencia(
                "GRUPO_CHICO",
                f"No se corrigió: un grupo tiene menos de {min_plantas_grupo} plantas "
                f"(bajo malla: {factor.n_bajo}, fuera de malla: {factor.n_fuera}).",
            ),
        )

    if factor.media_bajo is None or factor.media_bajo <= 0:
        return DecisionCorreccion(
            False,
            Advertencia("MEDIA_NO_POSITIVA", "No se corrigió: la media del KVPI bajo malla no es mayor que 0."),
        )

    if factor.p_valor is None:
        return DecisionCorreccion(
            False,
            Advertencia("P_NO_DISPONIBLE", "No se corrigió: no se pudo calcular el p-valor (los grupos no tienen variación)."),
        )

    if factor.p_valor >= alfa:
        return DecisionCorreccion(
            False,
            Advertencia(
                "NO_SIGNIFICATIVO",
                f"No se corrigió: la diferencia entre grupos no es significativa (p = {factor.p_valor:.4g}, alfa = {alfa}).",
            ),
        )

    return DecisionCorreccion(True)


def decidir_correccion(
    factor: FactorMalla, modo: str, alfa: float = 0.05, min_plantas_grupo: int = 2
) -> DecisionCorreccion:
    """Decide si corregir según el modo: "auto", "forzar" o "desactivar" (RF-7, RF-11 a RF-14)."""
    validar_parametros(correccion=modo)

    if modo == "desactivar":
        return DecisionCorreccion(False)
    if modo == "auto":
        return decidir_modo_auto(factor, alfa, min_plantas_grupo)

    # "forzar": ignora el p-valor, pero no puede saltearse que haya grupos y una media positiva.
    if factor.n_bajo < min_plantas_grupo or factor.n_fuera < min_plantas_grupo:
        return DecisionCorreccion(
            False,
            Advertencia(
                "GRUPO_CHICO",
                f"No se pudo forzar la corrección: un grupo tiene menos de {min_plantas_grupo} plantas "
                f"(bajo malla: {factor.n_bajo}, fuera de malla: {factor.n_fuera}).",
            ),
        )
    if factor.media_bajo is None or factor.media_bajo <= 0:
        return DecisionCorreccion(
            False,
            Advertencia("MEDIA_NO_POSITIVA", "No se pudo forzar la corrección: la media del KVPI bajo malla no es mayor que 0."),
        )
    p = "no disponible" if factor.p_valor is None else f"{factor.p_valor:.4g}"
    return DecisionCorreccion(
        True, Advertencia("CORRECCION_FORZADA", f"Corrección forzada por el usuario (p = {p}).")
    )


def aplicar_correccion(tabla: pd.DataFrame, fc: float | None) -> pd.DataFrame:
    """Copia de la tabla con KVPI_corregido: KVPI_mean x FC solo bajo malla; sin FC, igual a KVPI_mean."""
    resultado = tabla.copy()
    resultado["KVPI_corregido"] = resultado["KVPI_mean"]
    if fc is not None:
        bajo_malla = resultado["bajo_malla"] == 1
        resultado.loc[bajo_malla, "KVPI_corregido"] = resultado.loc[bajo_malla, "KVPI_mean"] * fc
    return resultado


@dataclass
class CorreccionResuelta:
    tabla: pd.DataFrame
    factor: FactorMalla
    aplicada: bool
    advertencias: list[Advertencia]


def resolver_correccion(
    tabla: pd.DataFrame,
    modo: str,
    huella_confirmada: str | None,
    alfa: float = 0.05,
    min_plantas_grupo: int = 2,
    huella_referencia: str | None = None,
) -> CorreccionResuelta:
    """Corrección completa: primero la confirmación visual (RF-8, RF-9), después la decisión."""
    validar_parametros(correccion=modo)
    factor = calcular_factor(tabla)

    bloqueo = evaluar_confirmacion(tabla, huella_confirmada, huella_referencia)
    if bloqueo is not None:
        return CorreccionResuelta(aplicar_correccion(tabla, None), factor, False, [bloqueo])

    decision = decidir_correccion(factor, modo, alfa, min_plantas_grupo)
    advertencias = [decision.advertencia] if decision.advertencia is not None else []
    fc = factor.fc if decision.corregir else None
    return CorreccionResuelta(aplicar_correccion(tabla, fc), factor, decision.corregir, advertencias)
