"""T4.7: escritura del CSV de plantas con KVPI (RF-16 y RF-19 de la spec 004)."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kiwitracking.resultado import ErrorDeEntrada
from kiwitracking.salida import escribir_plantas_kvpi

TABLA = pd.DataFrame(
    {
        "id": ["26", "4"],
        "KVPI_mean": [0.1 + 0.2, 0.123456789012345678],
        "KVPI_std": [np.nan, 0.031448249074820744],
        "KVPI_cv": [np.nan, 0.1],
        "n_campanas": [1, 6],
        "X": [-57.8939641537422, -57.89359036835818],
        "Y": [-38.2120094009993, -38.21168215635629],
        "nota": ["añejo", "ñandú"],
    }
)


def test_rf16_escribe_el_archivo_y_devuelve_su_ruta(tmp_path):
    destino = tmp_path / "plantas_kvpi.csv"
    assert escribir_plantas_kvpi(destino, TABLA) == destino
    assert destino.is_file()


def test_rf16_utf8_sin_bom(tmp_path):
    destino = tmp_path / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    crudo = destino.read_bytes()
    assert not crudo.startswith(b"\xef\xbb\xbf")
    assert "añejo" in crudo.decode("utf-8") and "ñandú" in crudo.decode("utf-8")


def test_rf16_salto_de_linea_lf_aunque_el_sistema_use_otro(tmp_path):
    destino = tmp_path / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    crudo = destino.read_bytes()
    assert b"\r" not in crudo
    assert crudo.count(b"\n") == 3  # encabezado y dos filas
    assert crudo.endswith(b"\n")


def test_rf16_los_numeros_salen_completos_sin_redondear(tmp_path):
    destino = tmp_path / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    leida = pd.read_csv(destino, dtype={"id": str}, float_precision="round_trip")
    assert leida["KVPI_mean"].tolist() == TABLA["KVPI_mean"].tolist()
    assert leida["X"].tolist() == TABLA["X"].tolist()
    assert "0.30000000000000004" in destino.read_text(encoding="utf-8")


def test_rf16_los_vacios_salen_como_celdas_vacias(tmp_path):
    destino = tmp_path / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    primera_fila = destino.read_text(encoding="utf-8").splitlines()[1]
    campos = primera_fila.split(",")
    assert campos[2] == "" and campos[3] == ""
    assert "nan" not in destino.read_text(encoding="utf-8").lower()


def test_rf16_columnas_y_filas_tal_cual_vienen_en_la_tabla(tmp_path):
    destino = tmp_path / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    encabezado = destino.read_text(encoding="utf-8").splitlines()[0]
    assert encabezado == "id,KVPI_mean,KVPI_std,KVPI_cv,n_campanas,X,Y,nota"
    assert pd.read_csv(destino, dtype={"id": str})["id"].tolist() == ["26", "4"]


def test_rf16_crea_la_carpeta_si_no_existe(tmp_path):
    destino = tmp_path / "a" / "b" / "salida.csv"
    escribir_plantas_kvpi(destino, TABLA)
    assert destino.is_file()


def test_rf16_rutas_con_espacios_y_tildes(tmp_path):
    destino = tmp_path / "carpeta con espacio" / "resultados ñandú.csv"
    escribir_plantas_kvpi(destino, TABLA)
    assert destino.is_file()


def test_rf16_si_ya_existe_y_no_se_indico_sobrescribir_da_error_sin_tocarlo(tmp_path):
    destino = tmp_path / "salida.csv"
    destino.write_bytes(b"anterior\n")
    with pytest.raises(ErrorDeEntrada, match="salida.csv") as error:
        escribir_plantas_kvpi(destino, TABLA)
    assert "--sobrescribir" in str(error.value)
    assert destino.read_bytes() == b"anterior\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["salida.csv"]


def test_rf16_con_sobrescribir_reemplaza_el_archivo(tmp_path):
    destino = tmp_path / "salida.csv"
    destino.write_bytes(b"anterior\n")
    escribir_plantas_kvpi(destino, TABLA, sobrescribir=True)
    assert destino.read_text(encoding="utf-8").startswith("id,KVPI_mean")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["salida.csv"]


def test_rf16_si_la_salida_es_una_carpeta_da_error(tmp_path):
    with pytest.raises(ErrorDeEntrada, match="carpeta"):
        escribir_plantas_kvpi(tmp_path, TABLA, sobrescribir=True)


def test_rf16_sin_fallos_no_quedan_archivos_temporales(tmp_path):
    escribir_plantas_kvpi(tmp_path / "salida.csv", TABLA)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["salida.csv"]


def _fallar(*_argumentos, **_nombrados):
    raise OSError(28, "No space left on device")


def test_rf16_si_falla_la_escritura_no_queda_un_archivo_a_medio_escribir(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "write_bytes", _fallar)
    destino = tmp_path / "salida.csv"
    with pytest.raises(ErrorDeEntrada, match="salida.csv") as error:
        escribir_plantas_kvpi(destino, TABLA)
    assert "No space left" in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_rf16_si_falla_al_reemplazar_el_archivo_anterior_queda_intacto(tmp_path, monkeypatch):
    destino = tmp_path / "salida.csv"
    destino.write_bytes(b"anterior\n")
    monkeypatch.setattr(os, "replace", _fallar)
    with pytest.raises(ErrorDeEntrada, match="salida.csv"):
        escribir_plantas_kvpi(destino, TABLA, sobrescribir=True)
    assert destino.read_bytes() == b"anterior\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["salida.csv"]


def test_rf16_si_falla_la_escritura_se_borra_la_carpeta_que_se_creo(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "write_bytes", _fallar)
    with pytest.raises(ErrorDeEntrada):
        escribir_plantas_kvpi(tmp_path / "nueva" / "salida.csv", TABLA)
    assert list(tmp_path.iterdir()) == []


def test_rf16_si_falla_la_escritura_no_se_borra_una_carpeta_que_ya_existia(tmp_path, monkeypatch):
    (tmp_path / "ya_estaba").mkdir()
    (tmp_path / "ya_estaba" / "otro.txt").write_text("x")
    monkeypatch.setattr(Path, "write_bytes", _fallar)
    with pytest.raises(ErrorDeEntrada):
        escribir_plantas_kvpi(tmp_path / "ya_estaba" / "salida.csv", TABLA)
    assert [p.name for p in (tmp_path / "ya_estaba").iterdir()] == ["otro.txt"]


def test_rf19_no_modifica_la_tabla_de_entrada(tmp_path):
    copia = TABLA.copy()
    escribir_plantas_kvpi(tmp_path / "salida.csv", TABLA)
    pd.testing.assert_frame_equal(TABLA, copia)
