import datetime

import pandas as pd
import pytest

from kiwitracking.clima_entrada import (
    descartar_fechas_duplicadas,
    normalizar_fechas,
    preparar_clima,
    validar_columnas_y_temperaturas,
    validar_temperaturas_plausibles,
)
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada


def _tabla():
    return pd.DataFrame(
        {
            "date": ["2019-01-01", "2019-01-02", "2019-01-03"],
            "Tmax": [27.4, 29.4, 24.5],
            "Tmin": [17.4, 18.1, 9.0],
        }
    )


# --- T2.2: columnas, tabla vacía y temperaturas numéricas ----------------------------------


def test_rf1_una_tabla_valida_no_da_error():
    validar_columnas_y_temperaturas(_tabla())


@pytest.mark.parametrize("columna", ["date", "Tmax", "Tmin"])
def test_rf1_falta_una_columna_obligatoria_y_el_error_la_nombra(columna):
    with pytest.raises(ErrorDeEntrada, match=columna):
        validar_columnas_y_temperaturas(_tabla().drop(columns=[columna]))


def test_rf1_si_faltan_varias_columnas_el_error_las_nombra_todas():
    with pytest.raises(ErrorDeEntrada) as error:
        validar_columnas_y_temperaturas(_tabla().drop(columns=["Tmax", "Tmin"]))

    assert "Tmax" in str(error.value) and "Tmin" in str(error.value)


def test_rf1_una_tabla_vacia_da_error():
    with pytest.raises(ErrorDeEntrada, match="vacía"):
        validar_columnas_y_temperaturas(_tabla().iloc[0:0])


def test_rf1_el_error_de_columnas_faltantes_va_antes_que_el_de_tabla_vacia():
    vacia_sin_columnas = _tabla().drop(columns=["Tmax"]).iloc[0:0]

    with pytest.raises(ErrorDeEntrada, match="Tmax"):
        validar_columnas_y_temperaturas(vacia_sin_columnas)


@pytest.mark.parametrize("columna", ["Tmax", "Tmin"])
def test_rf3_una_temperatura_con_texto_da_error_que_nombra_la_columna(columna):
    tabla = _tabla()
    tabla[columna] = ["10.5", "abc", "12.0"]

    with pytest.raises(ErrorDeEntrada, match=f"{columna}.*no numéric"):
        validar_columnas_y_temperaturas(tabla)


def test_rf3_numeros_escritos_como_texto_tambien_son_un_error():
    tabla = _tabla()
    tabla["Tmax"] = ["27.4", "29.4", "24.5"]

    with pytest.raises(ErrorDeEntrada, match="Tmax"):
        validar_columnas_y_temperaturas(tabla)


def test_rf3_con_coma_decimal_el_error_menciona_esa_causa_posible():
    tabla = _tabla()
    tabla["Tmax"] = ["27,4", "29,4", "24,5"]

    with pytest.raises(ErrorDeEntrada, match="coma decimal"):
        validar_columnas_y_temperaturas(tabla)


def test_rf3_un_texto_sin_comas_no_menciona_la_coma_decimal():
    tabla = _tabla()
    tabla["Tmax"] = ["abc", "def", "ghi"]

    with pytest.raises(ErrorDeEntrada) as error:
        validar_columnas_y_temperaturas(tabla)

    assert "coma decimal" not in str(error.value)


def test_rf3_los_valores_vacios_no_son_un_error():
    tabla = _tabla()
    tabla.loc[1, "Tmax"] = float("nan")
    tabla.loc[2, "Tmin"] = float("nan")

    validar_columnas_y_temperaturas(tabla)


def test_rf3_una_columna_de_objetos_con_numeros_y_vacios_no_es_un_error():
    tabla = _tabla()
    tabla["Tmax"] = pd.Series([27.4, None, 24.5], dtype=object)

    validar_columnas_y_temperaturas(tabla)


