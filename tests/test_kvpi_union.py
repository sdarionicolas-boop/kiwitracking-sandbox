"""T4.5: unión del resultado por planta con el muestreo (RF-13 y RF-14 de la spec 004)."""

import numpy as np
import pandas as pd
import pytest

from kiwitracking.kvpi import unir_con_muestreo
from kiwitracking.resultado import ErrorDeEntrada

COLUMNAS_RESULTADO = ["id", "KVPI_mean", "KVPI_std", "KVPI_cv", "n_campanas"]


def _por_planta(ids, n=3):
    """Resultado de `agregar_kvpi` armado a mano: los `id` salen como texto y ordenados."""
    ids = sorted(str(i) for i in ids)
    return pd.DataFrame(
        {
            "id": ids,
            "n_campanas": [n] * len(ids),
            "KVPI_mean": [0.1 * (k + 1) for k in range(len(ids))],
            "KVPI_std": [0.01 * (k + 1) for k in range(len(ids))],
            "KVPI_cv": [0.1] * len(ids),
        }
    )


def _muestreo(ids, **extra):
    datos = {"id": ids, "X": [float(i) * 10 for i in range(len(ids))], "Y": [float(i) * -10 for i in range(len(ids))]}
    datos.update(extra)
    return pd.DataFrame(datos)


def _codigos(avisos):
    return [a.codigo for a in avisos]


def _aviso(avisos, codigo):
    return next(a for a in avisos if a.codigo == codigo).mensaje


def test_rf13_columnas_en_el_orden_pedido_y_despues_las_del_muestreo():
    muestreo = _muestreo([1, 2, 3], row_index=[0, 1, 2], col_index=[5, 6, 7])
    tabla, _ = unir_con_muestreo(_por_planta([1, 2, 3]), muestreo)
    assert list(tabla.columns) == COLUMNAS_RESULTADO + ["X", "Y", "row_index", "col_index"]


def test_rf13_las_filas_salen_en_el_orden_del_muestreo():
    tabla, _ = unir_con_muestreo(_por_planta([1, 2, 3]), _muestreo([3, 1, 2]))
    assert list(tabla["id"]) == ["3", "1", "2"]


def test_rf13_cada_planta_recibe_sus_propios_valores():
    por_planta = _por_planta([1, 2, 3])
    tabla, _ = unir_con_muestreo(por_planta, _muestreo([3, 1, 2]))
    esperado = por_planta.set_index("id").loc[["3", "1", "2"]]
    assert list(tabla["KVPI_mean"]) == list(esperado["KVPI_mean"])
    assert list(tabla["n_campanas"]) == list(esperado["n_campanas"])


def test_rf13_las_coordenadas_siguen_a_su_planta():
    muestreo = pd.DataFrame({"id": [7, 5], "X": [70.0, 50.0], "Y": [-7.0, -5.0]})
    tabla, _ = unir_con_muestreo(_por_planta([5, 7]), muestreo)
    assert tabla.set_index("id").loc["5", ["X", "Y"]].tolist() == [50.0, -5.0]


def test_rf13_los_id_numericos_del_muestreo_coinciden_con_los_id_de_la_serie():
    tabla, avisos = unir_con_muestreo(_por_planta([4, 26]), _muestreo([4, 26]))
    assert list(tabla["id"]) == ["4", "26"]
    assert avisos == []


def test_rf13_los_espacios_alrededor_del_id_del_muestreo_no_importan():
    tabla, _ = unir_con_muestreo(_por_planta([4, 26]), _muestreo([" 4", "26 "]))
    assert list(tabla["id"]) == ["4", "26"]


def test_rf13_n_campanas_sigue_siendo_entero():
    tabla, _ = unir_con_muestreo(_por_planta([1, 2]), _muestreo([1, 2]))
    assert pd.api.types.is_integer_dtype(tabla["n_campanas"])


def test_rf13_una_planta_sin_ninguna_campana_con_dato_se_conserva_con_promedio_vacio():
    por_planta = _por_planta([1, 2])
    por_planta.loc[1, ["KVPI_mean", "KVPI_std", "KVPI_cv"]] = np.nan
    por_planta.loc[1, "n_campanas"] = 0
    tabla, _ = unir_con_muestreo(por_planta, _muestreo([1, 2]))
    assert len(tabla) == 2
    assert np.isnan(tabla.loc[1, "KVPI_mean"])


def test_rf13_planta_de_la_serie_que_no_esta_en_el_muestreo_queda_fuera_y_avisa_sin_coordenadas():
    tabla, avisos = unir_con_muestreo(_por_planta([1, 2, 3]), _muestreo([1, 2]))
    assert list(tabla["id"]) == ["1", "2"]
    assert _codigos(avisos) == ["PLANTAS_SIN_COORDENADAS"]
    assert "1 planta " in _aviso(avisos, "PLANTAS_SIN_COORDENADAS")
    assert "3" in _aviso(avisos, "PLANTAS_SIN_COORDENADAS")


