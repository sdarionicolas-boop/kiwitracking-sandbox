import math

import numpy as np
import pandas as pd
import pytest

from kiwitracking.clima_calculo import gdd_diario, horas_frio_diarias


def _horas_notebook(tmin, tmax, umbral=7.0):
    """Copia independiente de `horas_bajo_umbral` del notebook 03 (celda 14), con su misma lógica escalar."""
    if tmax <= umbral:
        return 24.0
    if tmin >= umbral:
        return 0.0
    amp = (tmax - tmin) / 2.0
    tmedia = (tmax + tmin) / 2.0
    if amp <= 0:
        return 24.0 if tmedia < umbral else 0.0
    theta = np.arccos(np.clip((umbral - tmedia) / amp, -1.0, 1.0))
    return (24.0 / np.pi) * (np.pi - theta)


# --- T2.7: GDD diario --------------------------------------------------------------------


def test_rf10_gdd_es_la_temperatura_media_menos_la_base():
    # Tmedia = (30 + 20) / 2 = 25  ->  25 - 10 = 15
    assert gdd_diario([30.0], [20.0]).tolist() == pytest.approx([15.0])


def test_rf10_gdd_no_es_negativo_cuando_la_media_esta_por_debajo_de_la_base():
    assert gdd_diario([12.0, 9.0], [4.0, -2.0]).tolist() == [0.0, 0.0]


def test_rf10_gdd_es_cero_cuando_la_media_es_exactamente_la_base():
    assert gdd_diario([14.0], [6.0]).tolist() == [0.0]


def test_rf10_tbase_es_un_parametro():
    assert gdd_diario([30.0], [20.0], tbase=12.5).tolist() == pytest.approx([12.5])


def test_rf10_un_dia_con_temperatura_vacia_da_vacio():
    resultado = gdd_diario([30.0, float("nan"), 30.0], [20.0, 10.0, float("nan")])

    assert resultado[0] == pytest.approx(15.0)
    assert math.isnan(resultado[1]) and math.isnan(resultado[2])


def test_rf10_con_series_devuelve_una_serie_con_el_mismo_indice():
    tmax = pd.Series([30.0, 12.0], index=[7, 9])
    tmin = pd.Series([20.0, 4.0], index=[7, 9])

    resultado = gdd_diario(tmax, tmin)

    assert isinstance(resultado, pd.Series)
    assert resultado.index.tolist() == [7, 9]
    assert resultado.tolist() == pytest.approx([15.0, 0.0])


# --- T2.7: horas de frío con el modelo de coseno ------------------------------------------


def test_rf11_valor_calculado_a_mano_con_tmax_10_tmin_0_y_umbral_7():
    # Tmedia = 5, amp = 5, (7 - 5) / 5 = 0,4; theta = arccos(0,4); horas = 24/pi x (pi - theta)
    assert horas_frio_diarias([10.0], [0.0]).tolist() == pytest.approx([15.1437], abs=1e-3)


def test_rf11_si_la_media_es_el_umbral_son_exactamente_12_horas_por_simetria():
    # Tmedia = 7 -> razon = 0 -> theta = pi/2 -> 12 horas
    assert horas_frio_diarias([14.0], [0.0]).tolist() == pytest.approx([12.0])


@pytest.mark.parametrize("tmax,tmin", [(5.0, -3.0), (7.0, 0.0), (7.0, -10.0)])
def test_rf11_si_tmax_no_supera_el_umbral_son_24_horas(tmax, tmin):
    assert horas_frio_diarias([tmax], [tmin]).tolist() == [24.0]


@pytest.mark.parametrize("tmax,tmin", [(20.0, 7.0), (25.0, 10.0), (8.0, 7.5)])
def test_rf11_si_tmin_alcanza_el_umbral_son_0_horas(tmax, tmin):
    assert horas_frio_diarias([tmax], [tmin]).tolist() == [0.0]


@pytest.mark.parametrize("temperatura,esperado", [(7.0, 24.0), (6.0, 24.0), (8.0, 0.0)])
def test_rf11_con_tmax_igual_a_tmin_se_aplica_primero_la_regla_de_las_24_horas(temperatura, esperado):
    # Con Tmax = Tmin = umbral se cumplen a la vez "Tmax <= umbral" y "Tmin >= umbral": gana la de 24 h (como el notebook).
    assert horas_frio_diarias([temperatura], [temperatura]).tolist() == [esperado]


