import re

import pandas as pd

from kiwitracking.huella import huella


def _tabla(ids, bajo_malla, kvpi=None):
    return pd.DataFrame(
        {
            "id": ids,
            "KVPI_mean": kvpi if kvpi is not None else [0.5] * len(ids),
            "KVPI_std": [0.03] * len(ids),
            "bajo_malla": bajo_malla,
        }
    )


def test_rf16_la_huella_es_un_texto_hexadecimal_de_12_caracteres():
    resultado = huella(_tabla([1, 2, 3], [0, 1, 1]))

    assert isinstance(resultado, str)
    assert re.fullmatch(r"[0-9a-f]{12}", resultado)


def test_rf16_es_determinista():
    tabla = _tabla([1, 2, 3], [0, 1, 1])

    assert huella(tabla) == huella(tabla.copy())


def test_rf16_no_depende_del_orden_de_las_filas():
    original = _tabla([1, 2, 3, 4], [0, 1, 1, 0])
    desordenada = original.iloc[[3, 1, 0, 2]].reset_index(drop=True)

    assert huella(original) == huella(desordenada)


def test_rf16_cambia_si_se_agrega_una_planta_bajo_malla():
    antes = _tabla([1, 2, 3], [0, 1, 0])
    despues = _tabla([1, 2, 3], [0, 1, 1])

    assert huella(antes) != huella(despues)


def test_rf16_cambia_si_se_quita_una_planta_bajo_malla():
    antes = _tabla([1, 2, 3], [0, 1, 1])
    despues = _tabla([1, 2, 3], [0, 1, 0])

    assert huella(antes) != huella(despues)


def test_rf16_cambia_si_se_reemplaza_una_planta_bajo_malla_por_otra_del_mismo_numero():
    antes = _tabla([1, 2, 3], [1, 0, 0])
    despues = _tabla([1, 2, 3], [0, 1, 0])

    assert huella(antes) != huella(despues)


def test_rf16_no_cambia_si_cambia_el_kvpi_pero_no_el_conjunto_bajo_malla():
    antes = _tabla([1, 2, 3], [0, 1, 1], kvpi=[0.50, 0.40, 0.41])
    despues = _tabla([1, 2, 3], [0, 1, 1], kvpi=[0.60, 0.45, 0.47])

    assert huella(antes) == huella(despues)


def test_rf16_no_cambia_por_las_plantas_fuera_de_malla():
    # Las plantas a cielo abierto no forman parte del conjunto que se confirma.
    antes = _tabla([1, 2, 3], [0, 1, 1])
    despues = _tabla([1, 2, 3, 4, 5], [0, 1, 1, 0, 0])

    assert huella(antes) == huella(despues)


def test_rf16_funciona_sin_plantas_bajo_malla_y_es_estable():
    sin_malla = _tabla([1, 2], [0, 0])

    assert huella(sin_malla) == huella(_tabla([7, 8, 9], [0, 0, 0]))
    assert huella(sin_malla) != huella(_tabla([1, 2], [1, 0]))


def test_rf16_no_modifica_la_tabla_de_entrada():
    tabla = _tabla([3, 1, 2], [1, 0, 1])
    copia = tabla.copy()

    huella(tabla)

    pd.testing.assert_frame_equal(tabla, copia)
