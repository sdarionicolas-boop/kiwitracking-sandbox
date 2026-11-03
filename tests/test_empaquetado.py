"""Construcción del paquete: `wheel` y `sdist` con el contenido exacto (spec 006, RF-13).

Construye con `python -m build --no-isolation` (necesita `build` y `setuptools>=77`, del extra `dev`), así que la
suite no usa la red. La construcción aislada y la instalación en un entorno limpio las prueba el script
`scripts/probar_instalacion.py`.
"""

import os
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
VERSION = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
DISTRIBUCION = f"kiwitracking-{VERSION}"
EXTENSIONES_DE_PRUEBAS = {".py", ".csv", ".geojson", ".txt"}


@pytest.fixture(scope="module")
def construccion(tmp_path_factory):
    """Construye el `sdist` y el `wheel` una sola vez para todos los tests del módulo.

    Antes se borra `kiwitracking.egg-info`: `setuptools` lee el `SOURCES.txt` viejo que haya ahí y lo suma al `sdist`,
    así que un metadato desactualizado hace viajar archivos que `MANIFEST.in` no nombra.
    """
    shutil.rmtree(RAIZ / "kiwitracking.egg-info", ignore_errors=True)
    salida = tmp_path_factory.mktemp("dist")
    entorno = {clave: valor for clave, valor in os.environ.items() if clave != "PYTHONDONTWRITEBYTECODE"}
    proceso = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(salida), str(RAIZ)],
        capture_output=True, text=True, encoding="utf-8", env=entorno, cwd=RAIZ,
    )  # fmt: skip
    return proceso, salida


@pytest.fixture(scope="module")
def wheel(construccion):
    with zipfile.ZipFile(construccion[1] / f"{DISTRIBUCION}-py3-none-any.whl") as archivo:
        yield archivo


@pytest.fixture(scope="module")
def sdist(construccion):
    with tarfile.open(construccion[1] / f"{DISTRIBUCION}.tar.gz") as archivo:
        yield archivo


def _nombres_del_sdist(sdist):
    prefijo = f"{DISTRIBUCION}/"
    return {m.name.removeprefix(prefijo) for m in sdist.getmembers() if m.isfile()}


def test_rf13_la_construccion_termina_bien_sin_errores_ni_avisos(construccion):
    proceso, _ = construccion
    texto = (proceso.stdout + proceso.stderr).lower()
    assert proceso.returncode == 0, proceso.stderr
    assert "successfully built" in texto
    for palabra in ("warning", "deprecat", "error"):
        assert palabra not in texto, f"la construcción emitió {palabra!r}:\n{proceso.stdout}{proceso.stderr}"


def test_rf13_se_generan_exactamente_el_wheel_y_el_sdist(construccion):
    nombres = sorted(p.name for p in construccion[1].iterdir())
    assert nombres == [f"{DISTRIBUCION}-py3-none-any.whl", f"{DISTRIBUCION}.tar.gz"]


# --- wheel ---------------------------------------------------------------------------------------------------------


def test_rf13_el_wheel_trae_solo_el_paquete_sus_metadatos_y_la_licencia(wheel):
    modulos = {f"kiwitracking/{p.name}" for p in (RAIZ / "kiwitracking").glob("*.py")}
    info = f"{DISTRIBUCION}.dist-info"
    metadatos = {f"{info}/{nombre}" for nombre in ("METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt")}
    assert set(wheel.namelist()) == modulos | metadatos | {f"{info}/licenses/LICENSE"}


def test_rf13_el_wheel_no_trae_tests_specs_ni_datos(wheel):
    for nombre in wheel.namelist():
        assert not nombre.startswith(("tests", "specs", "docs", "scripts")), nombre
        assert not nombre.endswith((".csv", ".geojson", ".xls", ".xlsx", ".html")), nombre


def test_rf13_el_punto_de_entrada_es_kiwitracking(wheel):
    texto = wheel.read(f"{DISTRIBUCION}.dist-info/entry_points.txt").decode("utf-8")
    assert "[console_scripts]" in texto and "kiwitracking = kiwitracking.cli:main" in texto


def test_rf13_la_licencia_del_wheel_es_la_del_repositorio(wheel):
    incluida = wheel.read(f"{DISTRIBUCION}.dist-info/licenses/LICENSE").decode("utf-8")
    assert incluida == (RAIZ / "LICENSE").read_text(encoding="utf-8")


