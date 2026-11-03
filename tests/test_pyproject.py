"""Metadatos y archivos del paquete (spec 006): licencia, cita, `.gitignore`, `pyproject.toml`."""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _leer(nombre):
    return (RAIZ / nombre).read_text(encoding="utf-8")


# --- T6.0: licencia, cita y .gitignore (RF-12, RF-17) -----------------------------------------------------------


def test_rf12_la_licencia_es_mit_con_el_titular_del_repositorio_original():
    texto = _leer("LICENSE")
    assert texto.startswith("MIT License")
    assert "Copyright (c) 2026 Darío Nicolás Sánchez Leguizamón" in texto
    for frase in ("Permission is hereby granted, free of charge", 'THE SOFTWARE IS PROVIDED "AS IS"', "SOFTWARE."):
        assert frase in texto


def test_rf12_la_licencia_esta_completa_y_sin_saltos_de_linea_de_windows():
    texto = (RAIZ / "LICENSE").read_bytes()
    assert b"\r\n" not in texto
    assert texto.endswith(b"SOFTWARE.\n")


def _cita():
    return _leer("CITATION.cff")


@pytest.mark.parametrize("clave", ["cff-version", "message", "title", "authors"])
def test_rf17_la_cita_tiene_los_campos_obligatorios_de_cff(clave):
    assert re.search(rf"^{clave}:", _cita(), re.M)


def test_rf17_la_cita_es_de_la_version_1_2_0_con_licencia_mit():
    texto = _cita()
    assert re.search(r"^version: 1\.2\.0$", texto, re.M)
    assert re.search(r"^license: MIT$", texto, re.M)
    assert re.search(r"^cff-version: 1\.2\.0$", texto, re.M)


def test_rf17_la_cita_tiene_la_misma_autoria_sin_correo():
    texto = _cita()
    assert 'family-names: "Sánchez Leguizamón"' in texto and 'given-names: "Darío Nicolás"' in texto
    assert "Universidad Nacional Arturo Jauretche" in texto
    assert re.search(r"orcid: \"https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]\"", texto)
    assert "email" not in texto and "@" not in texto


def test_rf17_la_cita_remite_a_la_tesis():
    texto = _cita()
    assert "preferred-citation:" in texto and "type: thesis" in texto
    assert "Análisis de variabilidad productiva para kiwi integrando teledetección, topografía y machine learning" in texto


def test_rf17_el_doi_de_zenodo_figura_como_el_del_proyecto_y_no_el_de_esta_version():
    texto = _cita()
    assert 'doi: "10.5281/zenodo.19352552"' in texto
    comentario = re.search(r"^# (DOI del proyecto[^\n]*)$", texto, re.M)
    assert comentario and "no tiene DOI propio" in comentario.group(1)


def test_rf17_la_cita_no_trae_fecha_de_publicacion_ni_enlace_al_repositorio_privado():
    texto = _cita()
    assert "date-released" not in texto  # todavía no se publicó
    assert "kiwitracking-sandbox" not in texto


def test_el_gitignore_ignora_los_archivos_generados_y_ya_no_dice_condiciones_sin_verificar():
    lineas = _leer(".gitignore").splitlines()
    assert "dist/" in lineas and "build/" in lineas
    assert "sin verificar" not in "\n".join(lineas)
    assert "*.xls" in lineas  # los originales de INTA se siguen sin versionar


# --- T6.1: metadatos de pyproject.toml (RF-11) --------------------------------------------------------------------

import tomllib  # noqa: E402
from importlib.metadata import version as version_instalada  # noqa: E402

PISOS = {"pandas": (3, 0), "numpy": (2, 5), "scipy": (1, 18), "shapely": (2, 2), "pyproj": (3, 8), "folium": (0, 20)}


@pytest.fixture(scope="module")
def pyproject():
    return tomllib.loads(_leer("pyproject.toml"))


def test_rf11_nombre_version_y_descripcion(pyproject):
    proyecto = pyproject["project"]
    assert proyecto["name"] == "kiwitracking"
    assert proyecto["version"] == "1.2.0"
    assert len(proyecto["description"]) > 30
    assert "sandbox" not in proyecto["description"].lower()


def test_rf11_readme_y_licencia(pyproject):
    proyecto = pyproject["project"]
    assert proyecto["readme"] == "README.md"
    assert proyecto["license"] == "MIT"
    assert proyecto["license-files"] == ["LICENSE"]
    assert not any(c.startswith("License ::") for c in proyecto["classifiers"])  # con SPDX, setuptools lo rechaza


def test_rf11_autor_sin_correo(pyproject):
    autores = pyproject["project"]["authors"]
    assert autores == [{"name": "Darío Nicolás Sánchez Leguizamón"}]


