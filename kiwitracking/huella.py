"""Huella del conjunto de plantas bajo malla."""

import hashlib

import pandas as pd

LARGO_HUELLA = 12


def huella(tabla: pd.DataFrame) -> str:
    """Código determinista del conjunto de `id` con bajo_malla = 1.

    No depende del orden de las filas ni de los valores de KVPI. Ata una confirmación visual
    a las plantas marcadas bajo malla; no prueba que alguien haya mirado el mapa.
    """
    ids = sorted(str(identificador) for identificador in tabla.loc[tabla["bajo_malla"] == 1, "id"])
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return digest[:LARGO_HUELLA]
