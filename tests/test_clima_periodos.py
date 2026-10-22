import pandas as pd
import pytest

from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.clima_periodos import (
    cobertura_temporadas,
    cobertura_ventanas,
    dias_esperados_temporada,
    dias_esperados_ventana,
    etiqueta_temporada,
    etiqueta_ventana,
    evaluar_cobertura,
)


def _fechas(*textos):
    return pd.Series(pd.to_datetime(list(textos)))


def _texto(indice):
    return [f"{d:%Y-%m-%d}" for d in indice]


# --- T2.8: temporadas ---------------------------------------------------------------------


def test_rf12_la_temporada_empieza_el_1_de_julio_y_se_etiqueta_con_el_ano_de_inicio():
    fechas = _fechas("2019-06-30", "2019-07-01", "2019-12-31", "2020-01-01", "2020-06-30", "2020-07-01")

    etiquetas = etiqueta_temporada(fechas, ParametrosClima())

    assert etiquetas.tolist() == [2018, 2019, 2019, 2019, 2019, 2020]


def test_rf12_mes_inicio_temporada_es_un_parametro():
    fechas = _fechas("2019-08-31", "2019-09-01", "2020-01-15")

    assert etiqueta_temporada(fechas, ParametrosClima(mes_inicio_temporada=9)).tolist() == [2018, 2019, 2019]


def test_rf12_con_inicio_en_enero_la_temporada_es_el_ano_calendario():
    fechas = _fechas("2019-01-01", "2019-12-31", "2020-01-01")

    assert etiqueta_temporada(fechas, ParametrosClima(mes_inicio_temporada=1)).tolist() == [2019, 2019, 2020]


def test_rf12_los_dias_esperados_de_una_temporada_van_del_1_de_julio_al_30_de_junio():
    dias = dias_esperados_temporada(2020, ParametrosClima())

    assert _texto(dias[[0, -1]]) == ["2020-07-01", "2021-06-30"]
    assert len(dias) == 365


def test_rf12_una_temporada_que_incluye_un_29_de_febrero_tiene_366_dias():
    dias = dias_esperados_temporada(2019, ParametrosClima())  # julio de 2019 a junio de 2020 (2020 es bisiesto)

    assert len(dias) == 366
    assert "2020-02-29" in _texto(dias)


def test_rf12_con_inicio_en_enero_un_ano_bisiesto_completo_tiene_366_dias():
    dias = dias_esperados_temporada(2020, ParametrosClima(mes_inicio_temporada=1))

    assert _texto(dias[[0, -1]]) == ["2020-01-01", "2020-12-31"]
    assert len(dias) == 366


def test_rf12_con_inicio_en_septiembre_la_temporada_cruza_el_ano_y_termina_el_31_de_agosto():
    dias = dias_esperados_temporada(2019, ParametrosClima(mes_inicio_temporada=9))

    assert _texto(dias[[0, -1]]) == ["2019-09-01", "2020-08-31"]


# --- T2.8: ventana de frío en modo "invierno" ---------------------------------------------


def test_rf13_en_modo_invierno_la_ventana_de_cada_ano_va_de_mayo_a_agosto_de_ese_ano():
    dias = dias_esperados_ventana(2019, ParametrosClima(ventana_frio="invierno"))

    assert _texto(dias[[0, -1]]) == ["2019-05-01", "2019-08-31"]
    assert len(dias) == 123


def test_rf13_en_modo_invierno_la_ventana_tiene_123_dias_tambien_en_ano_bisiesto():
    # El 29 de febrero cae fuera de mayo-agosto: la ventana no cambia de tamaño.
    assert len(dias_esperados_ventana(2020, ParametrosClima(ventana_frio="invierno"))) == 123


def test_rf13_meses_frio_es_un_parametro_en_modo_invierno():
    assert len(dias_esperados_ventana(2019, ParametrosClima(meses_frio=(6, 7)))) == 61
    # enero a marzo: 31 + 28 + 31 en un año común y 91 en uno bisiesto
    assert len(dias_esperados_ventana(2019, ParametrosClima(meses_frio=(1, 2, 3)))) == 90
    assert len(dias_esperados_ventana(2020, ParametrosClima(meses_frio=(1, 2, 3)))) == 91


