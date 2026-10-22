"""Integración de la spec 002 con la spec 001: el estado de frío calculado alimenta `analizar()`."""

import unicodedata
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.campana import estado_frio_de_campana
from kiwitracking.clima import COLUMNAS_FRIO, ResultadoClima, calcular_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.huella import huella
from kiwitracking.validacion import ESTADOS_FRIO, validar_parametros

GOLDEN = Path(__file__).parent / "golden" / "datos_plantas_completos.csv"


def _lote_de_12_plantas():
    """8 plantas fuera de malla y 4 bajo malla: hay plantas "Mantener" cuando no se ajusta por frío."""
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


def _clima_con_un_estado(estado):
    """ResultadoClima armado a mano con un único invierno clasificable."""
    horas = {"Óptimo": 1100.0, "Adecuado": 850.0, "Deficiente": 600.0}[estado]
    frio = pd.DataFrame(
        [{"periodo": 2024, "Horas_Frio": horas, "estado_frio": estado, "dias_disponibles": 123, "dias_esperados": 123,
          "cobertura": 1.0, "hueco_maximo": 0, "completo": True}],
        columns=COLUMNAS_FRIO,
    )
    return ResultadoClima(gdd=pd.DataFrame(), frio=frio, advertencias=[], ventana_frio="invierno")


def _analizar(estado, lote=None):
    lote = _lote_de_12_plantas() if lote is None else lote
    return analizar(lote, huella_confirmada=huella(lote), estado_frio_ultima_campana=estado)


# --- T2.15: el estado de la spec 002 lo acepta la spec 001 -------------------------------------


@pytest.mark.parametrize("estado", ["Óptimo", "Adecuado", "Deficiente"])
def test_rf22_el_estado_devuelto_lo_acepta_la_validacion_de_la_spec_001_y_analizar_no_da_error(estado):
    elegido = estado_frio_de_campana(_clima_con_un_estado(estado)).estado

    assert elegido == estado and elegido in ESTADOS_FRIO
    validar_parametros(estado_frio_ultima_campana=elegido)  # la misma validación que usa analizar()
    resultado = _analizar(elegido)
    assert "SIN_ESTADO_FRIO" not in [a.codigo for a in resultado.advertencias]


def test_rf22_los_textos_de_los_tres_estados_estan_en_la_misma_normalizacion_que_los_de_la_spec_001():
    # "Óptimo" con la Ó compuesta (NFC): si una spec usara la forma descompuesta, la comparación exacta fallaría.
    for estado in ESTADOS_FRIO:
        assert unicodedata.normalize("NFC", estado) == estado
        assert estado_frio_de_campana(_clima_con_un_estado(estado)).estado == estado


def test_rf22_con_estado_deficiente_ninguna_planta_queda_en_mantener_y_con_los_otros_dos_si():
    sin_mantener = _analizar(estado_frio_de_campana(_clima_con_un_estado("Deficiente")).estado)
    con_adecuado = _analizar(estado_frio_de_campana(_clima_con_un_estado("Adecuado")).estado)
    con_optimo = _analizar(estado_frio_de_campana(_clima_con_un_estado("Óptimo")).estado)

    assert not (sin_mantener.tabla["recomendacion"] == "Mantener").any()
    assert (con_adecuado.tabla["recomendacion"] == "Mantener").any()
    assert (con_optimo.tabla["recomendacion"] == "Mantener").any()


def test_rf24_un_estado_vacio_llega_a_analizar_y_produce_sin_estado_frio_sin_ajustar_nada():
    sin_clasificar = ResultadoClima(
        gdd=pd.DataFrame(), frio=pd.DataFrame(columns=COLUMNAS_FRIO), advertencias=[], ventana_frio="invierno"
    )
    elegido = estado_frio_de_campana(sin_clasificar)

    assert elegido.estado is None
    resultado = _analizar(elegido.estado)
    assert "SIN_ESTADO_FRIO" in [a.codigo for a in resultado.advertencias]
    assert (resultado.tabla["recomendacion"] == "Mantener").any()


# --- T2.15: de las temperaturas diarias a las recomendaciones -------------------------------


def _clima_diario(dias_frios_por_invierno):
    """Inviernos 2022 a 2024 completos; en cada uno, los primeros N días son de 24 h de frío y el resto, templados."""
    filas = []
    for anio, dias_frios in zip((2022, 2023, 2024), dias_frios_por_invierno):
        for i, dia in enumerate(pd.date_range(f"{anio}-05-01", f"{anio}-08-31")):
            frio = i < dias_frios
            filas.append((f"{dia:%Y-%m-%d}", 5.0 if frio else 20.0, -3.0 if frio else 10.0))
    return pd.DataFrame(filas, columns=["date", "Tmax", "Tmin"])


def test_el_flujo_completo_de_un_ultimo_invierno_deficiente_ajusta_las_recomendaciones():
    # 30 días de 24 h = 720 h en el último invierno: "Deficiente". Cobertura completa, por eso se clasifica.
    clima = calcular_clima(_clima_diario([60, 60, 30]), ParametrosClima())

    elegido = estado_frio_de_campana(clima)
    resultado = _analizar(elegido.estado)

    assert (elegido.periodo, elegido.estado) == (2024, "Deficiente")
    assert not (resultado.tabla["recomendacion"] == "Mantener").any()


def test_el_flujo_completo_de_un_ultimo_invierno_optimo_no_ajusta_nada():
    clima = calcular_clima(_clima_diario([60, 60, 60]), ParametrosClima())  # 60 días x 24 h = 1.440 h

    elegido = estado_frio_de_campana(clima, campana=2024)
    resultado = _analizar(elegido.estado)

    assert (elegido.periodo, elegido.estado) == (2024, "Óptimo")
    assert (resultado.tabla["recomendacion"] == "Mantener").any()


def test_elegir_otra_campana_cambia_el_estado_que_recibe_analizar():
    clima = calcular_clima(_clima_diario([60, 60, 30]), ParametrosClima())

    con_2023 = _analizar(estado_frio_de_campana(clima, campana=2023).estado)
    con_2024 = _analizar(estado_frio_de_campana(clima, campana=2024).estado)

    assert (con_2023.tabla["recomendacion"] == "Mantener").any()       # invierno 2023: Óptimo
    assert not (con_2024.tabla["recomendacion"] == "Mantener").any()   # invierno 2024: Deficiente


# --- Criterio 7 de la spec 002 con el lote de referencia (los números de la spec 001) ------------


@pytest.fixture(scope="module")
def lote_de_referencia():
    golden = pd.read_csv(GOLDEN, encoding="utf-8")
    return golden[["id", "KVPI_mean", "KVPI_std", "bajo_malla"]]


@pytest.mark.parametrize("estado,mantener", [("Deficiente", 0), ("Adecuado", 16), ("Óptimo", 16)])
def test_criterio7_con_el_lote_de_referencia_el_estado_de_frio_define_cuantas_plantas_quedan_en_mantener(
    lote_de_referencia, estado, mantener
):
    elegido = estado_frio_de_campana(_clima_con_un_estado(estado)).estado

    resultado = _analizar(elegido, lote_de_referencia)

    conteo = resultado.tabla["recomendacion"].value_counts().to_dict()
    assert conteo.get("Mantener", 0) == mantener
    assert conteo["Intervenir"] == 19
