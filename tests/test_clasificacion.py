import math

import pandas as pd
import pytest

from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.clasificacion import (
    Umbrales,
    ajustar_por_frio,
    asignar_ambiente,
    asignar_recomendacion,
    calcular_estabilidad,
    calcular_umbrales,
)


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


# --- T12: ambiente ----------------------------------------------------------------------

UMBRALES = Umbrales(p33=0.50, p66=0.60, p75_estabilidad=20.0)


def _tabla_ambiente(corregido):
    return pd.DataFrame({"id": range(1, len(corregido) + 1), "KVPI_corregido": corregido})


def test_rf23_asigna_alto_potencial_transicional_y_limitante():
    tabla = asignar_ambiente(_tabla_ambiente([0.70, 0.55, 0.40]), UMBRALES)

    assert tabla["ambiente"].tolist() == ["Alto Potencial", "Transicional", "Limitante"]


def test_rf23_una_planta_justo_en_p66_es_alto_potencial():
    tabla = asignar_ambiente(_tabla_ambiente([0.60]), UMBRALES)

    assert tabla["ambiente"].tolist() == ["Alto Potencial"]


def test_rf23_una_planta_justo_en_p33_es_transicional_y_no_limitante():
    tabla = asignar_ambiente(_tabla_ambiente([0.50]), UMBRALES)

    assert tabla["ambiente"].tolist() == ["Transicional"]


def test_rf23_una_planta_apenas_por_debajo_de_p33_es_limitante():
    tabla = asignar_ambiente(_tabla_ambiente([0.4999]), UMBRALES)

    assert tabla["ambiente"].tolist() == ["Limitante"]


def test_rf23_conserva_las_columnas_y_no_modifica_la_entrada():
    entrada = _tabla_ambiente([0.70, 0.40])
    copia = entrada.copy()

    resultado = asignar_ambiente(entrada, UMBRALES)

    assert list(resultado.columns) == list(copia.columns) + ["ambiente"]
    pd.testing.assert_frame_equal(entrada, copia)


# --- T13: recomendación -----------------------------------------------------------------
# UMBRALES: p33 = 0.50, p66 = 0.60, p75 de estabilidad = 20.0


def _tabla_recomendacion(filas):
    """`filas`: lista de (KVPI_corregido, estabilidad)."""
    return pd.DataFrame(
        {
            "id": range(1, len(filas) + 1),
            "KVPI_corregido": [f[0] for f in filas],
            "estabilidad": [f[1] for f in filas],
        }
    )


def test_rf24_mantener_con_potencial_alto_y_estabilidad_alta():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.70, 25.0)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Mantener"]


def test_rf24_intervenir_con_potencial_bajo_y_estabilidad_alta():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.40, 25.0)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Intervenir"]


def test_rf24_observar_con_potencial_intermedio_aunque_la_estabilidad_sea_alta():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.55, 25.0)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Observar"]


def test_rf24_observar_con_estabilidad_baja_aunque_el_potencial_sea_alto_o_bajo():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.70, 10.0), (0.40, 10.0)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Observar", "Observar"]


def test_rf24_estabilidad_justo_en_p75_alcanza():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.70, 20.0), (0.70, 19.999)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Mantener", "Observar"]


def test_rf24_potencial_justo_en_p66_es_mantener():
    tabla = asignar_recomendacion(_tabla_recomendacion([(0.60, 25.0)]), UMBRALES)

    assert tabla["recomendacion"].tolist() == ["Mantener"]


def test_rf24_potencial_justo_en_p33_es_intervenir_aunque_su_ambiente_sea_transicional():
    # Asimetría heredada de la metodología (duda abierta): Limitante es "< p33", Intervenir es "<= p33".
    tabla = _tabla_recomendacion([(0.50, 25.0)])

    recomendacion = asignar_recomendacion(tabla, UMBRALES)["recomendacion"].tolist()
    ambiente = asignar_ambiente(tabla, UMBRALES)["ambiente"].tolist()

    assert recomendacion == ["Intervenir"]
    assert ambiente == ["Transicional"]


def test_rf21_planta_sin_estabilidad_es_observar_aunque_su_potencial_sea_extremo():
    tabla = asignar_recomendacion(
        _tabla_recomendacion([(0.90, float("nan")), (0.10, float("nan"))]), UMBRALES
    )

    assert tabla["recomendacion"].tolist() == ["Observar", "Observar"]


def test_rf24_si_no_hay_p75_de_estabilidad_todas_son_observar():
    sin_p75 = Umbrales(p33=0.50, p66=0.60, p75_estabilidad=None)

    tabla = asignar_recomendacion(_tabla_recomendacion([(0.70, 25.0), (0.40, 25.0)]), sin_p75)

    assert tabla["recomendacion"].tolist() == ["Observar", "Observar"]


def test_rf24_conserva_las_columnas_y_no_modifica_la_entrada():
    entrada = _tabla_recomendacion([(0.70, 25.0), (0.40, 10.0)])
    copia = entrada.copy()

    resultado = asignar_recomendacion(entrada, UMBRALES)

    assert list(resultado.columns) == list(copia.columns) + ["recomendacion"]
    pd.testing.assert_frame_equal(entrada, copia)


# --- T14: ajuste por horas de frío ------------------------------------------------------


def _tabla_frio():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "recomendacion": ["Mantener", "Intervenir", "Observar", "Mantener"],
        }
    )


def test_rf25_con_frio_deficiente_las_mantener_pasan_a_observar():
    tabla, _ = ajustar_por_frio(_tabla_frio(), "Deficiente")

    assert tabla["recomendacion"].tolist() == ["Observar", "Intervenir", "Observar", "Observar"]


