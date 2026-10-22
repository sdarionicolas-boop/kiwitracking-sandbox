import math

import pandas as pd
import pytest

from kiwitracking.clasificacion import calcular_estabilidad, calcular_umbrales


def _tabla(corregido, std):
    return pd.DataFrame(
        {
            "id": range(1, len(corregido) + 1),
            "KVPI_mean": corregido,
            "KVPI_corregido": corregido,
            "KVPI_std": std,
            "bajo_malla": [0] * len(corregido),
        }
    )


# --- T10: estabilidad -------------------------------------------------------------------


def test_rf20_estabilidad_es_kvpi_corregido_sobre_kvpi_std():
    tabla, _ = calcular_estabilidad(_tabla(corregido=[0.60, 0.50, 0.45], std=[0.03, 0.05, 0.015]))

    assert tabla["estabilidad"].tolist() == pytest.approx([20.0, 10.0, 30.0])


def test_rf20_usa_el_kvpi_corregido_y_no_el_kvpi_mean():
    tabla = _tabla(corregido=[0.60], std=[0.03])
    tabla["KVPI_mean"] = [0.30]  # la planta estaba bajo malla y se corrigió al doble

    resultado, _ = calcular_estabilidad(tabla)

    assert resultado["estabilidad"].tolist() == pytest.approx([20.0])


def test_rf20_el_std_no_se_corrige_se_usa_tal_cual():
    # Comportamiento heredado del notebook (duda abierta): el KVPI_std no se escala con el FC.
    tabla = _tabla(corregido=[0.60], std=[0.03])
    tabla["KVPI_mean"] = [0.50]  # FC = 1.2

    resultado, _ = calcular_estabilidad(tabla)

    assert resultado["estabilidad"].iloc[0] == pytest.approx(0.60 / 0.03)


def test_rf20_conserva_las_columnas_y_agrega_estabilidad():
    entrada = _tabla(corregido=[0.60, 0.50], std=[0.03, 0.05])

    resultado, _ = calcular_estabilidad(entrada)

    assert list(resultado.columns) == list(entrada.columns) + ["estabilidad"]


def test_rf20_sin_std_cero_no_hay_advertencias():
    _, advertencias = calcular_estabilidad(_tabla(corregido=[0.60, 0.50], std=[0.03, 0.05]))

    assert advertencias == []


def test_rf21_con_std_cero_la_estabilidad_queda_vacia_y_hay_advertencia_std_cero():
    tabla, advertencias = calcular_estabilidad(_tabla(corregido=[0.60, 0.50, 0.55], std=[0.03, 0.0, 0.0]))

    assert tabla["estabilidad"].iloc[0] == pytest.approx(20.0)
    assert math.isnan(tabla["estabilidad"].iloc[1])
    assert math.isnan(tabla["estabilidad"].iloc[2])
    assert len(advertencias) == 1
    assert advertencias[0].codigo == "STD_CERO"
    assert "2" in advertencias[0].mensaje


def test_rf21_el_std_cero_no_produce_infinito():
    tabla, _ = calcular_estabilidad(_tabla(corregido=[0.60], std=[0.0]))

    assert not math.isinf(tabla["estabilidad"].iloc[0])


def test_rf20_no_modifica_la_tabla_de_entrada():
    entrada = _tabla(corregido=[0.60, 0.50], std=[0.03, 0.0])
    copia = entrada.copy()

    calcular_estabilidad(entrada)

    pd.testing.assert_frame_equal(entrada, copia)


# --- T11: umbrales ----------------------------------------------------------------------


def _tabla_umbrales(corregido, estabilidad):
    return pd.DataFrame(
        {
            "id": range(1, len(corregido) + 1),
            "KVPI_corregido": corregido,
            "estabilidad": estabilidad,
        }
    )


def test_rf22_los_percentiles_coinciden_con_el_calculo_a_mano_por_interpolacion_lineal():
    # 11 valores 0..10: el percentil p cae en la posición p/100 x 10, p33 = 3.3, p66 = 6.6
    valores = [float(v) for v in range(11)]

    umbrales = calcular_umbrales(_tabla_umbrales(valores, valores))

    assert umbrales.p33 == pytest.approx(3.3)
    assert umbrales.p66 == pytest.approx(6.6)
    assert umbrales.p75_estabilidad == pytest.approx(7.5)


def test_rf22_no_depende_del_orden_de_las_filas():
    valores = [float(v) for v in range(11)]
    desordenados = valores[5:] + valores[:5]

    assert calcular_umbrales(_tabla_umbrales(desordenados, desordenados)) == calcular_umbrales(
        _tabla_umbrales(valores, valores)
    )


def test_rf22_el_p75_de_estabilidad_no_cuenta_las_plantas_sin_estabilidad():
    estabilidad = [float("nan"), 0.0, 1.0, 2.0, 3.0, 4.0, float("nan")]  # válidas: 0..4 -> p75 = 3.0
    corregido = [0.1 * v for v in range(1, 8)]

    umbrales = calcular_umbrales(_tabla_umbrales(corregido, estabilidad))

    assert umbrales.p75_estabilidad == pytest.approx(3.0)


def test_rf22_p33_y_p66_se_calculan_sobre_todas_las_plantas_aunque_no_tengan_estabilidad():
    corregido = [float(v) for v in range(11)]
    estabilidad = [float("nan")] * 11

    umbrales = calcular_umbrales(_tabla_umbrales(corregido, estabilidad))

    assert umbrales.p33 == pytest.approx(3.3)
    assert umbrales.p75_estabilidad is None


def test_rf22_los_percentiles_son_parametros_con_33_66_y_75_por_defecto():
    valores = [float(v) for v in range(11)]
    tabla = _tabla_umbrales(valores, valores)

    umbrales = calcular_umbrales(tabla, p_ambiente=(25, 50), p_estabilidad=90)

    assert umbrales.p33 == pytest.approx(2.5)
    assert umbrales.p66 == pytest.approx(5.0)
    assert umbrales.p75_estabilidad == pytest.approx(9.0)


def test_rf22_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_umbrales([0.5, 0.6, 0.55], [10.0, 20.0, 15.0])
    copia = tabla.copy()

    calcular_umbrales(tabla)

    pd.testing.assert_frame_equal(tabla, copia)