def test_rf13_en_modo_invierno_la_etiqueta_es_el_ano_de_la_fecha_si_el_mes_esta_en_la_ventana():
    fechas = _fechas("2019-04-30", "2019-05-01", "2019-08-31", "2019-09-01", "2020-06-15")

    etiquetas = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="invierno"))

    assert etiquetas.isna().tolist() == [True, False, False, True, False]
    assert etiquetas.dropna().tolist() == [2019, 2019, 2020]


# --- T2.8: ventana de frío en modo "temporada" (cálculo del notebook) ----------------------


def test_rf13_en_modo_temporada_la_ventana_mezcla_julio_agosto_de_un_ano_con_mayo_junio_del_siguiente():
    dias = _texto(dias_esperados_ventana(2019, ParametrosClima(ventana_frio="temporada")))

    assert len(dias) == 123
    assert dias[0] == "2019-07-01" and dias[-1] == "2020-06-30"
    assert "2019-08-31" in dias and "2020-05-01" in dias
    assert "2019-05-15" not in dias  # mayo de 2019 pertenece a la ventana de la temporada anterior
    assert "2019-09-15" not in dias


def test_rf13_en_modo_temporada_dos_inviernos_distintos_comparten_una_misma_ventana():
    # La ventana 2024 suma julio-agosto de 2024 y mayo-junio de 2025: dos inviernos distintos.
    dias = _texto(dias_esperados_ventana(2024, ParametrosClima(ventana_frio="temporada")))

    assert any(d.startswith("2024-07") for d in dias) and any(d.startswith("2025-05") for d in dias)
    assert not any(d.startswith("2024-05") for d in dias)


def test_rf13_en_modo_temporada_la_etiqueta_es_la_de_la_temporada_si_el_mes_esta_en_la_ventana():
    fechas = _fechas("2019-05-01", "2019-06-30", "2019-07-01", "2019-08-31", "2019-09-01", "2020-05-15")

    etiquetas = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="temporada"))

    assert etiquetas.isna().tolist() == [False, False, False, False, True, False]
    assert etiquetas.dropna().tolist() == [2018, 2018, 2019, 2019, 2019]


def test_rf13_la_misma_fecha_tiene_etiqueta_distinta_segun_el_modo():
    fechas = _fechas("2019-05-15")

    invierno = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="invierno")).tolist()
    temporada = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="temporada")).tolist()

    assert invierno == [2019] and temporada == [2018]


def test_rf13_mes_inicio_temporada_no_afecta_al_modo_invierno():
    fechas = _fechas("2019-05-15", "2019-07-10")

    base = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="invierno", mes_inicio_temporada=7))
    otro = etiqueta_ventana(fechas, ParametrosClima(ventana_frio="invierno", mes_inicio_temporada=10))

    assert base.tolist() == otro.tolist() == [2019, 2019]


def test_rf13_toda_fecha_con_etiqueta_pertenece_a_los_dias_esperados_de_esa_etiqueta():
    # Coherencia entre las dos funciones, en los dos modos, durante tres años seguidos.
    fechas = pd.Series(pd.date_range("2019-01-01", "2021-12-31"))
    for modo in ("invierno", "temporada"):
        parametros = ParametrosClima(ventana_frio=modo)
        etiquetas = etiqueta_ventana(fechas, parametros)
        for etiqueta in sorted(etiquetas.dropna().unique()):
            esperados = set(dias_esperados_ventana(int(etiqueta), parametros))
            asignadas = set(fechas[etiquetas == etiqueta])
            assert asignadas <= esperados


def test_rf12_y_rf13_no_modifican_la_serie_de_entrada():
    fechas = _fechas("2019-05-15", "2019-07-10")
    copia = fechas.copy()

    etiqueta_temporada(fechas, ParametrosClima())
    etiqueta_ventana(fechas, ParametrosClima())

    pd.testing.assert_series_equal(fechas, copia)


# --- T2.9: cobertura, hueco máximo y período completo -------------------------------------


