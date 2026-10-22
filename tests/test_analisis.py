import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.clasificacion import calcular_umbrales
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada, Resultado


def _tabla_12():
    """8 plantas fuera de malla (KVPI ~0.61) y 4 bajo malla (KVPI ~0.46): FC ~1.35, p muy chico."""
    fuera = [0.62, 0.60, 0.64, 0.58, 0.66, 0.61, 0.59, 0.63]
    std_fuera = [0.02, 0.05, 0.02, 0.05, 0.03, 0.04, 0.05, 0.02]
    bajo = [0.46, 0.44, 0.48, 0.45]
    std_bajo = [0.03, 0.04, 0.02, 0.05]
    return pd.DataFrame(
        {
            "id": range(1, 13),
            "KVPI_mean": fuera + bajo,
            "KVPI_std": std_fuera + std_bajo,
            "bajo_malla": [0] * 8 + [1] * 4,
        }
    )


def _analizar_ok(tabla=None, **kwargs):
    tabla = _tabla_12() if tabla is None else tabla
    kwargs.setdefault("huella_confirmada", huella(tabla))
    kwargs.setdefault("estado_frio_ultima_campana", "Adecuado")
    return analizar(tabla, **kwargs)


def test_rf26_el_flujo_completo_devuelve_tabla_resumen_y_advertencias():
    tabla = _tabla_12()

    resultado = _analizar_ok(tabla)

    assert isinstance(resultado, Resultado)
    assert list(resultado.tabla.columns) == list(tabla.columns) + [
        "KVPI_corregido", "estabilidad", "ambiente", "recomendacion",
    ]
    assert resultado.tabla["id"].tolist() == tabla["id"].tolist()
    assert resultado.advertencias == []


def test_rf26_el_resumen_trae_fc_p_tamanos_umbrales_huella_y_si_se_corrigio():
    tabla = _tabla_12()

    resumen = _analizar_ok(tabla).resumen

    assert resumen.correccion_aplicada is True
    assert resumen.fc == pytest.approx(1.3470, abs=1e-3)
    assert resumen.p_valor < 0.001
    assert (resumen.n_bajo_malla, resumen.n_fuera_malla) == (4, 8)
    assert resumen.huella == huella(tabla)


def test_rf26_los_umbrales_del_resumen_son_los_de_la_tabla_resultante():
    resultado = _analizar_ok()

    umbrales = calcular_umbrales(resultado.tabla)

    assert resultado.resumen.p33 == pytest.approx(umbrales.p33)
    assert resultado.resumen.p66 == pytest.approx(umbrales.p66)
    assert resultado.resumen.p75_estabilidad == pytest.approx(umbrales.p75_estabilidad)


def test_rf7_con_correccion_las_plantas_bajo_malla_suben_y_las_demas_no():
    tabla = _tabla_12()

    resultado = _analizar_ok(tabla)

    bajo = tabla["bajo_malla"] == 1
    assert (resultado.tabla.loc[bajo, "KVPI_corregido"] > tabla.loc[bajo, "KVPI_mean"]).all()
    assert resultado.tabla.loc[~bajo, "KVPI_corregido"].tolist() == tabla.loc[~bajo, "KVPI_mean"].tolist()


def test_rf8_sin_huella_no_se_corrige_y_se_avisa():
    resultado = analizar(_tabla_12(), estado_frio_ultima_campana="Adecuado")

    assert resultado.resumen.correccion_aplicada is False
    assert [a.codigo for a in resultado.advertencias] == ["FALTA_CONFIRMACION"]
    assert resultado.tabla["KVPI_corregido"].tolist() == resultado.tabla["KVPI_mean"].tolist()


def test_rf25_con_frio_deficiente_no_queda_ninguna_planta_en_mantener():
    con_frio_ok = _analizar_ok(estado_frio_ultima_campana="Adecuado").tabla
    deficiente = _analizar_ok(estado_frio_ultima_campana="Deficiente").tabla

    assert (con_frio_ok["recomendacion"] == "Mantener").any()
    assert not (deficiente["recomendacion"] == "Mantener").any()


def test_rf25_sin_estado_de_frio_se_avisa_sin_estado_frio():
    resultado = _analizar_ok(estado_frio_ultima_campana=None)

    assert [a.codigo for a in resultado.advertencias] == ["SIN_ESTADO_FRIO"]


