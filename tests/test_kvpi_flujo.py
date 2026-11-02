"""T4.6: flujo del comando `kvpi` sin consola (RF-15 y RF-19 de la spec 004)."""

import pandas as pd
import pytest

from kiwitracking.flujo import ejecutar_kvpi
from kiwitracking.kvpi import agregar_kvpi, unir_con_muestreo
from kiwitracking.resultado import ErrorDeEntrada

SERIE = (
    "system:index,KVPI,campaña,col,id,row,.geo\n"
    '0_0_0,0.2,2019_2020,0,4,3,"{""type"":""Point""}"\n'
    '0_1_0,0.4,2020_2021,0,4,3,"{""type"":""Point""}"\n'
    '0_2_0,0.6,2019_2020,1,26,2,"{""type"":""Point""}"\n'
    '0_3_0,0.8,2020_2021,1,26,2,"{""type"":""Point""}"\n'
)
MUESTREO = "id,X,Y,row_index\n26,10.5,-20.5,2\n4,11.5,-21.5,3\n"


def _escribir(carpeta, nombre, texto, bom=False):
    ruta = carpeta / nombre
    ruta.write_bytes(texto.encode("utf-8-sig" if bom else "utf-8"))
    return ruta


@pytest.fixture
def archivos(tmp_path):
    return _escribir(tmp_path, "serie.csv", SERIE), _escribir(tmp_path, "muestreo.csv", MUESTREO)


def test_rf15_lee_los_dos_archivos_y_devuelve_la_tabla_en_el_orden_del_muestreo(archivos):
    resultado = ejecutar_kvpi(*archivos)
    assert list(resultado.tabla.columns) == ["id", "KVPI_mean", "KVPI_std", "KVPI_cv", "n_campanas", "X", "Y", "row_index"]
    assert list(resultado.tabla["id"]) == ["26", "4"]
    assert resultado.tabla["KVPI_mean"].tolist() == pytest.approx([0.7, 0.3])
    assert resultado.tabla["n_campanas"].tolist() == [2, 2]
    assert resultado.advertencias == []


def test_rf15_ignora_las_columnas_extra_de_la_exportacion(archivos):
    resultado = ejecutar_kvpi(*archivos)
    assert ".geo" not in resultado.tabla.columns and "system:index" not in resultado.tabla.columns


def test_rf15_tolera_el_bom_de_excel_en_los_dos_archivos(tmp_path):
    serie = _escribir(tmp_path, "serie.csv", SERIE, bom=True)
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO, bom=True)
    resultado = ejecutar_kvpi(serie, muestreo)
    assert list(resultado.tabla["id"]) == ["26", "4"]


def test_rf15_el_resultado_es_el_del_nucleo(archivos):
    serie, muestreo = pd.read_csv(archivos[0]), pd.read_csv(archivos[1])
    por_planta = agregar_kvpi(serie, total_plantas=2).tabla
    esperada, _ = unir_con_muestreo(por_planta, muestreo)
    pd.testing.assert_frame_equal(ejecutar_kvpi(*archivos).tabla, esperada)


@pytest.mark.parametrize("cual", ["serie", "muestreo"])
def test_rf15_archivo_inexistente_da_error_que_lo_nombra(tmp_path, cual):
    serie = _escribir(tmp_path, "serie.csv", SERIE)
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO)
    faltante = tmp_path / f"{cual}_que_no_esta.csv"
    argumentos = {"serie": (faltante, muestreo), "muestreo": (serie, faltante)}[cual]
    with pytest.raises(ErrorDeEntrada, match=faltante.name):
        ejecutar_kvpi(*argumentos)


def test_rf15_una_carpeta_en_lugar_de_un_archivo_da_error(tmp_path):
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO)
    with pytest.raises(ErrorDeEntrada, match="no es un archivo"):
        ejecutar_kvpi(tmp_path, muestreo)


@pytest.mark.parametrize("contenido", ["", "\n"])
def test_rf15_archivo_sin_contenido_da_error_que_lo_nombra(tmp_path, contenido):
    serie = _escribir(tmp_path, "serie_vacia.csv", contenido)
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO)
    with pytest.raises(ErrorDeEntrada, match="serie_vacia.csv"):
        ejecutar_kvpi(serie, muestreo)


