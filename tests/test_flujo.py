"""Flujo de la línea de comandos sin consola (spec 003): lectura de plantas y malla (T3.2, RF-2 a RF-5)."""

import json
import re

import pandas as pd
import pytest
from pyproj import Transformer
from shapely.geometry import box, mapping

from kiwitracking.flujo import ejecutar_mapa, preparar_plantas
from kiwitracking.huella import huella
from kiwitracking.resultado import ErrorDeEntrada

CSV_PLANTAS = (
    "id,KVPI_mean,KVPI_std,X,Y\n"
    "1,0.60,0.02,-58.00,-38.00\n"   # fuera de la malla
    "2,0.50,0.03,-57.95,-37.95\n"   # dentro
    "3,0.51,0.03,-57.94,-37.94\n"   # dentro
    "4,0.62,0.02,-57.80,-37.80\n"   # fuera
    "5,0.49,0.04,-57.90,-37.90\n"   # en el borde: cuenta como dentro
)
BAJO_MALLA = [0, 1, 1, 0, 1]
POLIGONO = box(-57.96, -37.96, -57.90, -37.90)


def _escribir_csv(ruta, texto=CSV_PLANTAS, codificacion="utf-8"):
    ruta.write_bytes(texto.encode(codificacion))
    return ruta


def _escribir_malla(ruta, poligono=POLIGONO, crs=None):
    contenido = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(poligono)}]}
    if crs:
        contenido["crs"] = {"type": "name", "properties": {"name": crs}}
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


@pytest.fixture
def plantas(tmp_path):
    return _escribir_csv(tmp_path / "plantas.csv")


@pytest.fixture
def malla(tmp_path):
    return _escribir_malla(tmp_path / "malla.geojson")


def _codigos(preparadas):
    return [a.codigo for a in preparadas.advertencias]


# --- RF-2: lectura de las plantas -----------------------------------------------------------------


def test_rf2_lee_el_csv_con_la_lectura_de_la_spec_001_aunque_traiga_el_bom_de_excel(tmp_path):
    ruta = _escribir_csv(tmp_path / "excel.csv", CSV_PLANTAS, "utf-8-sig")

    preparadas = preparar_plantas(ruta, _escribir_malla(tmp_path / "m.geojson"), "EPSG:4326")

    assert list(preparadas.tabla.columns)[:2] == ["id", "KVPI_mean"]  # sin "﻿id"


def test_rf2_un_archivo_de_plantas_que_no_existe_da_un_error_que_nombra_el_archivo(tmp_path):
    with pytest.raises(ErrorDeEntrada) as error:
        preparar_plantas(tmp_path / "no_existe.csv", None, None)

    assert "no_existe.csv" in str(error.value)


def test_rf2_una_malla_que_no_existe_da_un_error_que_nombra_el_archivo(plantas, tmp_path):
    with pytest.raises(ErrorDeEntrada) as error:
        preparar_plantas(plantas, tmp_path / "sin_malla.geojson", "EPSG:4326")

    assert "sin_malla.geojson" in str(error.value)


def test_rf2_un_csv_que_no_esta_en_utf8_da_el_error_de_codificacion_de_la_spec_001(tmp_path):
    ruta = _escribir_csv(tmp_path / "viejo.csv", "id,nota\n1,Óptimo\n", "cp1252")

    with pytest.raises(ErrorDeEntrada) as error:
        preparar_plantas(ruta, None, None)

    assert "UTF-8" in str(error.value) and "viejo.csv" in str(error.value)


# --- RF-3: bajo_malla con la malla ---------------------------------------------------------------


def test_rf3_con_malla_calcula_bajo_malla_como_el_cruce_de_la_spec_001(plantas, malla):
    preparadas = preparar_plantas(plantas, malla, "EPSG:4326")

    assert preparadas.tabla["bajo_malla"].tolist() == BAJO_MALLA
    assert preparadas.tabla["bajo_malla"].dtype.kind == "i"


def test_rf3_con_malla_sin_crs_de_las_plantas_da_un_error_que_pide_crs_plantas(plantas, malla):
    with pytest.raises(ErrorDeEntrada) as error:
        preparar_plantas(plantas, malla, None)

    assert "--crs-plantas" in str(error.value)


