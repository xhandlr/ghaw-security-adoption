# ghaw-security-adoption

Paquete de réplica del estudio de minería de repositorios sobre adopción de configuraciones de seguridad en GitHub Agentic Workflows (GH-AW), usando el dataset GHAW-H (`pavtch/GHAW-H`, Hugging Face).

## Preguntas de investigación

- RQ1: ¿Qué configuraciones de seguridad del frontmatter modifican los desarrolladores y cuáles mantienen en default?
- RQ2: ¿Qué mecanismos de seguridad implementan los desarrolladores en el body del Markdown, fuera de las configuraciones oficiales del frontmatter?

## Estructura del repositorio

TODO

## Entorno

TODO (versión de Python, `requirements.txt`)

## Cómo reproducir

TODO

## Estado del avance

Los campos de seguridad seleccionados para la demostración son:

- `strict`: default declarado en el JSON Schema de `gh-aw`.
- `permissions`: sin default en el schema ni en la documentación, deberá obtenerse cruzando el valor de los lock files compilados.
- `network`: sin default en el schema, es documentado en la referencia oficial de `gh-aw`.
- `tools.bash`: capacidad que se habilita. Su comportamiento por defecto está documentado en la descripción del propio schema.

El resto de los campos candidatos identificados (`sandbox`, `mcp-servers`, `on.roles`, otras acciones de `safe-outputs`) quedan pendientes para el estudio completo.

RQ2: sin resultados preliminares todavía.
