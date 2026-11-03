"""La guía de uso: formatos de entrada y archivos de salida contra el programa (spec 006, RF-6 y RF-7)."""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from kiwitracking.cli import main
from kiwitracking.clima_entrada import preparar_clima
from kiwitracking.clima_parametros import ParametrosClima
from kiwitracking.huella import huella
from kiwitracking.io import leer_poligono_geojson
from kiwitracking.kvpi import preparar_muestreo, validar_serie
from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.salida import ORDEN_CONOCIDO
from kiwitracking.validacion import COLUMNAS_OBLIGATORIAS, validar_tabla

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = RAIZ / "tests" / "golden"


@pytest.fixture(scope="module")
def guia():
    return (RAIZ / "docs" / "uso.md").read_text(encoding="utf-8")


def _seccion(texto, encabezado):
    """El texto entre un encabezado y el siguiente del mismo nivel o superior."""
    nivel = len(encabezado) - len(encabezado.lstrip("#"))
    coincidencia = re.search(rf"^{re.escape(encabezado)}\s*$", texto, re.M)
    assert coincidencia, f"falta el encabezado {encabezado!r}"
    resto = texto[coincidencia.end():]
    siguiente = re.search(rf"^#{{1,{nivel}}} ", resto, re.M)
    return resto[: siguiente.start()] if siguiente else resto


def _linea(seccion, etiqueta):
    coincidencia = re.search(rf"^- \*\*{re.escape(etiqueta)}:\*\*(.*)$", seccion, re.M)
    assert coincidencia, f"falta la línea «{etiqueta}»"
    return coincidencia.group(1)


def _nombres(linea):
    return set(re.findall(r"`([^`]+)`", linea))


def _exige_la_columna(funcion, tabla, columna):
    """Verdadero si `funcion` se detiene con un error al faltar `columna`."""
    try:
        funcion(tabla.drop(columns=columna))
    except ErrorDeEntrada:
        return True
    return False


# --- Formatos de entrada (RF-6) -----------------------------------------------------------------------------------


def test_rf6_la_guia_dice_como_son_todos_los_csv(guia):
    seccion = _seccion(guia, "## 3. Formatos de los archivos de entrada")
    for frase in ("UTF-8", "BOM", "comas", "punto decimal", "primera fila"):
        assert frase in seccion, f"falta explicar: {frase}"


def test_rf6_serie_columnas_obligatorias_y_lo_que_el_codigo_exige(guia):
    seccion = _seccion(guia, "### Serie")
    assert _nombres(_linea(seccion, "Obligatorias")) == {"id", "campaña", "campana", "KVPI"}
    base = pd.DataFrame({"id": [1], "campaña": ["a"], "KVPI": [0.1]})
    for columna in ("id", "campaña", "KVPI"):
        assert _exige_la_columna(validar_serie, base, columna), f"el código no exige {columna}"


def test_rf6_serie_explica_vacios_repetidos_y_columnas_extra(guia):
    seccion = _seccion(guia, "### Serie")
    for frase in ("sin dato", "se ignoran", "repetid"):
        assert frase in seccion


def test_rf6_muestreo_columnas_obligatorias_y_lo_que_el_codigo_exige(guia):
    seccion = _seccion(guia, "### Muestreo")
    assert _nombres(_linea(seccion, "Obligatorias")) == {"id", "X", "Y"}
    base = pd.DataFrame({"id": [1], "X": [1.0], "Y": [2.0]})
    for columna in ("id", "X", "Y"):
        assert _exige_la_columna(preparar_muestreo, base, columna), f"el código no exige {columna}"
    assert "se conservan" in seccion


def test_rf6_plantas_columnas_obligatorias_y_lo_que_el_codigo_exige(guia):
    seccion = _seccion(guia, "### Plantas")
    obligatorias = _nombres(_linea(seccion, "Obligatorias"))
    assert obligatorias == {"id", "KVPI_mean", "KVPI_std"}
    assert set(COLUMNAS_OBLIGATORIAS) == obligatorias | {"bajo_malla"}
    base = pd.DataFrame({"id": [1], "KVPI_mean": [0.5], "KVPI_std": [0.1], "bajo_malla": [0]})
    for columna in COLUMNAS_OBLIGATORIAS:
        assert _exige_la_columna(validar_tabla, base, columna), f"el código no exige {columna}"
    assert {"X", "Y", "bajo_malla"} <= _nombres(_linea(seccion, "Según el comando"))


def test_rf6_malla_explica_el_formato_y_el_sistema_de_coordenadas_por_defecto(guia, tmp_path):
    seccion = _seccion(guia, "### Malla")
    for frase in ("GeoJSON", "Polygon", "MultiPolygon", "EPSG:4326", "crs"):
        assert frase in seccion
    ruta = tmp_path / "malla.geojson"
    poligono = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    ruta.write_text(json.dumps(poligono), encoding="utf-8")
    assert leer_poligono_geojson(ruta)[1] == "EPSG:4326"  # lo que la guía afirma


