"""T5.3: el estado de la campaña y el aviso de días estimados (RF-2, RF-6, RF-7 y RF-8 de la spec 005)."""

import dataclasses

import pandas as pd
import pytest

from kiwitracking.campana import EstadoCampana, estado_frio_de_campana
from kiwitracking.clima import COLUMNAS_FRIO, ResultadoClima, calcular_clima
from kiwitracking.clima_origen import COLUMNAS_ESTIMADOS, estimados_vacios
from kiwitracking.resultado import Advertencia


def _resultado(filas, estimados=()):
    """ResultadoClima armado a mano. `filas`: (período, horas, estado o None, días disponibles).
    `estimados`: (período, días estimados, proporción)."""
    frio = pd.DataFrame(
        [
            {
                "periodo": periodo,
                "Horas_Frio": horas,
                "estado_frio": estado,
                "dias_disponibles": disponibles,
                "dias_esperados": 123,
                "cobertura": disponibles / 123,
                "hueco_maximo": 0 if disponibles == 123 else 4,
                "completo": estado is not None,
            }
            for periodo, horas, estado, disponibles in filas
        ],
        columns=COLUMNAS_FRIO,
    )
    tabla = (
        pd.DataFrame(list(estimados), columns=COLUMNAS_ESTIMADOS).astype(
            {"periodo": "int64", "dias_estimados": "int64", "proporcion_estimada": "float64"}
        )
        if estimados
        else estimados_vacios()
    )
    return ResultadoClima(gdd=pd.DataFrame(), frio=frio, advertencias=[], ventana_frio="invierno", estimados=tabla)


TRES = [(2023, 956.5, "Óptimo", 123), (2024, 1128.8, "Óptimo", 123), (2025, 853.5, "Adecuado", 119)]
ESTIMADOS = [(2023, 4, 4 / 123), (2024, 26, 26 / 123), (2025, 8, 8 / 119)]


def _codigos(estado):
    return [a.codigo for a in estado.advertencias]


def _aviso(estado):
    return next(a for a in estado.advertencias if a.codigo == "DIAS_ESTIMADOS")


def test_rf6_con_campana_indicada_trae_los_dias_estimados_del_periodo_elegido():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS), 2024)
    assert estado.periodo == 2024
    assert estado.dias_estimados == 26
    assert estado.proporcion_estimada == pytest.approx(26 / 123)


def test_rf6_el_aviso_nombra_el_periodo_los_dias_estimados_de_cuantos_el_porcentaje_y_que_no_son_mediciones():
    mensaje = _aviso(estado_frio_de_campana(_resultado(TRES, ESTIMADOS), 2024)).mensaje
    assert "2024" in mensaje and "26 de 123" in mensaje and "21,1 %" in mensaje
    assert "estimados" in mensaje and "no son mediciones" in mensaje


def test_rf6_el_aviso_usa_los_dias_disponibles_y_no_los_esperados():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS), 2025)
    assert "8 de 119" in _aviso(estado).mensaje and "6,7 %" in _aviso(estado).mensaje


def test_rf6_sin_indicar_la_campana_el_recuento_es_el_de_la_ventana_clasificable_mas_reciente():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS))
    assert estado.periodo == 2025 and estado.dias_estimados == 8
    assert "2025" in _aviso(estado).mensaje


def test_rf6_una_ventana_mas_reciente_no_clasificable_con_estimados_no_genera_aviso():
    filas = TRES + [(2026, 100.0, None, 40)]
    estado = estado_frio_de_campana(_resultado(filas, ESTIMADOS + [(2026, 9, 9 / 40)]))
    assert estado.periodo == 2025
    assert "2026" not in _aviso(estado).mensaje


def test_rf6_solo_se_avisa_del_periodo_que_decide_el_estado():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS), 2023)
    avisos = [a for a in estado.advertencias if a.codigo == "DIAS_ESTIMADOS"]
    assert len(avisos) == 1 and "4 de 123" in avisos[0].mensaje
    assert "26" not in avisos[0].mensaje


def test_rf6_con_cero_dias_estimados_no_hay_aviso_y_el_recuento_es_cero():
    estado = estado_frio_de_campana(_resultado(TRES, [(2024, 0, 0.0)]), 2024)
    assert "DIAS_ESTIMADOS" not in _codigos(estado)
    assert estado.dias_estimados == 0 and estado.proporcion_estimada == 0.0


def test_rf2_sin_fila_para_el_periodo_los_valores_quedan_vacios_y_no_hay_aviso():
    estado = estado_frio_de_campana(_resultado(TRES), 2024)
    assert estado.dias_estimados is None and estado.proporcion_estimada is None
    assert "DIAS_ESTIMADOS" not in _codigos(estado)