def test_rf15_los_parametros_se_validan_antes_de_leer_los_archivos(tmp_path):
    inexistente = tmp_path / "no_esta.csv"
    with pytest.raises(ErrorDeEntrada, match="min_campanas"):
        ejecutar_kvpi(inexistente, inexistente, min_campanas=1)


def test_rf15_los_parametros_llegan_al_nucleo(archivos):
    resultado = ejecutar_kvpi(*archivos, min_campanas=3)
    assert resultado.tabla["KVPI_std"].isna().all()
    assert "SIN_DESVIO" in [a.codigo for a in resultado.advertencias]


def test_rf15_las_campanas_esperadas_llegan_al_nucleo(archivos):
    with pytest.raises(ErrorDeEntrada, match="2021_2022"):
        ejecutar_kvpi(*archivos, campanas=["2019_2020", "2020_2021", "2021_2022"])


def test_rf15_la_cobertura_se_mide_contra_las_plantas_del_muestreo(tmp_path):
    muestreo = "id,X,Y\n4,1.0,1.0\n26,2.0,2.0\n91,3.0,3.0\n92,4.0,4.0\n"
    resultado = ejecutar_kvpi(
        _escribir(tmp_path, "serie.csv", SERIE), _escribir(tmp_path, "muestreo.csv", muestreo)
    )
    assert [c.proporcion for c in resultado.cobertura] == [0.5, 0.5]
    assert resultado.n_plantas_muestreo == 4


def test_rf15_con_plantas_de_la_serie_fuera_del_muestreo_la_cobertura_puede_pasar_de_100(tmp_path):
    muestreo = "id,X,Y\n4,1.0,1.0\n"
    resultado = ejecutar_kvpi(
        _escribir(tmp_path, "serie.csv", SERIE), _escribir(tmp_path, "muestreo.csv", muestreo)
    )
    assert [c.proporcion for c in resultado.cobertura] == [2.0, 2.0]
    assert "PLANTAS_SIN_COORDENADAS" in [a.codigo for a in resultado.advertencias]


def test_rf15_las_advertencias_salen_en_orden_validacion_calculo_cobertura_union(tmp_path):
    serie = (
        "id,campaña,KVPI\n"
        "4,a,0.2\n4,a,0.2\n4,b,0.4\n"  # repetida igual
        "26,a,0.6\n"  # una sola campaña
        "77,a,0.1\n77,b,0.2\n"  # sin coordenadas
    )
    muestreo = "id,X,Y\n4,1.0,1.0\n26,2.0,2.0\n91,3.0,3.0\n91,3.0,3.0\n"  # 91 sin serie; repetida igual
    resultado = ejecutar_kvpi(
        _escribir(tmp_path, "serie.csv", serie),
        _escribir(tmp_path, "muestreo.csv", muestreo),
        cobertura_minima_campana=1,
    )
    assert [a.codigo for a in resultado.advertencias] == [
        "KVPI_DUPLICADO",
        "PLANTAS_CON_MENOS_CAMPANAS",
        "SIN_DESVIO",
        "CAMPANA_CON_POCOS_DATOS",
        "MUESTREO_DUPLICADO",
        "PLANTAS_SIN_COORDENADAS",
        "PLANTAS_SIN_SERIE",
    ]


def test_rf19_no_modifica_los_archivos_de_entrada(archivos, tmp_path):
    antes = [ruta.read_bytes() for ruta in archivos]
    ejecutar_kvpi(*archivos)
    assert [ruta.read_bytes() for ruta in archivos] == antes
    assert sorted(p.name for p in tmp_path.iterdir()) == ["muestreo.csv", "serie.csv"]


def test_rf19_un_error_no_deja_archivos_nuevos(tmp_path):
    serie = _escribir(tmp_path, "serie.csv", "id,campaña,KVPI\n1,a,n/d\n")
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO)
    with pytest.raises(ErrorDeEntrada):
        ejecutar_kvpi(serie, muestreo)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["muestreo.csv", "serie.csv"]


def test_rf15_un_archivo_que_no_esta_en_utf8_da_error_que_lo_nombra(tmp_path):
    serie = tmp_path / "serie_latin.csv"
    serie.write_bytes("id,campaña,KVPI\n1,a,0.1\n".encode("cp1252"))
    muestreo = _escribir(tmp_path, "muestreo.csv", MUESTREO)
    with pytest.raises(ErrorDeEntrada, match="serie_latin.csv"):
        ejecutar_kvpi(serie, muestreo)
