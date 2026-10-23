"""Línea de comandos `kiwitracking` (spec 003, RF-1 en esta tarea; el resto se agrega tarea por tarea)."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from kiwitracking.cli import main

RAIZ = Path(__file__).parent.parent


# --- T3.0: programa y ayuda (RF-1) --------------------------------------------------------------


def _nombra(texto, opcion):
    """La opción aparece completa (no como prefijo de otra más larga)."""
    return re.search(re.escape(opcion) + r"(?![\w-])", texto) is not None


def test_rf1_main_devuelve_el_codigo_como_entero_y_no_termina_el_proceso(capsys):
    codigo = main(["--help"])  # si llamara a sys.exit, el test se cortaría con SystemExit

    assert codigo == 0 and isinstance(codigo, int)


def test_rf1_con_help_muestra_una_ayuda_en_espanol_con_los_dos_subcomandos(capsys):
    main(["--help"])

    salida = capsys.readouterr().out
    assert "uso:" in salida and "usage:" not in salida
    assert "kiwitracking" in salida and "mapa" in salida and "analizar" in salida


def test_rf1_sin_subcomando_muestra_la_ayuda_por_la_salida_de_errores_y_da_codigo_2(capsys):
    codigo = main([])

    captura = capsys.readouterr()
    assert codigo == 2
    assert "mapa" in captura.err and "analizar" in captura.err
    assert captura.out == ""


def test_rf1_un_subcomando_desconocido_da_error_de_uso_con_codigo_2(capsys):
    codigo = main(["inventado"])

    assert codigo == 2
    assert "inventado" in capsys.readouterr().err


def test_rf1_la_ayuda_de_mapa_nombra_sus_opciones(capsys):
    codigo = main(["mapa", "--help"])

    salida = capsys.readouterr().out
    assert codigo == 0
    for opcion in ("--plantas", "--malla", "--crs-plantas", "--salida", "--sin-fondo-satelital", "--sobrescribir", "--depurar"):
        assert _nombra(salida, opcion), opcion


def test_rf1_la_ayuda_de_analizar_nombra_sus_opciones(capsys):
    codigo = main(["analizar", "--help"])

    salida = capsys.readouterr().out
    assert codigo == 0
    opciones = (
        "--plantas", "--malla", "--crs-plantas", "--depurar", "--huella", "--salida", "--sobrescribir",
        "--correccion", "--prueba-t", "--alfa", "--min-plantas-grupo", "--p-ambiente", "--p-estabilidad",
        "--no-escalar-std", "--clima", "--campana", "--ventana-frio", "--formato-fecha", "--cobertura-minima",
        "--max-hueco-dias", "--estado-frio",
    )
    for opcion in opciones:
        assert _nombra(salida, opcion), opcion


def test_rf1_una_opcion_desconocida_da_error_de_uso_con_codigo_2(capsys):
    codigo = main(["mapa", "--plantas", "x.csv", "--no-existe"])

    assert codigo == 2
    assert "--no-existe" in capsys.readouterr().err


def test_rf1_python_m_kiwitracking_muestra_la_ayuda_en_un_proceso_aparte():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # la codificación de la consola es tema de T3.9 (RF-22)
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", "--help"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ, env=entorno
    )

    assert proceso.returncode == 0
    assert "mapa" in proceso.stdout and "analizar" in proceso.stdout


def test_rf1_pyproject_declara_el_punto_de_entrada_kiwitracking():
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.scripts]" in texto
    assert 'kiwitracking = "kiwitracking.cli:main"' in texto


def test_rf1_los_errores_de_uso_muestran_el_encabezado_en_espanol(capsys):
    main(["inventado"])

    assert capsys.readouterr().err.startswith("uso: ")


def test_rf1_python_m_kiwitracking_propaga_el_codigo_de_salida_de_un_error_de_uso():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", "inventado"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ, env=entorno
    )

    assert proceso.returncode == 2


# --- T3.3: comando mapa (RF-6, RF-7, RF-26) ------------------------------------------------------

import pandas as pd  # noqa: E402

from kiwitracking.huella import huella  # noqa: E402
from kiwitracking.resultado import ErrorDeEntrada  # noqa: E402

GOLDEN = RAIZ / "tests" / "golden"


def _argumentos_de_mapa(tmp_path, *extra):
    return [
        "mapa", "--plantas", str(GOLDEN / "datos_plantas_completos.csv"), "--malla", str(GOLDEN / "malla_zona.geojson"),
        "--crs-plantas", "EPSG:4326", "--salida", str(tmp_path / "mapa.html"), "--sin-fondo-satelital", *extra,
    ]


def test_rf6_mapa_imprime_la_cantidad_de_plantas_bajo_malla_y_fuera_de_malla(tmp_path, capsys):
    codigo = main(_argumentos_de_mapa(tmp_path))

    salida = capsys.readouterr().out
    assert codigo == 0
    assert re.search(r"bajo malla: 53\b", salida) and re.search(r"fuera de malla: 106\b", salida)
    assert (tmp_path / "mapa.html").is_file() and str(tmp_path / "mapa.html") in salida


def test_rf26_la_huella_sale_en_una_linea_propia_con_el_formato_exacto(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    lineas = capsys.readouterr().out.splitlines()
    huellas = [linea for linea in lineas if linea.startswith("Huella:")]
    assert len(huellas) == 1 and re.fullmatch(r"Huella: [0-9a-f]{12}", huellas[0])


def test_rf6_la_huella_que_imprime_mapa_es_la_del_lote_de_referencia(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    lote = pd.read_csv(GOLDEN / "datos_plantas_completos.csv", encoding="utf-8")
    assert f"Huella: {huella(lote)}" in capsys.readouterr().out


def test_rf6_mapa_imprime_las_advertencias(tmp_path, capsys):
    lejos = tmp_path / "lejos.geojson"
    lejos.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":'
        '{"type":"Polygon","coordinates":[[[10,10],[10.1,10],[10.1,10.1],[10,10.1],[10,10]]]}}]}',
        encoding="utf-8",
    )
    argumentos = _argumentos_de_mapa(tmp_path)
    argumentos[argumentos.index("--malla") + 1] = str(lejos)

    main(argumentos)

    assert "POSIBLE_ERROR_COORDENADAS" in capsys.readouterr().out


def test_rf6_sin_salida_el_mapa_se_guarda_como_mapa_html_en_el_directorio_actual(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    argumentos = _argumentos_de_mapa(tmp_path)
    del argumentos[argumentos.index("--salida"): argumentos.index("--salida") + 2]

    main(argumentos)

    assert (tmp_path / "mapa.html").is_file()


def test_rf7_el_mapa_con_sin_fondo_satelital_no_pide_teselas(tmp_path, capsys):
    main(_argumentos_de_mapa(tmp_path))

    assert "arcgisonline" not in (tmp_path / "mapa.html").read_text(encoding="utf-8")


def test_rf6_mapa_sin_sobrescribir_sobre_un_archivo_existente_no_lo_toca(tmp_path, capsys):
    existente = tmp_path / "mapa.html"
    existente.write_text("anterior", encoding="utf-8")

    with pytest.raises(ErrorDeEntrada):  # hasta T3.9 (RF-19) el error sale como excepción, no como código
        main(_argumentos_de_mapa(tmp_path))

    assert existente.read_text(encoding="utf-8") == "anterior"


def test_rf6_mapa_con_sobrescribir_reemplaza_el_archivo_existente(tmp_path, capsys):
    existente = tmp_path / "mapa.html"
    existente.write_text("anterior", encoding="utf-8")

    codigo = main(_argumentos_de_mapa(tmp_path, "--sobrescribir"))

    assert codigo == 0 and "anterior" not in existente.read_text(encoding="utf-8")