def test_rf3_una_columna_de_temperatura_completamente_vacia_no_es_un_error():
    tabla = _tabla()
    tabla["Tmax"] = pd.Series([None, None, None], dtype=object)

    validar_columnas_y_temperaturas(tabla)


def test_rf3_los_enteros_son_temperaturas_validas():
    tabla = _tabla()
    tabla["Tmax"] = [27, 29, 24]

    validar_columnas_y_temperaturas(tabla)


def test_rf1_las_columnas_extra_no_afectan_aunque_traigan_texto_o_numeros_precalculados():
    tabla = _tabla()
    tabla["Tmedia"] = [21.5, 23.7, 16.7]
    tabla["horas_frio"] = [0.0, 0.0, 3.2]
    tabla["comentario"] = ["a", "b", "c"]

    validar_columnas_y_temperaturas(tabla)


def test_rf1_no_modifica_la_tabla_de_entrada():
    tabla = _tabla()
    copia = tabla.copy()

    validar_columnas_y_temperaturas(tabla)

    pd.testing.assert_frame_equal(tabla, copia)


# --- T2.3: fechas ------------------------------------------------------------------------


def _dias(serie, **kwargs):
    return [f"{d:%Y-%m-%d}" for d in normalizar_fechas(serie, **kwargs)]


@pytest.mark.parametrize(
    "texto",
    ["2019-01-02", "2019-01-02 13:45", "2019-01-02 13:45:30", "2019-01-02T00:00:00", "2019-01-02T23:30:00-03:00", "  2019-01-02  "],
)
def test_rf2_el_formato_iso_con_o_sin_hora_o_zona_da_el_dia_tal_como_esta_escrito(texto):
    assert _dias(pd.Series([texto])) == ["2019-01-02"]


def test_rf2_la_zona_horaria_no_mueve_el_dia():
    # 23:30 en -03:00 serían las 02:30 del día 3 en UTC: el día escrito es el 2.
    assert _dias(pd.Series(["2019-01-02T23:30:00-03:00", "2019-01-02T00:10:00+05:00"])) == ["2019-01-02", "2019-01-02"]


def test_rf2_una_columna_ya_convertida_a_fecha_se_acepta():
    fechas = pd.Series([pd.Timestamp("2019-01-02 18:30"), pd.Timestamp("2019-01-03")])

    assert _dias(fechas) == ["2019-01-02", "2019-01-03"]


def test_rf2_una_columna_de_fechas_con_zona_horaria_conserva_el_dia_escrito():
    fechas = pd.Series(pd.to_datetime(["2019-01-02T23:30:00-03:00"]))

    assert _dias(fechas) == ["2019-01-02"]


def test_rf2_acepta_objetos_date_y_timestamp_en_una_columna_de_objetos():
    fechas = pd.Series([datetime.date(2019, 1, 2), pd.Timestamp("2019-01-03 10:00"), "2019-01-04"], dtype=object)

    assert _dias(fechas) == ["2019-01-02", "2019-01-03", "2019-01-04"]


def test_rf2_el_resultado_es_de_tipo_fecha_sin_hora_y_conserva_el_indice():
    resultado = normalizar_fechas(pd.Series(["2019-01-02 13:45", "2019-01-03"], index=[10, 20]))

    assert pd.api.types.is_datetime64_any_dtype(resultado)
    assert resultado.index.tolist() == [10, 20]
    assert (resultado == resultado.dt.normalize()).all()


def test_rf2_una_fecha_dd_mm_aaaa_no_se_interpreta_y_da_error_con_el_ejemplo():
    with pytest.raises(ErrorDeEntrada) as error:
        normalizar_fechas(pd.Series(["01/02/2019", "13/02/2019"]))

    assert "2 fechas" in str(error.value)
    assert "01/02/2019" in str(error.value)
    assert "AAAA-MM-DD" in str(error.value)


def test_rf2_con_formato_fecha_explicito_se_lee_exactamente_con_ese_formato():
    serie = pd.Series(["01/02/2019", "13/02/2019"])

    assert _dias(serie, formato_fecha="%d/%m/%Y") == ["2019-02-01", "2019-02-13"]


