import numpy as np
import pandas as pd
import pytest

from kiwitracking.clima import ResultadoClima, calcular_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada


def _diario(inicio, fin, tmax=30.0, tmin=20.0, faltantes=(), como_vacios=False):
    """Tabla diaria cruda (fechas en texto, como llegaría de un CSV) con temperaturas constantes.

    `faltantes` son rangos (desde, hasta) sin datos: sin fila, o con las temperaturas vacías si `como_vacios`.
    """
    fechas = pd.date_range(inicio, fin)
    tabla = pd.DataFrame({"date": [f"{d:%Y-%m-%d}" for d in fechas], "Tmax": tmax, "Tmin": tmin})
    for desde, hasta in faltantes:
        en_rango = (fechas >= desde) & (fechas <= hasta)
        if como_vacios:
            tabla.loc[en_rango, ["Tmax", "Tmin"]] = float("nan")
        else:
            tabla = tabla[~en_rango]
            fechas = fechas[~en_rango]
    return tabla.reset_index(drop=True)


def _gdd(advertencias):
    """Las advertencias del GDD (desde T2.11 `calcular_clima` también devuelve las del frío)."""
    return [a for a in advertencias if a.mensaje.startswith("GDD")]


# --- T2.10: GDD por temporada -------------------------------------------------------------


def test_rf17_el_resultado_trae_la_tabla_de_gdd_las_advertencias_y_el_modo_de_la_ventana():
    resultado = calcular_clima(_diario("2020-07-01", "2021-06-30"))

    assert isinstance(resultado, ResultadoClima)
    assert resultado.ventana_frio == "invierno"
    assert isinstance(resultado.gdd, pd.DataFrame) and isinstance(resultado.advertencias, list)


def test_rf17_una_temporada_completa_suma_el_gdd_de_cada_dia():
    # Tmedia = 25 todos los días -> 15 °C día por día, durante 365 días.
    gdd = calcular_clima(_diario("2020-07-01", "2021-06-30")).gdd

    fila = gdd.iloc[0]
    assert fila["temporada"] == 2020
    assert fila["GDD_total"] == pytest.approx(365 * 15.0)
    assert (fila["dias_disponibles"], fila["dias_esperados"], fila["hueco_maximo"]) == (365, 365, 0)
    assert fila["cobertura"] == 1.0 and fila["completo"]


def test_rf17_la_tabla_trae_las_columnas_acordadas_con_sus_tipos():
    gdd = calcular_clima(_diario("2020-07-01", "2021-06-30")).gdd

    assert list(gdd.columns) == [
        "temporada", "GDD_total", "dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo",
    ]
    assert pd.api.types.is_integer_dtype(gdd["temporada"]) and pd.api.types.is_float_dtype(gdd["GDD_total"])
    assert gdd["completo"].dtype == bool
    assert gdd.index.tolist() == [0]


def test_rf17_una_temporada_abarca_dos_anos_calendario():
    # Julio a diciembre de 2019 y enero a junio de 2020 son una sola temporada (la 2019).
    gdd = calcular_clima(_diario("2019-07-01", "2020-06-30")).gdd

    assert gdd["temporada"].tolist() == [2019]
    assert gdd["GDD_total"].tolist() == pytest.approx([366 * 15.0])  # 2020 es bisiesto


def test_rf17_varias_temporadas_salen_ordenadas_por_etiqueta():
    tabla = pd.concat([_diario("2021-07-01", "2022-06-30"), _diario("2019-07-01", "2020-06-30")], ignore_index=True)

    assert calcular_clima(tabla).gdd["temporada"].tolist() == [2019, 2021]


def test_rf17_tbase_es_un_parametro():
    gdd = calcular_clima(_diario("2020-07-01", "2021-06-30"), ParametrosClima(tbase=12.5)).gdd

    assert gdd["GDD_total"].tolist() == pytest.approx([365 * 12.5])


def test_rf17_un_dia_mas_frio_que_la_base_aporta_cero_y_no_resta():
    gdd = calcular_clima(_diario("2020-07-01", "2021-06-30", tmax=10.0, tmin=0.0)).gdd

    assert gdd["GDD_total"].tolist() == [0.0]
    assert gdd["temporada"].tolist() == [2020]  # la temporada aparece aunque no sume nada


