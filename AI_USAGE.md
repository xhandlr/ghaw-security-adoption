# Declaración de uso de IA

Se usó Claude (Anthropic) para implementar y ejecutar el código de este repositorio.
Las decisiones metodológicas del estudio son de la autora.

| Herramienta | Archivo                               | Código generado con IA                                                         | Verificación                                                                                                                     |
|-------------|---------------------------------------|--------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| Claude Code | `scripts/01_load_dataset.py`          | Script de descarga del dataset.                                                | Conteos (262 repositorios, 604 workflows, 2.820 snapshots) comparados con la página del dataset en Hugging Face.                 |
| Claude Code | `scripts/02_list_frontmatter_keys.py` | Conteo de claves, `FrontmatterLoader` (evita que YAML lea `on` como booleano). | Revisión del CSV de salida, que permitió detectar el error de `on`.                                                              |
| Claude Code | `scripts/02_list_frontmatter_keys.py` | Separación entre frontmatter vacío, no diccionario y diccionario vacío.        | Verificable abriendo `results/02_frontmatter_keys/empty_dicts_*.csv`: 2 líneas en total, solo el encabezado, sin filas de datos. |
| Claude Code | `scripts/03_extract_doc_fields.py`    | Extracción del JSON Schema de `gh-aw`.                                         | Ejecución sin errores. Revisión manual del CSV contra el schema: pendiente.                                                      |
| Claude Code | `scripts/04_rq2_pilot_sample.py`      | Muestreo del piloto de RQ2 con semilla fija.                                   | Ejecución sin errores y muestra reproducible entre corridas.                                                                     |