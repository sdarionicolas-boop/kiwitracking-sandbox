"""T5.4: los días estimados en el estado de frío del flujo y en `resumen.json` (RF-11 de la spec 005)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.analisis import analizar
from kiwitracking.flujo import (
    EstadoDeFrio,
    ResultadoFlujo,
    SolicitudAnalisis,
    _parametros_usados,
    elegir_estado_de_frio,
)
from kiwitracking.huella import huella
from kiwitracking.resultado import Advertencia, Resultado, Resumen
from kiwitracking.salida import advertencias_json, resumen_json

GOLDEN = Path(__file__).parent / "golden" / "datos_plantas_completos.csv"


def _clima_csv(carpeta, anios_con_estimados, con_origen=True, nombre="clima.csv"):
    """Un clima de inviernos completos; `anios_con_estimados`: {año: días interpolados}."""
    trozos = []
    for anio, estimados in anios_con_estimados.items():
        fechas = pd.date_range(f"{anio}-05-01", f"{anio}-08-31", freq="D").strftime("%Y-%m-%d")
        trozo = pd.DataFrame({"date": fechas, "Tmax": 12.0, "Tmin": 2.0, "origen": "INTA_verificado"})
        trozo.loc[: estimados - 1, "origen"] = "interpolado"
        trozos.append(trozo)
    tabla = pd.concat(trozos, ignore_index=True)
    ruta = carpeta / nombre
    (tabla if con_origen else tabla.drop(columns="origen")).to_csv(ruta, index=False)
    return ruta


def _resumen_del_flujo(estado, parametros=None, advertencias=None):
    tabla = pd.read_csv(GOLDEN)
    resultado = analizar(tabla, huella_confirmada=huella(tabla), estado_frio_ultima_campana="Adecuado")
    flujo = ResultadoFlujo(resultado, estado, advertencias or [], parametros or {"correccion": "auto"})
    return json.loads(resumen_json(flujo))


# --- EstadoDeFrio y elegir_estado_de_frio ---------------------------------------------------------------------


def test_rf11_el_estado_del_clima_trae_los_dias_estimados_y_su_proporcion(tmp_path):
    clima = _clima_csv(tmp_path, {2023: 4, 2024: 26})
    estado = elegir_estado_de_frio(clima, None, 2024, {})
    assert (estado.origen, estado.periodo) == ("clima", 2024)
    assert estado.dias_estimados == 26
    assert estado.proporcion_estimada == pytest.approx(26 / 123)


def test_rf11_el_aviso_de_dias_estimados_va_al_final_de_las_advertencias_del_estado(tmp_path):
    clima = _clima_csv(tmp_path, {2023: 4, 2024: 26})
    estado = elegir_estado_de_frio(clima, None, None, {})
    codigos = [a.codigo for a in estado.advertencias]
    assert codigos[-2:] == ["CAMPANA_NO_INDICADA", "DIAS_ESTIMADOS"]  # antes van los avisos del clima
    assert "26 de 123" in estado.advertencias[-1].mensaje


def test_rf11_sin_la_columna_origen_los_dos_valores_quedan_vacios_y_no_hay_aviso(tmp_path):
    clima = _clima_csv(tmp_path, {2024: 26}, con_origen=False)
    estado = elegir_estado_de_frio(clima, None, 2024, {})
    assert estado.origen == "clima"
    assert estado.dias_estimados is None and estado.proporcion_estimada is None
    assert "DIAS_ESTIMADOS" not in [a.codigo for a in estado.advertencias]


def test_rf11_con_estado_manual_o_sin_estado_no_hay_recuento():
    for estado in (elegir_estado_de_frio(None, "Adecuado", None, {}), elegir_estado_de_frio(None, None, None, {})):
        assert estado.dias_estimados is None and estado.proporcion_estimada is None


def test_rf11_la_lista_de_etiquetas_llega_al_recuento(tmp_path):
    clima = _clima_csv(tmp_path, {2024: 26})
    assert elegir_estado_de_frio(clima, None, 2024, {"origenes_estimados": ["satelital"]}).dias_estimados == 0
    assert elegir_estado_de_frio(clima, None, 2024, {"origenes_estimados": [" Interpolado "]}).dias_estimados == 26


def test_rf11_sin_ventana_clasificable_el_origen_es_ninguno_y_no_hay_recuento(tmp_path):
    fechas = pd.date_range("2024-05-01", "2024-05-20", freq="D").strftime("%Y-%m-%d")
    ruta = tmp_path / "corto.csv"
    pd.DataFrame({"date": fechas, "Tmax": 12.0, "Tmin": 2.0, "origen": "interpolado"}).to_csv(ruta, index=False)
    estado = elegir_estado_de_frio(ruta, None, None, {})
    assert estado.origen == "ninguno" and estado.dias_estimados is None and estado.proporcion_estimada is None
    assert "DIAS_ESTIMADOS" not in [a.codigo for a in estado.advertencias]


def test_rf11_los_campos_nuevos_de_estado_de_frio_van_al_final_y_con_valor_por_defecto():
    estado = EstadoDeFrio("clima", "Óptimo", 2024, 1128.8, 1.0, 0)  # construcción posicional de siempre
    assert estado.dias_estimados is None and estado.proporcion_estimada is None


# --- resumen.json: estado_frio ----------------------------------------------------------------------------------


def test_rf11_resumen_con_clima_trae_las_dos_claves_a_continuacion_de_hueco_maximo():
    estado = EstadoDeFrio("clima", "Óptimo", 2024, 1128.8, 1.0, 0, dias_estimados=26, proporcion_estimada=26 / 123)
    documento = _resumen_del_flujo(estado)["estado_frio"]
    assert list(documento) == [
        "origen", "estado", "periodo", "horas", "cobertura", "hueco_maximo", "dias_estimados", "proporcion_estimada",
    ]  # fmt: skip
    assert documento["dias_estimados"] == 26
    assert documento["proporcion_estimada"] == pytest.approx(26 / 123)


def test_rf11_resumen_con_clima_sin_origen_escribe_null_en_las_dos_claves():
    documento = _resumen_del_flujo(EstadoDeFrio("clima", "Óptimo", 2024, 1128.8, 1.0, 0))["estado_frio"]
    assert documento["dias_estimados"] is None and documento["proporcion_estimada"] is None
    assert "dias_estimados" in documento and "proporcion_estimada" in documento


def test_rf11_resumen_con_cero_dias_estimados_escribe_cero():
    estado = EstadoDeFrio("clima", "Óptimo", 2024, 1128.8, 1.0, 0, dias_estimados=0, proporcion_estimada=0.0)
    documento = _resumen_del_flujo(estado)["estado_frio"]
    assert documento["dias_estimados"] == 0 and documento["proporcion_estimada"] == 0.0


@pytest.mark.parametrize("estado", [EstadoDeFrio("manual", "Adecuado"), EstadoDeFrio("ninguno")])
def test_rf11_resumen_con_estado_manual_o_sin_estado_no_agrega_las_claves(estado):
    documento = _resumen_del_flujo(estado)["estado_frio"]
    assert "dias_estimados" not in documento and "proporcion_estimada" not in documento


# --- resumen.json: parametros.clima ----------------------------------------------------------------------------


def _solicitud(**clima):
    return SolicitudAnalisis("abc123abc123", "clima.csv", None, 2024, {}, clima)


def test_rf11_parametros_clima_registra_origenes_estimados_aunque_sea_el_valor_por_defecto():
    parametros = _parametros_usados(_solicitud())["clima"]
    assert parametros["origenes_estimados"] == ["interpolado"]
    assert list(parametros) == [
        "ventana_frio", "formato_fecha", "cobertura_minima", "max_hueco_dias", "campana", "origenes_estimados",
    ]  # fmt: skip


def test_rf11_parametros_clima_registra_la_lista_indicada():
    parametros = _parametros_usados(_solicitud(origenes_estimados=["interpolado", "estimado"]))["clima"]
    assert parametros["origenes_estimados"] == ["interpolado", "estimado"]


def test_rf11_parametros_clima_es_una_lista_json_y_llega_al_resumen():
    parametros = {"correccion": "auto", "clima": _parametros_usados(_solicitud())["clima"]}
    documento = _resumen_del_flujo(EstadoDeFrio("ninguno"), parametros)["parametros"]["clima"]
    assert documento["origenes_estimados"] == ["interpolado"]


def test_rf11_sin_clima_parametros_no_trae_la_seccion_clima():
    solicitud = SolicitudAnalisis("abc123abc123", None, "Adecuado", None, {}, {})
    assert "clima" not in _parametros_usados(solicitud)


# --- advertencias.json ------------------------------------------------------------------------------------------


def test_rf11_la_advertencia_de_dias_estimados_llega_a_advertencias_json_en_su_lugar(tmp_path):
    clima = _clima_csv(tmp_path, {2024: 26})
    estado = elegir_estado_de_frio(clima, None, None, {})
    texto = advertencias_json([Advertencia("PRIMERA", "a"), *estado.advertencias, Advertencia("ULTIMA", "z")])
    codigos = [a["codigo"] for a in json.loads(texto)]
    assert codigos[0] == "PRIMERA"
    assert codigos[-3:] == ["CAMPANA_NO_INDICADA", "DIAS_ESTIMADOS", "ULTIMA"]