def test_rf2_el_mismo_texto_con_otro_formato_explicito_da_otra_fecha():
    assert _dias(pd.Series(["01/02/2019"]), formato_fecha="%m/%d/%Y") == ["2019-01-02"]


def test_rf2_con_formato_fecha_un_valor_que_no_lo_cumple_da_error_que_nombra_el_formato():
    with pytest.raises(ErrorDeEntrada) as error:
        normalizar_fechas(pd.Series(["01/02/2019", "2019-02-03"]), formato_fecha="%d/%m/%Y")

    assert "1 fecha" in str(error.value)
    assert "%d/%m/%Y" in str(error.value)


def test_rf2_una_fecha_con_formato_explicito_y_hora_conserva_solo_el_dia():
    assert _dias(pd.Series(["01/02/2019 18:30"]), formato_fecha="%d/%m/%Y %H:%M") == ["2019-02-01"]


@pytest.mark.parametrize("texto", ["2019-02-30", "2019-13-01", "2019-1-5", "2019-01-0213", "20190102", "2019/01/02", "enero"])
def test_rf2_los_textos_que_no_son_iso_o_no_son_fechas_reales_dan_error(texto):
    with pytest.raises(ErrorDeEntrada, match="1 fecha"):
        normalizar_fechas(pd.Series([texto]))


@pytest.mark.parametrize("vacio", [None, float("nan"), "", "   ", pd.NaT])
def test_rf2_una_fecha_vacia_da_error(vacio):
    with pytest.raises(ErrorDeEntrada, match="1 fecha.*vacías o ilegibles"):
        normalizar_fechas(pd.Series(["2019-01-02", vacio], dtype=object))


def test_rf2_el_error_cuenta_todas_las_fechas_invalidas():
    fechas = pd.Series(["2019-01-02", None, "01/02/2019", "", "2019-01-05"], dtype=object)

    with pytest.raises(ErrorDeEntrada, match="3 fechas"):
        normalizar_fechas(fechas)


def test_rf2_un_numero_no_es_una_fecha():
    with pytest.raises(ErrorDeEntrada, match="2 fechas"):
        normalizar_fechas(pd.Series([20190102, 43466], dtype=object))


def test_rf2_una_columna_de_fechas_con_valores_vacios_da_error():
    fechas = pd.Series(pd.to_datetime(["2019-01-02", None]))

    with pytest.raises(ErrorDeEntrada, match="1 fecha"):
        normalizar_fechas(fechas)


def test_rf2_no_modifica_la_serie_de_entrada():
    fechas = pd.Series(["2019-01-02 13:45", "2019-01-03"])
    copia = fechas.copy()

    normalizar_fechas(fechas)

    pd.testing.assert_series_equal(fechas, copia)


# --- T2.4: fechas repetidas --------------------------------------------------------------


def _dias_tabla(filas, **extra):
    """`filas`: lista de (fecha AAAA-MM-DD, Tmax, Tmin). La fecha ya viene normalizada, como la deja `normalizar_fechas`."""
    tabla = pd.DataFrame(filas, columns=["date", "Tmax", "Tmin"])
    tabla["date"] = pd.to_datetime(tabla["date"])
    for nombre, valores in extra.items():
        tabla[nombre] = valores
    return tabla


BASE = [("2019-01-01", 27.4, 17.4), ("2019-01-02", 29.4, 18.1), ("2019-01-03", 24.5, 9.0)]
NAN = float("nan")


def test_rf4_sin_fechas_repetidas_la_tabla_sale_igual_y_sin_advertencias():
    entrada = _dias_tabla(BASE)

    tabla, advertencias = descartar_fechas_duplicadas(entrada)

    pd.testing.assert_frame_equal(tabla, entrada)
    assert advertencias == []