def test_rf2_si_el_periodo_elegido_no_esta_en_estimados_pero_otros_si_no_hay_aviso():
    estado = estado_frio_de_campana(_resultado(TRES, [(2023, 4, 4 / 123)]), 2024)
    assert estado.dias_estimados is None and "DIAS_ESTIMADOS" not in _codigos(estado)


def test_rf6_sin_ventana_clasificable_no_hay_recuento_ni_aviso():
    estado = estado_frio_de_campana(_resultado([(2024, 439.2, None, 60)], [(2024, 9, 9 / 60)]))
    assert estado.estado is None
    assert estado.dias_estimados is None and estado.proporcion_estimada is None
    assert _codigos(estado) == ["SIN_PERIODO_CLASIFICABLE"]


def test_rf7_el_aviso_sale_despues_de_campana_no_indicada_y_de_cobertura_parcial():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS))
    assert _codigos(estado) == ["CAMPANA_NO_INDICADA", "COBERTURA_PARCIAL", "DIAS_ESTIMADOS"]


def test_rf7_con_campana_indicada_sale_despues_de_cobertura_parcial():
    estado = estado_frio_de_campana(_resultado(TRES, ESTIMADOS), 2025)
    assert _codigos(estado) == ["COBERTURA_PARCIAL", "DIAS_ESTIMADOS"]


def test_rf7_con_cobertura_completa_y_sin_campana_indicada_va_despues_de_campana_no_indicada():
    estado = estado_frio_de_campana(_resultado(TRES[:2], ESTIMADOS))
    assert _codigos(estado) == ["CAMPANA_NO_INDICADA", "DIAS_ESTIMADOS"]


@pytest.mark.parametrize("campana", [None, 2023, 2024, 2025])
def test_rf8_el_aviso_no_cambia_el_estado_ni_las_horas_ni_las_demas_advertencias(campana):
    con = estado_frio_de_campana(_resultado(TRES, ESTIMADOS), campana)
    sin = estado_frio_de_campana(_resultado(TRES), campana)
    for campo in ("estado", "periodo", "horas", "cobertura", "hueco_maximo"):
        assert getattr(con, campo) == getattr(sin, campo)
    assert [a for a in con.advertencias if a.codigo != "DIAS_ESTIMADOS"] == sin.advertencias


def test_rf8_el_estado_es_el_mismo_con_el_96_por_ciento_de_los_dias_estimados():
    estado = estado_frio_de_campana(_resultado(TRES, [(2024, 118, 118 / 123)]), 2024)
    assert estado.estado == "Óptimo" and estado.horas == pytest.approx(1128.8)


def test_los_campos_nuevos_van_al_final_y_con_valor_por_defecto():
    nombres = [campo.name for campo in dataclasses.fields(EstadoCampana)]
    assert nombres[-2:] == ["dias_estimados", "proporcion_estimada"]
    vacio = EstadoCampana(None, None, None, None, None, [Advertencia("X", "x")])
    assert vacio.dias_estimados is None and vacio.proporcion_estimada is None and vacio.advertencias[0].codigo == "X"


# --- el recuento viene de un clima real calculado con calcular_clima ------------------------------------------------


def _clima_con_estimados():
    def invierno(anio, estimados):
        fechas = pd.date_range(f"{anio}-05-01", f"{anio}-08-31", freq="D").strftime("%Y-%m-%d")
        tabla = pd.DataFrame({"date": fechas, "Tmax": 12.0, "Tmin": 2.0, "origen": "INTA_verificado"})
        tabla.loc[: estimados - 1, "origen"] = "interpolado"
        return tabla

    return pd.concat([invierno(2023, 4), invierno(2024, 26)], ignore_index=True)


def test_rf6_con_calcular_clima_el_estado_trae_el_recuento_y_el_aviso():
    resultado = calcular_clima(_clima_con_estimados())
    estado = estado_frio_de_campana(resultado, 2024)
    assert (estado.dias_estimados, estado.proporcion_estimada) == (26, pytest.approx(26 / 123))
    assert "26 de 123" in _aviso(estado).mensaje


def test_rf2_con_calcular_clima_sin_la_columna_origen_no_hay_recuento_ni_aviso():
    resultado = calcular_clima(_clima_con_estimados().drop(columns="origen"))
    estado = estado_frio_de_campana(resultado, 2024)
    assert estado.dias_estimados is None and estado.proporcion_estimada is None
    assert "DIAS_ESTIMADOS" not in _codigos(estado)


def test_rf8_con_calcular_clima_el_estado_es_el_mismo_con_y_sin_la_columna_origen():
    con = estado_frio_de_campana(calcular_clima(_clima_con_estimados()), 2024)
    sin = estado_frio_de_campana(calcular_clima(_clima_con_estimados().drop(columns="origen")), 2024)
    assert (con.estado, con.horas, con.cobertura, con.periodo) == (sin.estado, sin.horas, sin.cobertura, sin.periodo)
