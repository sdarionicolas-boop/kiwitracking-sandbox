"""Reproducción de los resultados publicados (notebook 03, v1.1, lote "El Abrojito", 159 plantas).

Los datos de `tests/golden/` son la verdad contra la que se compara el núcleo (constitución #5).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.huella import huella
from kiwitracking.io import cruzar_con_malla, leer_poligono_geojson

GOLDEN = Path(__file__).parent / "golden" / "datos_plantas_completos.csv"


@pytest.fixture(scope="module")
def golden():
    return pd.read_csv(GOLDEN, encoding="utf-8").set_index("id")


@pytest.fixture(scope="module")
def entrada(golden):
    return golden.reset_index()[["id", "KVPI_mean", "KVPI_std", "bajo_malla"]]


def _analizar(entrada, estado_frio, **kwargs):
    return analizar(
        entrada, huella_confirmada=huella(entrada), estado_frio_ultima_campana=estado_frio, **kwargs
    )


@pytest.fixture(scope="module")
def con_frio_deficiente(entrada):
    return _analizar(entrada, "Deficiente")


@pytest.fixture(scope="module")
def sin_ajuste_de_frio(entrada):
    return _analizar(entrada, "Adecuado")


def test_criterio2_kvpi_corregido_y_estabilidad_coinciden_con_el_golden(con_frio_deficiente, golden):
    resultado = con_frio_deficiente.tabla.set_index("id").loc[golden.index]

    pd.testing.assert_series_equal(resultado["KVPI_corregido"], golden["KVPI_corregido"], atol=1e-6, rtol=0)
    pd.testing.assert_series_equal(resultado["estabilidad"], golden["estabilidad"], atol=1e-6, rtol=0)


def test_criterio2_ambiente_y_recomendacion_coinciden_exactamente(con_frio_deficiente, golden):
    resultado = con_frio_deficiente.tabla.set_index("id").loc[golden.index]

    assert resultado["ambiente"].tolist() == golden["ambiente"].tolist()
    assert resultado["recomendacion"].tolist() == golden["recomendacion"].tolist()


def test_criterio2_los_umbrales_coinciden_con_los_del_golden_y_con_los_publicados(con_frio_deficiente, golden):
    resumen = con_frio_deficiente.resumen

    assert resumen.p33 == pytest.approx(np.percentile(golden["KVPI_corregido"], 33), abs=1e-6)
    assert resumen.p66 == pytest.approx(np.percentile(golden["KVPI_corregido"], 66), abs=1e-6)
    assert resumen.p75_estabilidad == pytest.approx(np.percentile(golden["estabilidad"], 75), abs=1e-6)
    # Valores publicados en metadata_ejecucion.txt (3 decimales): "Bajo <= 0.536 | Alto >= 0.564"
    assert resumen.p33 == pytest.approx(0.536, abs=5e-4)
    assert resumen.p66 == pytest.approx(0.564, abs=5e-4)


def test_criterio3_el_fc_calculado_es_1_2262(con_frio_deficiente):
    assert con_frio_deficiente.resumen.fc == pytest.approx(1.2262, abs=1e-3)


def test_criterio3_la_diferencia_entre_grupos_es_altamente_significativa(con_frio_deficiente):
    # La documentación dice p < 0.001
    assert con_frio_deficiente.resumen.p_valor < 0.001


def test_criterio4_el_cruce_de_grupos_da_53_plantas_bajo_malla_y_106_fuera(con_frio_deficiente):
    assert con_frio_deficiente.resumen.n_bajo_malla == 53
    assert con_frio_deficiente.resumen.n_fuera_malla == 106


def test_criterio2_la_distribucion_de_ambientes_es_54_53_52(con_frio_deficiente):
    ambientes = con_frio_deficiente.tabla["ambiente"].value_counts().to_dict()

    assert ambientes == {"Alto Potencial": 54, "Limitante": 53, "Transicional": 52}


def test_criterio2_con_frio_deficiente_no_hay_mantener_y_hay_19_intervenir(con_frio_deficiente):
    recomendaciones = con_frio_deficiente.tabla["recomendacion"].value_counts().to_dict()

    assert recomendaciones.get("Mantener", 0) == 0
    assert recomendaciones["Intervenir"] == 19


def test_criterio5_sin_ajuste_de_frio_el_lote_da_15_mantener_y_19_intervenir(sin_ajuste_de_frio):
    recomendaciones = sin_ajuste_de_frio.tabla["recomendacion"].value_counts().to_dict()

    assert recomendaciones["Mantener"] == 15
    assert recomendaciones["Intervenir"] == 19


def test_el_analisis_del_lote_de_referencia_no_genera_advertencias(con_frio_deficiente):
    assert con_frio_deficiente.advertencias == []


def test_control_negativo_sin_corregir_los_resultados_ya_no_coinciden_con_el_golden(entrada, golden):
    # Garantiza que este archivo puede fallar: sin corrección, las plantas bajo malla se alejan del golden.
    sin_corregir = _analizar(entrada, "Deficiente", correccion="desactivar").tabla.set_index("id").loc[golden.index]

    diferencia = (sin_corregir["KVPI_corregido"] - golden["KVPI_corregido"]).abs().max()
    assert diferencia > 0.05
    assert sin_corregir["ambiente"].tolist() != golden["ambiente"].tolist()


# --- T20: el cruce con el polígono reproduce la columna bajo_malla del lote ----------------


def test_criterio4_el_cruce_con_malla_zona_geojson_da_53_plantas_bajo_malla(golden):
    poligono, crs_poligono = leer_poligono_geojson(GOLDEN.parent / "malla_zona.geojson")
    plantas = golden.reset_index()[["id", "X", "Y"]]

    bajo_malla, advertencias = cruzar_con_malla(plantas, poligono, "EPSG:4326", crs_poligono)

    assert int(bajo_malla.sum()) == 53
    assert advertencias == []


def test_criterio4_el_cruce_coincide_planta_por_planta_con_la_columna_del_notebook(golden):
    poligono, crs_poligono = leer_poligono_geojson(GOLDEN.parent / "malla_zona.geojson")
    plantas = golden.reset_index()[["id", "X", "Y"]]

    bajo_malla, _ = cruzar_con_malla(plantas, poligono, "EPSG:4326", crs_poligono)

    assert bajo_malla.tolist() == golden["bajo_malla"].tolist()


def test_criterio4_y_6_del_cruce_al_analisis_completo_reproduce_el_resultado_publicado(golden):
    # De punta a punta: coordenadas + polígono -> bajo_malla -> huella -> analizar().
    poligono, crs_poligono = leer_poligono_geojson(GOLDEN.parent / "malla_zona.geojson")
    plantas = golden.reset_index()[["id", "KVPI_mean", "KVPI_std", "X", "Y"]]
    bajo_malla, _ = cruzar_con_malla(plantas, poligono, "EPSG:4326", crs_poligono)
    entrada = plantas.assign(bajo_malla=bajo_malla)

    resultado = analizar(entrada, huella_confirmada=huella(entrada), estado_frio_ultima_campana="Deficiente")

    resultado_por_id = resultado.tabla.set_index("id").loc[golden.index]
    assert resultado.resumen.fc == pytest.approx(1.2262, abs=1e-3)
    assert resultado_por_id["recomendacion"].tolist() == golden["recomendacion"].tolist()
    assert resultado_por_id["ambiente"].tolist() == golden["ambiente"].tolist()


# --- T26 (Cambio 1): escalar_std sobre el lote de referencia -------------------------------

CAMBIAN_CON_ESCALAR_STD = {
    107: ("Intervenir", "Observar"),  # bajo malla
    180: ("Intervenir", "Observar"),  # bajo malla
    215: ("Observar", "Mantener"),
    237: ("Observar", "Intervenir"),
    357: ("Observar", "Intervenir"),
}


@pytest.fixture(scope="module")
def con_escalar_std(entrada):
    return _analizar(entrada, "Adecuado", escalar_std=True)


def test_cambio1_con_el_valor_por_defecto_el_resultado_publicado_no_cambia(entrada, golden):
    explicito = _analizar(entrada, "Deficiente", escalar_std=False).tabla.set_index("id").loc[golden.index]

    assert explicito["recomendacion"].tolist() == golden["recomendacion"].tolist()
    assert explicito["estabilidad"].tolist() == pytest.approx(golden["estabilidad"].tolist(), abs=1e-6)


def test_cambio1_el_resumen_informa_que_se_escalo_el_desvio(con_escalar_std):
    assert con_escalar_std.resumen.escalar_std is True


def test_cambio1_la_estabilidad_con_escalar_std_es_kvpi_mean_sobre_kvpi_std_en_las_159_plantas(con_escalar_std, golden):
    resultado = con_escalar_std.tabla.set_index("id").loc[golden.index]

    esperado = golden["KVPI_mean"] / golden["KVPI_std"]
    pd.testing.assert_series_equal(resultado["estabilidad"], esperado, check_names=False, atol=1e-9, rtol=0)


def test_cambio1_el_p75_de_estabilidad_baja_de_15_185_a_14_932(con_escalar_std, golden):
    esperado = np.percentile(golden["KVPI_mean"] / golden["KVPI_std"], 75)

    assert con_escalar_std.resumen.p75_estabilidad == pytest.approx(esperado, abs=1e-9)
    assert con_escalar_std.resumen.p75_estabilidad == pytest.approx(14.932, abs=1e-3)


def test_cambio1_la_estabilidad_de_las_plantas_bajo_malla_baja_exactamente_el_fc(con_escalar_std, con_frio_deficiente):
    escalada = con_escalar_std.tabla.set_index("id")
    publicada = con_frio_deficiente.tabla.set_index("id")
    bajo = escalada["bajo_malla"] == 1

    cociente = publicada.loc[bajo, "estabilidad"] / escalada.loc[bajo, "estabilidad"]

    assert cociente.tolist() == pytest.approx([con_escalar_std.resumen.fc] * 53, abs=1e-9)
    assert (publicada.loc[~bajo, "estabilidad"] - escalada.loc[~bajo, "estabilidad"]).abs().max() < 1e-9


def test_cambio1_las_recomendaciones_coinciden_con_un_calculo_independiente_a_partir_de_los_datos_crudos(con_escalar_std, golden):
    # Recalcula la regla con numpy, sin usar el paquete, y compara con el resultado de analizar().
    kvpi = golden["KVPI_corregido"].to_numpy()
    estabilidad = (golden["KVPI_mean"] / golden["KVPI_std"]).to_numpy()
    p33, p66 = np.percentile(kvpi, [33, 66])
    p75 = np.percentile(estabilidad, 75)
    esperado = np.select(
        [(estabilidad >= p75) & (kvpi >= p66), (estabilidad >= p75) & (kvpi <= p33)],
        ["Mantener", "Intervenir"],
        default="Observar",
    )

    resultado = con_escalar_std.tabla.set_index("id").loc[golden.index]

    assert resultado["recomendacion"].tolist() == esperado.tolist()


def test_cambio1_cambian_exactamente_5_recomendaciones_y_son_estas(con_escalar_std, sin_ajuste_de_frio):
    antes = sin_ajuste_de_frio.tabla.set_index("id")["recomendacion"]
    despues = con_escalar_std.tabla.set_index("id")["recomendacion"]

    cambiaron = {i: (antes[i], despues[i]) for i in antes.index if antes[i] != despues[i]}

    assert cambiaron == CAMBIAN_CON_ESCALAR_STD


def test_cambio1_las_dos_plantas_bajo_malla_que_dejan_intervenir_son_las_unicas_bajo_malla_que_cambian(con_escalar_std, golden):
    bajo_malla = set(golden.index[golden["bajo_malla"] == 1])

    assert bajo_malla & set(CAMBIAN_CON_ESCALAR_STD) == {107, 180}
    intervenir = con_escalar_std.tabla.set_index("id")
    assert not ((intervenir["recomendacion"] == "Intervenir") & (intervenir["bajo_malla"] == 1)).any()


def test_cambio1_los_ambientes_y_el_kvpi_corregido_no_cambian(con_escalar_std, sin_ajuste_de_frio):
    escalado = con_escalar_std.tabla.set_index("id")
    normal = sin_ajuste_de_frio.tabla.set_index("id")

    assert escalado["ambiente"].tolist() == normal["ambiente"].tolist()
    assert escalado["KVPI_corregido"].tolist() == normal["KVPI_corregido"].tolist()


def test_cambio1_sin_ajuste_de_frio_hay_16_mantener_y_19_intervenir(con_escalar_std):
    recomendaciones = con_escalar_std.tabla["recomendacion"].value_counts().to_dict()

    assert recomendaciones["Mantener"] == 16
    assert recomendaciones["Intervenir"] == 19


def test_cambio1_con_frio_deficiente_sigue_sin_haber_mantener_y_hay_19_intervenir(entrada):
    resultado = _analizar(entrada, "Deficiente", escalar_std=True)

    recomendaciones = resultado.tabla["recomendacion"].value_counts().to_dict()
    assert recomendaciones.get("Mantener", 0) == 0
    assert recomendaciones["Intervenir"] == 19
    assert resultado.advertencias == []


def test_cambio1_con_escalar_std_las_plantas_bajo_malla_siguen_siendo_menos_estables_que_las_de_afuera(con_escalar_std):
    # Dato que el cambio deja a la vista: la corrección arregla el nivel del KVPI, no su variabilidad.
    tabla = con_escalar_std.tabla
    bajo = tabla.loc[tabla["bajo_malla"] == 1, "estabilidad"].mean()
    fuera = tabla.loc[tabla["bajo_malla"] == 0, "estabilidad"].mean()

    assert bajo == pytest.approx(9.32, abs=0.01)
    assert fuera == pytest.approx(14.46, abs=0.01)


# --- T29 (Cambio 2): borde estricto en p33 sobre el lote de referencia --------------------


@pytest.mark.parametrize("escalar_std", [False, True])
@pytest.mark.parametrize("estado_frio", ["Deficiente", "Adecuado", "Óptimo"])
def test_cambio2_en_el_lote_real_toda_mantener_es_alto_potencial_y_toda_intervenir_es_limitante(entrada, estado_frio, escalar_std):
    tabla = _analizar(entrada, estado_frio, escalar_std=escalar_std).tabla

    mantener = tabla.loc[tabla["recomendacion"] == "Mantener", "ambiente"]
    intervenir = tabla.loc[tabla["recomendacion"] == "Intervenir", "ambiente"]
    assert (mantener == "Alto Potencial").all()
    assert (intervenir == "Limitante").all()


def test_cambio2_ninguna_planta_del_lote_cae_exactamente_en_p33_ni_en_p66_por_eso_no_cambia_el_resultado_publicado(sin_ajuste_de_frio):
    # El borde estricto solo importa con empates exactos; el lote de referencia no los tiene.
    kvpi = sin_ajuste_de_frio.tabla["KVPI_corregido"]
    resumen = sin_ajuste_de_frio.resumen

    assert not np.isclose(kvpi, resumen.p33, rtol=0, atol=1e-12).any()
    assert not np.isclose(kvpi, resumen.p66, rtol=0, atol=1e-12).any()
    assert sin_ajuste_de_frio.tabla["recomendacion"].value_counts().to_dict()["Intervenir"] == 19


# --- T32 (Cambio 3): prueba t de Welch por defecto sobre el lote de referencia ---------------

# Con p-valores tan chicos pytest.approx necesita abs=0: su tolerancia absoluta por defecto (1e-12) los daría por iguales.
P_VALOR_STUDENT_V1_1 = 1.0256448140817872e-26  # el de la versión anterior (v1.1) sobre estas 159 plantas


def _grupos(golden):
    bajo = golden.loc[golden["bajo_malla"] == 1, "KVPI_mean"]
    fuera = golden.loc[golden["bajo_malla"] == 0, "KVPI_mean"]
    return fuera, bajo


def test_cambio3_el_lote_de_referencia_incumple_el_supuesto_de_varianzas_iguales(golden):
    # Motivo del cambio: la varianza bajo malla es menos de un tercio de la de fuera de malla.
    from scipy import stats

    fuera, bajo = _grupos(golden)

    assert bajo.var() / fuera.var() < 0.3
    assert stats.levene(fuera, bajo).pvalue < 0.001


def test_cambio3_por_defecto_el_p_valor_del_lote_es_el_de_welch(con_frio_deficiente, golden):
    from scipy import stats

    fuera, bajo = _grupos(golden)
    welch = stats.ttest_ind(fuera, bajo, equal_var=False).pvalue

    assert con_frio_deficiente.resumen.prueba_t == "welch"
    assert con_frio_deficiente.resumen.p_valor == pytest.approx(welch, rel=1e-9, abs=0)
    assert con_frio_deficiente.resumen.p_valor == pytest.approx(5.86e-35, rel=1e-2, abs=0)


def test_cambio3_con_student_se_reproduce_exactamente_el_p_valor_de_v1_1(entrada):
    resultado = _analizar(entrada, "Deficiente", prueba_t="student")

    assert resultado.resumen.prueba_t == "student"
    assert resultado.resumen.p_valor == pytest.approx(P_VALOR_STUDENT_V1_1, rel=1e-9, abs=0)


def test_cambio3_la_decision_y_todos_los_resultados_del_lote_son_identicos_con_ambas_pruebas(entrada):
    welch = _analizar(entrada, "Adecuado", prueba_t="welch")
    student = _analizar(entrada, "Adecuado", prueba_t="student")

    assert welch.resumen.correccion_aplicada is True and student.resumen.correccion_aplicada is True
    pd.testing.assert_frame_equal(welch.tabla, student.tabla)
    assert welch.resumen.fc == student.resumen.fc
    assert (welch.resumen.p33, welch.resumen.p66, welch.resumen.p75_estabilidad) == (
        student.resumen.p33, student.resumen.p66, student.resumen.p75_estabilidad,
    )
    assert welch.advertencias == student.advertencias == []


def test_cambio3_ambas_pruebas_dan_una_diferencia_altamente_significativa(entrada):
    for prueba in ("welch", "student"):
        assert _analizar(entrada, "Deficiente", prueba_t=prueba).resumen.p_valor < 0.001