def test_rf4_una_fecha_repetida_con_las_mismas_temperaturas_se_conserva_una_sola_vez():
    tabla, _ = descartar_fechas_duplicadas(_dias_tabla(BASE + [("2019-01-02", 29.4, 18.1)]))

    assert [f"{d:%Y-%m-%d}" for d in tabla["date"]] == ["2019-01-01", "2019-01-02", "2019-01-03"]


def test_rf4_se_avisa_con_codigo_estable_y_la_cantidad_descartada():
    entrada = _dias_tabla(BASE + [("2019-01-02", 29.4, 18.1), ("2019-01-03", 24.5, 9.0)])

    _, advertencias = descartar_fechas_duplicadas(entrada)

    assert [a.codigo for a in advertencias] == ["FECHA_DUPLICADA"]
    assert "2" in advertencias[0].mensaje


def test_rf4_tres_copias_de_la_misma_fecha_cuentan_dos_descartadas():
    _, advertencias = descartar_fechas_duplicadas(_dias_tabla(BASE + [("2019-01-01", 27.4, 17.4)] * 2))

    assert "2" in advertencias[0].mensaje


def test_rf4_se_conserva_la_primera_aparicion_y_el_orden_original():
    entrada = _dias_tabla([("2019-01-03", 24.5, 9.0), ("2019-01-01", 27.4, 17.4), ("2019-01-03", 24.5, 9.0)])

    tabla, _ = descartar_fechas_duplicadas(entrada)

    assert [f"{d:%Y-%m-%d}" for d in tabla["date"]] == ["2019-01-03", "2019-01-01"]


def test_rf4_dos_filas_de_la_misma_fecha_con_los_mismos_vacios_cuentan_como_identicas():
    entrada = _dias_tabla(BASE + [("2019-01-04", NAN, 5.0), ("2019-01-04", NAN, 5.0)])

    tabla, advertencias = descartar_fechas_duplicadas(entrada)

    assert len(tabla) == 4
    assert advertencias[0].codigo == "FECHA_DUPLICADA"


def test_rf4_una_columna_extra_distinta_no_hace_que_las_filas_sean_conflicto():
    # Las columnas extra se ignoran: solo cuentan date, Tmax y Tmin (se conserva la primera fila).
    entrada = _dias_tabla(BASE + [("2019-01-02", 29.4, 18.1)], Precip=[0.0, 5.0, 1.0, 9.9])

    tabla, advertencias = descartar_fechas_duplicadas(entrada)

    assert len(tabla) == 3
    assert tabla.loc[tabla["date"] == "2019-01-02", "Precip"].tolist() == [5.0]
    assert [a.codigo for a in advertencias] == ["FECHA_DUPLICADA"]


def test_rf4_la_misma_fecha_con_distinta_tmax_da_error_que_nombra_la_fecha():
    with pytest.raises(ErrorDeEntrada) as error:
        descartar_fechas_duplicadas(_dias_tabla(BASE + [("2019-01-02", 30.0, 18.1)]))

    assert "2019-01-02" in str(error.value)
    assert "distintas" in str(error.value)


def test_rf4_la_misma_fecha_con_distinta_tmin_da_error():
    with pytest.raises(ErrorDeEntrada, match="2019-01-03"):
        descartar_fechas_duplicadas(_dias_tabla(BASE + [("2019-01-03", 24.5, 8.0)]))


def test_rf4_un_valor_en_una_fila_y_vacio_en_la_otra_es_un_conflicto():
    with pytest.raises(ErrorDeEntrada, match="2019-01-02"):
        descartar_fechas_duplicadas(_dias_tabla(BASE + [("2019-01-02", NAN, 18.1)]))


def test_rf4_si_hay_duplicados_exactos_y_tambien_un_conflicto_manda_el_error():
    entrada = _dias_tabla(BASE + [("2019-01-01", 27.4, 17.4), ("2019-01-02", 31.0, 18.1)])

    with pytest.raises(ErrorDeEntrada, match="2019-01-02"):
        descartar_fechas_duplicadas(entrada)