def test_rf13_los_metadatos_del_wheel(wheel):
    texto = wheel.read(f"{DISTRIBUCION}.dist-info/METADATA").decode("utf-8")
    lineas = set(texto.splitlines())
    assert "Name: kiwitracking" in lineas and f"Version: {VERSION}" in lineas
    assert "License-Expression: MIT" in lineas and "License-File: LICENSE" in lineas
    assert "Requires-Python: >=3.14" in lineas
    for dependencia in ("pandas>=3.0", "numpy>=2.5", "scipy>=1.18", "shapely>=2.2", "pyproj>=3.8", "folium>=0.20"):
        assert f"Requires-Dist: {dependencia}" in lineas
    assert "Provides-Extra: dev" in lineas
    assert "Description-Content-Type: text/markdown" in lineas
    assert "sandbox" not in texto.split("\n\n", 1)[0].lower()  # ni en los metadatos


# --- sdist ---------------------------------------------------------------------------------------------------------


def _esperado_en_el_sdist():
    generados = {
        "PKG-INFO", "MANIFEST.in", "setup.cfg",
        "kiwitracking.egg-info/PKG-INFO", "kiwitracking.egg-info/SOURCES.txt",
        "kiwitracking.egg-info/dependency_links.txt", "kiwitracking.egg-info/entry_points.txt",
        "kiwitracking.egg-info/requires.txt", "kiwitracking.egg-info/top_level.txt",
    }  # fmt: skip
    pedidos = {"pyproject.toml", "README.md", "LICENSE", "CITATION.cff", "docs/uso.md"}
    modulos = {f"kiwitracking/{p.name}" for p in (RAIZ / "kiwitracking").glob("*.py")}
    pruebas = {
        p.relative_to(RAIZ).as_posix()
        for p in (RAIZ / "tests").rglob("*")
        if p.is_file() and p.suffix in EXTENSIONES_DE_PRUEBAS
    }
    return generados | pedidos | modulos | pruebas


def test_rf13_el_sdist_trae_exactamente_la_lista_de_inclusion(sdist):
    obtenidos = _nombres_del_sdist(sdist)
    esperado = _esperado_en_el_sdist()
    assert obtenidos - esperado == set(), f"sobran en el sdist: {sorted(obtenidos - esperado)}"
    assert esperado - obtenidos == set(), f"faltan en el sdist: {sorted(esperado - obtenidos)}"


@pytest.mark.parametrize(
    "prohibido",
    ["specs/", "AGENTS.md", "CLAUDE.md", "docs/constitution.md", "mapa.html", "resultados", ".xls", ".xlsx", ".venv",
     "dist/", "build/", "__pycache__", ".pyc", ".git", "scripts/"],
)  # fmt: skip
def test_rf13_el_sdist_no_trae_nada_fuera_de_la_lista(sdist, prohibido):
    ofensores = [nombre for nombre in _nombres_del_sdist(sdist) if prohibido in nombre]
    assert ofensores == []


def test_rf13_el_sdist_trae_los_tests_y_los_datos_de_referencia(sdist):
    nombres = _nombres_del_sdist(sdist)
    for esperado in ("tests/test_empaquetado.py", "tests/golden/datos_plantas_completos.csv", "tests/golden/kvpi_serie.csv",
                     "tests/golden/clima_diario.csv", "tests/golden/malla_zona.geojson"):  # fmt: skip
        assert esperado in nombres


def test_rf13_el_sdist_trae_la_guia_la_licencia_y_la_cita(sdist):
    nombres = _nombres_del_sdist(sdist)
    assert {"README.md", "docs/uso.md", "LICENSE", "CITATION.cff", "pyproject.toml"} <= nombres


def test_rf13_la_licencia_y_la_cita_del_sdist_son_las_del_repositorio(sdist):
    prefijo = f"{DISTRIBUCION}/"
    for nombre in ("LICENSE", "CITATION.cff"):
        incluido = sdist.extractfile(prefijo + nombre).read().decode("utf-8")
        assert incluido == (RAIZ / nombre).read_text(encoding="utf-8")


def test_rf13_el_pkg_info_del_sdist_tiene_la_version(sdist):
    texto = sdist.extractfile(f"{DISTRIBUCION}/PKG-INFO").read().decode("utf-8")
    assert f"Version: {VERSION}" in texto.splitlines()


def test_rf13_construir_no_deja_carpetas_dist_ni_build_en_el_proyecto(construccion):
    assert not (RAIZ / "build").exists()