def test_rf3_las_plantas_en_un_sistema_proyectado_se_cruzan_con_una_malla_en_grados(tmp_path, malla):
    ida = Transformer.from_crs("EPSG:4326", "EPSG:22185", always_xy=True)
    tabla = pd.read_csv(_escribir_csv(tmp_path / "base.csv"))
    x, y = ida.transform(tabla["X"].to_numpy(), tabla["Y"].to_numpy())
    proyectadas = tmp_path / "proyectadas.csv"
    tabla.assign(X=x, Y=y).to_csv(proyectadas, index=False)

    preparadas = preparar_plantas(proyectadas, malla, "EPSG:22185")

    # La planta 5 está justo en el borde: tras convertir de sistema, el redondeo decide de qué lado cae.
    assert preparadas.tabla["bajo_malla"].tolist()[:4] == BAJO_MALLA[:4]


def test_rf3_devuelve_el_poligono_y_su_sistema_para_dibujar_el_mapa(tmp_path, plantas):
    malla = _escribir_malla(tmp_path / "malla84.geojson")

    preparadas = preparar_plantas(plantas, malla, "EPSG:4326")

    assert preparadas.poligono.equals(POLIGONO)
    assert preparadas.crs_poligono == "EPSG:4326"  # un GeoJSON sin `crs` es WGS84, según el estándar


def test_rf3_incluye_las_advertencias_del_cruce(tmp_path, plantas):
    lejos = _escribir_malla(tmp_path / "lejos.geojson", box(10.0, 10.0, 10.1, 10.1))

    preparadas = preparar_plantas(plantas, lejos, "EPSG:4326")

    assert "POSIBLE_ERROR_COORDENADAS" in _codigos(preparadas)
    assert preparadas.tabla["bajo_malla"].tolist() == [0] * 5


# --- RF-4: bajo_malla del CSV ---------------------------------------------------------------------


def test_rf4_sin_malla_usa_la_columna_bajo_malla_del_csv_tal_cual(tmp_path):
    ruta = _escribir_csv(tmp_path / "con_bajo.csv", "id,KVPI_mean,KVPI_std,bajo_malla\n1,0.6,0.02,0\n2,0.5,0.03,1\n")

    preparadas = preparar_plantas(ruta, None, None)

    assert preparadas.tabla["bajo_malla"].tolist() == [0, 1]
    assert preparadas.advertencias == []
    assert preparadas.poligono is None and preparadas.crs_poligono is None


def test_rf4_sin_malla_y_sin_columna_bajo_malla_da_un_error_que_pide_una_de_las_dos(plantas):
    with pytest.raises(ErrorDeEntrada) as error:
        preparar_plantas(plantas, None, None)

    assert "--malla" in str(error.value) and "bajo_malla" in str(error.value)


# --- RF-5: malla y bajo_malla en el CSV -----------------------------------------------------------


def _con_bajo_malla(tmp_path, valores):
    lineas = ["id,KVPI_mean,bajo_malla,KVPI_std,X,Y"]
    for fila, valor in zip(CSV_PLANTAS.strip().splitlines()[1:], valores):
        identificador, kvpi, std, x, y = fila.split(",")
        lineas.append(f"{identificador},{kvpi},{valor},{std},{x},{y}")
    return _escribir_csv(tmp_path / "con_bajo.csv", "\n".join(lineas) + "\n")


def test_rf5_con_malla_y_bajo_malla_en_el_csv_gana_el_calculo_y_avisa_cuantas_cambiaron(tmp_path, malla):
    ruta = _con_bajo_malla(tmp_path, [1, 1, 0, 0, 1])  # distinto en las plantas 1 y 3

    preparadas = preparar_plantas(ruta, malla, "EPSG:4326")

    assert preparadas.tabla["bajo_malla"].tolist() == BAJO_MALLA
    aviso = [a for a in preparadas.advertencias if a.codigo == "BAJO_MALLA_REEMPLAZADO"]
    assert len(aviso) == 1 and "2" in aviso[0].mensaje


