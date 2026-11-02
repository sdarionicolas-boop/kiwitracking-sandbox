"""Días estimados del clima (spec 005): parámetro, entrada y recuento por ventana (RF-1 a RF-5 y RF-9)."""

import numpy as np
import pytest

from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada

# --- T5.0: el parámetro `origenes_estimados` (RF-9) ------------------------------------------------------------


def test_rf9_el_valor_por_defecto_es_interpolado():
    assert ParametrosClima().origenes_estimados == ("interpolado",)


def test_rf9_una_lista_se_convierte_en_tupla():
    parametros = ParametrosClima(origenes_estimados=["interpolado", "estimado"])
    assert parametros.origenes_estimados == ("interpolado", "estimado")
    assert isinstance(parametros.origenes_estimados, tuple)


def test_rf9_acepta_una_tupla_de_un_solo_elemento():
    assert ParametrosClima(origenes_estimados=("satelital",)).origenes_estimados == ("satelital",)


@pytest.mark.parametrize(
    "valor",
    [
        [],
        (),
        "interpolado",
        None,
        3,
        {"interpolado"},
        [""],
        ["   "],
        ["interpolado", ""],
        ["interpolado", None],
        ["interpolado", 3],
        [np.nan],
    ],
)
def test_rf9_un_valor_no_permitido_da_error_con_lo_que_se_espera(valor):
    with pytest.raises(ErrorDeEntrada, match="origenes_estimados") as error:
        ParametrosClima(origenes_estimados=valor)
    assert "lista" in str(error.value) and "textos" in str(error.value)


def test_rf9_los_demas_parametros_no_cambian():
    parametros = ParametrosClima()
    assert (parametros.ventana_frio, parametros.cobertura_minima, parametros.max_hueco_dias) == ("invierno", 0.9, 7)
    assert parametros.umbral_optimo == 950 and parametros.meses_frio == (5, 6, 7, 8)