def test_rf13_x_o_y_vacias_cuentan_como_sin_coordenadas():
    muestreo = pd.DataFrame({"id": [1, 2, 3], "X": [1.0, np.nan, 3.0], "Y": [1.0, 2.0, np.nan]})
    tabla, avisos = unir_con_muestreo(_por_planta([1, 2, 3]), muestreo)
    assert list(tabla["id"]) == ["1"]
    mensaje = _aviso(avisos, "PLANTAS_SIN_COORDENADAS")
    assert "2 plantas" in mensaje and "2" in mensaje and "3" in mensaje


def test_rf13_planta_del_muestreo_sin_serie_queda_fuera_y_avisa_con_la_huella():
    tabla, avisos = unir_con_muestreo(_por_planta([1, 2]), _muestreo([1, 2, 3, 4]))
    assert list(tabla["id"]) == ["1", "2"]
    assert _codigos(avisos) == ["PLANTAS_SIN_SERIE"]
    mensaje = _aviso(avisos, "PLANTAS_SIN_SERIE")
    assert "2 plantas" in mensaje and "3, 4" in mensaje
    assert "huella" in mensaje


def test_rf13_el_aviso_sin_serie_nombra_hasta_10_id_y_cuantos_mas_hay():
    muestreo = _muestreo(list(range(100, 113)) + [1])
    mensaje = _aviso(unir_con_muestreo(_por_planta([1]), muestreo)[1], "PLANTAS_SIN_SERIE")
    assert "13 plantas" in mensaje
    assert "100, 101, 102, 103, 104, 105, 106, 107, 108, 109" in mensaje
    assert "110" not in mensaje
    assert "3 más" in mensaje


def test_rf13_con_exactamente_10_no_dice_cuantos_mas_hay():
    muestreo = _muestreo(list(range(100, 110)) + [1])
    assert "más" not in _aviso(unir_con_muestreo(_por_planta([1]), muestreo)[1], "PLANTAS_SIN_SERIE")


def test_rf13_el_aviso_sin_coordenadas_nombra_hasta_10_id_y_cuantos_mas_hay():
    avisos = unir_con_muestreo(_por_planta(list(range(100, 113)) + [1]), _muestreo([1]))[1]
    mensaje = _aviso(avisos, "PLANTAS_SIN_COORDENADAS")
    assert "13 plantas" in mensaje and "3 más" in mensaje


def test_rf13_ninguna_planta_en_comun_es_un_error():
    with pytest.raises(ErrorDeEntrada, match="Ninguna planta"):
        unir_con_muestreo(_por_planta([1, 2]), _muestreo([8, 9]))


def test_rf13_si_solo_quedan_plantas_sin_coordenadas_tambien_es_error():
    muestreo = pd.DataFrame({"id": [1], "X": [np.nan], "Y": [1.0]})
    with pytest.raises(ErrorDeEntrada, match="Ninguna planta"):
        unir_con_muestreo(_por_planta([1]), muestreo)


def test_rf13_las_columnas_del_muestreo_con_nombre_de_resultado_se_reemplazan():
    muestreo = _muestreo([1, 2], KVPI_mean=[9.9, 9.9], n_campanas=[0, 0])
    por_planta = _por_planta([1, 2])
    tabla, _ = unir_con_muestreo(por_planta, muestreo)
    assert list(tabla.columns).count("KVPI_mean") == 1
    assert list(tabla["KVPI_mean"]) == list(por_planta["KVPI_mean"])
    assert list(tabla["n_campanas"]) == [3, 3]


def test_rf13_las_advertencias_salen_en_orden_duplicados_sin_coordenadas_sin_serie():
    muestreo = pd.concat([_muestreo([1, 2, 9]), _muestreo([1])], ignore_index=True)
    avisos = unir_con_muestreo(_por_planta([1, 2, 3]), muestreo)[1]
    assert _codigos(avisos) == ["MUESTREO_DUPLICADO", "PLANTAS_SIN_COORDENADAS", "PLANTAS_SIN_SERIE"]


@pytest.mark.parametrize("columna", ["id", "X", "Y"])
def test_rf14_falta_una_columna_obligatoria_y_la_nombra(columna):
    muestreo = _muestreo([1, 2]).drop(columns=columna)
    with pytest.raises(ErrorDeEntrada, match=columna):
        unir_con_muestreo(_por_planta([1, 2]), muestreo)


