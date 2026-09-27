# Declaración de uso de IA

| Herramienta | Tarea | Archivos afectados | Qué se incorporó | Cómo se verificó |
|---|---|---|---|---|
| Claude Code | Escribir script de descarga del dataset | `scripts/01_load_dataset.py` | Lógica completa del script | Se corrió el script y se comparó manualmente el resumen (262 repos, 604 workflows, 2.820 snapshots) contra los conteos que muestra la página del dataset en Hugging Face. El script solo calcula y reporta el commit SHA de la revisión solicitada. Fue la investigadora quien decidió fijar ese SHA específico en `config/settings.yaml` |
| Claude Code | Escribir script de conteo de claves del frontmatter | `scripts/02_list_frontmatter_keys.py` | Lógica completa del script. La decisión de usar la versión más reciente de cada workflow (no las 2.820 completas) como unidad de análisis fue de la investigadora | Se corrió el script y se revisaron los valores de ejemplo en el CSV resultante. La investigadora notó una clave `True` inesperada en los resultados, lo que llevó a detectar y corregir un error de interpretación: YAML lee `on` como el booleano `True` |
