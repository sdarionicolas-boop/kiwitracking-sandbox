"""La versión del paquete y la opción `--version` (spec 006, RF-15)."""

import importlib
import importlib.metadata
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import kiwitracking
from kiwitracking.cli import main

RAIZ = Path(__file__).resolve().parent.parent


def _version_de_pyproject():
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_rf15_la_version_instalada_es_la_de_pyproject():
    esperada = _version_de_pyproject()
    assert kiwitracking.__version__ == esperada, (
        f"__version__ es {kiwitracking.__version__!r} y pyproject.toml dice {esperada!r}: "
        "reinstalá el entorno de desarrollo con `pip install -e .[dev]`."
    )


def test_rf15_la_version_es_la_1_2_0():
    assert _version_de_pyproject() == "1.2.0"


def test_rf15_version_imprime_el_nombre_y_la_version_y_devuelve_0(capsys):
    codigo = main(["--version"])  # si llamara a sys.exit, el test se cortaría con SystemExit
    salida = capsys.readouterr()
    assert codigo == 0
    assert salida.out == f"kiwitracking {_version_de_pyproject()}\n"
    assert salida.err == ""


def test_rf15_version_no_necesita_un_subcomando_ni_archivos(capsys):
    assert main(["--version"]) == 0
    assert "kiwitracking" in capsys.readouterr().out


def test_rf15_la_ayuda_general_lista_la_opcion_version(capsys):
    main(["--help"])
    ayuda = capsys.readouterr().out
    assert "--version" in ayuda and "versión" in ayuda


def test_rf15_en_un_proceso_aparte_version_da_codigo_0():
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(
        [sys.executable, "-m", "kiwitracking", "--version"], capture_output=True, text=True, cwd=RAIZ, env=entorno
    )
    assert proceso.returncode == 0
    assert proceso.stdout.strip() == f"kiwitracking {_version_de_pyproject()}"


def test_rf15_sin_metadatos_la_version_es_desconocida(monkeypatch):
    def sin_metadatos(nombre):
        raise importlib.metadata.PackageNotFoundError(nombre)

    monkeypatch.setattr(importlib.metadata, "version", sin_metadatos)
    try:
        importlib.reload(kiwitracking)
        assert kiwitracking.__version__ == "desconocida"
    finally:
        monkeypatch.undo()
        importlib.reload(kiwitracking)
    assert kiwitracking.__version__ == _version_de_pyproject()


def test_rf15_sin_metadatos_version_imprime_desconocida_y_no_falla(monkeypatch, capsys):
    monkeypatch.setattr(kiwitracking, "__version__", "desconocida")
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == "kiwitracking desconocida\n"


def test_rf15_el_numero_de_version_no_esta_escrito_en_el_codigo():
    for archivo in (RAIZ / "kiwitracking").glob("*.py"):
        assert _version_de_pyproject() not in archivo.read_text(encoding="utf-8"), archivo.name