def test_rf5_si_ninguna_planta_cambio_no_hay_advertencia(tmp_path, malla):
    ruta = _con_bajo_malla(tmp_path, BAJO_MALLA)

    preparadas = preparar_plantas(ruta, malla, "EPSG:4326")

    assert "BAJO_MALLA_REEMPLAZADO" not in _codigos(preparadas)


def test_rf5_una_celda_vacia_de_bajo_malla_cuenta_como_cambio(tmp_path, malla):
    ruta = _con_bajo_malla(tmp_path, ["", 1, 1, 0, 1])

    preparadas = preparar_plantas(ruta, malla, "EPSG:4326")

    aviso = [a for a in preparadas.advertencias if a.codigo == "BAJO_MALLA_REEMPLAZADO"]
    assert len(aviso) == 1 and "1" in aviso[0].mensaje
    assert preparadas.tabla["bajo_malla"].tolist() == BAJO_MALLA


def test_rf5_la_columna_bajo_malla_se_reemplaza_en_su_lugar_y_no_se_duplica(tmp_path, malla):
    ruta = _con_bajo_malla(tmp_path, [1, 1, 0, 0, 1])

    preparadas = preparar_plantas(ruta, malla, "EPSG:4326")

    assert list(preparadas.tabla.columns) == ["id", "KVPI_mean", "bajo_malla", "KVPI_std", "X", "Y"]


# --- No modifica los archivos de entrada (RF-20) ---------------------------------------------------


def test_rf20_leer_y_cruzar_no_modifica_los_archivos_de_entrada(plantas, malla):
    antes = (plantas.read_bytes(), malla.read_bytes())

    preparar_plantas(plantas, malla, "EPSG:4326")

    assert (plantas.read_bytes(), malla.read_bytes()) == antes


# --- T3.3: comando mapa (RF-6, RF-7, RF-23) ---------------------------------------------------------

def _mapa(tmp_path, plantas, malla, crs="EPSG:4326", salida=None, **opciones):
    opciones.setdefault("sin_fondo_satelital", True)
    return ejecutar_mapa(plantas, malla, crs, salida or tmp_path / "mapa.html", **opciones)


def test_rf6_genera_el_html_y_devuelve_la_huella_de_la_tabla_preparada(tmp_path, plantas, malla):
    resultado = _mapa(tmp_path, plantas, malla)

    assert (tmp_path / "mapa.html").is_file()
    assert resultado.huella == huella(preparar_plantas(plantas, malla, "EPSG:4326").tabla)


def test_rf6_cuenta_las_plantas_bajo_malla_y_fuera_de_malla(tmp_path, plantas, malla):
    resultado = _mapa(tmp_path, plantas, malla)

    assert (resultado.n_bajo_malla, resultado.n_fuera_de_malla) == (3, 2)


def test_rf6_incluye_las_advertencias_del_cruce_y_las_del_mapa(tmp_path):
    repetida = CSV_PLANTAS + "2,0.50,0.03,-57.95,-37.95\n"  # fila idéntica a la de la planta 2
    ruta = _escribir_csv(tmp_path / "repetidas.csv", repetida)
    lejos = _escribir_malla(tmp_path / "lejos.geojson", box(10.0, 10.0, 10.1, 10.1))

    resultado = _mapa(tmp_path, ruta, lejos)

    codigos = [a.codigo for a in resultado.advertencias]
    assert "POSIBLE_ERROR_COORDENADAS" in codigos and "ID_DUPLICADO" in codigos
    assert codigos.index("POSIBLE_ERROR_COORDENADAS") < codigos.index("ID_DUPLICADO")  # primero el cruce


def test_rf23_el_mapa_dibuja_longitud_y_latitud_aunque_las_plantas_esten_en_metros(tmp_path, malla):
    ida = Transformer.from_crs("EPSG:4326", "EPSG:22185", always_xy=True)
    base = pd.read_csv(_escribir_csv(tmp_path / "base.csv"))
    x, y = ida.transform(base["X"].to_numpy(), base["Y"].to_numpy())
    proyectadas = tmp_path / "proyectadas.csv"
    base.assign(X=x, Y=y).to_csv(proyectadas, index=False)

    resultado = _mapa(tmp_path, proyectadas, malla, crs="EPSG:22185")

    html = (tmp_path / "mapa.html").read_text(encoding="utf-8")
    pares = [(float(a), float(b)) for a, b in re.findall(r"\[(-?\d+\.\d+), (-?\d+\.\d+)\]", html)]
    assert len(pares) >= 5 and all(abs(a) <= 180 and abs(b) <= 180 for a, b in pares)
    assert resultado.n_bajo_malla + resultado.n_fuera_de_malla == 5