def test_rf4_el_error_nombra_hasta_10_fechas_y_dice_cuantas_mas_hay():
    fechas = [f"2019-01-{d:02d}" for d in range(1, 16)]
    base = [(f, 20.0, 10.0) for f in fechas]
    conflictos = [(f, 25.0, 10.0) for f in fechas]  # 15 fechas con dos valores distintos

    with pytest.raises(ErrorDeEntrada) as error:
        descartar_fechas_duplicadas(_dias_tabla(base + conflictos))

    texto = str(error.value)
    assert "15" in texto and "y 5 más" in texto
    assert "2019-01-10" in texto and "2019-01-11" not in texto


def test_rf4_no_modifica_la_tabla_de_entrada():
    entrada = _dias_tabla(BASE + [("2019-01-02", 29.4, 18.1)])
    copia = entrada.copy()

    descartar_fechas_duplicadas(entrada)

    pd.testing.assert_frame_equal(entrada, copia)


# --- T2.5: Tmax < Tmin y rango físico ----------------------------------------------------


def _plausible(filas):
    """`filas`: lista de (fecha AAAA-MM-DD, Tmax, Tmin), con la fecha ya normalizada."""
    tabla = pd.DataFrame(filas, columns=["date", "Tmax", "Tmin"])
    tabla["date"] = pd.to_datetime(tabla["date"])
    return tabla


BUENAS = [("2019-01-01", 27.4, 17.4), ("2019-01-02", 29.4, 18.1), ("2019-01-03", 24.5, 9.0)]


def test_rf5_una_tabla_con_temperaturas_plausibles_no_da_error():
    validar_temperaturas_plausibles(_plausible(BUENAS))


def test_rf5_tmax_igual_a_tmin_es_valido_porque_la_amplitud_cero_no_es_un_error():
    validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", 12.0, 12.0)]))


def test_rf5_un_dia_con_tmax_menor_que_tmin_da_error_con_la_cantidad_y_la_fecha():
    with pytest.raises(ErrorDeEntrada) as error:
        validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", 10.0, 15.0)]))

    texto = str(error.value)
    assert "1 día" in texto and "Tmax menor que Tmin" in texto and "2019-01-04" in texto


def test_rf5_varios_dias_se_cuentan_y_se_nombran_las_primeras_10_fechas():
    invertidos = [(f"2019-02-{d:02d}", 10.0, 15.0) for d in range(1, 13)]  # 12 días con Tmax < Tmin

    with pytest.raises(ErrorDeEntrada) as error:
        validar_temperaturas_plausibles(_plausible(BUENAS + invertidos))

    texto = str(error.value)
    assert "12 días" in texto and "y 2 más" in texto
    assert "2019-02-10" in texto and "2019-02-11" not in texto


def test_rf5_un_dia_con_una_temperatura_vacia_no_se_cuenta_como_invertido():
    nan = float("nan")

    validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", nan, 15.0), ("2019-01-05", 10.0, nan)]))


def test_rf6_una_temperatura_fuera_del_rango_fisico_da_error_con_la_cantidad_y_un_ejemplo():
    with pytest.raises(ErrorDeEntrada) as error:
        validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", 20.0, -999.0)]))

    texto = str(error.value)
    assert "1 temperatura" in texto and "rango" in texto
    assert "-999" in texto and "2019-01-04" in texto


def test_rf6_se_cuentan_los_valores_de_las_dos_columnas():
    filas = BUENAS + [("2019-01-04", 999.0, 5.0), ("2019-01-05", 20.0, -999.0), ("2019-01-06", 70.0, -70.0)]

    with pytest.raises(ErrorDeEntrada, match="4 temperaturas"):
        validar_temperaturas_plausibles(_plausible(filas))


@pytest.mark.parametrize("valor,debe_fallar", [(60.0, False), (-60.0, False), (60.1, True), (-60.1, True)])
def test_rf6_los_limites_del_rango_estan_incluidos(valor, debe_fallar):
    filas = BUENAS + [("2019-01-04", 60.0 if valor < 0 else valor, valor if valor < 0 else -10.0)]

    if debe_fallar:
        with pytest.raises(ErrorDeEntrada, match="rango"):
            validar_temperaturas_plausibles(_plausible(filas))
    else:
        validar_temperaturas_plausibles(_plausible(filas))


