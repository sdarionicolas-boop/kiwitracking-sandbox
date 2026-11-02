"""La serie real de KVPI contra lo publicado, y el flujo completo `kvpi` → `mapa` → `analizar` (spec 004, criterios 3 y 4).

La serie (`kvpi_serie.csv`) se exportó de Google Earth Engine el 24/10/2026; el muestreo (`id`, `X`, `Y`) sale de
`datos_plantas_completos.csv`, que tiene las mismas coordenadas que `muestreo_sistematico.csv`. Si una exportación
futura no reproduce lo publicado con esta tolerancia, el test falla y se investiga (criterio 3): no se ajusta.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.cli import main
from kiwitracking.flujo import ejecutar_kvpi
from kiwitracking.huella import huella
from kiwitracking.kvpi import agregar_kvpi

GOLDEN = Path(__file__).parent / "golden"
SERIE = GOLDEN / "kvpi_serie.csv"
PUBLICADO = GOLDEN / "datos_plantas_completos.csv"
MALLA = GOLDEN / "malla_zona.geojson"
CLIMA = GOLDEN / "clima_diario.csv"
TOLERANCIA = 1e-12
CAMPANAS = ["2019_2020", "2020_2021", "2021_2022", "2022_2023", "2023_2024", "2024_2025"]


@pytest.fixture(scope="module")
def publicado():
    return pd.read_csv(PUBLICADO, encoding="utf-8")


@pytest.fixture
def muestreo(tmp_path, publicado):
    ruta = tmp_path / "muestreo.csv"
    publicado[["id", "X", "Y"]].to_csv(ruta, index=False)
    return ruta


def _kvpi(muestreo, destino, capsys):
    codigo = main(["kvpi", "--serie", str(SERIE), "--muestreo", str(muestreo), "--salida", str(destino)])
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    return salida


# --- Criterio 3: la serie real reproduce lo publicado ---------------------------------------------------------


def test_criterio3_el_nucleo_reproduce_kvpi_mean_y_kvpi_std_publicados_de_las_159_plantas(publicado):
    obtenido = agregar_kvpi(pd.read_csv(SERIE, encoding="utf-8")).tabla.set_index("id")
    esperado = publicado.assign(id=publicado["id"].astype(str)).set_index("id")

    assert len(obtenido) == 159 and set(obtenido.index) == set(esperado.index)
    assert (obtenido["KVPI_mean"] - esperado["KVPI_mean"]).abs().max() < TOLERANCIA
    assert (obtenido["KVPI_std"] - esperado["KVPI_std"]).abs().max() < TOLERANCIA


def test_criterio3_las_159_plantas_tienen_las_6_campanas_y_no_hay_advertencias():
    resultado = agregar_kvpi(pd.read_csv(SERIE, encoding="utf-8"))

    assert (resultado.tabla["n_campanas"] == 6).all()
    assert resultado.advertencias == []


def test_criterio3_la_cobertura_de_las_6_campanas_es_completa():
    resultado = agregar_kvpi(pd.read_csv(SERIE, encoding="utf-8"))

    assert [c.campana for c in resultado.cobertura] == CAMPANAS
    assert all(c.plantas_con_dato == 159 and c.proporcion == 1.0 for c in resultado.cobertura)


def test_criterio3_con_las_campanas_esperadas_correctas_no_da_error():
    agregar_kvpi(pd.read_csv(SERIE, encoding="utf-8"), campanas=CAMPANAS)


def test_criterio3_el_flujo_conserva_el_orden_y_las_coordenadas_del_muestreo(muestreo, publicado):
    resultado = ejecutar_kvpi(SERIE, muestreo)

    assert resultado.advertencias == []
    assert resultado.tabla["id"].tolist() == publicado["id"].astype(str).tolist()
    assert resultado.tabla["X"].tolist() == publicado["X"].tolist()
    assert resultado.tabla["Y"].tolist() == publicado["Y"].tolist()


def test_criterio3_el_comando_kvpi_escribe_un_csv_que_reproduce_lo_publicado(tmp_path, capsys, muestreo, publicado):
    salida = _kvpi(muestreo, tmp_path / "plantas_kvpi.csv", capsys)

    escrito = pd.read_csv(tmp_path / "plantas_kvpi.csv", encoding="utf-8", float_precision="round_trip")
    assert escrito["id"].tolist() == publicado["id"].tolist()
    assert (escrito["KVPI_mean"] - publicado["KVPI_mean"]).abs().max() < TOLERANCIA
    assert (escrito["KVPI_std"] - publicado["KVPI_std"]).abs().max() < TOLERANCIA
    assert (escrito["n_campanas"] == 6).all()
    assert "Plantas en el resultado: 159" in salida and "6 campañas: 159 plantas" in salida
    assert all(f"{c}: 159 plantas con dato (100,0 %)" in salida for c in CAMPANAS)
    assert "Advertencia" not in salida


# --- Criterio 4: el flujo completo ------------------------------------------------------------------------------


def _mapa_y_huella(carpeta, plantas, capsys):
    codigo = main(
        ["mapa", "--plantas", str(plantas), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326",
         "--salida", str(carpeta / "mapa.html"), "--sin-fondo-satelital"]
    )  # fmt: skip
    salida = capsys.readouterr().out
    assert codigo == 0, salida
    return re.search(r"^Huella: ([0-9a-f]{12})$", salida, re.M).group(1)


def _analizar(carpeta, plantas, huella_del_mapa, capsys, *extra):
    codigo = main(
        ["analizar", "--plantas", str(plantas), "--malla", str(MALLA), "--crs-plantas", "EPSG:4326",
         "--huella", huella_del_mapa, "--salida", str(carpeta / "resultados"), *extra]
    )  # fmt: skip
    capsys.readouterr()
    assert codigo == 0
    return pd.read_csv(carpeta / "resultados" / "plantas.csv", encoding="utf-8")


def test_criterio4_kvpi_mapa_y_analizar_dan_16_mantener_y_19_intervenir_con_el_frio_de_2024(tmp_path, capsys, muestreo, publicado):
    plantas = tmp_path / "plantas_kvpi.csv"
    _kvpi(muestreo, plantas, capsys)

    huella_del_mapa = _mapa_y_huella(tmp_path, plantas, capsys)
    assert huella_del_mapa == huella(publicado)  # mismas plantas bajo malla que el lote publicado

    resultado = _analizar(tmp_path, plantas, huella_del_mapa, capsys, "--clima", str(CLIMA), "--campana", "2024")
    cuentas = resultado["recomendacion"].value_counts().to_dict()
    assert (cuentas["Mantener"], cuentas["Intervenir"]) == (16, 19)
    resumen = json.loads((tmp_path / "resultados" / "resumen.json").read_text(encoding="utf-8"))
    assert resumen["estado_frio"]["estado"] == "Óptimo" and resumen["estado_frio"]["periodo"] == 2024


def test_criterio4_el_resultado_es_el_mismo_que_con_el_csv_publicado(tmp_path, capsys, muestreo, publicado):
    plantas = tmp_path / "plantas_kvpi.csv"
    _kvpi(muestreo, plantas, capsys)
    huella_del_mapa = _mapa_y_huella(tmp_path, plantas, capsys)
    desde_kvpi = _analizar(tmp_path, plantas, huella_del_mapa, capsys, "--no-escalar-std", "--estado-frio", "Deficiente")

    (tmp_path / "publicado").mkdir()
    desde_publicado = _analizar(tmp_path / "publicado", PUBLICADO, huella_del_mapa, capsys, "--no-escalar-std", "--estado-frio", "Deficiente")

    for columna in ("KVPI_corregido", "estabilidad"):
        assert (desde_kvpi[columna] - desde_publicado[columna]).abs().max() < 1e-9
    assert desde_kvpi["id"].tolist() == desde_publicado["id"].tolist()
    assert desde_kvpi["ambiente"].tolist() == desde_publicado["ambiente"].tolist()
    assert desde_kvpi["recomendacion"].tolist() == desde_publicado["recomendacion"].tolist()
    assert desde_kvpi["recomendacion"].tolist() == publicado["recomendacion"].tolist()