def test_rf2_las_plantas_con_kvpi_vacio_se_excluyen_y_se_avisa():
    tabla = _tabla_12()
    tabla.loc[[0, 9], "KVPI_mean"] = float("nan")  # una fuera de malla y una bajo malla

    resultado = _analizar_ok(tabla, huella_confirmada=huella(tabla))

    assert len(resultado.tabla) == 10
    assert 1 not in resultado.tabla["id"].tolist() and 10 not in resultado.tabla["id"].tolist()
    assert resultado.advertencias[0].codigo == "PLANTAS_EXCLUIDAS"


def test_rf9_la_huella_se_calcula_sobre_la_tabla_de_entrada_completa_aunque_se_excluyan_plantas():
    tabla = _tabla_12()
    tabla.loc[9, "KVPI_mean"] = float("nan")  # una planta bajo malla se excluye por no tener KVPI
    huella_del_mapa = huella(tabla)  # lo que el usuario vio y confirmó

    resultado = analizar(tabla, huella_confirmada=huella_del_mapa, estado_frio_ultima_campana="Adecuado")

    assert resultado.resumen.correccion_aplicada is True
    assert resultado.resumen.huella == huella_del_mapa
    assert "HUELLA_NO_COINCIDE" not in [a.codigo for a in resultado.advertencias]


def test_rf21_una_planta_con_std_cero_avisa_y_queda_en_observar():
    tabla = _tabla_12()
    tabla.loc[2, "KVPI_std"] = 0.0  # la planta 3 era "Mantener"

    resultado = _analizar_ok(tabla)

    assert "STD_CERO" in [a.codigo for a in resultado.advertencias]
    fila = resultado.tabla.loc[resultado.tabla["id"] == 3].iloc[0]
    assert pd.isna(fila["estabilidad"])
    assert fila["recomendacion"] == "Observar"


def test_rf26_el_orden_de_las_advertencias_sigue_el_del_flujo():
    tabla = _tabla_12()
    tabla.loc[0, "KVPI_mean"] = float("nan")
    tabla.loc[2, "KVPI_std"] = 0.0

    resultado = analizar(tabla)  # sin huella y sin estado de frío

    assert [a.codigo for a in resultado.advertencias] == [
        "PLANTAS_EXCLUIDAS", "FALTA_CONFIRMACION", "STD_CERO", "SIN_ESTADO_FRIO",
    ]


def test_rf11_si_no_queda_ninguna_planta_con_kvpi_da_error():
    tabla = _tabla_12()
    tabla["KVPI_mean"] = float("nan")

    with pytest.raises(ErrorDeEntrada, match="(?i)ninguna planta"):
        analizar(tabla)


@pytest.mark.parametrize(
    "kwargs",
    [{"correccion": "siempre"}, {"estado_frio_ultima_campana": "deficiente"}],
)
def test_rf14_los_parametros_invalidos_dan_error(kwargs):
    with pytest.raises(ErrorDeEntrada):
        analizar(_tabla_12(), **kwargs)


def test_rf1_una_tabla_sin_columnas_obligatorias_da_error():
    with pytest.raises(ErrorDeEntrada, match="KVPI_std"):
        analizar(_tabla_12().drop(columns=["KVPI_std"]))


def test_rf12_los_modos_forzar_y_desactivar_llegan_hasta_el_resultado():
    tabla = _tabla_12()
    comunes = {"huella_confirmada": huella(tabla), "estado_frio_ultima_campana": "Adecuado"}

    forzar = analizar(tabla, correccion="forzar", **comunes)
    desactivar = analizar(tabla, correccion="desactivar", **comunes)

    assert forzar.resumen.correccion_aplicada is True
    assert [a.codigo for a in forzar.advertencias] == ["CORRECCION_FORZADA"]
    assert desactivar.resumen.correccion_aplicada is False
    assert desactivar.advertencias == []


def test_rf26_no_modifica_la_tabla_de_entrada():
    tabla = _tabla_12()
    tabla.loc[0, "KVPI_mean"] = float("nan")
    copia = tabla.copy()

    analizar(tabla, huella_confirmada=huella(tabla))

    pd.testing.assert_frame_equal(tabla, copia)


# --- T25 (Cambio 1): escalar_std en analizar() -------------------------------------------