def test_rf6_el_rango_fisico_es_un_parametro():
    filas = BUENAS + [("2019-01-04", 20.0, -40.0)]

    validar_temperaturas_plausibles(_plausible(filas))  # -40 está dentro de (-60, 60)
    with pytest.raises(ErrorDeEntrada, match="-30"):
        validar_temperaturas_plausibles(_plausible(filas), rango_fisico=(-30, 55))


def test_rf6_los_valores_vacios_no_estan_fuera_de_rango():
    validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", float("nan"), float("nan"))]))


def test_rf6_un_infinito_esta_fuera_de_rango():
    with pytest.raises(ErrorDeEntrada, match="rango"):
        validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", float("inf"), 5.0)]))


def test_rf5_y_rf6_si_hay_un_valor_fuera_de_rango_y_ademas_tmax_menor_que_tmin_manda_el_rango():
    # Tmax = -999 con Tmin = 5: además de invertido, es un valor imposible; el rango explica mejor la causa.
    with pytest.raises(ErrorDeEntrada) as error:
        validar_temperaturas_plausibles(_plausible(BUENAS + [("2019-01-04", -999.0, 5.0)]))

    assert "rango" in str(error.value)
    assert "Tmax menor que Tmin" not in str(error.value)


def test_rf5_y_rf6_no_modifican_la_tabla_de_entrada():
    entrada = _plausible(BUENAS)
    copia = entrada.copy()

    validar_temperaturas_plausibles(entrada)

    pd.testing.assert_frame_equal(entrada, copia)


# --- T2.6: días faltantes, orden y preparación completa ----------------------------------


def _entrada(filas, **extra):
    """`filas`: lista de (fecha en texto, Tmax, Tmin), tal como llegaría de un CSV."""
    tabla = pd.DataFrame(filas, columns=["date", "Tmax", "Tmin"])
    for nombre, valores in extra.items():
        tabla[nombre] = valores
    return tabla


FILAS = [("2019-01-01", 27.4, 17.4), ("2019-01-02", 29.4, 18.1), ("2019-01-03", 24.5, 9.0)]


def test_rf7_el_resultado_trae_date_tmax_tmin_y_disponible_con_los_tipos_esperados():
    tabla, advertencias = preparar_clima(_entrada(FILAS))

    assert list(tabla.columns) == ["date", "Tmax", "Tmin", "disponible"]
    assert pd.api.types.is_datetime64_any_dtype(tabla["date"])
    assert tabla["Tmax"].dtype == "float64" and tabla["Tmin"].dtype == "float64"
    assert tabla["disponible"].dtype == bool
    assert advertencias == []


def test_rf7_un_dia_con_tmax_o_tmin_vacio_queda_marcado_como_faltante_y_no_se_descarta():
    nan = float("nan")
    entrada = _entrada(FILAS + [("2019-01-04", nan, 5.0), ("2019-01-05", 20.0, nan), ("2019-01-06", nan, nan)])

    tabla, _ = preparar_clima(entrada)

    assert tabla["disponible"].tolist() == [True, True, True, False, False, False]
    assert len(tabla) == 6


def test_rf7_una_columna_de_objetos_con_none_se_trata_como_dias_faltantes():
    entrada = _entrada(FILAS)
    entrada["Tmax"] = pd.Series([27.4, None, 24.5], dtype=object)

    tabla, _ = preparar_clima(entrada)

    assert tabla["disponible"].tolist() == [True, False, True]
    assert tabla["Tmax"].dtype == "float64"


