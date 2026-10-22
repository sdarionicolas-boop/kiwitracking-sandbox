"""Flujo completo del núcleo: de la tabla de plantas al resultado con ambientes y recomendaciones."""

import pandas as pd

from kiwitracking.clasificacion import (
    ajustar_por_frio,
    asignar_ambiente,
    asignar_recomendacion,
    calcular_estabilidad,
    calcular_umbrales,
)
from kiwitracking.correccion import resolver_correccion
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada, Resultado, Resumen
from kiwitracking.validacion import descartar_duplicados, excluir_sin_kvpi, validar_parametros, validar_tabla


def analizar(
    tabla: pd.DataFrame,
    correccion: str = "auto",
    huella_confirmada: str | None = None,
    estado_frio_ultima_campana: str | None = None,
    alfa: float = 0.05,
    min_plantas_grupo: int = 2,
    p_ambiente: tuple[float, float] = (33, 66),
    p_estabilidad: float = 75,
    escalar_std: bool = True,
    prueba_t: str = "welch",
) -> Resultado:
    """Corrige por malla, clasifica ambientes y recomienda (RF-1 a RF-26). No modifica la entrada.

    La huella se calcula sobre la tabla de entrada completa: es la que el usuario vio en el mapa.
    """
    validar_parametros(correccion, estado_frio_ultima_campana, prueba_t)
    validar_tabla(tabla)
    huella_entrada = huella(tabla)

    plantas, advertencias = descartar_duplicados(tabla)
    plantas, avisos = excluir_sin_kvpi(plantas)
    advertencias += avisos
    if plantas.empty:
        raise ErrorDeEntrada("Ninguna planta tiene KVPI_mean válido: no hay nada que analizar.")

    correccion_resuelta = resolver_correccion(
        plantas, correccion, huella_confirmada, alfa, min_plantas_grupo,
        huella_referencia=huella_entrada, prueba_t=prueba_t,
    )
    advertencias += correccion_resuelta.advertencias

    plantas, avisos = calcular_estabilidad(correccion_resuelta.tabla, escalar_std)
    advertencias += avisos

    umbrales = calcular_umbrales(plantas, p_ambiente, p_estabilidad)
    plantas = asignar_recomendacion(asignar_ambiente(plantas, umbrales), umbrales)

    plantas, avisos = ajustar_por_frio(plantas, estado_frio_ultima_campana)
    advertencias += avisos

    factor = correccion_resuelta.factor
    resumen = Resumen(
        fc=factor.fc,
        p_valor=factor.p_valor,
        n_bajo_malla=factor.n_bajo,
        n_fuera_malla=factor.n_fuera,
        correccion_aplicada=correccion_resuelta.aplicada,
        p33=umbrales.p33,
        p66=umbrales.p66,
        p75_estabilidad=umbrales.p75_estabilidad,
        huella=huella_entrada,
        escalar_std=escalar_std and correccion_resuelta.aplicada,
        prueba_t=prueba_t,
    )
    return Resultado(tabla=plantas, resumen=resumen, advertencias=advertencias)