def test_rf11_sin_urls_del_proyecto(pyproject):
    assert "urls" not in pyproject["project"]


def test_rf11_requires_python_y_clasificadores_solo_de_lo_probado(pyproject):
    proyecto = pyproject["project"]
    assert proyecto["requires-python"] == ">=3.14"
    clasificadores = proyecto["classifiers"]
    assert "Programming Language :: Python :: 3.14" in clasificadores
    otras_versiones = [c for c in clasificadores if re.match(r"Programming Language :: Python :: 3\.\d+$", c)]
    assert otras_versiones == ["Programming Language :: Python :: 3.14"]
    assert not any(c.startswith("Operating System ::") for c in clasificadores)  # solo se probó en Windows 11


def test_rf11_clasificadores_de_publico_y_tema(pyproject):
    clasificadores = pyproject["project"]["classifiers"]
    assert "Intended Audience :: Science/Research" in clasificadores
    assert "Natural Language :: Spanish" in clasificadores
    assert "Topic :: Scientific/Engineering :: GIS" in clasificadores


def test_rf11_palabras_clave(pyproject):
    claves = pyproject["project"]["keywords"]
    assert len(claves) >= 4 and "kiwi" in claves


def test_rf11_dependencias_con_los_pisos_probados(pyproject):
    esperadas = {f"{nombre}>={mayor}.{menor}" for nombre, (mayor, menor) in PISOS.items()}
    assert set(pyproject["project"]["dependencies"]) == esperadas


def test_rf11_las_versiones_instaladas_cumplen_los_pisos_declarados():
    for nombre, (mayor, menor) in PISOS.items():
        instalada = tuple(int(x) for x in version_instalada(nombre).split(".")[:2])
        assert instalada >= (mayor, menor), f"{nombre} {instalada} está por debajo del piso declarado {mayor}.{menor}"


def test_rf11_extra_dev_con_pytest_y_build(pyproject):
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(d.startswith("pytest") for d in dev) and any(d.startswith("build") for d in dev)
    assert "setuptools>=77" in dev  # la construcción de los tests no usa un entorno aislado


def test_rf11_construccion_con_setuptools_reciente_y_punto_de_entrada(pyproject):
    sistema = pyproject["build-system"]
    assert sistema["build-backend"] == "setuptools.build_meta"
    assert sistema["requires"] == ["setuptools>=77"]
    assert pyproject["project"]["scripts"] == {"kiwitracking": "kiwitracking.cli:main"}
    assert pyproject["tool"]["setuptools"]["packages"] == ["kiwitracking"]


# --- T6.3: dependencias declaradas contra imports (RF-16) ---------------------------------------------------------

import ast  # noqa: E402
import sys  # noqa: E402


def _modulos_de_terceros_importados():
    """Los módulos de nivel superior que importa el paquete, sin la biblioteca estándar ni el propio paquete."""
    modulos = set()
    for archivo in sorted((RAIZ / "kiwitracking").glob("*.py")):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                modulos |= {alias.name.split(".")[0] for alias in nodo.names}
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                modulos.add(nodo.module.split(".")[0])
    return {m for m in modulos if m not in sys.stdlib_module_names and m != "kiwitracking"}


def _nombres_de_dependencias(pyproject):
    return {re.split(r"[<>=!~ ]", dependencia, maxsplit=1)[0] for dependencia in pyproject["project"]["dependencies"]}


def test_rf16_cada_modulo_de_terceros_que_importa_el_paquete_esta_declarado(pyproject):
    sin_declarar = _modulos_de_terceros_importados() - _nombres_de_dependencias(pyproject)
    assert not sin_declarar, f"el paquete importa {sorted(sin_declarar)} y pyproject.toml no los declara"


def test_rf16_cada_dependencia_declarada_se_usa(pyproject):
    sin_usar = _nombres_de_dependencias(pyproject) - _modulos_de_terceros_importados()
    assert not sin_usar, f"pyproject.toml declara {sorted(sin_usar)} y el paquete no los importa"


def test_rf16_el_conjunto_es_exactamente_el_esperado(pyproject):
    esperado = {"folium", "numpy", "pandas", "pyproj", "scipy", "shapely"}
    assert _modulos_de_terceros_importados() == esperado == _nombres_de_dependencias(pyproject)


def test_rf16_pytest_y_build_son_solo_de_desarrollo(pyproject):
    assert not {"pytest", "build", "setuptools"} & _modulos_de_terceros_importados()
    assert not {"pytest", "build", "setuptools"} & _nombres_de_dependencias(pyproject)
