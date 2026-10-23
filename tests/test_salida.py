"""Contenido de los archivos de resultados (spec 003, T3.7: RF-15, RF-16, RF-25, RF-27)."""

import json
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.flujo import EstadoDeFrio, ResultadoFlujo
from kiwitracking.huella import huella
from kiwitracking.resultado import Advertencia, Resultado, Resumen
from kiwitracking.salida import advertencias_json, plantas_csv, resumen_json, tabla_de_plantas

GOLDEN = Path(__file__).parent / "golden" / "datos_plantas_completos.csv"
ORDEN_CONOCIDO = ["id", "KVPI_mean", "KVPI_corregido", "KVPI_std", "estabilidad", "ambiente", "recomendacion", "bajo_malla"]


@pytest.fixture(scope="module")
def lote():
    return pd.read_csv(GOLDEN, encoding="utf-8")


def _analizar(tabla):
    return analizar(tabla, huella_confirmada=huella(tabla), estado_frio_ultima_campana="Adecuado")


def _flujo(resultado, estado=None, parametros=None, advertencias=None):
    return ResultadoFlujo(
        resultado=resultado,
        estado_frio=estado or EstadoDeFrio("ninguno"),
        advertencias=advertencias or [],
        parametros=parametros or {"correccion": "auto", "p_ambiente": (33, 66)},
    )


def _resumen(**cambios):
    base = dict(fc=1.2, p_valor=0.01, n_bajo_malla=3, n_fuera_malla=5, correccion_aplicada=True, p33=0.5, p66=0.6,
                p75_estabilidad=14.9, huella="abc123abc123", escalar_std=True, prueba_t="welch")
    return Resumen(**{**base, **cambios})


def _resultado_de(resumen):
    return Resultado(tabla=pd.DataFrame({"id": [1]}), resumen=resumen, advertencias=[])


def _cargar(texto):
    def rechazar(constante):
        raise AssertionError(f"el JSON trae {constante}, que no es JSON válido")

    return json.loads(texto, parse_constant=rechazar)


# --- RF-27: columnas y filas de plantas.csv -----------------------------------------------------------


def test_rf27_las_columnas_conocidas_van_en_el_orden_fijo_y_las_demas_despues_en_su_orden(lote):
    entrada = lote[["elev_m", "id", "slope_pct", "KVPI_std", "KVPI_mean", "bajo_malla", "X", "Y"]]

    tabla = tabla_de_plantas(_analizar(entrada).tabla)

    assert list(tabla.columns) == ORDEN_CONOCIDO + ["elev_m", "slope_pct", "X", "Y"]


def test_rf27_el_archivo_sale_igual_aunque_cambie_el_orden_de_las_columnas_conocidas_de_la_entrada(lote):
    una = lote[["id", "KVPI_mean", "KVPI_std", "bajo_malla", "X", "Y"]]
    otra = lote[["bajo_malla", "KVPI_std", "id", "X", "Y", "KVPI_mean"]]

    assert plantas_csv(_analizar(una).tabla) == plantas_csv(_analizar(otra).tabla)


def test_rf27_las_filas_salen_en_el_orden_de_entrada(lote):
    entrada = lote[["id", "KVPI_mean", "KVPI_std", "bajo_malla"]].iloc[::-1].reset_index(drop=True)

    tabla = tabla_de_plantas(_analizar(entrada).tabla)

    assert tabla["id"].tolist() == entrada["id"].tolist()


def test_rf27_las_columnas_de_resultado_que_ya_venian_se_reemplazan_y_no_se_duplican(lote):
    viejo = lote.assign(KVPI_corregido=-1.0, recomendacion="viejo")  # trae valores de resultado de otra corrida

    tabla = tabla_de_plantas(_analizar(viejo).tabla)

    assert list(tabla.columns).count("KVPI_corregido") == 1 and list(tabla.columns).count("recomendacion") == 1
    assert (tabla["KVPI_corregido"] != -1.0).all() and (tabla["recomendacion"] != "viejo").all()