def test_rf8_el_resultado_no_depende_del_orden_de_las_filas():
    ordenada = _entrada(FILAS + [("2019-01-04", 21.0, 11.0)])
    desordenada = ordenada.iloc[[3, 0, 2, 1]].reset_index(drop=True)

    pd.testing.assert_frame_equal(preparar_clima(ordenada)[0], preparar_clima(desordenada)[0])


def test_rf8_el_resultado_sale_ordenado_por_fecha_con_indice_nuevo():
    tabla, _ = preparar_clima(_entrada(FILAS[::-1]))

    assert [f"{d:%Y-%m-%d}" for d in tabla["date"]] == ["2019-01-01", "2019-01-02", "2019-01-03"]
    assert tabla.index.tolist() == [0, 1, 2]


def test_rf8_las_filas_repetidas_y_desordenadas_dan_el_mismo_resultado_que_sin_repetir():
    limpia = _entrada(FILAS)
    sucia = _entrada(FILAS + [("2019-01-01", 27.4, 17.4)]).iloc[[3, 2, 1, 0]].reset_index(drop=True)

    tabla_sucia, advertencias = preparar_clima(sucia)

    pd.testing.assert_frame_equal(tabla_sucia, preparar_clima(limpia)[0])
    assert [a.codigo for a in advertencias] == ["FECHA_DUPLICADA"]


def test_rf8_las_columnas_extra_se_ignoran_y_no_pasan_al_resultado():
    entrada = _entrada(FILAS, Tmedia=[22.4, 23.7, 16.7], horas_frio=[0.0, 0.0, 3.2], Precip=[0.0, 5.0, 1.0])

    tabla, _ = preparar_clima(entrada)

    assert list(tabla.columns) == ["date", "Tmax", "Tmin", "disponible"]
    pd.testing.assert_frame_equal(tabla, preparar_clima(_entrada(FILAS))[0])


def test_rf7_y_rf8_no_modifican_la_tabla_de_entrada():
    entrada = _entrada(FILAS[::-1] + [("2019-01-01", 27.4, 17.4)])
    copia = entrada.copy()

    preparar_clima(entrada)

    pd.testing.assert_frame_equal(entrada, copia)


def test_rf2_preparar_clima_usa_el_formato_fecha_de_los_parametros():
    entrada = _entrada([("01/02/2019", 20.0, 10.0), ("02/02/2019", 21.0, 11.0)])

    tabla, _ = preparar_clima(entrada, ParametrosClima(formato_fecha="%d/%m/%Y"))

    assert [f"{d:%Y-%m-%d}" for d in tabla["date"]] == ["2019-02-01", "2019-02-02"]


def test_rf6_preparar_clima_usa_el_rango_fisico_de_los_parametros():
    entrada = _entrada(FILAS + [("2019-01-04", 20.0, -40.0)])

    preparar_clima(entrada)
    with pytest.raises(ErrorDeEntrada, match="rango"):
        preparar_clima(entrada, ParametrosClima(rango_fisico=(-30, 55)))


@pytest.mark.parametrize(
    "entrada,texto",
    [
        (_entrada(FILAS).drop(columns=["Tmax"]), "Tmax"),
        (_entrada(FILAS).assign(Tmax=["a", "b", "c"]), "no numéric"),
        (_entrada([("01/02/2019", 20.0, 10.0)]), "AAAA-MM-DD"),
        (_entrada(FILAS + [("2019-01-02", 30.0, 18.1)]), "distintas"),
        (_entrada(FILAS + [("2019-01-04", 10.0, 15.0)]), "Tmax menor que Tmin"),
        (_entrada(FILAS + [("2019-01-04", 20.0, -999.0)]), "rango"),
    ],
)
def test_rf1_a_rf6_preparar_clima_deja_pasar_los_errores_de_cada_validacion(entrada, texto):
    with pytest.raises(ErrorDeEntrada, match=texto):
        preparar_clima(entrada)


def test_rf7_una_tabla_de_una_sola_fila_se_prepara():
    tabla, _ = preparar_clima(_entrada(FILAS[:1]))

    assert len(tabla) == 1 and tabla["disponible"].tolist() == [True]
