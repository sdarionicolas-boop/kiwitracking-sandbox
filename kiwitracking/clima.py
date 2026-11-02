"""GDD por temporada y horas de frío por ventana a partir de temperaturas diarias (spec 002)."""

from dataclasses import dataclass, field

import pandas as pd

from kiwitracking.clima_calculo import gdd_diario, horas_frio_diarias
from kiwitracking.clima_entrada import preparar_clima_con_origen
from kiwitracking.clima_origen import contar_estimados, estimados_vacios
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.clima_periodos import cobertura_temporadas, cobertura_ventanas, etiqueta_temporada, etiqueta_ventana
from kiwitracking.resultado import Advertencia
from kiwitracking.validacion import ESTADOS_FRIO

COLUMNAS_FRIO = [
    "periodo", "Horas_Frio", "estado_frio", "dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo",
]


@dataclass
class ResultadoClima:
    """`gdd`: una fila por temporada; `frio`: una fila por ventana de frío; `advertencias`: en orden;
    `estimados`: días estimados por ventana (spec 005), sin filas si el clima no trae `origen`."""

    gdd: pd.DataFrame
    frio: pd.DataFrame
    advertencias: list[Advertencia]
    ventana_frio: str
    estimados: pd.DataFrame = field(default_factory=estimados_vacios)


def formatear_porcentaje(fraccion: float) -> str:
    return f"{fraccion * 100:.1f}".replace(".", ",") + " %"


def calcular_gdd(
    tabla: pd.DataFrame, parametros: ParametrosClima
) -> tuple[pd.DataFrame, list[tuple[int, Advertencia]]]:
    """GDD total por temporada, con su cobertura (RF-17), y un aviso por cada temporada incompleta (RF-18).

    `tabla` es la tabla ya preparada (`preparar_clima`). El GDD se calcula con los días disponibles aunque
    la temporada sea incompleta: en ese caso queda subestimado y el aviso es la señal. Cada aviso viaja
    con la etiqueta de su temporada, para ordenar después los avisos de GDD y de frío por período.
    """
    diario = tabla.assign(gdd=gdd_diario(tabla["Tmax"], tabla["Tmin"], parametros.tbase))
    totales = diario.groupby(etiqueta_temporada(diario["date"], parametros))["gdd"].sum()

    cobertura = cobertura_temporadas(tabla, parametros)
    gdd = cobertura.assign(GDD_total=totales.reindex(cobertura.index).astype(float))
    gdd = gdd.reset_index().rename(columns={"etiqueta": "temporada"})
    gdd = gdd[["temporada", "GDD_total", "dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo"]]

    advertencias = [
        (
            int(fila.temporada),
            Advertencia(
                "PERIODO_INCOMPLETO",
                f"GDD, temporada {fila.temporada}: cobertura {formatear_porcentaje(fila.cobertura)}, hueco máximo {fila.hueco_maximo} días; "
                "el GDD está calculado solo con los días disponibles.",
            ),
        )
        for fila in gdd.itertuples()
        if not fila.completo
    ]
    return gdd, advertencias


def _clasificar(horas: float, parametros: ParametrosClima) -> str:
    deficiente, adecuado, optimo = ESTADOS_FRIO  # los textos son los de la spec 001
    if horas >= parametros.umbral_optimo:
        return optimo
    return adecuado if horas >= parametros.umbral_adecuado else deficiente


def calcular_frio(
    tabla: pd.DataFrame, parametros: ParametrosClima
) -> tuple[pd.DataFrame, list[tuple[int, Advertencia]]]:
    """Horas de frío por ventana (RF-19), con su estado solo si la ventana es completa (RF-20, RF-21).

    `tabla` es la tabla ya preparada. Las horas se calculan con los días disponibles aunque la ventana sea
    incompleta, pero esa ventana no se clasifica: un estado armado con datos truncados es lo que produjo
    los falsos "Deficiente" de los bordes del registro.
    """
    diario = tabla.assign(horas=horas_frio_diarias(tabla["Tmax"], tabla["Tmin"], parametros.umbral_frio))
    totales = diario.groupby(etiqueta_ventana(diario["date"], parametros))["horas"].sum()

    cobertura = cobertura_ventanas(tabla, parametros)
    frio = cobertura.assign(Horas_Frio=totales.reindex(cobertura.index).astype(float))
    frio["estado_frio"] = [
        _clasificar(fila.Horas_Frio, parametros) if fila.completo else None for fila in frio.itertuples()
    ]
    frio = frio.reset_index().rename(columns={"etiqueta": "periodo"})[COLUMNAS_FRIO]

    advertencias = []
    for fila in frio.itertuples():
        if not fila.completo:
            advertencias.append(
                (
                    int(fila.periodo),
                    Advertencia(
                        "PERIODO_INCOMPLETO",
                        f"Frío, ventana {fila.periodo}: cobertura {formatear_porcentaje(fila.cobertura)}, hueco máximo {fila.hueco_maximo} días; "
                        "no se clasifica.",
                    ),
                )
            )
        elif fila.cobertura < 1:
            advertencias.append(
                (
                    int(fila.periodo),
                    Advertencia(
                        "COBERTURA_PARCIAL",
                        f"Frío, ventana {fila.periodo}: cobertura {formatear_porcentaje(fila.cobertura)}; las horas están calculadas "
                        "con los días disponibles.",
                    ),
                )
            )
    return frio, advertencias


def calcular_clima(tabla: pd.DataFrame, parametros: ParametrosClima | None = None) -> ResultadoClima:
    """Valida la tabla diaria y calcula el clima agrícola (RF-26). No modifica la entrada.

    Las advertencias salen primero las de la entrada y después las de cada período en orden cronológico;
    con el mismo año, la del GDD antes que la del frío.
    """
    parametros = parametros or ParametrosClima()
    con_origen, advertencias = preparar_clima_con_origen(tabla, parametros)
    preparada = con_origen.drop(columns="estimado", errors="ignore")

    gdd, avisos_gdd = calcular_gdd(preparada, parametros)
    frio, avisos_frio = calcular_frio(preparada, parametros)
    por_periodo = [(etiqueta, 0, aviso) for etiqueta, aviso in avisos_gdd] + [(etiqueta, 1, aviso) for etiqueta, aviso in avisos_frio]
    por_periodo.sort(key=lambda fila: (fila[0], fila[1]))
    return ResultadoClima(
        gdd=gdd,
        frio=frio,
        advertencias=advertencias + [aviso for _, _, aviso in por_periodo],
        ventana_frio=parametros.ventana_frio,
        estimados=contar_estimados(con_origen, parametros),
    )