def test_rf25_con_frio_deficiente_no_se_tocan_intervenir_ni_observar():
    tabla, _ = ajustar_por_frio(_tabla_frio(), "Deficiente")

    assert tabla.loc[1, "recomendacion"] == "Intervenir"
    assert tabla.loc[2, "recomendacion"] == "Observar"


@pytest.mark.parametrize("estado", ["Adecuado", "Óptimo"])
def test_rf25_con_frio_adecuado_u_optimo_no_se_cambia_nada_ni_se_avisa(estado):
    tabla, advertencias = ajustar_por_frio(_tabla_frio(), estado)

    assert tabla["recomendacion"].tolist() == _tabla_frio()["recomendacion"].tolist()
    assert advertencias == []


def test_rf25_sin_estado_de_frio_no_hay_ajuste_y_se_avisa_sin_estado_frio():
    tabla, advertencias = ajustar_por_frio(_tabla_frio(), None)

    assert tabla["recomendacion"].tolist() == _tabla_frio()["recomendacion"].tolist()
    assert [a.codigo for a in advertencias] == ["SIN_ESTADO_FRIO"]


def test_rf25_con_frio_deficiente_no_hay_advertencia():
    _, advertencias = ajustar_por_frio(_tabla_frio(), "Deficiente")

    assert advertencias == []


def test_rf5_un_estado_de_frio_no_permitido_da_error():
    with pytest.raises(ErrorDeEntrada, match="Deficiente"):
        ajustar_por_frio(_tabla_frio(), "deficiente")


def test_rf25_no_modifica_la_tabla_de_entrada():
    entrada = _tabla_frio()
    copia = entrada.copy()

    ajustar_por_frio(entrada, "Deficiente")

    pd.testing.assert_frame_equal(entrada, copia)


# --- T24 (Cambio 1): estabilidad con escalar_std ----------------------------------------


def _tabla_corregida(medias, corregidos, stds):
    return pd.DataFrame(
        {
            "id": range(1, len(medias) + 1),
            "KVPI_mean": medias,
            "KVPI_corregido": corregidos,
            "KVPI_std": stds,
            "bajo_malla": [1 if c != m else 0 for m, c in zip(medias, corregidos)],
        }
    )


def test_rf27_escalar_std_es_falso_por_defecto_y_reproduce_el_comportamiento_anterior():
    tabla = _tabla_corregida([0.50, 0.60], [0.60, 0.60], [0.03, 0.04])

    por_defecto, _ = calcular_estabilidad(tabla)
    explicito, _ = calcular_estabilidad(tabla, escalar_std=False)

    pd.testing.assert_frame_equal(por_defecto, explicito)
    assert por_defecto["estabilidad"].tolist() == pytest.approx([0.60 / 0.03, 0.60 / 0.04])


def test_rf27_con_escalar_std_la_estabilidad_es_kvpi_mean_sobre_kvpi_std():
    # Planta bajo malla: media 0.50 corregida a 0.60 (FC = 1.2), std 0.03.
    tabla = _tabla_corregida([0.50], [0.60], [0.03])

    resultado, _ = calcular_estabilidad(tabla, escalar_std=True)

    assert resultado["estabilidad"].tolist() == pytest.approx([0.50 / 0.03])


def test_rf27_equivale_a_dividir_el_corregido_por_el_std_multiplicado_por_el_fc_de_la_planta():
    tabla = _tabla_corregida([0.50, 0.45], [0.60, 0.54], [0.03, 0.02])  # FC = 1.2 en ambas
    fc = 1.2

    resultado, _ = calcular_estabilidad(tabla, escalar_std=True)

    esperado = tabla["KVPI_corregido"] / (tabla["KVPI_std"] * fc)
    assert resultado["estabilidad"].tolist() == pytest.approx(esperado.tolist())


def test_rf27_en_las_plantas_no_corregidas_escalar_std_no_cambia_nada():
    tabla = _tabla_corregida([0.60, 0.55], [0.60, 0.55], [0.03, 0.04])  # ninguna se corrigió

    escalado, _ = calcular_estabilidad(tabla, escalar_std=True)
    normal, _ = calcular_estabilidad(tabla)

    assert escalado["estabilidad"].tolist() == pytest.approx(normal["estabilidad"].tolist())


def test_rf27_solo_cambia_la_estabilidad_de_las_plantas_corregidas():
    tabla = _tabla_corregida([0.60, 0.50], [0.60, 0.60], [0.03, 0.03])  # la 2.ª se corrigió

    escalado, _ = calcular_estabilidad(tabla, escalar_std=True)
    normal, _ = calcular_estabilidad(tabla)

    assert escalado["estabilidad"].iloc[0] == pytest.approx(normal["estabilidad"].iloc[0])
    assert escalado["estabilidad"].iloc[1] < normal["estabilidad"].iloc[1]


def test_rf21_con_escalar_std_y_std_cero_la_estabilidad_sigue_vacia_y_avisa():
    tabla = _tabla_corregida([0.50, 0.60], [0.60, 0.60], [0.0, 0.03])

    resultado, advertencias = calcular_estabilidad(tabla, escalar_std=True)

    assert math.isnan(resultado["estabilidad"].iloc[0])
    assert [a.codigo for a in advertencias] == ["STD_CERO"]


def test_rf27_escalar_std_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_corregida([0.50, 0.60], [0.60, 0.60], [0.03, 0.04])
    copia = tabla.copy()

    calcular_estabilidad(tabla, escalar_std=True)

    pd.testing.assert_frame_equal(tabla, copia)