def test_rf6_clima_columnas_obligatorias_y_lo_que_el_codigo_exige(guia):
    seccion = _seccion(guia, "### Clima")
    assert _nombres(_linea(seccion, "Obligatorias")) == {"date", "Tmax", "Tmin"}
    assert _nombres(_linea(seccion, "Opcionales")) == {"origen"}
    base = pd.DataFrame({"date": ["2024-05-01"], "Tmax": [15.0], "Tmin": [5.0]})
    for columna in ("date", "Tmax", "Tmin"):
        assert _exige_la_columna(preparar_clima, base, columna), f"el código no exige {columna}"


def test_rf6_clima_explica_fechas_unidades_y_rango(guia):
    seccion = _seccion(guia, "### Clima")
    rango = ParametrosClima().rango_fisico
    for frase in ("AAAA-MM-DD", "--formato-fecha", "Celsius", str(rango[0]), str(rango[1]), "interpolado"):
        assert frase in seccion, f"falta explicar: {frase}"


# --- Archivos de salida (RF-7) ------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("salidas")
    publicado = pd.read_csv(GOLDEN / "datos_plantas_completos.csv")
    publicado[["id", "X", "Y"]].to_csv(carpeta / "muestreo.csv", index=False)
    codigo = main(["kvpi", "--serie", str(GOLDEN / "kvpi_serie.csv"), "--muestreo", str(carpeta / "muestreo.csv"),
                   "--salida", str(carpeta / "plantas_kvpi.csv")])  # fmt: skip
    assert codigo == 0
    codigo = main(["analizar", "--plantas", str(carpeta / "plantas_kvpi.csv"), "--malla", str(GOLDEN / "malla_zona.geojson"),
                   "--crs-plantas", "EPSG:4326", "--huella", huella(publicado), "--clima", str(GOLDEN / "clima_diario.csv"),
                   "--campana", "2024", "--salida", str(carpeta / "res")])  # fmt: skip
    assert codigo == 0
    return carpeta


def _en_orden(seccion, nombres):
    posiciones = [seccion.index(f"`{nombre}`") for nombre in nombres]
    return posiciones == sorted(posiciones)


def test_rf7_la_guia_describe_el_formato_de_los_archivos_de_salida(guia):
    seccion = _seccion(guia, "## 4. Archivos de salida")
    for frase in ("UTF-8 sin BOM", "decimales", "celdas vacías"):
        assert frase in seccion


def test_rf7_plantas_kvpi_csv_las_columnas_de_la_guia_son_las_del_archivo(guia, corrida):
    seccion = _seccion(guia, "### `plantas_kvpi.csv`")
    columnas = list(pd.read_csv(corrida / "plantas_kvpi.csv").columns)
    propias = ["id", "KVPI_mean", "KVPI_std", "KVPI_cv", "n_campanas"]
    assert columnas[:5] == propias
    assert _en_orden(seccion, propias)
    assert "columnas del muestreo" in seccion


def test_rf7_plantas_csv_las_columnas_de_la_guia_son_las_del_archivo(guia, corrida):
    seccion = _seccion(guia, "### `plantas.csv`")
    columnas = list(pd.read_csv(corrida / "res" / "plantas.csv").columns)
    assert columnas[: len(ORDEN_CONOCIDO)] == list(ORDEN_CONOCIDO)
    assert _en_orden(seccion, ORDEN_CONOCIDO)
    assert "demás columnas" in seccion


def test_rf7_plantas_csv_explica_ambientes_y_recomendaciones(guia):
    seccion = _seccion(guia, "### `plantas.csv`")
    for palabra in ("Alto Potencial", "Transicional", "Limitante", "Mantener", "Observar", "Intervenir"):
        assert palabra in seccion


def _claves(documento):
    claves = set()
    if isinstance(documento, dict):
        for clave, valor in documento.items():
            claves.add(clave)
            claves |= _claves(valor)
    return claves


def test_rf7_resumen_json_todas_las_claves_del_archivo_estan_en_la_guia(guia, corrida):
    seccion = _seccion(guia, "### `resumen.json`")
    documento = json.loads((corrida / "res" / "resumen.json").read_text(encoding="utf-8"))
    sin_documentar = _claves(documento) - _nombres(seccion)
    assert sin_documentar == set(), f"claves sin documentar: {sorted(sin_documentar)}"


def test_rf7_resumen_json_la_guia_no_nombra_claves_que_no_existen(guia, corrida):
    seccion = _seccion(guia, "### `resumen.json`")
    documento = json.loads((corrida / "res" / "resumen.json").read_text(encoding="utf-8"))
    claves_de_la_guia = set(re.findall(r"^\s*- `([a-z0-9_]+)`", seccion, re.M))
    assert claves_de_la_guia - _claves(documento) == set()


def test_rf7_advertencias_json_es_una_lista_de_codigo_y_mensaje(guia, corrida):
    seccion = _seccion(guia, "### `advertencias.json`")
    documento = json.loads((corrida / "res" / "advertencias.json").read_text(encoding="utf-8"))
    assert {clave for fila in documento for clave in fila} == {"codigo", "mensaje"}
    assert {"codigo", "mensaje"} <= _nombres(seccion)
    assert "lista" in seccion
