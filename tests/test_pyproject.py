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
