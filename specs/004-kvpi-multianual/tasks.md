# Tareas — Spec 004

Estado: BORRADOR. Una tarea a la vez, en este orden. Regla de cada tarea (constitución #5): primero el test (que lleva el número de RF), se ve fallar, después el código mínimo, y al final se corre toda la suite con `-W error`. Al cerrar un grupo de tareas se hacen mutaciones.

Lee: `spec.md` (RF-1 a RF-22), `clarificacion.md` y `plan.md`.

## Datos

- [x] **T4.0. Serie real como dato de referencia.** `tests/golden/`.
  - Cubre: C12; prepara los criterios 3 y 4.
  - **Pide permiso antes de empezar:** mover `KVPI_serie_2019_2025 (1).csv` del directorio raíz del sandbox a `tests/golden/kvpi_serie.csv` y escribir una nota de procedencia (fecha de exportación 24/10/2026, 954 filas, 159 plantas por 6 campañas, proyecto y versión de imágenes que indique la persona responsable). El muestreo de las 159 plantas no se copia: `datos_plantas_completos.csv` ya trae `id`, `X` e `Y` idénticos a los de `muestreo_sistematico.csv` (el archivo original no está en el entorno).
  - Hecho cuando: ambos archivos están en `tests/golden/` con su nota de procedencia en `AGENTS.md`, y un test lee la serie y comprueba 954 filas, 159 `id`, 6 campañas, sin repetidos ni vacíos.

## Núcleo

- [x] **T4.1. Validación de la serie.** `kvpi.validar_serie`.
  - Cubre: RF-1, RF-2, RF-3, RF-4, RF-5, RF-6.
  - Hecho cuando: faltan columnas → error que las nombra; serie vacía → error; `campaña` y `campana` juntas → error; `id` o campaña vacíos → error con la cantidad; `KVPI` con texto no numérico → error con ejemplo (y la coma decimal como causa probable); infinitos → error con la cantidad; los textos ausentes de `pandas` y la celda en blanco son vacío sin error; repetidos iguales (incluidos dos vacíos) → una sola y `KVPI_DUPLICADO`; repetidos distintos (incluido número contra vacío) → error con hasta 10 pares y cuántos más; etiquetas con espacios son la misma campaña; el resultado no cambia al reordenar filas o columnas; la tabla de entrada no se modifica.

- [x] **T4.2. Cálculo por planta.** `kvpi.agregar_kvpi` (sin cobertura ni advertencias).
  - Cubre: RF-7, RF-8, RF-9, RF-10; criterio 2.
  - Hecho cuando: con una serie armada a mano (varias plantas, campañas faltantes, una con una sola campaña, una con todas vacías) `n_campanas`, `KVPI_mean`, `KVPI_std` (n−1) y `KVPI_cv` coinciden con los valores calculados a mano; con menos de `min_campanas` el desvío y el CV quedan vacíos y el promedio se conserva; media 0 o vacía deja el CV vacío; `min_campanas` menor que 2 o no entero → error con los valores permitidos; la tabla sale ordenada por `id`.

- [x] **T4.3. Advertencias de planta.** `kvpi.agregar_kvpi`.
  - Cubre: RF-11, RF-12.
  - Hecho cuando: plantas con menos campañas que las etiquetas encontradas dan `PLANTAS_CON_MENOS_CAMPANAS` con la cantidad y el rango de `n_campanas`; plantas con desvío vacío por `min_campanas` dan `SIN_DESVIO`; con una sola campaña en toda la serie sale `SIN_DESVIO` y no `PLANTAS_CON_MENOS_CAMPANAS`.

- [ ] **T4.4. Cobertura por campaña.** `kvpi.agregar_kvpi`.
  - Cubre: RF-20, RF-21, RF-22.
  - Hecho cuando: por cada campaña se informa cuántas plantas tienen dato y qué proporción son del total (`total_plantas` o los `id` distintos de la serie), con 0 para una campaña sin datos; por debajo de `cobertura_minima_campana` sale `CAMPANA_CON_POCOS_DATOS` con campaña, cantidad y proporción; un valor fuera de 0 a 1 → error; con `campanas` indicadas, una faltante o una inesperada → error que las nombra, y una lista vacía o con repetidas → error.

## Unión con el muestreo

- [ ] **T4.5. Muestreo y unión.** `kvpi.unir_con_muestreo`.
  - Cubre: RF-13, RF-14.
  - Hecho cuando: faltan `id`, `X` o `Y` → error que las nombra; `id` repetidos del muestreo iguales → una sola con aviso, distintos → error con hasta 10 `id`; el resultado trae solo las plantas en ambos, en el orden del muestreo, con las columnas `id`, `KVPI_mean`, `KVPI_std`, `KVPI_cv`, `n_campanas` y después las del muestreo; `PLANTAS_SIN_COORDENADAS` con la cantidad y `PLANTAS_SIN_SERIE` con la cantidad, los primeros 10 `id` y la frase sobre la huella; ninguna en común → error.

## Comando

- [ ] **T4.6. Flujo del comando.** `flujo.ejecutar_kvpi`.
  - Cubre: RF-15, RF-19.
  - Hecho cuando: lee la serie y el muestreo con `leer_csv` (UTF-8, BOM); un archivo inexistente da un error que lo nombra; pasa `total_plantas` igual a las plantas del muestreo; devuelve la tabla, la cobertura y las advertencias en orden (validación, cálculo, cobertura, unión); no modifica los archivos de entrada (se comparan los bytes).

- [ ] **T4.7. Escritura del resultado.** `salida.escribir_plantas_kvpi`.
  - Cubre: RF-16, RF-19.
  - Hecho cuando: el archivo sale en UTF-8 sin BOM, con `\n`, números completos y celdas vacías en blanco; si existe y no se indicó `--sobrescribir`, error sin tocarlo; con `--sobrescribir` lo reemplaza; si falla la escritura (simulada) no queda un archivo a medio escribir.

- [ ] **T4.8. Subcomando y pantalla.** `cli.py`.
  - Cubre: RF-17, RF-18.
  - Hecho cuando: `kiwitracking kvpi --serie … --muestreo …` acepta `--salida` (por defecto `plantas_kvpi.csv`), `--min-campanas`, `--campanas`, `--cobertura-minima-campana`, `--sobrescribir` y `--depurar`; la pantalla muestra las plantas del resultado, las campañas con su cobertura, cuántas plantas tienen cada cantidad de campañas, las advertencias, dónde quedó el archivo y la línea que dice que es la entrada `--plantas` de `mapa` y `analizar`; códigos 0, 1, 2 y 3 con el mismo formato de mensajes que los otros comandos; un test corre el programa en un proceso aparte y comprueba el código de salida real.

## Datos reales

- [ ] **T4.9. Flujo con la serie real (criterios 3 y 4).** `test_kvpi_golden.py`.
  - Cubre: criterios 3 y 4.
  - Hecho cuando: `KVPI_mean` y `KVPI_std` de las 159 plantas coinciden con los de `datos_plantas_completos.csv` con una diferencia menor que 1e-12; `n_campanas` es 6 en todas; `kvpi` sobre la serie y el muestreo reales, seguido de `mapa` y `analizar` con la malla, la huella y el clima de la campaña 2024, da 16 "Mantener" y 19 "Intervenir".

## Cierre

- [ ] **T4.10. Validación final.**
  - Cubre: criterio 6 de la spec (cada RF con test).
  - Hecho cuando: existe `validacion.md` con la matriz de los 22 RF contra sus tests y el estado de cada criterio; la suite completa pasa con `-W error` sin tests saltados; se hicieron mutaciones (divisor del desvío, qué cuenta como repetido igual, umbral de `min_campanas`, cobertura contra el total equivocado, orden de las columnas de salida, advertencia de huella en `PLANTAS_SIN_SERIE`) y cada una hace fallar al menos un test; el trabajo queda commiteado.

## Notas

- Orden de dependencia: T4.0 (datos) → T4.1 a T4.4 (núcleo) → T4.5 (unión) → T4.6 a T4.8 (comando) → T4.9 (datos reales) → T4.10.
- T4.1 a T4.5 usan datos sintéticos y no dependen de T4.0; T4.0 va primero porque necesita tu permiso y porque los tests con la serie real pueden agregarse tarea a tarea.
- Las dudas abiertas (C8, C9, C11, C12 y las de la spec) no tienen tarea propia: se resuelven con la sección 8 del plan. C12 se cubre en T4.0.
- `mapa.html` y el `.gitignore` quedan fuera de esta spec.