def test_rf27_bajo_malla_lleva_el_valor_usado_en_el_analisis_como_entero(lote):
    tabla = tabla_de_plantas(_analizar(lote).tabla)

    assert tabla["bajo_malla"].tolist() == lote["bajo_malla"].tolist() and tabla["bajo_malla"].dtype.kind == "i"


# --- RF-16: formato de plantas.csv ----------------------------------------------------------------------


def test_rf16_el_csv_usa_salto_de_linea_lf_no_trae_bom_y_termina_en_salto_de_linea(lote):
    texto = plantas_csv(_analizar(lote).tabla)

    assert "\r" not in texto and not texto.startswith("﻿") and texto.endswith("\n")


def test_rf16_los_numeros_se_escriben_completos_sin_redondear(lote):
    tabla = tabla_de_plantas(_analizar(lote).tabla)

    leido = pd.read_csv(StringIO(plantas_csv(_analizar(lote).tabla)), float_precision="round_trip")

    pd.testing.assert_frame_equal(leido[["KVPI_mean", "KVPI_corregido", "KVPI_std"]], tabla[["KVPI_mean", "KVPI_corregido", "KVPI_std"]], check_exact=True)


def test_rf16_un_valor_vacio_se_escribe_como_celda_vacia_y_no_como_nan():
    tabla = pd.DataFrame({"id": [1, 2], "KVPI_mean": [0.5, 0.6], "KVPI_std": [0.0, 0.1], "bajo_malla": [0, 1]})
    resultado = analizar(tabla, huella_confirmada=huella(tabla), estado_frio_ultima_campana="Adecuado")  # std = 0: estabilidad vacía

    texto = plantas_csv(resultado.tabla)

    assert "nan" not in texto.lower()
    fila = texto.splitlines()[1].split(",")
    assert fila[ORDEN_CONOCIDO.index("estabilidad")] == ""


def test_rf16_las_tildes_y_los_encabezados_salen_en_utf8_legible(lote):
    texto = plantas_csv(_analizar(lote).tabla)

    assert texto.splitlines()[0].startswith("id,KVPI_mean,KVPI_corregido,KVPI_std,estabilidad,ambiente,recomendacion,bajo_malla")
    assert "Alto Potencial" in texto or "Limitante" in texto


# --- RF-25: resumen.json ----------------------------------------------------------------------------------


def test_rf25_la_estructura_y_el_orden_de_las_claves_son_los_de_la_spec():
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()))))

    assert list(documento) == ["huella", "resumen", "parametros", "estado_frio"]
    assert list(documento["resumen"]) == [
        "fc", "p_valor", "n_bajo_malla", "n_fuera_malla", "correccion_aplicada", "p33", "p66", "p75_estabilidad",
        "escalar_std", "prueba_t",
    ]
    assert documento["huella"] == "abc123abc123"


def test_rf25_se_lee_con_un_lector_estricto_y_devuelve_los_mismos_valores(lote):
    resultado = _analizar(lote)

    documento = _cargar(resumen_json(_flujo(resultado)))

    r = resultado.resumen
    assert (documento["resumen"]["fc"], documento["resumen"]["p_valor"]) == (r.fc, r.p_valor)
    assert documento["resumen"]["p75_estabilidad"] == r.p75_estabilidad
    assert documento["resumen"]["n_bajo_malla"] == r.n_bajo_malla == 53 and documento["resumen"]["n_fuera_malla"] == 106
    assert documento["resumen"]["correccion_aplicada"] is True and documento["resumen"]["prueba_t"] == "welch"


def test_rf25_los_decimales_conservan_todas_sus_cifras():
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen(p_valor=5.863362026237887e-35)))))

    assert documento["resumen"]["p_valor"] == 5.863362026237887e-35


@pytest.mark.parametrize("vacio", [None, float("nan"), float("inf"), float("-inf")])
def test_rf25_los_valores_vacios_nan_e_infinitos_se_escriben_como_null(vacio):
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen(fc=vacio, p_valor=vacio)))))

    assert documento["resumen"]["fc"] is None and documento["resumen"]["p_valor"] is None


