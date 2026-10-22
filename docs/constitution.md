# Constitución — KiwiTracking sandbox (BORRADOR)

1. **Stack:** Python 3.10+; núcleo con pandas, numpy y scipy; entrada/salida y visualización con shapely, pyproj y folium; tests con pytest. Earth Engine queda fuera del núcleo.
2. **Spec primero:** ningún comportamiento se implementa sin un requisito `RF-n` aprobado.
3. **Cada RF tiene al menos un test** que lo cubre, nombrado con su número (`test_rf3_...`).
4. **Tests primero:** el test se escribe y se ve fallar antes de escribir el código.
5. **Fidelidad:** con las mismas entradas, el resultado coincide con `tests/golden/` dentro de una tolerancia declarada en la spec.
6. **Sin rutas fijas:** ningún path de Drive, Desktop ni usuario dentro del paquete.
7. **Parámetros explícitos:** umbrales, factores y percentiles se pasan como argumentos o configuración, no como constantes ocultas.
8. **Codificación:** los CSV se leen y escriben en UTF-8; un archivo mal codificado es un error claro, no un resultado silencioso.
9. **Funciones puras:** el núcleo no lee ni escribe archivos; eso queda en una capa aparte.
10. **Alcance honesto:** el software no afirma predecir rendimiento; el KVPI es un índice de vigor.
