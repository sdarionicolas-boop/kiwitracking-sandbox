"""Contenido de los archivos de resultados de `analizar` (spec 003): tabla por planta, resumen y advertencias.

Cada función devuelve el texto del archivo; escribirlo en disco (con limpieza si algo falla) es otra tarea.
"""

import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from kiwitracking.flujo import ResultadoFlujo
from kiwitracking.resultado import Advertencia, ErrorDeEntrada

# Columnas que van primero y en este orden (RF-27); las demás de entrada siguen en su orden original.
ORDEN_CONOCIDO = (
    "id", "KVPI_mean", "KVPI_corregido", "KVPI_std", "estabilidad", "ambiente", "recomendacion", "bajo_malla",
)
ARCHIVOS_DE_RESULTADOS = ("plantas.csv", "resumen.json", "advertencias.json")
CAMPOS_DEL_RESUMEN = (
    "fc", "p_valor", "n_bajo_malla", "n_fuera_malla", "correccion_aplicada", "p33", "p66", "p75_estabilidad",
    "escalar_std", "prueba_t",
)


def tabla_de_plantas(tabla: pd.DataFrame) -> pd.DataFrame:
    """La tabla por planta con las columnas conocidas primero y las demás después, sin cambiar las filas (RF-27)."""
    conocidas = [columna for columna in ORDEN_CONOCIDO if columna in tabla.columns]
    otras = [columna for columna in tabla.columns if columna not in ORDEN_CONOCIDO]
    return tabla[conocidas + otras]


def plantas_csv(tabla: pd.DataFrame) -> str:
    """El texto de `plantas.csv`: números completos, celdas vacías para los valores vacíos y saltos de línea LF (RF-16)."""
    return tabla_de_plantas(tabla).to_csv(index=False, lineterminator="\n")


def _a_json(valor):
    """Valores comunes de Python y `None` para lo vacío, `NaN` e infinito: lo que un lector JSON estricto acepta (RF-25)."""
    if isinstance(valor, dict):
        return {str(clave): _a_json(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_a_json(contenido) for contenido in valor]
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    if isinstance(valor, (int, np.integer)):
        return int(valor)
    if isinstance(valor, (float, np.floating)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None
    return valor


def _texto_json(documento) -> str:
    return json.dumps(_a_json(documento), indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def resumen_json(flujo: ResultadoFlujo) -> str:
    """El texto de `resumen.json`, con la estructura de RF-25."""
    resumen = flujo.resultado.resumen
    estado = flujo.estado_frio
    estado_frio = {"origen": estado.origen, "estado": estado.estado}
    if estado.origen == "clima":
        estado_frio.update(
            periodo=estado.periodo,
            horas=estado.horas,
            cobertura=estado.cobertura,
            hueco_maximo=estado.hueco_maximo,
            dias_estimados=estado.dias_estimados,
            proporcion_estimada=estado.proporcion_estimada,
        )
    return _texto_json(
        {
            "huella": resumen.huella,
            "resumen": {campo: getattr(resumen, campo) for campo in CAMPOS_DEL_RESUMEN},
            "parametros": flujo.parametros,
            "estado_frio": estado_frio,
        }
    )


def advertencias_json(advertencias: list[Advertencia]) -> str:
    """El texto de `advertencias.json`: una lista de objetos con `codigo` y `mensaje`, en el orden recibido."""
    return _texto_json([{"codigo": a.codigo, "mensaje": a.mensaje} for a in advertencias])


def escribir_resultados(carpeta, flujo: ResultadoFlujo, sobrescribir: bool = False) -> list[Path]:
    """Escribe los tres archivos de resultados en la carpeta y devuelve sus rutas (RF-17, RF-20).

    Todo el contenido se arma antes de tocar el disco, así que un error de datos no deja nada escrito. Si falla
    la escritura de un archivo (disco lleno, permisos, un archivo abierto en otro programa), se borran los que
    esta misma corrida ya había escrito (y la carpeta, si la creó ella) y se informa cuál falló y por qué. No hay
    garantía si el sistema se interrumpe durante la escritura. Con `sobrescribir`, los archivos anteriores se
    reemplazan recién cuando ya se calculó todo.
    """
    carpeta = Path(carpeta)
    if carpeta.exists() and not carpeta.is_dir():
        raise ErrorDeEntrada(f"{carpeta.name} es un archivo, no una carpeta: indicá una carpeta para --salida.")
    previos = [nombre for nombre in ARCHIVOS_DE_RESULTADOS if (carpeta / nombre).exists()]
    if previos and not sobrescribir:
        raise ErrorDeEntrada(
            f"La carpeta {carpeta.name} ya tiene resultados ({', '.join(previos)}): usá --sobrescribir para reemplazarlos."
        )

    contenidos = {
        "plantas.csv": plantas_csv(flujo.resultado.tabla),
        "resumen.json": resumen_json(flujo),
        "advertencias.json": advertencias_json(flujo.advertencias),
    }
    creada = not carpeta.exists()
    escritos: list[Path] = []
    nombre = ""
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, texto in contenidos.items():
            ruta = carpeta / nombre
            with open(ruta, "w", encoding="utf-8", newline="") as archivo:
                escritos.append(ruta)
                archivo.write(texto)
    except OSError as error:
        for ruta in escritos:
            ruta.unlink(missing_ok=True)
        if creada and carpeta.is_dir() and not any(carpeta.iterdir()):
            carpeta.rmdir()
        raise ErrorDeEntrada(f"No se pudo escribir {nombre or carpeta.name}: {error.strerror or error}.") from error
    return escritos


def escribir_plantas_kvpi(ruta, tabla: pd.DataFrame, sobrescribir: bool = False) -> Path:
    """Escribe el CSV del comando `kvpi` y devuelve su ruta (spec 004, RF-16 y RF-19).

    UTF-8 sin BOM, `\\n` como salto de línea, números completos y celdas vacías para los vacíos. Escribe primero un
    archivo temporal en la misma carpeta y lo mueve al destino recién cuando está completo, así que ante un error
    no queda un archivo a medio escribir y el archivo anterior (con `sobrescribir`) queda intacto. Crea la carpeta
    si no existe, y la borra si ella misma la creó y algo falla.
    """
    destino = Path(ruta)
    if destino.is_dir():
        raise ErrorDeEntrada(f"{destino.name} es una carpeta: indicá un archivo CSV para la salida.")
    if destino.exists() and not sobrescribir:
        raise ErrorDeEntrada(f"El archivo {destino.name} ya existe: usá --sobrescribir para reemplazarlo.")

    contenido = tabla.to_csv(index=False, lineterminator="\n").encode("utf-8")
    por_crear = [carpeta for carpeta in reversed(destino.parents) if not carpeta.exists()]
    temporal = None
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        descriptor, nombre = tempfile.mkstemp(dir=destino.parent, prefix=f".{destino.name}.", suffix=".tmp")
        os.close(descriptor)
        temporal = Path(nombre)
        temporal.write_bytes(contenido)
        os.replace(temporal, destino)
    except OSError as error:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
        for carpeta in reversed(por_crear):
            try:
                carpeta.rmdir()
            except OSError:
                break
        raise ErrorDeEntrada(f"No se pudo escribir {destino.name}: {error.strerror or error}.") from error
    return destino
