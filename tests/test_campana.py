import pandas as pd
import pytest

from kiwitracking.campana import EstadoCampana, estado_frio_de_campana
from kiwitracking.clima import COLUMNAS_FRIO, ResultadoClima, calcular_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.validacion import ESTADOS_FRIO


def _resultado(filas, ventana="invierno"):
    """ResultadoClima armado a mano. `filas`: (período, horas, estado o None, cobertura, hueco máximo)."""
    frio = pd.DataFrame(
        [
            {
                "periodo": periodo,
                "Horas_Frio": horas,
                "estado_frio": estado,
                "dias_disponibles": round(cobertura * 123),
                "dias_esperados": 123,
                "cobertura": cobertura,
                "hueco_maximo": hueco,
                "completo": estado is not None,
            }
            for periodo, horas, estado, cobertura, hueco in filas
        ],
        columns=COLUMNAS_FRIO,
    )
    return ResultadoClima(gdd=pd.DataFrame(), frio=frio, advertencias=[], ventana_frio=ventana)


TRES_INVIERNOS = [(2019, 956.5, "Óptimo", 1.0, 0), (2020, 853.5, "Adecuado", 1.0, 0), (2021, 700.0, "Deficiente", 1.0, 0)]


# --- T2.13: última campaña clasificable (sin indicar la campaña) -------------------------------


def test_rf22_sin_indicar_la_campana_devuelve_la_ventana_clasificable_mas_reciente():
    resultado = estado_frio_de_campana(_resultado(TRES_INVIERNOS))

    assert isinstance(resultado, EstadoCampana)
    assert resultado.periodo == 2021 and resultado.estado == "Deficiente"  # clasificable aunque sea "Deficiente"


def test_rf22_trae_el_estado_el_periodo_las_horas_la_cobertura_y_el_hueco_maximo():
    resultado = estado_frio_de_campana(_resultado([(2019, 956.5, "Óptimo", 1.0, 0), (2020, 853.5, "Adecuado", 0.9675, 4)]))

    assert (resultado.estado, resultado.periodo) == ("Adecuado", 2020)
    assert resultado.horas == pytest.approx(853.5)
    assert resultado.cobertura == pytest.approx(0.9675)
    assert resultado.hueco_maximo == 4


def test_rf22_una_ventana_mas_reciente_que_no_se_clasifica_se_salta_y_se_usa_la_anterior():
    filas = [(2019, 956.5, "Óptimo", 1.0, 0), (2020, 853.5, "Adecuado", 1.0, 0), (2021, 439.2, None, 0.5, 61)]

    resultado = estado_frio_de_campana(_resultado(filas))

    assert (resultado.periodo, resultado.estado) == (2020, "Adecuado")


def test_rf22_el_orden_de_las_filas_no_cambia_el_resultado():
    desordenado = [TRES_INVIERNOS[1], TRES_INVIERNOS[2], TRES_INVIERNOS[0]]

    assert estado_frio_de_campana(_resultado(desordenado)).periodo == 2021


def test_rf22_el_estado_devuelto_es_uno_de_los_textos_de_la_spec_001():
    for fila in TRES_INVIERNOS:
        estado = estado_frio_de_campana(_resultado([fila])).estado

        assert estado == fila[2] and estado in ESTADOS_FRIO


def test_rf22_el_periodo_y_el_hueco_son_enteros_de_python():
    resultado = estado_frio_de_campana(_resultado(TRES_INVIERNOS))

    assert type(resultado.periodo) is int and type(resultado.hueco_maximo) is int
    assert isinstance(resultado.horas, float) and isinstance(resultado.cobertura, float)


def test_rf22_funciona_igual_en_modo_temporada():
    resultado = estado_frio_de_campana(_resultado(TRES_INVIERNOS, ventana="temporada"))

    assert (resultado.periodo, resultado.estado) == (2021, "Deficiente")


def test_rf22_no_modifica_el_resultado_de_clima():
    entrada = _resultado(TRES_INVIERNOS)
    copia = entrada.frio.copy()

    estado_frio_de_campana(entrada)

    pd.testing.assert_frame_equal(entrada.frio, copia)


def test_rf22_con_clima_calculado_elige_el_ultimo_invierno_completo_y_no_el_que_esta_a_medias():
    # Datos de enero de 2019 a junio de 2022: el invierno 2022 solo tiene mayo-junio (cobertura 0,496).
    fechas = pd.date_range("2019-01-01", "2022-06-30")
    frio = fechas.month.isin([5, 6, 7, 8])
    tabla = pd.DataFrame(
        {
            "date": [f"{d:%Y-%m-%d}" for d in fechas],
            "Tmax": [14.0 if f else 25.0 for f in frio],
            "Tmin": [0.0 if f else 15.0 for f in frio],
        }
    )

    clima = calcular_clima(tabla, ParametrosClima())
    resultado = estado_frio_de_campana(clima)

    assert clima.frio["periodo"].tolist() == [2019, 2020, 2021, 2022]
    assert pd.isna(clima.frio.set_index("periodo").loc[2022, "estado_frio"])
    assert (resultado.periodo, resultado.estado) == (2021, "Óptimo")