def test_rf11_el_umbral_es_un_parametro():
    # Con umbral 10, un día de 10 a 0 queda por debajo todo el día.
    assert horas_frio_diarias([10.0], [0.0], umbral=10.0).tolist() == [24.0]
    assert horas_frio_diarias([10.0], [0.0], umbral=7.0)[0] < 24.0


def test_rf11_un_dia_con_temperatura_vacia_da_vacio_y_no_cero():
    resultado = horas_frio_diarias([10.0, float("nan"), 10.0], [0.0, 0.0, float("nan")])

    assert resultado[0] == pytest.approx(15.1437, abs=1e-3)
    assert math.isnan(resultado[1]) and math.isnan(resultado[2])


def test_rf11_coincide_con_la_funcion_del_notebook_en_1000_pares_aleatorios():
    generador = np.random.default_rng(42)
    tmin = generador.uniform(-12.0, 25.0, 1000)
    tmax = tmin + generador.uniform(0.0, 22.0, 1000)

    vectorizado = horas_frio_diarias(tmax, tmin)

    esperado = np.array([_horas_notebook(a, b) for a, b in zip(tmin, tmax)])
    assert vectorizado == pytest.approx(esperado, abs=1e-9)


def test_rf11_coincide_con_el_notebook_en_los_casos_borde():
    pares = [(7.0, 7.0), (7.0, 6.9), (7.1, 7.0), (14.0, 0.0), (0.0, 0.0), (30.0, 30.0), (7.0, -7.0), (21.0, 7.0), (7.000001, 6.999999)]
    tmax = np.array([p[0] for p in pares])
    tmin = np.array([p[1] for p in pares])

    esperado = np.array([_horas_notebook(a, b) for a, b in zip(tmin, tmax)])
    assert horas_frio_diarias(tmax, tmin) == pytest.approx(esperado, abs=1e-9)


def test_rf11_las_horas_estan_siempre_entre_0_y_24():
    generador = np.random.default_rng(7)
    tmin = generador.uniform(-30.0, 40.0, 2000)
    tmax = tmin + generador.uniform(0.0, 30.0, 2000)

    horas = horas_frio_diarias(tmax, tmin)

    assert (horas >= 0).all() and (horas <= 24).all()


def test_rf11_un_dia_mas_calido_nunca_tiene_mas_horas_de_frio_con_la_misma_amplitud():
    # Misma amplitud térmica (12 grados) y la media subiendo de a 0,5: las horas de frío no pueden aumentar.
    medias = np.arange(-5.0, 20.0, 0.5)
    horas = horas_frio_diarias(medias + 6.0, medias - 6.0)

    assert (np.diff(horas) <= 1e-9).all()


def test_rf11_con_series_devuelve_una_serie_con_el_mismo_indice():
    tmax = pd.Series([10.0, 20.0], index=[3, 5])
    tmin = pd.Series([0.0, 7.0], index=[3, 5])

    resultado = horas_frio_diarias(tmax, tmin)

    assert isinstance(resultado, pd.Series)
    assert resultado.index.tolist() == [3, 5]
    assert resultado.tolist() == pytest.approx([15.1437, 0.0], abs=1e-3)


def test_rf10_y_rf11_no_modifican_las_series_de_entrada():
    tmax = pd.Series([10.0, 20.0])
    tmin = pd.Series([0.0, 7.0])
    copias = tmax.copy(), tmin.copy()

    gdd_diario(tmax, tmin)
    horas_frio_diarias(tmax, tmin)

    pd.testing.assert_series_equal(tmax, copias[0])
    pd.testing.assert_series_equal(tmin, copias[1])


def test_rf11_no_emite_avisos_de_numpy_con_amplitud_cero_ni_con_vacios():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        horas_frio_diarias([10.0, 8.0, float("nan")], [10.0, 8.0, 5.0])


@pytest.mark.parametrize(
    "tmax,tmin",
    [(5.0, float("nan")), (float("nan"), 10.0), (float("nan"), -5.0), (float("nan"), float("nan"))],
)
def test_rf11_un_dia_faltante_nunca_se_confunde_con_24_o_0_horas_aunque_la_otra_temperatura_cumpla_una_regla(tmax, tmin):
    # Con Tmax = 5 la regla de 24 h se cumpliría sin mirar Tmin; con Tmin = 10, la de 0 h sin mirar Tmax.
    assert math.isnan(horas_frio_diarias([tmax], [tmin])[0])