def test_rf14_faltan_varias_columnas_las_nombra_todas():
    with pytest.raises(ErrorDeEntrada) as error:
        unir_con_muestreo(_por_planta([1]), pd.DataFrame({"z": [1]}))
    assert all(nombre in str(error.value) for nombre in ("id", "X", "Y"))


def test_rf14_muestreo_vacio_es_un_error():
    with pytest.raises(ErrorDeEntrada, match="vacío"):
        unir_con_muestreo(_por_planta([1]), pd.DataFrame(columns=["id", "X", "Y"]))


def test_rf14_id_vacio_en_el_muestreo_es_un_error_con_la_cantidad():
    muestreo = pd.DataFrame({"id": [1, None, "  "], "X": [1.0, 2.0, 3.0], "Y": [1.0, 2.0, 3.0]})
    with pytest.raises(ErrorDeEntrada, match="2 filas"):
        unir_con_muestreo(_por_planta([1]), muestreo)


@pytest.mark.parametrize("columna", ["X", "Y"])
def test_rf14_coordenada_con_texto_es_un_error_que_nombra_la_columna(columna):
    muestreo = _muestreo([1, 2])
    muestreo[columna] = ["10.5", "norte"]
    with pytest.raises(ErrorDeEntrada, match=columna):
        unir_con_muestreo(_por_planta([1, 2]), muestreo)


def test_rf14_coordenadas_como_texto_numerico_se_convierten():
    muestreo = _muestreo([1, 2])
    muestreo["X"] = ["10.5", "20"]
    tabla, _ = unir_con_muestreo(_por_planta([1, 2]), muestreo)
    assert list(tabla["X"]) == [10.5, 20.0]


def test_rf14_id_repetido_con_todos_los_valores_iguales_se_conserva_uno_y_avisa():
    muestreo = pd.concat([_muestreo([1, 2]), _muestreo([1])], ignore_index=True)
    tabla, avisos = unir_con_muestreo(_por_planta([1, 2]), muestreo)
    assert list(tabla["id"]) == ["1", "2"]
    assert _codigos(avisos) == ["MUESTREO_DUPLICADO"]
    assert "1 fila" in _aviso(avisos, "MUESTREO_DUPLICADO")


def test_rf14_repetidos_iguales_con_vacios_en_otra_columna_tambien_se_unifican():
    muestreo = pd.DataFrame({"id": [1, 1], "X": [1.0, 1.0], "Y": [2.0, 2.0], "nota": [np.nan, np.nan]})
    tabla, avisos = unir_con_muestreo(_por_planta([1]), muestreo)
    assert len(tabla) == 1
    assert _codigos(avisos) == ["MUESTREO_DUPLICADO"]


def test_rf14_id_repetido_con_valores_distintos_es_un_error_que_lo_nombra():
    muestreo = pd.DataFrame({"id": [1, 1, 2], "X": [1.0, 5.0, 3.0], "Y": [1.0, 1.0, 3.0]})
    with pytest.raises(ErrorDeEntrada, match="distintos") as error:
        unir_con_muestreo(_por_planta([1, 2]), muestreo)
    assert "1" in str(error.value)


def test_rf14_el_error_de_repetidos_nombra_hasta_10_id_y_cuantos_mas_hay():
    ids = list(range(100, 113))
    muestreo = pd.DataFrame({"id": ids + ids, "X": [1.0] * 13 + [2.0] * 13, "Y": [0.0] * 26})
    with pytest.raises(ErrorDeEntrada) as error:
        unir_con_muestreo(_por_planta([100]), muestreo)
    texto = str(error.value)
    assert "13" in texto and "3 más" in texto
    assert "109" in texto and "110" not in texto


def test_rf14_con_exactamente_10_id_en_conflicto_no_dice_cuantos_mas_hay():
    ids = list(range(100, 110))
    muestreo = pd.DataFrame({"id": ids + ids, "X": [1.0] * 10 + [2.0] * 10, "Y": [0.0] * 20})
    with pytest.raises(ErrorDeEntrada) as error:
        unir_con_muestreo(_por_planta([100]), muestreo)
    assert "más" not in str(error.value)


def test_no_modifica_las_tablas_de_entrada():
    por_planta = _por_planta([1, 2, 3])
    muestreo = pd.DataFrame(
        {"id": [1, 2, 2, 9], "X": [1.0, 2.0, 2.0, 9.0], "Y": [1.0, 2.0, 2.0, 9.0], "nota": ["a", "b", "b", "c"]}
    )
    por_planta_copia, muestreo_copia = por_planta.copy(), muestreo.copy()
    unir_con_muestreo(por_planta, muestreo)
    pd.testing.assert_frame_equal(por_planta, por_planta_copia)
    pd.testing.assert_frame_equal(muestreo, muestreo_copia)
