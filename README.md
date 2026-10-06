# Adopción de configuraciones de seguridad en GitHub Agentic Workflows

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23176659.svg)](https://doi.org/10.5281/zenodo.23176659)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Licencia código](https://img.shields.io/badge/código-MIT-green)
![Licencia resultados](https://img.shields.io/badge/resultados-CC%20BY%204.0-lightgrey)

> Paquete de réplica parcial (Etapa 2) del estudio sobre adopción de configuraciones de seguridad en GitHub Agentic Workflows (GH-AW), construido sobre el dataset GHAW-H v0.1.2.

**Autores:** Camille Elgueta, Carlos Pradenas

**Curso:** ICC760 Investigación Aplicada en Informática, Universidad de La Frontera

**Versión del repo:** `v0.2.0`

---

## Contenido

- [Preguntas de investigación](#preguntas-de-investigación)
- [Organización del paquete](#organización-del-paquete)
- [Preparar el entorno](#preparar-el-entorno)
- [Datos de entrada](#datos-de-entrada)
- [Ejecutar el análisis](#ejecutar-el-análisis)
- [Resultados por pregunta](#resultados-por-pregunta)
- [Qué se puede reproducir y qué no](#qué-se-puede-reproducir-y-qué-no)
- [Estado de la implementación](#estado-de-la-implementación)
- [Licencias y cómo citar](#licencias-y-cómo-citar)

---

## Preguntas de investigación

| ID      | Pregunta                                                                                                                                                           |
|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **RQ1** | ¿Qué configuraciones de seguridad del frontmatter mantienen los desarrolladores en su valor por defecto, cuáles modifican y en qué dirección?                      |
| **RQ2** | ¿Qué instrucciones defensivas incorporan los desarrolladores en el body de los archivos Markdown de GH-AW, fuera de las configuraciones oficiales del frontmatter? |

---

## Organización del paquete

```
.
├── scripts/            # Scripts numerados por bloque
│   ├── 01–04           # Comunes (descarga y preparación)
│   ├── 10–15           # RQ1
│   └── 20–27           # RQ2
├── results/            # Una carpeta por script, cada una con provenance.json
├── coding/             # Libros de códigos, planillas de codificadores, consenso y piloto
├── config/
│   └── settings.yaml   # Versiones fijadas y criterios
├── data/raw/           # Insumos descargados (no versionado en git)
├── requirements.txt
├── AI_USAGE.md
└── LICENSE
```

---

## Preparar el entorno

Requiere **Python 3.13**.

```bash
git clone https://github.com/xhandlr/ghaw-security-adoption.git
cd ghaw-security-adoption
git checkout v0.2.0
python3.13 -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Datos de entrada

| Insumo | Fuente | Versión fijada |
|--------|--------|----------------|
| GHAW-H (5 Parquet) | [DOI 10.5281/zenodo.22084012](https://doi.org/10.5281/zenodo.22084012) | v0.1.2 (Hugging Face rev. `9ccc840`) |
| Schema de gh-aw | [github/gh-aw](https://github.com/github/gh-aw) | commit `5ecd40a4` |
| Página de arquitectura de gh-aw | [github/gh-aw](https://github.com/github/gh-aw) | commit `5ecd40a4` |

Los insumos se descargan en `data/raw/`: el dataset con el script `01`, y el schema y la página de arquitectura con los scripts `03` y `11`. Esos tres scripts requieren conexión a internet. El resto del análisis se ejecuta en local.

**Verificación (SHA-256):**

| Archivo | Hash |
|----|----|
| `lock_file_snapshot.parquet` | `0272d5b7b7e93d26d52116214dd167b5f3940d135f75474092e06bb434df77b3` |
| `repository.parquet` | `75bc7e5a838281f49403e682709775936568f781031ef94b01bec343148c6ae8` |
| `source_markdown_file_history.parquet` | `5c90e748b8e5ad59de088111ea91af6b06ec08789d70e0a7600e9273ca5a02a4` |
| `source_markdown_file_snapshot.parquet` | `b8049b2f05bdbce449f24dfef3ca70e1b135b339a17347ad9d88a98f4e8d94b9` |
| `source_markdown_file_version.parquet` | `88576175db0645f52f399279d6e263f35fc2c152fbc18f734f2eb28c05cc1b2f` |

---

## Ejecutar el análisis

Ejecutar en este orden desde la raíz del repo:

```bash
# Datos (requiere conexión; descarga GHAW-H en data/raw/)
python scripts/01_load_dataset.py

# Comunes
python scripts/02_list_frontmatter_keys.py
python scripts/03_extract_schema_fields.py     # descarga el schema de gh-aw (commit fijado)
python scripts/04_dataset_overview.py

# RQ1
python scripts/10_rq1_schema_roots.py
python scripts/11_rq1_arch_doc_fields.py       # descarga la página de arquitectura (commit fijado)
python scripts/12_rq1_lock_evidence.py
python scripts/13_rq1_lock_evidence_summary.py
python scripts/14_rq1_measurement.py
python scripts/15_rq1_candidate_fields.py

# RQ2
python scripts/20_rq2_pilot_sample.py          # regenera coding/pilot_sample/ (idéntico, semilla fija)
python scripts/22_rq2_pilot_summary.py
python scripts/23_rq2_workflow_families.py
python scripts/27_rq2_sample_size.py
```

El valor de los parámetros fijados (commits/semillas) se encuentra en `config/settings.yaml`.

> [!NOTE] 
> No es necesario volver a ejecutar los scripts 21, 24, 25 y 26 para reproducir los resultados: 21 y 24 prepararon las planillas de codificación, 25 calculó el acuerdo entre codificadores una sola vez, antes de discutir los desacuerdos, y 26 generó la planilla de consenso. Sus salidas ya están en `coding/` y `results/25_rq2_intercoder_agreement/`.

⏱️ Sin contar la descarga del dataset (script 01), todo el procesamiento tarda menos de un minuto en un notebook. En un computador con Intel Core i7-12700H y 16 GB de RAM, se registró un tiempo de ejecución de **53 s**.

---

## Resultados por pregunta

### RQ1: demostración con cuatro campos

Se obtuvieron resultados preliminares para cuatro campos:
- `strict`: default declarado en el JSON Schema de gh-aw.
- `permissions`: sin default en el schema. La documentación indica solo lectura por defecto, y el valor exacto (`contents: read`) se obtuvo de los lock files de los workflows que no declaran el campo.
- `network`: sin default en el schema, es documentado en la referencia oficial de gh-aw.
- `tools.bash`: capacidad que se habilita. Su comportamiento por defecto está documentado en la descripción del propio schema.

Cada uno representaba un desafío distinto para obtener sus valores por defecto, por lo que fueron utilizados 
como una medida de estimación de esfuerzo y definición de alcance definitivo del estudio.


**Tabla I. Estado y dirección de los cuatro campos**

| Campo       | Implícito | Igual al default | Modificado | Más permisivo | Más estricto | Sin dirección |
| ----------- | --------- | ---------------- | ---------- | ------------- | ------------ | ------------- |
| strict      | 439       | 146              | 18         | 18            | 0            | 0             |
| tools.bash  | 386       | 6                | 211        | 140           | 1            | 70            |
| network     | 249       | 113              | 241        | 205           | 12           | 24            |
| permissions | 3         | 8                | 592        | 573           | 0            | 19            |

**Fuente:** [results/14_rq1_measurement/summary.csv](results/14_rq1_measurement/summary.csv) (estado) y [results/14_rq1_measurement/direction_summary.csv](results/14_rq1_measurement/direction_summary.csv) (dirección). Se midieron 603 workflows y se excluye uno con frontmatter vacío. Los defaults, las formas y sus fuentes están en `coding/rq1_codebook.yaml`.

---

### RQ2: codificación piloto

Se realizó un piloto de 30 workflows para encontrar la cantidad de workflows
que declaran instrucciones defensivas dentro del cuerpo de los archivos Markdown.
Se obtuvo la frecuencia de las categorías a las que pertenecen esas instrucciones defensivas.

**Tabla II. Distribución de categorías de instrucciones defensivas**

| **Categoría**                                     | **Workflows** |
| ------------------------------------------------- | ------------- |
| Restringir acciones sobre el contenido            | 3             |
| No tratar el contenido como órdenes               | 2             |
| Restringir la divulgación de información sensible | 1             |
| Delimitar comandos de activación                  | 2             |

Un workflow tiene dos categorías, por lo que la tabla suma 8.

Ambos codificadores coincidieron en 29 de los 30 workflows (96,7%) antes de discutir los desacuerdos. 
El kappa de Cohen fue de 0,902.
El único desacuerdo se resolvió por consenso, y el libro de códigos registra los casos resueltos en el piloto. Con la codificación de consenso, 
7 de los 30 workflows contienen al menos una instrucción defensiva (23,3%). 
Con un 95% de confianza, la proporción en la población elegible (486 workflows con instrucciones escritas en el body) se encuentra entre 11,8% y 40,9% (intervalo de Wilson). Es una estimación preliminar.

**Fuentes:** [results/22_rq2_pilot_summary/](results/22_rq2_pilot_summary/) (proporción, intervalo y categorías), [results/25_rq2_intercoder_agreement/](results/25_rq2_intercoder_agreement/) (acuerdo) y [results/20_rq2_pilot_sample/eligibility.csv](results/20_rq2_pilot_sample/eligibility.csv) (población elegible).



---

## Qué se puede reproducir y qué no

- ✅ **Reproducible con código:** todos los resultados de `results/`, a partir de los insumos y de las planillas de `coding/`.
- ✋ **No reproducible con código:** la codificación manual, es decir, las planillas de cada codificador y las decisiones de consenso, junto con los libros de códigos que la guían. 
Al ser trabajo manual de los codificadores, se entrega como datos.

**Archivos que no se deben modificar**:

- `coding/rq2_coding_coder1.csv`
- `coding/rq2_coding_coder2.csv`

Estos archivos representan la clasificación independiente de cada codificador
para cada uno de los 30 workflows del piloto. El consenso de codificadores
se registra en `coding/rq2_coding_consensus.csv`, pero los originales no se modifican. 
Es decir, se respeta la visión inicial de cada codificador.

---

## Estado de la implementación

**Implementado**
- [x] Descarga y descripción del dataset (scripts 01–04)
- [x] RQ1: extracción de schema, frontmatter y arquitectura de gh-aw (4.646 rutas del schema)
- [x] RQ1: demostración con cuatro campos: libro de códigos con defaults y fuentes, evidencia de lock files y medición de estado y dirección (scripts 10–14)
- [x] RQ2: criterio de elegibilidad (486 workflows) y muestra aleatoria de 240 (script 20)
- [x] RQ2: piloto de 30 workflows con dos codificadores, acuerdo (kappa de Cohen) y consenso (scripts 21–26)

**Pendiente**
- [ ] RQ1: clasificar, con dos codificadores, las 140 rutas candidatas según la definición de campo de seguridad
- [ ] RQ1: aplicar la medición de estado y dirección a los campos seleccionados
- [ ] RQ1: revisar si los defaults cambian entre versiones del compilador
- [ ] RQ1: el script 14 no detecta conflictos que difieren solo en amplitud y depende de un identificador escrito en el código
- [ ] RQ1: revisar superposiciones en el libro de códigos (por ejemplo, `bash: []` y `defaults` combinado con `firewall` sin otros dominios)
- [ ] Codificar las filas restantes de RQ2 (210 de 240)
- [ ] RQ2: decidir cómo tratar los bodies duplicados por plantilla
- [ ] Relacionar RQ2 con RQ1

---

## Licencias y cómo citar

- **Código:** [MIT](LICENSE)
- **Resultados** (`results/`, `coding/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), excepto el contenido de terceros.
- **Datos de GHAW-H:** los archivos Parquet no se redistribuyen. Los bodies de `coding/pilot_sample/` y las frases citadas en las planillas son texto de workflows de terceros: se incluyen solo para permitir verificar la codificación y conservan la licencia de su repositorio de origen.

**Uso de IA:** ver [AI_USAGE.md](AI_USAGE.md).

### Citar este paquete

```bibtex
@software{elgueta_ghaw_security_2026,
  author    = {Elgueta, Camille and Pradenas, Carlos},
  title     = {Adopción de configuraciones de seguridad en GitHub Agentic Workflows: paquete de réplica (Etapa 2)},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v0.2.0},
  doi       = {10.5281/zenodo.23176659}
}
```

### Citar GHAW-H

```bibtex
@dataset{valenzuela_toledo_ghaw_h_2026,
  author    = {Valenzuela-Toledo, Pablo and Kehrer, Timo and Panichella, Sebastiano},
  title     = {{GHAW-H}: A Dataset of GitHub Agentic Workflow Histories},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v0.1.2},
  doi       = {10.5281/zenodo.22084012}
}
```