# --- T2.13: advertencia de campaña no indicada ----------------------------------------------


def test_rf28_sin_indicar_la_campana_avisa_campana_no_indicada_con_el_periodo_usado():
    resultado = estado_frio_de_campana(_resultado(TRES_INVIERNOS))

    assert [a.codigo for a in resultado.advertencias] == ["CAMPANA_NO_INDICADA"]
    mensaje = resultado.advertencias[0].mensaje
    assert "2021" in mensaje and "posterior" in mensaje and "última campaña" in mensaje


def test_rf28_el_mensaje_nombra_el_estado_y_las_horas_del_periodo_usado():
    mensaje = estado_frio_de_campana(_resultado([(2020, 853.5, "Adecuado", 1.0, 0)])).advertencias[0].mensaje

    assert "Adecuado" in mensaje and "854" in mensaje


# --- T2.13: ninguna ventana clasificable -----------------------------------------------------


def test_rf24_si_ninguna_ventana_es_clasificable_el_estado_queda_vacio_y_se_avisa():
    filas = [(2019, 400.0, None, 0.5, 61), (2020, 300.0, None, 0.4, 70)]

    resultado = estado_frio_de_campana(_resultado(filas))

    assert resultado.estado is None and resultado.periodo is None
    assert resultado.horas is None and resultado.cobertura is None and resultado.hueco_maximo is None
    assert [a.codigo for a in resultado.advertencias] == ["SIN_PERIODO_CLASIFICABLE"]


def test_rf24_sin_ningun_periodo_en_la_tabla_de_frio_tambien_queda_vacio():
    resultado = estado_frio_de_campana(_resultado([]))

    assert resultado.estado is None
    assert [a.codigo for a in resultado.advertencias] == ["SIN_PERIODO_CLASIFICABLE"]


def test_rf24_cuando_no_se_elige_ningun_periodo_no_se_avisa_campana_no_indicada():
    codigos = [a.codigo for a in estado_frio_de_campana(_resultado([(2019, 400.0, None, 0.5, 61)])).advertencias]

    assert "CAMPANA_NO_INDICADA" not in codigos


def test_rf24_el_mensaje_explica_por_que_no_hay_estado():
    mensaje = estado_frio_de_campana(_resultado([(2019, 400.0, None, 0.5, 61)])).advertencias[0].mensaje

    assert "ninguna" in mensaje.lower() and "clasific" in mensaje.lower()


# --- T2.14: campaña indicada y cobertura parcial ---------------------------------------------

CINCO_PERIODOS = [
    (2019, 956.5, "Óptimo", 1.0, 0),
    (2020, 853.5, "Adecuado", 1.0, 0),
    (2021, 925.0, "Adecuado", 1.0, 0),
    (2022, 1090.4, "Óptimo", 1.0, 0),
    (2023, 700.0, "Deficiente", 1.0, 0),
]


def test_rf23_con_campana_indicada_se_usa_el_periodo_de_esa_etiqueta_aunque_haya_uno_mas_reciente():
    resultado = estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=2020)

    assert (resultado.periodo, resultado.estado) == (2020, "Adecuado")
    assert resultado.horas == pytest.approx(853.5)


def test_rf23_con_campana_indicada_no_se_avisa_campana_no_indicada():
    resultado = estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=2022)

    assert resultado.advertencias == []


def test_rf23_indicar_la_ultima_campana_da_el_mismo_estado_que_no_indicarla_pero_sin_aviso():
    sin_indicar = estado_frio_de_campana(_resultado(CINCO_PERIODOS))
    indicada = estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=2023)

    assert (indicada.estado, indicada.periodo, indicada.horas) == (sin_indicar.estado, sin_indicar.periodo, sin_indicar.horas)
    assert [a.codigo for a in sin_indicar.advertencias] == ["CAMPANA_NO_INDICADA"] and indicada.advertencias == []


def test_rf23_acepta_un_entero_de_numpy_como_campana():
    import numpy as np

    assert estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=np.int64(2021)).periodo == 2021


def test_rf23_una_campana_sin_datos_da_error_que_dice_que_no_hay_datos_y_no_usa_otro_periodo():
    with pytest.raises(ErrorDeEntrada) as error:
        estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=2018)

    assert "2018" in str(error.value) and "sin datos" in str(error.value)


def test_rf23_una_campana_no_clasificable_da_error_con_su_cobertura_y_su_hueco_y_no_usa_otro_periodo():
    filas = CINCO_PERIODOS + [(2024, 439.2, None, 0.5, 61)]

    with pytest.raises(ErrorDeEntrada) as error:
        estado_frio_de_campana(_resultado(filas), campana=2024)

    texto = str(error.value)
    assert "2024" in texto and "no es clasificable" in texto
    assert "50,0" in texto and "61 días" in texto


