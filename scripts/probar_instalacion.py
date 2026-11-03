"""Prueba la instalación de kiwitracking en un entorno limpio (spec 006, RF-14).

Qué hace, en orden:
1. Construye el `wheel` con `python -m build` (aislado: descarga `setuptools`), o usa el que se indique con `--wheel`.
2. Crea un entorno virtual nuevo.
3. Instala el `wheel` con sus dependencias (descarga pandas, scipy, shapely, pyproj, folium y numpy).
4. Desde una carpeta que no es la del código corre `kiwitracking --version`, `kiwitracking --help`,
   `python -m kiwitracking --help` y el ejemplo mínimo del `README.md`, con archivos armados a partir de `tests/golden/`.

Tarda más de un minuto y necesita internet. Termina con código 0 si todo anduvo y con 1 si algún paso falló, diciendo cuál.
Se corre desde el repositorio (necesita `README.md`, `pyproject.toml` y `tests/golden/`):

    python scripts/probar_instalacion.py
"""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HUELLA_DEL_LOTE_DE_REFERENCIA = "c4e55ae105c6"
TIEMPO_MAXIMO_POR_PASO = 900  # segundos


class FalloDeInstalacion(Exception):
    """Un paso de la prueba no anduvo; el mensaje dice cuál y por qué."""


def entorno_de_los_hijos() -> dict:
    """El entorno de los procesos hijos: sin la variable que desactiva el bytecode y con salida en UTF-8."""
    entorno = {clave: valor for clave, valor in os.environ.items() if clave != "PYTHONDONTWRITEBYTECODE"}
    entorno["PYTHONIOENCODING"] = "utf-8"
    return entorno


def version_del_proyecto() -> str:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def leer_ejemplo(readme: str) -> list[str]:
    """Los comandos del bloque marcado `<!-- prueba: ejemplo-minimo -->` del README."""
    coincidencia = re.search(r"<!-- prueba: ejemplo-minimo -->\s*```bash\n(.*?)```", readme, re.S)
    if not coincidencia:
        raise FalloDeInstalacion("el README no tiene el ejemplo mínimo en un bloque marcado `<!-- prueba: ejemplo-minimo -->`")
    return [linea.strip() for linea in coincidencia.group(1).splitlines() if linea.strip()]


def comprobar_version(salida: str, esperada: str) -> None:
    """`kiwitracking --version` tiene que imprimir `kiwitracking <versión del proyecto>`."""
    if salida.strip() != f"kiwitracking {esperada}":
        raise FalloDeInstalacion(f"`kiwitracking --version` imprimió {salida.strip()!r} y se esperaba 'kiwitracking {esperada}'")