def test_rf27_por_defecto_no_se_escala_el_desvio_y_el_resumen_lo_dice():
    resultado = _analizar_ok()

    assert resultado.resumen.escalar_std is False


def test_rf27_escalar_std_por_defecto_equivale_a_pasarlo_en_falso():
    tabla = _tabla_12()

    por_defecto = _analizar_ok(tabla)
    explicito = _analizar_ok(tabla, escalar_std=False)

    pd.testing.assert_frame_equal(por_defecto.tabla, explicito.tabla)
    assert por_defecto.resumen == explicito.resumen


def test_rf27_con_escalar_std_la_estabilidad_de_todas_las_plantas_es_kvpi_mean_sobre_kvpi_std():
    tabla = _tabla_12()

    resultado = _analizar_ok(tabla, escalar_std=True)

    esperado = (tabla["KVPI_mean"] / tabla["KVPI_std"]).tolist()
    assert resultado.tabla["estabilidad"].tolist() == pytest.approx(esperado)


def test_rf27_con_escalar_std_solo_baja_la_estabilidad_de_las_plantas_bajo_malla():
    tabla = _tabla_12()
    normal = _analizar_ok(tabla).tabla
    escalado = _analizar_ok(tabla, escalar_std=True).tabla

    bajo = tabla["bajo_malla"] == 1
    assert (escalado.loc[bajo, "estabilidad"] < normal.loc[bajo, "estabilidad"]).all()
    assert escalado.loc[~bajo, "estabilidad"].tolist() == pytest.approx(normal.loc[~bajo, "estabilidad"].tolist())


def test_rf27_escalar_std_no_cambia_el_kvpi_corregido_ni_los_ambientes():
    tabla = _tabla_12()
    normal = _analizar_ok(tabla).tabla
    escalado = _analizar_ok(tabla, escalar_std=True).tabla

    assert escalado["KVPI_corregido"].tolist() == normal["KVPI_corregido"].tolist()
    assert escalado["ambiente"].tolist() == normal["ambiente"].tolist()


def test_rf26_el_resumen_informa_que_se_escalo_el_desvio_y_sus_umbrales_son_los_de_la_tabla():
    resultado = _analizar_ok(escalar_std=True)

    assert resultado.resumen.escalar_std is True
    umbrales = calcular_umbrales(resultado.tabla)
    assert resultado.resumen.p75_estabilidad == pytest.approx(umbrales.p75_estabilidad)


def test_rf27_si_no_se_aplico_la_correccion_escalar_std_no_tiene_efecto_y_el_resumen_lo_refleja():
    tabla = _tabla_12()

    sin_huella = analizar(tabla, estado_frio_ultima_campana="Adecuado")
    sin_huella_y_escalar = analizar(tabla, estado_frio_ultima_campana="Adecuado", escalar_std=True)

    pd.testing.assert_frame_equal(sin_huella.tabla, sin_huella_y_escalar.tabla)
    assert sin_huella_y_escalar.resumen.correccion_aplicada is False
    assert sin_huella_y_escalar.resumen.escalar_std is False  # se pidió, pero no hubo nada que escalar


def test_rf27_con_desactivar_escalar_std_no_tiene_efecto():
    tabla = _tabla_12()
    comunes = {"huella_confirmada": huella(tabla), "estado_frio_ultima_campana": "Adecuado", "correccion": "desactivar"}

    normal = analizar(tabla, **comunes)
    escalado = analizar(tabla, escalar_std=True, **comunes)

    pd.testing.assert_frame_equal(normal.tabla, escalado.tabla)
    assert escalado.resumen.escalar_std is False


def test_rf27_con_forzar_y_escalar_std_se_escala_porque_hubo_correccion():
    tabla = _tabla_12()

    resultado = analizar(
        tabla, correccion="forzar", huella_confirmada=huella(tabla),
        estado_frio_ultima_campana="Adecuado", escalar_std=True,
    )

    assert resultado.resumen.escalar_std is True
    assert resultado.tabla["estabilidad"].tolist() == pytest.approx((tabla["KVPI_mean"] / tabla["KVPI_std"]).tolist())


def test_rf27_escalar_std_no_agrega_advertencias():
    resultado = _analizar_ok(escalar_std=True)

    assert resultado.advertencias == []


