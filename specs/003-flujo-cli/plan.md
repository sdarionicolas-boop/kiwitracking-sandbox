# Plan — Spec 003

Estado: BORRADOR. Sin código. Lee: `docs/constitution.md`, `spec.md` (RF-1 a RF-27) y `clarificacion.md`. Los hallazgos menores (C13 a C17) quedan como dudas abiertas; donde el plan necesita una decisión sobre uno de ellos, la toma la sección 8 y se puede cambiar.

## 1. Idea general

Una capa fina de entrada y salida sobre lo que ya existe. No calcula nada: lee archivos, llama a las funciones de las specs 001 y 002 y escribe resultados. **No hacen falta dependencias nuevas** (constitución #1): la línea de comandos usa `argparse` y `json` de la biblioteca estándar, y el resto sale de `pandas`, `shapely`, `pyproj` y `folium`, que ya son dependencias.

```
mapa:      --plantas ──► leer_csv ─┐
           --malla ────► leer_poligono_geojson ─► cruzar_con_malla ─► bajo_malla
                                                                       │
                                  a_wgs84 (RF-23, solo para dibujar) ◄─┤
                                         │                             │
                                         ▼                             ▼
                                  generar_mapa ──► mapa.html      línea "Huella: …"

analizar:  (mismos pasos de lectura y cruce) ─► tabla con bajo_malla
           --clima ─► leer_csv ─► calcular_clima ─► estado_frio_de_campana ─┐
           --estado-frio ─► normalizar (RF-11) ───────────────────────────┤
                                                                           ▼
                                  analizar(tabla, huella_confirmada, estado_frio, …)   [spec 001]
                                                   │
                                  huella ausente o incorrecta ─► error (RF-8)
                                                   │
                                                   ▼
                          plantas.csv · resumen.json · advertencias.json  (RF-15, 25, 27)
```

El flujo respeta el orden de lectura de la spec: primero se validan los argumentos (que es barato y da errores claros), después se leen los archivos, después se calcula, y recién al final se escribe (RF-20).

## 2. Módulos

| Módulo | Qué hace | RF que cubre |
|---|---|---|
| `kiwitracking/__main__.py` | Permite `python -m kiwitracking`; llama a `cli.main()` | RF-1 |
| `kiwitracking/cli.py` | Define los comandos y sus opciones (`argparse`), valida la combinación de argumentos, llama al flujo, imprime en pantalla y traduce errores a mensajes y códigos de salida | RF-1, RF-8 (falta de `--huella`), RF-11, RF-18, RF-19, RF-21, RF-22, RF-24, RF-26 |
| `kiwitracking/flujo.py` | Orquesta sin `argparse`: prepara las plantas (lectura, malla, `bajo_malla`), arma el mapa, elige el estado de frío, corre el análisis y convierte las advertencias de huella en error | RF-2 a RF-10, RF-13, RF-14, RF-6, RF-8 |
| `kiwitracking/salida.py` | Arma `plantas.csv` (orden de columnas), `resumen.json` y `advertencias.json`, y los escribe con limpieza si algo falla | RF-15 a RF-17, RF-20, RF-25, RF-27 |
| `kiwitracking/io.py` (se amplía) | Agrega `a_wgs84(...)`: convierte plantas y polígono a `EPSG:4326` para dibujar | RF-23 |

`flujo.py` no importa `argparse` ni imprime: recibe valores y devuelve datos (la tabla, los avisos, el estado elegido, la huella). Así se prueba sin consola. `cli.py` es lo único que conoce los nombres de las opciones.

## 3. Modelo de datos

| Estructura | Campos |
|---|---|
| `PlantasPreparadas` | `tabla` (con `bajo_malla`), `poligono` (o `None`), `crs_poligono` (o `None`), `advertencias` |
| `EstadoDeFrio` | `origen` (`clima`, `manual` o `ninguno`), `estado`, `periodo`, `horas`, `cobertura`, `hueco_maximo`, `advertencias` |
| `ResultadoFlujo` | `resultado` (el de la spec 001), `estado_frio` (`EstadoDeFrio`), `advertencias` (todas, en el orden de RF-14), `parametros` (los usados) |

Son estructuras simples (`dataclass`), sin lógica.

## 4. Decisiones técnicas

| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| D1 | `main(argv=None) -> int` devuelve el código de salida y no llama a `sys.exit`; `__main__` hace `raise SystemExit(main())` | Llamar a `sys.exit` dentro de `main` | Se prueba en el mismo proceso y se compara el código devuelto |
| D2 | Los errores salen como excepciones: `ErrorDeEntrada` (código 1), cualquier otra (código 3) y `argparse` (código 2, con `SystemExit`); `main` los captura y los traduce | Códigos de salida repartidos por todo el programa | Un solo lugar decide el código (RF-19) |
| D3 | `--huella` se declara opcional ante `argparse` y se comprueba a mano (RF-8) | `required=True` | Con `required=True` sale el mensaje genérico y el código 2 (hallazgo C4) |
| D4 | La huella ausente o incorrecta se detecta mirando las advertencias del análisis (`FALTA_CONFIRMACION`, `HUELLA_NO_COINCIDE`) y se convierte en `ErrorDeEntrada`; no se recalcula la huella en la línea de comandos | Comparar la huella con `huella(tabla)` en `flujo` | Una sola definición de "coincide" (la de la spec 001); el núcleo no cambia (RF-8) |
| D5 | `a_wgs84` convierte con `pyproj.Transformer` (`always_xy=True`) las columnas de coordenadas y, con `shapely.transform`, el polígono; devuelve copias y no toca la tabla del análisis | Reproyectar la tabla y analizar con las coordenadas convertidas | `bajo_malla` y la huella no deben depender de la conversión (RF-23) |
| D6 | `plantas.csv` se arma reordenando las columnas del resultado: las conocidas en el orden de RF-27 y el resto de las de entrada en su orden original | Escribir la tabla del análisis tal cual | El archivo debe salir igual aunque cambie el orden de la entrada (RF-27) |
| D7 | `resumen.json` se arma con un diccionario ordenado y una función que convierte `NaN`, infinitos y tipos de NumPy a `null` o a números comunes; se escribe con `json.dumps(..., allow_nan=False, indent=2, ensure_ascii=False)` | `json.dumps` por defecto | JSON estricto (RF-25); `allow_nan=False` hace fallar un `NaN` que se escapó en vez de escribir un archivo inválido |
| D8 | Los archivos se escriben con `newline="\n"` y codificación UTF-8 sin BOM; el CSV con `lineterminator="\n"` | El salto de línea del sistema | Resultados idénticos en cualquier sistema (RF-16) |
| D9 | La escritura va en orden (`plantas.csv`, `resumen.json`, `advertencias.json`); se lleva la lista de lo ya escrito y, si algo falla, se borra y se informa (RF-20) | Carpeta temporal y renombrar | Cubre el fallo más probable con poco código (hallazgo C8) |
| D10 | `--estado-frio` se normaliza quitando tildes y mayúsculas (`unicodedata`) y se compara contra `ESTADOS_FRIO` | Reescribir la lista de estados en la línea de comandos | Una sola definición (RF-11, hallazgo C9) |
| D11 | Las opciones de clima se aplican con `ParametrosClima(**solo_los_indicados)` | Pasar todas con sus valores por defecto escritos otra vez | Los valores por defecto salen de `ParametrosClima` (constitución #7) |
| D12 | La pantalla se escribe con `print` a `sys.stdout` tras reconfigurarlo a UTF-8 con `errors="replace"`; los errores van a `sys.stderr` | Dejar la codificación de la consola | RF-22: en Windows, "Óptimo" no debe hacer fallar la salida |
| D13 | El nombre del programa es `kiwitracking`, declarado en `[project.scripts]` de `pyproject.toml`; hay que reinstalar el paquete (`pip install -e .`) para que exista el comando | Un script suelto | Es el punto de entrada estándar; los tests no dependen de él (llaman a `main`) |

## 5. Estrategia de pruebas

Mismas reglas de las specs anteriores: cada RF tiene un test que lleva su número (`test_rfN_...`), el test se escribe primero y se ve fallar, y al cerrar cada cambio se hacen mutaciones. Las pruebas de la línea de comandos llaman a `main(argv)` en el mismo proceso y leen `capsys` y el código devuelto; **al menos dos** corren el programa en un proceso aparte (`python -m kiwitracking`) para comprobar de verdad el código de salida (RF-19) y la salida por pantalla (RF-22).

| Archivo de tests | Qué prueba | Datos |
|---|---|---|
| `test_coordenadas.py` | RF-23: conversión de plantas y polígono, ida y vuelta, que no cambia `bajo_malla` ni la huella, sistema desconocido | Sintéticos y el lote real convertido |
| `test_flujo.py` | RF-2 a RF-5, RF-8 (huella a error), RF-10, RF-13, RF-14 | Sintéticos de pocas filas y archivos en `tmp_path` |
| `test_salida.py` | RF-15 a RF-17, RF-20, RF-25, RF-27: orden de columnas, JSON estricto, `null`, saltos de línea, limpieza ante fallo | Sintéticos; un fallo de escritura simulado |
| `test_cli.py` | RF-1, RF-6, RF-7, RF-8, RF-9, RF-11, RF-18, RF-19, RF-21, RF-22, RF-24, RF-26: opciones, mensajes y códigos de salida | `main(argv)` con archivos en `tmp_path`; dos casos en proceso aparte |
| `test_flujo_golden.py` | Criterios 2 a 5 y 7 con el lote real y el clima real | `tests/golden/` |

## 6. Riesgos

1. **Mensajes de `argparse`.** Sus textos están en inglés por defecto y dependen de la versión de Python; los errores de uso (código 2) pueden salir en inglés. Se acepta en esta versión y se anota como duda abierta (sección 8).
2. **La huella entre los dos comandos.** Depende de que `mapa` y `analizar` preparen las plantas igual; un solo camino de preparación en `flujo.py` lo garantiza, y un test corre los dos comandos y compara.
3. **El mapa necesita internet para las teselas.** Los tests usan `--sin-fondo-satelital` y no tocan la red.
4. **Windows y la consola.** La codificación de la consola puede fallar o alterar tildes; por eso RF-22 y los casos en proceso aparte.
5. **Tiempo de las pruebas con datos reales.** Generar el mapa del lote real y correr el clima de 2.604 días suma segundos; se aceptan, y se evita repetir el cálculo con fixtures de alcance de módulo.

## 7. Cobertura de requisitos

| RF | Módulo | Test |
|---|---|---|
| 1 | `__main__`, `cli` | `test_cli` |
| 2 a 5 | `flujo` | `test_flujo` |
| 6, 7 | `flujo`, `cli` | `test_cli`, `test_flujo_golden` |
| 8 | `cli` (falta), `flujo` (incorrecta) | `test_cli`, `test_flujo`, `test_flujo_golden` |
| 9 | `cli`, `flujo` | `test_cli` |
| 10, 13, 14 | `flujo` | `test_flujo`, `test_flujo_golden` |
| 11, 24 | `cli` | `test_cli` |
| 12 | `flujo` | `test_flujo` |
| 15 a 17, 25, 27 | `salida` | `test_salida`, `test_flujo_golden` |
| 16 | `salida` | `test_salida` |
| 18, 26 | `cli` | `test_cli` |
| 19, 21, 22 | `cli` | `test_cli` (también en proceso aparte) |
| 20 | `salida`, `flujo` | `test_salida`, `test_flujo` |
| 23 | `io` | `test_coordenadas`, `test_flujo_golden` |

## 8. Decisiones provisionales sobre los hallazgos menores

Todas siguen como dudas abiertas y se pueden cambiar:

- **C13.** Si `--salida` de `analizar` apunta a un archivo existente que no es carpeta, el programa termina con un error de entrada que lo dice.
- **C14.** `advertencias.json` es una lista de objetos con `codigo` y `mensaje`, en el orden de RF-14.
- **C15.** El punto de entrada `kiwitracking` se declara en `pyproject.toml` y exige reinstalar (`pip install -e .`); los tests llaman a `main(argv)` y a `python -m kiwitracking`.
- **C16.** La reproducibilidad byte a byte vale para los tres archivos de resultados; `mapa.html` queda fuera, porque `folium` usa identificadores aleatorios y el mapa necesita internet para las teselas.
- **C17.** No hay `--version` en esta versión.
- **Mensajes de `argparse`.** Los errores de uso (código 2) usan los textos de `argparse` y pueden salir en inglés.
- **Huella copiada a mano.** No hay `--huella-desde` en esta versión; la huella se copia de la pantalla.
- **Coordenadas.** Las columnas se llaman `X` e `Y`; no se exponen otros nombres.
- **`resumen.json`.** No incluye versión del paquete ni fecha de la corrida, para que dos corridas iguales den el mismo archivo (RF-16).