def ejecutar(argumentos: list, cwd: Path | None, descripcion: str) -> str:
    """Corre un comando; si no termina con código 0, falla con lo que imprimió. Devuelve lo que imprimió en pantalla."""
    inicio = time.monotonic()
    try:
        proceso = subprocess.run(
            [str(a) for a in argumentos], cwd=cwd, env=entorno_de_los_hijos(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIEMPO_MAXIMO_POR_PASO,
        )  # fmt: skip
    except subprocess.TimeoutExpired as error:
        raise FalloDeInstalacion(f"{descripcion}: pasaron más de {TIEMPO_MAXIMO_POR_PASO} s sin terminar") from error
    if proceso.returncode != 0:
        cola = "\n".join((proceso.stdout + proceso.stderr).strip().splitlines()[-15:])
        raise FalloDeInstalacion(f"{descripcion} terminó con código {proceso.returncode}:\n{cola}")
    print(f"  ok  {descripcion} ({time.monotonic() - inicio:.1f} s)")
    return proceso.stdout


def construir(salida: Path) -> Path:
    """Construye el wheel (y el sdist) con la construcción aislada y devuelve la ruta del wheel."""
    shutil.rmtree(RAIZ / "kiwitracking.egg-info", ignore_errors=True)  # un SOURCES.txt viejo contamina el sdist
    ejecutar([sys.executable, "-m", "build", "--outdir", salida, RAIZ], None, "construir el wheel y el sdist (python -m build)")
    ruedas = sorted(salida.glob("*.whl"))
    if len(ruedas) != 1:
        raise FalloDeInstalacion(f"se esperaba un wheel en {salida} y hay {len(ruedas)}")
    return ruedas[0]


def _ejecutable(entorno: Path, nombre: str) -> Path:
    return entorno / ("Scripts" if os.name == "nt" else "bin") / (nombre + (".exe" if os.name == "nt" else ""))


def crear_entorno(carpeta: Path) -> Path:
    """Crea un entorno virtual nuevo y devuelve la ruta de su Python."""
    ejecutar([sys.executable, "-m", "venv", carpeta], None, "crear un entorno virtual nuevo")
    return _ejecutable(carpeta, "python")


def instalar(python: Path, wheel: Path) -> None:
    """Instala el wheel con sus dependencias (descarga de internet)."""
    ejecutar([python, "-m", "pip", "install", "--disable-pip-version-check", wheel], None, f"instalar {wheel.name} con sus dependencias (pip)")


def _preparar_archivos_de_ejemplo(carpeta: Path) -> None:
    """Arma serie.csv, muestreo.csv, malla.geojson y clima_diario.csv a partir de los datos de referencia."""
    golden = RAIZ / "tests" / "golden"
    fuentes = [golden / n for n in ("datos_plantas_completos.csv", "kvpi_serie.csv", "malla_zona.geojson", "clima_diario.csv")]
    faltan = [f.name for f in fuentes if not f.is_file()]
    if faltan:
        raise FalloDeInstalacion(f"faltan datos de referencia en {golden}: {', '.join(faltan)}; el script se corre desde el repositorio")
    carpeta.mkdir(parents=True, exist_ok=True)
    cabecera, *filas = (golden / "datos_plantas_completos.csv").read_text(encoding="utf-8").splitlines()
    columnas = cabecera.split(",")
    posiciones = [columnas.index(c) for c in ("id", "X", "Y")]
    muestreo = ["id,X,Y"] + [",".join(f.split(",")[i] for i in posiciones) for f in filas]
    (carpeta / "muestreo.csv").write_text("\n".join(muestreo) + "\n", encoding="utf-8")
    shutil.copy(golden / "kvpi_serie.csv", carpeta / "serie.csv")
    shutil.copy(golden / "malla_zona.geojson", carpeta / "malla.geojson")
    shutil.copy(golden / "clima_diario.csv", carpeta / "clima_diario.csv")


def comprobar_instalacion(python: Path, carpeta_de_trabajo: Path) -> None:
    """Corre, desde una carpeta que no es la del código, los comandos que prueban que la instalación sirve."""
    _preparar_archivos_de_ejemplo(carpeta_de_trabajo)
    programa = _ejecutable(python.parent.parent, "kiwitracking")
    if not programa.is_file():
        raise FalloDeInstalacion(f"la instalación no creó el comando kiwitracking ({programa})")

    comprobar_version(ejecutar([programa, "--version"], carpeta_de_trabajo, "kiwitracking --version"), version_del_proyecto())
    for argumentos, descripcion in (([programa, "--help"], "kiwitracking --help"),
                                    ([python, "-m", "kiwitracking", "--help"], "python -m kiwitracking --help")):  # fmt: skip
        if "kvpi" not in ejecutar(argumentos, carpeta_de_trabajo, descripcion):
            raise FalloDeInstalacion(f"{descripcion} no lista el comando kvpi")

    donde = ejecutar([python, "-c", "import kiwitracking; print(kiwitracking.__file__)"], carpeta_de_trabajo, "ubicar el paquete importado").strip()
    if str(python.parent.parent.resolve()) not in str(Path(donde).resolve()):
        raise FalloDeInstalacion(f"se importó el paquete desde {donde} y no desde el entorno nuevo")

    esperado = {"kvpi": "Plantas en el resultado: 159", "mapa": f"Huella: {HUELLA_DEL_LOTE_DE_REFERENCIA}", "analizar": "Plantas analizadas: 159"}
    huella = None
    for comando in leer_ejemplo((RAIZ / "README.md").read_text(encoding="utf-8")):
        if huella:
            comando = comando.replace("HUELLA", huella)
        argumentos = shlex.split(comando)
        pantalla = ejecutar([programa, *argumentos[1:]], carpeta_de_trabajo, f"ejemplo mínimo: kiwitracking {argumentos[1]}")
        if esperado[argumentos[1]] not in pantalla:
            raise FalloDeInstalacion(f"el ejemplo mínimo ({argumentos[1]}) no imprimió {esperado[argumentos[1]]!r}")
        encontrada = re.search(r"^Huella: ([0-9a-f]{12})$", pantalla, re.M)
        huella = encontrada.group(1) if encontrada else huella


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prueba la instalación de kiwitracking en un entorno limpio: construye el wheel, crea un entorno "
                    "virtual nuevo, lo instala con sus dependencias (necesita internet) y corre los comandos básicos.",
    )  # fmt: skip
    parser.add_argument("--wheel", type=Path, help="Usa este wheel en lugar de construirlo.")
    parser.add_argument("--conservar", action="store_true", help="No borra la carpeta temporal con el entorno y los archivos.")
    argumentos = parser.parse_args(argv)

    if argumentos.wheel is not None:
        if not argumentos.wheel.is_file():
            print(f"ERROR: no existe el wheel {argumentos.wheel}")
            return 1
        if argumentos.wheel.suffix != ".whl":
            print(f"ERROR: {argumentos.wheel.name} no es un wheel (.whl)")
            return 1

    inicio = time.monotonic()
    temporal = Path(tempfile.mkdtemp(prefix="kiwitracking_instalacion_"))
    paso = "preparar"
    try:
        print(f"Prueba de instalación de kiwitracking {version_del_proyecto()} (carpeta temporal: {temporal})")
        paso = "construir"
        wheel = argumentos.wheel or construir(temporal / "dist")
        paso = "crear el entorno"
        python = crear_entorno(temporal / "entorno")
        paso = "instalar"
        instalar(python, wheel)
        paso = "comprobar"
        comprobar_instalacion(python, temporal / "trabajo")
    except FalloDeInstalacion as error:
        print(f"ERROR en el paso «{paso}»: {error}")
        return 1
    finally:
        if argumentos.conservar:
            print(f"Se conservó la carpeta temporal: {temporal}")
        else:
            shutil.rmtree(temporal, ignore_errors=True)
    print(f"Instalación verificada: kiwitracking {version_del_proyecto()} ({time.monotonic() - inicio:.0f} s)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