def test_rf25_los_numeros_de_numpy_se_escriben_como_numeros_comunes():
    resumen = _resumen(fc=np.float64(1.25), n_bajo_malla=np.int64(7), correccion_aplicada=np.bool_(True), p33=np.float32(0.5))

    documento = _cargar(resumen_json(_flujo(_resultado_de(resumen))))

    assert documento["resumen"]["fc"] == 1.25 and type(documento["resumen"]["fc"]) is float
    assert documento["resumen"]["n_bajo_malla"] == 7 and type(documento["resumen"]["n_bajo_malla"]) is int
    assert documento["resumen"]["correccion_aplicada"] is True
    assert documento["resumen"]["p33"] == 0.5


def test_rf25_p_ambiente_sale_como_una_lista_de_dos_numeros():
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()), parametros={"p_ambiente": (30.0, 60.0), "alfa": 0.05})))

    assert documento["parametros"] == {"p_ambiente": [30.0, 60.0], "alfa": 0.05}


def test_rf25_con_clima_los_parametros_traen_la_seccion_clima():
    clima = {"ventana_frio": "invierno", "formato_fecha": None, "cobertura_minima": 0.9, "max_hueco_dias": 7, "campana": 2024}

    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()), parametros={"alfa": 0.05, "clima": clima})))

    assert documento["parametros"]["clima"] == clima


def test_rf25_el_estado_de_frio_del_clima_trae_periodo_horas_cobertura_y_hueco():
    estado = EstadoDeFrio("clima", "Óptimo", 2024, 1128.8, 1.0, 0)

    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()), estado=estado)))

    assert documento["estado_frio"] == {
        "origen": "clima", "estado": "Óptimo", "periodo": 2024, "horas": 1128.8, "cobertura": 1.0, "hueco_maximo": 0,
    }
    assert list(documento["estado_frio"]) == ["origen", "estado", "periodo", "horas", "cobertura", "hueco_maximo"]


def test_rf25_un_estado_manual_trae_solo_origen_y_estado():
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()), estado=EstadoDeFrio("manual", "Adecuado"))))

    assert documento["estado_frio"] == {"origen": "manual", "estado": "Adecuado"}


def test_rf25_sin_estado_de_frio_el_origen_es_ninguno_y_el_estado_es_null():
    documento = _cargar(resumen_json(_flujo(_resultado_de(_resumen()), estado=EstadoDeFrio("ninguno"))))

    assert documento["estado_frio"] == {"origen": "ninguno", "estado": None}


def test_rf25_el_formato_es_utf8_legible_con_sangria_de_2_espacios_lf_y_linea_final():
    texto = resumen_json(_flujo(_resultado_de(_resumen()), estado=EstadoDeFrio("manual", "Óptimo")))

    assert "Óptimo" in texto and "\\u" not in texto  # las tildes salen tal cual, no escapadas
    assert texto.splitlines()[1].startswith('  "') and not texto.splitlines()[1].startswith('   ')
    assert "\r" not in texto and texto.endswith("\n") and not texto.endswith("\n\n")


# --- RF-15: advertencias.json -----------------------------------------------------------------------------


def test_rf15_las_advertencias_son_una_lista_de_objetos_con_codigo_y_mensaje_en_orden():
    avisos = [Advertencia("A_PRIMERO", "Mensaje con tilde: Óptimo"), Advertencia("B_SEGUNDO", "Otro")]

    documento = _cargar(advertencias_json(avisos))

    assert documento == [{"codigo": "A_PRIMERO", "mensaje": "Mensaje con tilde: Óptimo"}, {"codigo": "B_SEGUNDO", "mensaje": "Otro"}]
    assert all(list(aviso) == ["codigo", "mensaje"] for aviso in documento)  # el orden de las claves también cuenta


def test_rf15_sin_advertencias_el_archivo_es_una_lista_vacia():
    assert advertencias_json([]) == "[]\n"


def test_rf15_las_advertencias_tienen_el_mismo_formato_que_el_resumen():
    texto = advertencias_json([Advertencia("X", "Óptimo")])

    assert "Óptimo" in texto and "\r" not in texto and texto.endswith("\n")
    assert texto.splitlines()[1].startswith('  {')