def _dias(inicio, fin, faltantes=(), como_vacios=False):
    """Tabla preparada (date, disponible) entre `inicio` y `fin`.

    `faltantes` son rangos (desde, hasta) de días sin datos: se quitan de la tabla, o se dejan con
    `disponible` falso si `como_vacios` es verdadero.
    """
    fechas = pd.date_range(inicio, fin)
    tabla = pd.DataFrame({"date": fechas, "disponible": True})
    for desde, hasta in faltantes:
        en_rango = (tabla["date"] >= desde) & (tabla["date"] <= hasta)
        if como_vacios:
            tabla.loc[en_rango, "disponible"] = False
        else:
            tabla = tabla[~en_rango]
    return tabla.reset_index(drop=True)


def test_rf14_una_ventana_completa_tiene_cobertura_1_y_hueco_0():
    cobertura = cobertura_ventanas(_dias("2019-05-01", "2019-08-31"), ParametrosClima())

    fila = cobertura.loc[2019]
    assert (fila["dias_disponibles"], fila["dias_esperados"]) == (123, 123)
    assert fila["cobertura"] == 1.0 and fila["hueco_maximo"] == 0 and fila["completo"]


def test_rf14_cuatro_dias_faltantes_dan_119_de_123_y_hueco_4_como_el_invierno_2025():
    cobertura = cobertura_ventanas(_dias("2025-05-01", "2025-08-31", [("2025-05-08", "2025-05-11")]), ParametrosClima())

    fila = cobertura.loc[2025]
    assert (fila["dias_disponibles"], fila["dias_esperados"], fila["hueco_maximo"]) == (119, 123, 4)
    assert fila["cobertura"] == pytest.approx(119 / 123)
    assert fila["completo"]  # 0,9675 >= 0,9 y 4 <= 7


def test_rf14_los_dias_con_fila_pero_sin_temperaturas_cuentan_como_faltantes_igual_que_los_que_no_tienen_fila():
    sin_fila = cobertura_ventanas(_dias("2025-05-01", "2025-08-31", [("2025-05-08", "2025-05-11")]), ParametrosClima())
    con_fila = cobertura_ventanas(
        _dias("2025-05-01", "2025-08-31", [("2025-05-08", "2025-05-11")], como_vacios=True), ParametrosClima()
    )

    pd.testing.assert_frame_equal(sin_fila, con_fila)


def test_rf14_el_hueco_maximo_es_la_racha_mas_larga_de_dias_consecutivos_sin_datos():
    faltantes = [("2019-05-10", "2019-05-12"), ("2019-06-20", "2019-06-29"), ("2019-08-01", "2019-08-05")]  # 3, 10 y 5 días

    fila = cobertura_ventanas(_dias("2019-05-01", "2019-08-31", faltantes), ParametrosClima()).loc[2019]

    assert fila["hueco_maximo"] == 10 and fila["dias_disponibles"] == 123 - 18


def test_rf14_los_dias_esperados_incluyen_los_que_quedan_fuera_del_rango_de_los_datos():
    # Datos de enero a diciembre de 2019: la temporada 2018 solo tiene enero-junio de 2019 (181 de 365 días).
    cobertura = cobertura_temporadas(_dias("2019-01-01", "2019-12-31"), ParametrosClima())

    primera = cobertura.loc[2018]
    assert (primera["dias_disponibles"], primera["dias_esperados"]) == (181, 365)
    assert primera["hueco_maximo"] == 184  # de julio a diciembre de 2018
    assert primera["cobertura"] == pytest.approx(181 / 365) and not primera["completo"]


def test_rf14_una_temporada_con_datos_solo_al_principio_cuenta_el_hueco_del_final():
    cobertura = cobertura_temporadas(_dias("2019-01-01", "2019-12-31"), ParametrosClima())

    segunda = cobertura.loc[2019]  # julio de 2019 a junio de 2020: hay datos de julio a diciembre de 2019
    assert (segunda["dias_disponibles"], segunda["dias_esperados"], segunda["hueco_maximo"]) == (184, 366, 182)


