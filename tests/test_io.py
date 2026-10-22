import pandas as pd
import pytest

from kiwitracking.io import leer_csv
from kiwitracking.resultado import ErrorDeEntrada

CONTENIDO = "temporada,estado_frio\n2019,Adecuado\n2021,Óptimo\n"


def _escribir(ruta, texto, codificacion):
    ruta.write_bytes(texto.encode(codificacion))
    return ruta


def test_rf3_lee_un_csv_utf8_con_tildes(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "utf-8")

    tabla = leer_csv(ruta)

    assert list(tabla.columns) == ["temporada", "estado_frio"]
    assert tabla["estado_frio"].tolist() == ["Adecuado", "Óptimo"]


def test_rf3_lee_un_csv_solo_ascii(tmp_path):
    ruta = _escribir(tmp_path / "plantas.csv", "id,KVPI_mean\n1,0.5\n2,0.6\n", "utf-8")

    tabla = leer_csv(ruta)

    assert tabla["KVPI_mean"].tolist() == [0.5, 0.6]


def test_rf3_un_csv_en_windows_1252_con_tildes_da_error_que_menciona_utf8(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "cp1252")

    with pytest.raises(ErrorDeEntrada, match="UTF-8"):
        leer_csv(ruta)


def test_rf3_el_error_de_codificacion_nombra_el_archivo(tmp_path):
    ruta = _escribir(tmp_path / "frio_roto.csv", CONTENIDO, "cp1252")

    with pytest.raises(ErrorDeEntrada, match="frio_roto.csv"):
        leer_csv(ruta)


def test_rf3_un_csv_utf8_con_bom_de_excel_no_contamina_el_nombre_de_la_primera_columna(tmp_path):
    ruta = _escribir(tmp_path / "bom.csv", "﻿" + CONTENIDO, "utf-8")

    tabla = leer_csv(ruta)

    assert list(tabla.columns) == ["temporada", "estado_frio"]


def test_rf3_un_archivo_inexistente_sigue_siendo_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        leer_csv(tmp_path / "no_existe.csv")


def test_rf3_devuelve_un_dataframe(tmp_path):
    ruta = _escribir(tmp_path / "frio.csv", CONTENIDO, "utf-8")

    assert isinstance(leer_csv(ruta), pd.DataFrame)



# --- T18: texto corrupto en columnas de categorías --------------------------------------


def _csv_utf8(tmp_path, texto, nombre="datos.csv"):
    return _escribir(tmp_path / nombre, texto, "utf-8")


def test_rf4_texto_corrupto_en_una_columna_de_categorias_da_error_que_nombra_columna_y_valor(tmp_path):
    ruta = _csv_utf8(tmp_path, "temporada,estado_frio\n2021,Ã“ptimo\n")

    with pytest.raises(ErrorDeEntrada) as error:
        leer_csv(ruta)

    assert "estado_frio" in str(error.value)
    assert "Ã“ptimo" in str(error.value)


@pytest.mark.parametrize("corrupto", ["Ã“ptimo", "Â°C", "â€œcomillasâ€"])
def test_rf4_detecta_las_tres_secuencias_tipicas(tmp_path, corrupto):
    ruta = _csv_utf8(tmp_path, f"id,ambiente\n1,{corrupto}\n")

    with pytest.raises(ErrorDeEntrada, match="ambiente"):
        leer_csv(ruta)


@pytest.mark.parametrize("columna", ["ambiente", "recomendacion", "estado_frio", "estado_frio_ultima_campana"])
def test_rf4_revisa_las_cuatro_columnas_de_categorias(tmp_path, columna):
    ruta = _csv_utf8(tmp_path, f"id,{columna}\n1,Ã“ptimo\n")

    with pytest.raises(ErrorDeEntrada, match=columna):
        leer_csv(ruta)


def test_rf4_el_mismo_texto_en_otra_columna_no_da_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,comentario\n1,Ã“ptimo\n")

    tabla = leer_csv(ruta)

    assert tabla["comentario"].tolist() == ["Ã“ptimo"]


def test_rf4_categorias_bien_escritas_con_tildes_no_dan_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "temporada,estado_frio\n2019,Adecuado\n2021,Óptimo\n2018,Deficiente\n")

    tabla = leer_csv(ruta)

    assert tabla["estado_frio"].tolist() == ["Adecuado", "Óptimo", "Deficiente"]


def test_rf4_los_valores_vacios_en_una_columna_de_categorias_no_dan_error(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,recomendacion\n1,Mantener\n2,\n")

    tabla = leer_csv(ruta)

    assert len(tabla) == 2


def test_rf4_el_error_nombra_el_archivo(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,ambiente\n1,Ã“ptimo\n", nombre="resultados.csv")

    with pytest.raises(ErrorDeEntrada, match="resultados.csv"):
        leer_csv(ruta)


def test_rf4_un_archivo_sin_columnas_de_categorias_no_se_revisa(tmp_path):
    ruta = _csv_utf8(tmp_path, "id,KVPI_mean\n1,0.5\n")

    assert len(leer_csv(ruta)) == 1