def test_rf23_con_la_tabla_de_frio_vacia_una_campana_indicada_da_error_de_sin_datos():
    with pytest.raises(ErrorDeEntrada, match="sin datos"):
        estado_frio_de_campana(_resultado([]), campana=2020)


def test_rf23_el_mensaje_nombra_el_invierno_o_la_temporada_segun_el_modo():
    en_invierno = pytest.raises(ErrorDeEntrada)
    with en_invierno as error:
        estado_frio_de_campana(_resultado(CINCO_PERIODOS, ventana="invierno"), campana=2018)
    assert "invierno 2018" in str(error.value)

    with pytest.raises(ErrorDeEntrada) as error:
        estado_frio_de_campana(_resultado(CINCO_PERIODOS, ventana="temporada"), campana=2018)
    assert "temporada 2018" in str(error.value)


@pytest.mark.parametrize("valor", ["2020", 2020.5, True, 2020.0])
def test_rf23_una_campana_que_no_es_un_entero_da_error_que_nombra_el_parametro(valor):
    with pytest.raises(ErrorDeEntrada, match="campana"):
        estado_frio_de_campana(_resultado(CINCO_PERIODOS), campana=valor)


def test_rf23_en_modo_temporada_la_campana_se_corresponde_con_la_temporada_de_esa_etiqueta():
    resultado = estado_frio_de_campana(_resultado(CINCO_PERIODOS, ventana="temporada"), campana=2021)

    assert (resultado.periodo, resultado.estado) == (2021, "Adecuado")


# --- RF-25: cobertura parcial ------------------------------------------------------------------


def test_rf25_un_periodo_elegido_con_cobertura_menor_que_1_avisa_cobertura_parcial():
    filas = [(2024, 1128.8, "Óptimo", 1.0, 0), (2025, 834.2, "Adecuado", 119 / 123, 4)]

    resultado = estado_frio_de_campana(_resultado(filas), campana=2025)

    assert [a.codigo for a in resultado.advertencias] == ["COBERTURA_PARCIAL"]
    assert "2025" in resultado.advertencias[0].mensaje and "96,7" in resultado.advertencias[0].mensaje


def test_rf25_sin_indicar_la_campana_se_avisa_primero_la_campana_no_indicada_y_despues_la_cobertura():
    filas = [(2024, 1128.8, "Óptimo", 1.0, 0), (2025, 834.2, "Adecuado", 119 / 123, 4)]

    resultado = estado_frio_de_campana(_resultado(filas))

    assert [a.codigo for a in resultado.advertencias] == ["CAMPANA_NO_INDICADA", "COBERTURA_PARCIAL"]
    assert resultado.periodo == 2025


def test_rf25_con_cobertura_exactamente_1_no_se_avisa_cobertura_parcial():
    resultado = estado_frio_de_campana(_resultado([(2024, 1128.8, "Óptimo", 1.0, 0)]), campana=2024)

    assert resultado.advertencias == []


def test_rf25_la_cobertura_del_periodo_no_elegido_no_genera_aviso():
    # El 2025 tiene cobertura parcial, pero se pide el 2024, que está completo.
    filas = [(2024, 1128.8, "Óptimo", 1.0, 0), (2025, 834.2, "Adecuado", 119 / 123, 4)]

    assert estado_frio_de_campana(_resultado(filas), campana=2024).advertencias == []


def test_rf23_y_rf25_con_clima_calculado_como_el_caso_del_invierno_2025():
    # Inviernos 2023, 2024 y 2025 con 12 h de frío por día; en 2025 faltan los días del 8 al 11 de mayo.
    fechas = pd.date_range("2023-01-01", "2025-12-31")
    frio_dia = fechas.month.isin([5, 6, 7, 8])
    tabla = pd.DataFrame(
        {
            "date": [f"{d:%Y-%m-%d}" for d in fechas],
            "Tmax": [14.0 if f else 25.0 for f in frio_dia],
            "Tmin": [0.0 if f else 15.0 for f in frio_dia],
        }
    )
    tabla = tabla[~((tabla["date"] >= "2025-05-08") & (tabla["date"] <= "2025-05-11"))]

    clima = calcular_clima(tabla, ParametrosClima())
    sin_indicar = estado_frio_de_campana(clima)
    para_2024 = estado_frio_de_campana(clima, campana=2024)

    assert (sin_indicar.periodo, sin_indicar.estado) == (2025, "Óptimo")
    assert sin_indicar.cobertura == pytest.approx(119 / 123) and sin_indicar.hueco_maximo == 4
    assert [a.codigo for a in sin_indicar.advertencias] == ["CAMPANA_NO_INDICADA", "COBERTURA_PARCIAL"]
    assert (para_2024.periodo, para_2024.estado, para_2024.advertencias) == (2024, "Óptimo", [])


def test_rf23_no_modifica_el_resultado_de_clima_con_campana_indicada():
    entrada = _resultado(CINCO_PERIODOS)
    copia = entrada.frio.copy()

    estado_frio_de_campana(entrada, campana=2021)

    pd.testing.assert_frame_equal(entrada.frio, copia)