def test_rf14_los_dias_fuera_de_los_meses_de_la_ventana_no_cuentan_para_su_cobertura():
    # Faltan los 30 días de septiembre, que no pertenecen a la ventana de mayo a agosto.
    fila = cobertura_ventanas(_dias("2019-05-01", "2019-12-31", [("2019-09-01", "2019-09-30")]), ParametrosClima()).loc[2019]

    assert fila["cobertura"] == 1.0 and fila["hueco_maximo"] == 0


def test_rf14_en_modo_temporada_la_cobertura_de_la_ventana_suma_mayo_junio_del_ano_siguiente():
    faltantes = [("2025-05-08", "2025-05-11")]
    tabla = _dias("2024-07-01", "2025-08-31", faltantes)

    fila = cobertura_ventanas(tabla, ParametrosClima(ventana_frio="temporada")).loc[2024]

    assert (fila["dias_disponibles"], fila["dias_esperados"], fila["hueco_maximo"]) == (119, 123, 4)


# --- T2.9: período completo ---------------------------------------------------------------


def _generica(disponibles, esperados, **parametros):
    dias = pd.date_range("2019-01-01", periods=esperados)
    tabla = pd.DataFrame({"date": dias[:disponibles], "disponible": True})
    etiquetas = pd.Series(1, index=tabla.index, dtype="Int64")
    return evaluar_cobertura(tabla, etiquetas, lambda etiqueta: dias, ParametrosClima(**parametros)).loc[1]


@pytest.mark.parametrize(
    "disponibles,esperados,minimo,completo",
    [
        (7, 25, 0.28, True),   # 7 / 25 = 0,28; pero 0,28 x 25 = 7,000000000000001 y 7 >= 7,000000000000001 es falso
        (6, 25, 0.28, False),
        (14, 25, 0.56, True),  # igual: 0,56 x 25 = 14,000000000000002
        (13, 25, 0.56, False),
        (57, 100, 0.57, True),
        (56, 100, 0.57, False),
        (9, 10, 0.9, True),
        (8, 10, 0.9, False),
        (7, 10, 0.7, True),
    ],
)
def test_rf15_la_cobertura_se_compara_dividiendo_asi_que_el_borde_exacto_es_completo(disponibles, esperados, minimo, completo):
    # Dividir (disponibles / esperados >= minimo) acierta en el borde exacto; multiplicar (minimo x esperados)
    # lo rechaza en los dos primeros casos por el error de redondeo del punto flotante.
    fila = _generica(disponibles, esperados, cobertura_minima=minimo, max_hueco_dias=None)

    assert bool(fila["completo"]) is completo


def test_rf15_un_hueco_de_8_dias_con_limite_7_hace_incompleto_un_periodo_con_cobertura_de_98_por_ciento():
    # Temporada de 365 días con 8 días seguidos sin datos: 357 / 365 = 0,978.
    tabla = _dias("2020-07-01", "2021-06-30", [("2020-10-01", "2020-10-08")])

    fila = cobertura_temporadas(tabla, ParametrosClima()).loc[2020]

    assert fila["cobertura"] == pytest.approx(357 / 365) and fila["cobertura"] > 0.97
    assert fila["hueco_maximo"] == 8 and not fila["completo"]


def test_rf15_un_hueco_de_7_dias_con_limite_7_es_completo():
    tabla = _dias("2020-07-01", "2021-06-30", [("2020-10-01", "2020-10-07")])

    assert cobertura_temporadas(tabla, ParametrosClima()).loc[2020]["completo"]


def test_rf15_max_hueco_dias_none_desactiva_el_limite():
    tabla = _dias("2020-07-01", "2021-06-30", [("2020-10-01", "2020-10-30")])  # hueco de 30 días, cobertura 0,92

    con_limite = cobertura_temporadas(tabla, ParametrosClima()).loc[2020]
    sin_limite = cobertura_temporadas(tabla, ParametrosClima(max_hueco_dias=None)).loc[2020]

    assert con_limite["cobertura"] > 0.9 and not con_limite["completo"]
    assert sin_limite["completo"]


