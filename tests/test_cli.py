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