# --- T31 (Cambio 3): prueba_t en analizar() ----------------------------------------------

# Caso clásico donde Student engaña: el grupo grande (fuera de malla) casi no varía y el chico (bajo malla)
# varía mucho. Student da p = 0.0005 y Welch p = 0.103: la decisión de corregir es distinta.
FUERA_DESIGUAL = [0.553, 0.549, 0.556, 0.565, 0.558, 0.570, 0.558, 0.560, 0.575, 0.565]
BAJO_DESIGUAL = [0.495, 0.511, 0.547]


def _tabla_desigual():
    kvpi = FUERA_DESIGUAL + BAJO_DESIGUAL
    return pd.DataFrame(
        {
            "id": range(1, len(kvpi) + 1),
            "KVPI_mean": kvpi,
            "KVPI_std": [0.02] * len(kvpi),
            "bajo_malla": [0] * len(FUERA_DESIGUAL) + [1] * len(BAJO_DESIGUAL),
        }
    )


def test_rf26_por_defecto_el_resumen_dice_que_la_prueba_fue_welch():
    assert _analizar_ok().resumen.prueba_t == "welch"


def test_rf6_prueba_t_student_llega_hasta_el_resumen_con_su_p_valor():
    tabla = _tabla_12()

    welch = _analizar_ok(tabla)
    student = _analizar_ok(tabla, prueba_t="student")

    assert student.resumen.prueba_t == "student"
    assert student.resumen.p_valor != pytest.approx(welch.resumen.p_valor)


def test_rf6_el_p_valor_del_resumen_es_el_de_la_prueba_pedida():
    from scipy import stats

    tabla = _tabla_12()
    bajo = tabla.loc[tabla["bajo_malla"] == 1, "KVPI_mean"]
    fuera = tabla.loc[tabla["bajo_malla"] == 0, "KVPI_mean"]

    welch = _analizar_ok(tabla, prueba_t="welch").resumen.p_valor
    student = _analizar_ok(tabla, prueba_t="student").resumen.p_valor

    assert welch == pytest.approx(stats.ttest_ind(fuera, bajo, equal_var=False).pvalue)
    assert student == pytest.approx(stats.ttest_ind(fuera, bajo, equal_var=True).pvalue)


def test_rf6_con_este_lote_ambas_pruebas_corrigen_y_la_tabla_resultante_es_la_misma():
    tabla = _tabla_12()

    welch = _analizar_ok(tabla, prueba_t="welch")
    student = _analizar_ok(tabla, prueba_t="student")

    assert welch.resumen.correccion_aplicada and student.resumen.correccion_aplicada
    pd.testing.assert_frame_equal(welch.tabla, student.tabla)


def test_rf6_la_eleccion_de_la_prueba_puede_cambiar_la_decision_de_corregir():
    tabla = _tabla_desigual()
    comunes = {"huella_confirmada": huella(tabla), "estado_frio_ultima_campana": "Adecuado"}

    student = analizar(tabla, prueba_t="student", **comunes)
    welch = analizar(tabla, prueba_t="welch", **comunes)

    assert student.resumen.p_valor < 0.001 and student.resumen.correccion_aplicada is True
    assert welch.resumen.p_valor > 0.05 and welch.resumen.correccion_aplicada is False
    assert [a.codigo for a in welch.advertencias] == ["NO_SIGNIFICATIVO"]


@pytest.mark.parametrize("valor", ["Welch", "t", "", None])
def test_rf28_una_prueba_invalida_da_error_desde_analizar(valor):
    with pytest.raises(ErrorDeEntrada) as error:
        analizar(_tabla_12(), prueba_t=valor)

    assert "welch" in str(error.value) and "student" in str(error.value)


def test_rf26_prueba_t_no_agrega_advertencias():
    assert _analizar_ok(prueba_t="student").advertencias == []


def test_rf6_prueba_t_no_cambia_el_fc_ni_los_tamanos_de_grupo():
    tabla = _tabla_12()

    welch = _analizar_ok(tabla, prueba_t="welch").resumen
    student = _analizar_ok(tabla, prueba_t="student").resumen

    assert (welch.fc, welch.n_bajo_malla, welch.n_fuera_malla) == (student.fc, student.n_bajo_malla, student.n_fuera_malla)