def test_rf15_max_hueco_dias_cero_solo_admite_periodos_sin_ningun_dia_faltante():
    parametros = ParametrosClima(max_hueco_dias=0)
    completa = cobertura_ventanas(_dias("2019-05-01", "2019-08-31"), parametros).loc[2019]
    con_un_dia_menos = cobertura_ventanas(_dias("2019-05-01", "2019-08-31", [("2019-06-01", "2019-06-01")]), parametros).loc[2019]

    assert completa["completo"] and not con_un_dia_menos["completo"]


def test_rf15_cobertura_minima_1_solo_admite_periodos_completos_y_0_admite_cualquiera_con_cobertura_positiva():
    tabla = _dias("2019-05-01", "2019-08-31", [("2019-06-01", "2019-06-03")])

    estricta = cobertura_ventanas(tabla, ParametrosClima(cobertura_minima=1, max_hueco_dias=None)).loc[2019]
    laxa = cobertura_ventanas(tabla, ParametrosClima(cobertura_minima=0, max_hueco_dias=None)).loc[2019]

    assert not estricta["completo"] and laxa["completo"]


def test_rf15_las_dos_condiciones_deben_cumplirse_a_la_vez():
    # Cobertura insuficiente con hueco corto: incompleto; cobertura suficiente con hueco largo: incompleto.
    corto_y_muchos = [(f"2019-05-{d:02d}", f"2019-05-{d:02d}") for d in range(1, 31, 2)]  # 15 días sueltos, hueco 1
    suelto = cobertura_ventanas(_dias("2019-05-01", "2019-08-31", corto_y_muchos + [("2019-07-01", "2019-07-31")]), ParametrosClima())

    assert suelto.loc[2019]["hueco_maximo"] == 31 and not suelto.loc[2019]["completo"]


# --- T2.9: períodos sin datos y forma de la salida ----------------------------------------


def test_rf16_un_periodo_sin_ningun_dia_disponible_no_aparece_en_el_resultado():
    cobertura = cobertura_ventanas(_dias("2020-05-01", "2020-08-31"), ParametrosClima())

    assert cobertura.index.tolist() == [2020]  # el invierno 2019 (sin datos) no aparece


def test_rf16_un_periodo_con_filas_pero_todas_sin_temperaturas_tampoco_aparece():
    tabla = _dias("2019-05-01", "2019-08-31", [("2019-05-01", "2019-08-31")], como_vacios=True)

    assert cobertura_ventanas(tabla, ParametrosClima()).empty


def test_rf14_la_salida_trae_las_columnas_esperadas_con_sus_tipos_y_ordenada_por_etiqueta():
    tabla = pd.concat([_dias("2021-05-01", "2021-08-31"), _dias("2019-05-01", "2019-08-31")], ignore_index=True)

    cobertura = cobertura_ventanas(tabla, ParametrosClima())

    assert cobertura.index.tolist() == [2019, 2021]
    assert list(cobertura.columns) == ["dias_disponibles", "dias_esperados", "cobertura", "hueco_maximo", "completo"]
    assert cobertura["completo"].dtype == bool
    assert pd.api.types.is_integer_dtype(cobertura["dias_disponibles"]) and pd.api.types.is_float_dtype(cobertura["cobertura"])


def test_rf14_el_resultado_no_depende_del_orden_de_las_filas():
    tabla = _dias("2019-05-01", "2019-08-31", [("2019-06-10", "2019-06-12")])

    ordenada = cobertura_ventanas(tabla, ParametrosClima())
    desordenada = cobertura_ventanas(tabla.sample(frac=1, random_state=3).reset_index(drop=True), ParametrosClima())

    pd.testing.assert_frame_equal(ordenada, desordenada)


def test_rf14_no_modifica_la_tabla_de_entrada():
    tabla = _dias("2019-05-01", "2019-08-31", [("2019-06-10", "2019-06-12")])
    copia = tabla.copy()

    cobertura_ventanas(tabla, ParametrosClima())
    cobertura_temporadas(tabla, ParametrosClima())

    pd.testing.assert_frame_equal(tabla, copia)
