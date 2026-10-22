import dataclasses

import pandas as pd
import pytest

from kiwitracking.resultado import Advertencia, ErrorDeEntrada, Resultado, Resumen


def test_rf26_resultado_guarda_tabla_resumen_y_advertencias():
    tabla = pd.DataFrame({"id": [1, 2]})
    advertencia = Advertencia(codigo="FALTA_CONFIRMACION", mensaje="Falta la validación visual.")
    resumen = Resumen(fc=1.2, p_valor=0.01, n_bajo_malla=3, n_fuera_malla=5, correccion_aplicada=True)

    resultado = Resultado(tabla=tabla, resumen=resumen, advertencias=[advertencia])

    assert resultado.tabla is tabla
    assert resultado.resumen.fc == 1.2
    assert resultado.resumen.correccion_aplicada is True
    assert resultado.advertencias[0].codigo == "FALTA_CONFIRMACION"
    assert resultado.advertencias[0].mensaje == "Falta la validación visual."


def test_rf26_resumen_tiene_los_campos_del_plan_con_valores_vacios_por_defecto():
    resumen = Resumen()

    campos = {campo.name for campo in dataclasses.fields(resumen)}
    assert campos == {
        "fc", "p_valor", "n_bajo_malla", "n_fuera_malla", "correccion_aplicada",
        "p33", "p66", "p75_estabilidad", "huella", "escalar_std", "prueba_t",
    }
    assert resumen.correccion_aplicada is False
    assert resumen.escalar_std is False
    assert resumen.prueba_t == "welch"
    assert resumen.fc is None


def test_rf26_las_advertencias_por_defecto_no_se_comparten_entre_resultados():
    primero = Resultado(tabla=pd.DataFrame(), resumen=Resumen())
    segundo = Resultado(tabla=pd.DataFrame(), resumen=Resumen())

    primero.advertencias.append(Advertencia("STD_CERO", "x"))

    assert segundo.advertencias == []


def test_rf26_advertencia_es_inmutable():
    advertencia = Advertencia("STD_CERO", "x")

    with pytest.raises(dataclasses.FrozenInstanceError):
        advertencia.codigo = "OTRO"


def test_error_de_entrada_es_un_value_error():
    assert issubclass(ErrorDeEntrada, ValueError)
    with pytest.raises(ValueError, match="falta la columna"):
        raise ErrorDeEntrada("falta la columna KVPI_std")