def test_rf23_la_conversion_para_dibujar_no_cambia_la_huella(tmp_path, malla):
    # Sin la planta 5, que está en el borde: tras convertir de sistema el redondeo la puede mover de lado.
    sin_borde = "".join(linea + chr(10) for linea in CSV_PLANTAS.strip().splitlines()[:-1])
    en_grados = _escribir_csv(tmp_path / "grados.csv", sin_borde)
    ida = Transformer.from_crs("EPSG:4326", "EPSG:22185", always_xy=True)
    base = pd.read_csv(en_grados)
    x, y = ida.transform(base["X"].to_numpy(), base["Y"].to_numpy())
    en_metros = tmp_path / "metros.csv"
    base.assign(X=x, Y=y).to_csv(en_metros, index=False)

    con_grados = _mapa(tmp_path, en_grados, malla, salida=tmp_path / "a.html")
    con_metros = _mapa(tmp_path, en_metros, malla, crs="EPSG:22185", salida=tmp_path / "b.html")

    assert con_metros.huella == con_grados.huella
    assert (con_metros.n_bajo_malla, con_metros.n_fuera_de_malla) == (2, 2)


def test_rf7_sin_fondo_satelital_el_html_no_pide_teselas_y_con_fondo_si(tmp_path, plantas, malla):
    _mapa(tmp_path, plantas, malla, salida=tmp_path / "sin.html")
    _mapa(tmp_path, plantas, malla, salida=tmp_path / "con.html", sin_fondo_satelital=False)

    assert "arcgisonline" not in (tmp_path / "sin.html").read_text(encoding="utf-8")
    assert "arcgisonline" in (tmp_path / "con.html").read_text(encoding="utf-8")


def test_rf6_si_el_mapa_ya_existe_y_no_se_indica_sobrescribir_da_un_error_sin_tocarlo(tmp_path, plantas, malla):
    existente = tmp_path / "mapa.html"
    existente.write_text("mapa anterior", encoding="utf-8")

    with pytest.raises(ErrorDeEntrada) as error:
        _mapa(tmp_path, plantas, malla)

    assert "mapa.html" in str(error.value) and "--sobrescribir" in str(error.value)
    assert existente.read_text(encoding="utf-8") == "mapa anterior"


def test_rf6_con_sobrescribir_reemplaza_el_mapa_existente(tmp_path, plantas, malla):
    existente = tmp_path / "mapa.html"
    existente.write_text("mapa anterior", encoding="utf-8")

    _mapa(tmp_path, plantas, malla, sobrescribir=True)

    assert "mapa anterior" not in existente.read_text(encoding="utf-8")


def test_rf6_crea_la_carpeta_del_mapa_si_no_existe(tmp_path, plantas, malla):
    destino = tmp_path / "salidas" / "nueva" / "mapa.html"

    _mapa(tmp_path, plantas, malla, salida=destino)

    assert destino.is_file()


def test_rf6_si_la_salida_es_una_carpeta_da_un_error(tmp_path, plantas, malla):
    with pytest.raises(ErrorDeEntrada) as error:
        _mapa(tmp_path, plantas, malla, salida=tmp_path)

    assert "carpeta" in str(error.value)


def test_rf6_si_falla_la_lectura_no_se_crea_ningun_archivo(tmp_path, malla):
    with pytest.raises(ErrorDeEntrada):
        _mapa(tmp_path, tmp_path / "no_existe.csv", malla)

    assert not (tmp_path / "mapa.html").exists()


def test_rf20_generar_el_mapa_no_modifica_los_archivos_de_entrada(tmp_path, plantas, malla):
    antes = (plantas.read_bytes(), malla.read_bytes())

    _mapa(tmp_path, plantas, malla)

    assert (plantas.read_bytes(), malla.read_bytes()) == antes