def test_rf17_el_gdd_se_calcula_aunque_la_temporada_sea_incompleta_con_los_dias_disponibles():
    gdd = calcular_clima(_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")])).gdd

    fila = gdd.iloc[0]
    assert fila["GDD_total"] == pytest.approx((365 - 8) * 15.0)
    assert fila["hueco_maximo"] == 8 and not fila["completo"]


def test_rf17_un_dia_con_las_temperaturas_vacias_no_suma_gdd_y_cuenta_como_faltante():
    sin_fila = calcular_clima(_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")])).gdd
    con_vacios = calcular_clima(_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")], como_vacios=True)).gdd

    pd.testing.assert_frame_equal(sin_fila, con_vacios)


def test_rf17_las_temporadas_de_los_bordes_del_registro_quedan_parciales():
    gdd = calcular_clima(_diario("2019-01-01", "2019-12-31")).gdd

    assert gdd["temporada"].tolist() == [2018, 2019]
    assert gdd["dias_disponibles"].tolist() == [181, 184]
    assert gdd["completo"].tolist() == [False, False]


def test_rf17_mes_inicio_temporada_es_un_parametro():
    gdd = calcular_clima(_diario("2020-01-01", "2020-12-31"), ParametrosClima(mes_inicio_temporada=1)).gdd

    assert gdd["temporada"].tolist() == [2020]
    assert gdd["GDD_total"].tolist() == pytest.approx([366 * 15.0])
    assert gdd["completo"].tolist() == [True]


def test_rf17_el_resultado_no_depende_del_orden_de_las_filas():
    tabla = _diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")])

    ordenado = calcular_clima(tabla).gdd
    desordenado = calcular_clima(tabla.sample(frac=1, random_state=5).reset_index(drop=True)).gdd

    pd.testing.assert_frame_equal(ordenado, desordenado)


def test_rf17_no_modifica_la_tabla_de_entrada():
    tabla = _diario("2020-07-01", "2021-06-30")
    copia = tabla.copy()

    calcular_clima(tabla)

    pd.testing.assert_frame_equal(tabla, copia)


def test_rf1_a_rf9_los_errores_de_la_entrada_llegan_hasta_calcular_clima():
    with pytest.raises(ErrorDeEntrada, match="Tmax"):
        calcular_clima(_diario("2020-07-01", "2020-07-10").drop(columns=["Tmax"]))


# --- T2.10: advertencias de las temporadas incompletas ------------------------------------


def test_rf18_una_temporada_incompleta_avisa_con_codigo_estable_y_un_mensaje_que_nombra_el_tipo_y_la_temporada():
    resultado = calcular_clima(_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")]))

    assert [a.codigo for a in _gdd(resultado.advertencias)] == ["PERIODO_INCOMPLETO"]
    mensaje = _gdd(resultado.advertencias)[0].mensaje
    assert mensaje.startswith("GDD, temporada 2020")
    assert "97,8" in mensaje and "8 días" in mensaje


def test_rf18_una_temporada_completa_no_avisa():
    assert _gdd(calcular_clima(_diario("2020-07-01", "2021-06-30")).advertencias) == []


def test_rf18_una_temporada_completa_con_cobertura_menor_que_1_no_avisa_decision_provisional_de_la_clarificacion_c3():
    # 4 días de 365: cobertura 0,989 y hueco 4 -> completa. La spec solo avisa de las incompletas (RF-18).
    resultado = calcular_clima(_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-04")]))

    assert resultado.gdd["completo"].tolist() == [True]
    assert _gdd(resultado.advertencias) == []


def test_rf18_cada_temporada_incompleta_avisa_en_orden_cronologico():
    resultado = calcular_clima(_diario("2019-01-01", "2019-12-31"))

    avisos = _gdd(resultado.advertencias)
    assert [a.codigo for a in avisos] == ["PERIODO_INCOMPLETO", "PERIODO_INCOMPLETO"]
    assert avisos[0].mensaje.startswith("GDD, temporada 2018")
    assert avisos[1].mensaje.startswith("GDD, temporada 2019")


def test_rf18_el_mensaje_de_una_temporada_parcial_trae_cobertura_y_hueco():
    mensaje = _gdd(calcular_clima(_diario("2019-01-01", "2019-12-31")).advertencias)[0].mensaje

    assert "49,6" in mensaje and "184 días" in mensaje  # 181 de 365 días; hueco de julio a diciembre de 2018


def test_rf18_las_advertencias_de_la_entrada_van_antes_que_las_de_los_periodos():
    tabla = pd.concat([_diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")]), _diario("2020-07-01", "2020-07-01")], ignore_index=True)

    resultado = calcular_clima(tabla)

    sin_frio = [a for a in resultado.advertencias if not a.mensaje.startswith("Frío")]
    assert [a.codigo for a in sin_frio] == ["FECHA_DUPLICADA", "PERIODO_INCOMPLETO"]


def test_rf18_los_limites_de_completitud_son_parametros():
    tabla = _diario("2020-07-01", "2021-06-30", faltantes=[("2020-10-01", "2020-10-08")])

    laxo = calcular_clima(tabla, ParametrosClima(max_hueco_dias=None))

    assert laxo.gdd["completo"].tolist() == [True]
    assert _gdd(laxo.advertencias) == []


# --- T2.11: horas de frío y estado --------------------------------------------------------


def _invierno(anio, dias_frios, faltantes=(), hasta=None):
    """Mayo a agosto de `anio`: los primeros `dias_frios` días son de 24 h de frío (Tmax 5, Tmin -3) y el resto, templados."""
    fechas = pd.date_range(f"{anio}-05-01", hasta or f"{anio}-08-31")
    tabla = pd.DataFrame(
        {
            "date": [f"{d:%Y-%m-%d}" for d in fechas],
            "Tmax": [5.0 if i < dias_frios else 20.0 for i in range(len(fechas))],
            "Tmin": [-3.0 if i < dias_frios else 10.0 for i in range(len(fechas))],
        }
    )
    for desde, hasta_falta in faltantes:
        tabla = tabla[~((tabla["date"] >= desde) & (tabla["date"] <= hasta_falta))]
    return tabla.reset_index(drop=True)


def _frio(tabla, **parametros):
    return calcular_clima(tabla, ParametrosClima(**parametros)).frio


def test_rf19_la_tabla_de_frio_trae_las_columnas_acordadas_con_sus_tipos():
    frio = _frio(_invierno(2019, 40))

    assert list(frio.columns) == [
        "periodo", "Horas_Frio", "estado_frio", "dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo",
    ]
    assert frio["periodo"].tolist() == [2019]
    assert pd.api.types.is_float_dtype(frio["Horas_Frio"]) and frio["completo"].dtype == bool
    assert frio.index.tolist() == [0]


def test_rf19_las_horas_de_frio_son_la_suma_de_las_horas_de_cada_dia_disponible():
    # 40 días de 24 h y 83 días templados (0 h): 960 h.
    fila = _frio(_invierno(2019, 40)).iloc[0]

    assert fila["Horas_Frio"] == pytest.approx(960.0)
    assert (fila["dias_disponibles"], fila["dias_esperados"], fila["hueco_maximo"]) == (123, 123, 0)


def test_rf19_con_temperaturas_reales_usa_el_modelo_de_coseno():
    # Tmax 10, Tmin 0: 15,1437 h por día durante los 123 días de la ventana.
    tabla = _invierno(2019, 0).assign(Tmax=10.0, Tmin=0.0)

    assert _frio(tabla).iloc[0]["Horas_Frio"] == pytest.approx(123 * 15.143757, rel=1e-6)


def test_rf19_los_dias_fuera_de_los_meses_de_la_ventana_no_suman_horas():
    # Septiembre y octubre de 24 h cada día: no pertenecen a mayo-agosto.
    otoño = _invierno(2019, 0, hasta="2019-10-31")
    otoño.loc[otoño["date"] >= "2019-09-01", ["Tmax", "Tmin"]] = [5.0, -3.0]

    assert _frio(otoño).iloc[0]["Horas_Frio"] == 0.0


def test_rf19_las_horas_se_calculan_aunque_la_ventana_sea_incompleta_con_los_dias_disponibles():
    fila = _frio(_invierno(2019, 40, hasta="2019-06-30")).iloc[0]  # 61 de 123 días

    assert fila["Horas_Frio"] == pytest.approx(960.0) and not fila["completo"]


@pytest.mark.parametrize("dias_frios,estado", [(40, "Óptimo"), (39, "Adecuado"), (32, "Adecuado"), (31, "Deficiente"), (0, "Deficiente")])
def test_rf20_el_estado_sale_de_las_horas_con_los_umbrales_950_y_750(dias_frios, estado):
    # 40 días = 960 h; 39 = 936; 32 = 768; 31 = 744.
    assert _frio(_invierno(2019, dias_frios)).iloc[0]["estado_frio"] == estado


@pytest.mark.parametrize(
    "parametros,estado",
    [
        ({"umbral_optimo": 960}, "Óptimo"),       # 960 >= 960
        ({"umbral_optimo": 961}, "Adecuado"),     # 960 < 961
        ({"umbral_optimo": 2000, "umbral_adecuado": 960}, "Adecuado"),   # 960 >= 960
        ({"umbral_optimo": 2000, "umbral_adecuado": 961}, "Deficiente"),
    ],
)
def test_rf20_los_umbrales_son_parametros_y_el_valor_exacto_alcanza(parametros, estado):
    assert _frio(_invierno(2019, 40), **parametros).iloc[0]["estado_frio"] == estado


def test_rf20_los_textos_del_estado_son_los_de_la_spec_001():
    from kiwitracking.validacion import ESTADOS_FRIO

    estados = {_frio(_invierno(2019, d)).iloc[0]["estado_frio"] for d in (40, 39, 0)}

    assert estados == set(ESTADOS_FRIO) == {"Óptimo", "Adecuado", "Deficiente"}


def test_rf20_una_ventana_incompleta_no_se_clasifica_pero_conserva_sus_horas():
    # Ventana con 61 de 123 días (cobertura 0,496): sin estado aunque las horas serían "Óptimo".
    fila = _frio(_invierno(2019, 61, hasta="2019-06-30")).iloc[0]

    assert pd.isna(fila["estado_frio"]) and fila["Horas_Frio"] == pytest.approx(61 * 24.0)


def test_rf20_un_hueco_largo_impide_clasificar_aunque_la_cobertura_sea_alta():
    # 8 días seguidos sin datos: cobertura 0,935 (>= 0,9) pero hueco 8 > 7.
    fila = _frio(_invierno(2019, 40, faltantes=[("2019-07-10", "2019-07-17")])).iloc[0]

    assert fila["cobertura"] > 0.9 and fila["hueco_maximo"] == 8
    assert not fila["completo"] and pd.isna(fila["estado_frio"])


def test_rf20_una_ventana_incompleta_avisa_con_codigo_estable_y_un_mensaje_que_nombra_el_tipo_y_la_ventana():
    resultado = calcular_clima(_invierno(2019, 40, hasta="2019-06-30"))

    avisos = [a for a in resultado.advertencias if a.mensaje.startswith("Frío")]
    assert [a.codigo for a in avisos] == ["PERIODO_INCOMPLETO"]
    assert avisos[0].mensaje.startswith("Frío, ventana 2019")
    assert "49,6" in avisos[0].mensaje and "62 días" in avisos[0].mensaje


def test_rf20_una_ventana_completa_y_con_todos_los_dias_no_avisa_nada():
    resultado = calcular_clima(_invierno(2019, 40))

    assert [a for a in resultado.advertencias if a.mensaje.startswith("Frío")] == []


def test_rf21_una_ventana_completa_con_cobertura_menor_que_1_se_clasifica_y_avisa_cobertura_parcial():
    # Como el invierno 2025: 119 de 123 días (0,9675) con un hueco de 4 días.
    # 50 días fríos, 4 de ellos sin datos: quedan 46 x 24 = 1.104 h.
    resultado = calcular_clima(_invierno(2025, 50, faltantes=[("2025-05-08", "2025-05-11")]))

    fila = resultado.frio.iloc[0]
    assert fila["completo"] and fila["estado_frio"] == "Óptimo"
    avisos = [a for a in resultado.advertencias if a.mensaje.startswith("Frío")]
    assert [a.codigo for a in avisos] == ["COBERTURA_PARCIAL"]
    assert avisos[0].mensaje.startswith("Frío, ventana 2025") and "96,7" in avisos[0].mensaje


def test_rf21_cobertura_parcial_no_aparece_si_la_ventana_no_es_completa():
    resultado = calcular_clima(_invierno(2019, 40, hasta="2019-06-30"))

    codigos = [a.codigo for a in resultado.advertencias if a.mensaje.startswith("Frío")]
    assert "COBERTURA_PARCIAL" not in codigos


def test_rf19_varias_ventanas_salen_ordenadas_y_cada_una_con_su_estado():
    tabla = pd.concat([_invierno(2021, 0), _invierno(2019, 40)], ignore_index=True)

    frio = _frio(tabla)

    assert frio["periodo"].tolist() == [2019, 2021]
    assert frio["estado_frio"].tolist() == ["Óptimo", "Deficiente"]


def test_rf19_en_modo_temporada_la_ventana_suma_julio_agosto_de_un_ano_con_mayo_junio_del_siguiente():
    # Solo mayo-junio de 2020 es frío. Datos de julio de 2019 a agosto de 2020.
    fechas = pd.date_range("2019-07-01", "2020-08-31")
    tabla = pd.DataFrame({"date": [f"{d:%Y-%m-%d}" for d in fechas], "Tmax": 20.0, "Tmin": 10.0})
    frio_pleno = (fechas >= "2020-05-01") & (fechas <= "2020-06-30")
    tabla.loc[frio_pleno, ["Tmax", "Tmin"]] = [5.0, -3.0]

    invierno = _frio(tabla, ventana_frio="invierno").set_index("periodo")
    temporada = _frio(tabla, ventana_frio="temporada").set_index("periodo")

    assert invierno.loc[2020, "Horas_Frio"] == pytest.approx(61 * 24.0)   # el invierno 2020 completo
    assert 2019 not in invierno.index or invierno.loc[2019, "Horas_Frio"] == 0.0
    assert temporada.loc[2019, "Horas_Frio"] == pytest.approx(61 * 24.0)  # mayo-junio de 2020 cae en la temporada 2019
    assert temporada.loc[2019, "completo"]                                # julio-agosto de 2019 + mayo-junio de 2020 = 123 días


def test_rf19_no_modifica_la_tabla_de_entrada():
    tabla = _invierno(2019, 40)
    copia = tabla.copy()

    calcular_clima(tabla)

    pd.testing.assert_frame_equal(tabla, copia)


def test_rf19_umbral_frio_es_un_parametro_que_llega_hasta_las_horas_de_la_ventana():
    # Tmax 10 y Tmin 0: con umbral 7 son 15,14 h por día; con umbral 10 todo el día está por debajo (24 h).
    tabla = _invierno(2019, 0).assign(Tmax=10.0, Tmin=0.0)

    por_defecto = _frio(tabla).iloc[0]["Horas_Frio"]
    con_umbral_10 = _frio(tabla, umbral_frio=10.0).iloc[0]["Horas_Frio"]

    assert por_defecto == pytest.approx(123 * 15.143757, rel=1e-6)
    assert con_umbral_10 == pytest.approx(123 * 24.0)


# --- T2.12: orden de las advertencias y modo de reproducción ---------------------------------


def _clima_constante(inicio, fin, tmax, tmin):
    fechas = pd.date_range(inicio, fin)
    return pd.DataFrame({"date": [f"{d:%Y-%m-%d}" for d in fechas], "Tmax": tmax, "Tmin": tmin})


def _clave(advertencia):
    """(tipo, período) de una advertencia de período, tomados del comienzo de su mensaje."""
    cabecera = advertencia.mensaje.split(":")[0]  # "GDD, temporada 2018" o "Frío, ventana 2019"
    tipo, resto = cabecera.split(", ")
    return tipo, int(resto.split()[-1])


def test_rf26_el_resultado_trae_las_dos_tablas_y_la_lista_de_advertencias():
    resultado = calcular_clima(_clima_constante("2019-06-01", "2021-02-15", 30.0, 20.0))

    assert isinstance(resultado.gdd, pd.DataFrame) and not resultado.gdd.empty
    assert isinstance(resultado.frio, pd.DataFrame) and not resultado.frio.empty
    assert all(a.codigo in {"PERIODO_INCOMPLETO", "COBERTURA_PARCIAL", "FECHA_DUPLICADA"} for a in resultado.advertencias)


def test_rf26_las_advertencias_de_los_periodos_van_ordenadas_por_periodo_y_no_agrupadas_por_tipo():
    # GDD incompleto en las temporadas 2018 y 2020, y frío incompleto en la ventana 2019: el orden cronológico
    # intercala los tipos (GDD 2018, Frío 2019, GDD 2020); agrupar por tipo daría GDD 2018, GDD 2020, Frío 2019.
    resultado = calcular_clima(_clima_constante("2019-06-01", "2021-02-15", 30.0, 20.0))

    assert [_clave(a) for a in resultado.advertencias] == [("GDD", 2018), ("Frío", 2019), ("GDD", 2020)]


def test_rf26_con_el_mismo_periodo_la_advertencia_del_gdd_va_antes_que_la_del_frio():
    # Datos desde el 1 de junio de 2020: GDD incompleto en 2019 y 2020; frío incompleto en la ventana 2020.
    resultado = calcular_clima(_clima_constante("2020-06-01", "2021-02-15", 30.0, 20.0))

    assert [_clave(a) for a in resultado.advertencias] == [("GDD", 2019), ("GDD", 2020), ("Frío", 2020)]


def test_rf26_las_advertencias_de_la_entrada_van_antes_que_las_de_los_periodos_aun_con_periodos_anteriores():
    tabla = pd.concat([_clima_constante("2019-06-01", "2021-02-15", 30.0, 20.0), _clima_constante("2019-06-01", "2019-06-01", 30.0, 20.0)], ignore_index=True)

    resultado = calcular_clima(tabla)

    assert resultado.advertencias[0].codigo == "FECHA_DUPLICADA"
    assert [_clave(a) for a in resultado.advertencias[1:]] == [("GDD", 2018), ("Frío", 2019), ("GDD", 2020)]


# --- RF-27: modo de reproducción del cálculo original --------------------------------------

REPRODUCCION = dict(ventana_frio="temporada", cobertura_minima=0, max_hueco_dias=None)


def _tres_anos_con_12_horas_de_frio_por_dia():
    """2019 a 2021: de mayo a agosto, Tmax 14 y Tmin 0 (12 h de frío por día); el resto del año, templado."""
    fechas = pd.date_range("2019-01-01", "2021-12-31")
    frio = fechas.month.isin([5, 6, 7, 8])
    return pd.DataFrame(
        {
            "date": [f"{d:%Y-%m-%d}" for d in fechas],
            "Tmax": [14.0 if f else 25.0 for f in frio],
            "Tmin": [0.0 if f else 15.0 for f in frio],
        }
    )


def test_rf27_en_modo_de_reproduccion_las_ventanas_de_los_bordes_salen_clasificadas_como_deficiente():
    frio = calcular_clima(_tres_anos_con_12_horas_de_frio_por_dia(), ParametrosClima(**REPRODUCCION)).frio.set_index("periodo")

    # 2018 solo tiene mayo-junio de 2019 (61 días) y 2021 solo julio-agosto de 2021 (62 días): 732 y 744 h.
    assert frio["Horas_Frio"].round(1).to_dict() == {2018: 732.0, 2019: 1476.0, 2020: 1476.0, 2021: 744.0}
    assert frio["estado_frio"].to_dict() == {2018: "Deficiente", 2019: "Óptimo", 2020: "Óptimo", 2021: "Deficiente"}


def test_rf27_con_el_calculo_por_invierno_esos_deficiente_de_los_bordes_desaparecen():
    frio = calcular_clima(_tres_anos_con_12_horas_de_frio_por_dia()).frio.set_index("periodo")

    assert frio["Horas_Frio"].round(1).to_dict() == {2019: 1476.0, 2020: 1476.0, 2021: 1476.0}
    assert set(frio["estado_frio"]) == {"Óptimo"}


def test_rf27_con_los_parametros_por_defecto_las_ventanas_truncadas_no_se_clasifican():
    frio = calcular_clima(_tres_anos_con_12_horas_de_frio_por_dia(), ParametrosClima(ventana_frio="temporada")).frio.set_index("periodo")

    assert pd.isna(frio.loc[2018, "estado_frio"]) and pd.isna(frio.loc[2021, "estado_frio"])
    assert frio.loc[2019, "estado_frio"] == "Óptimo" and frio.loc[2020, "estado_frio"] == "Óptimo"


def test_rf27_reproducir_el_notebook_exige_relajar_las_dos_reglas_no_solo_la_cobertura_minima():
    datos = _tres_anos_con_12_horas_de_frio_por_dia()

    solo_cobertura = calcular_clima(datos, ParametrosClima(ventana_frio="temporada", cobertura_minima=0)).frio.set_index("periodo")
    solo_hueco = calcular_clima(datos, ParametrosClima(ventana_frio="temporada", max_hueco_dias=None)).frio.set_index("periodo")

    assert pd.isna(solo_cobertura.loc[2018, "estado_frio"])  # el hueco de 62 días sigue impidiendo clasificar
    assert pd.isna(solo_hueco.loc[2018, "estado_frio"])      # la cobertura de 0,496 también


def _notebook_gdd_y_frio(tabla):
    """Reimplementación independiente de las celdas 12 y 14 del notebook 03, sobre una tabla con date, Tmax y Tmin."""
    d = tabla.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["Tmedia"] = (d["Tmax"] + d["Tmin"]) / 2
    d["gdd_diario"] = np.maximum(d["Tmedia"] - 10, 0)
    d["temporada"] = np.where(d["date"].dt.month >= 7, d["date"].dt.year, d["date"].dt.year - 1)
    gdd = d.groupby("temporada")["gdd_diario"].sum()
    dormancia = d[d["date"].dt.month.isin([5, 6, 7, 8])].copy()
    dormancia["horas_frio"] = [_horas_notebook(a, b) for a, b in zip(dormancia["Tmin"], dormancia["Tmax"])]
    frio = dormancia.groupby("temporada")["horas_frio"].sum()
    estado = pd.Series(np.where(frio >= 950, "Óptimo", np.where(frio >= 750, "Adecuado", "Deficiente")), index=frio.index)
    return gdd, frio, estado


def _horas_notebook(tmin, tmax, umbral=7.0):
    if tmax <= umbral:
        return 24.0
    if tmin >= umbral:
        return 0.0
    amp = (tmax - tmin) / 2.0
    tmedia = (tmax + tmin) / 2.0
    if amp <= 0:
        return 24.0 if tmedia < umbral else 0.0
    return (24.0 / np.pi) * (np.pi - np.arccos(np.clip((umbral - tmedia) / amp, -1.0, 1.0)))


def test_rf27_el_modo_de_reproduccion_coincide_con_el_calculo_del_notebook_sobre_datos_aleatorios():
    generador = np.random.default_rng(2024)
    fechas = pd.date_range("2019-01-01", "2022-03-28")
    tmin = generador.normal(8.0, 6.0, len(fechas))
    tmax = tmin + generador.uniform(3.0, 15.0, len(fechas))
    tabla = pd.DataFrame({"date": [f"{d:%Y-%m-%d}" for d in fechas], "Tmax": tmax, "Tmin": tmin})

    resultado = calcular_clima(tabla, ParametrosClima(**REPRODUCCION))
    gdd, frio, estado = _notebook_gdd_y_frio(tabla)

    assert resultado.gdd["temporada"].tolist() == gdd.index.tolist()
    assert resultado.gdd["GDD_total"].tolist() == pytest.approx(gdd.tolist(), abs=1e-9)
    assert resultado.frio["periodo"].tolist() == frio.index.tolist()
    assert resultado.frio["Horas_Frio"].tolist() == pytest.approx(frio.tolist(), abs=1e-9)
    assert resultado.frio["estado_frio"].tolist() == estado.tolist()
