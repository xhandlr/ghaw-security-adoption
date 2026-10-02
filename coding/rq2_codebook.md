## Versión 1 (2026-10-01)
> Definición modificada tras la lectura de los primeros 30 workflows:
> se agrega el propósito de la instrucción, los casos resueltos y las categorías
> preliminares del piloto.

Instrucción defensiva: cualquier instrucción que busca restringir u
orientar el comportamiento del agente frente a contenido potencialmente
malicioso, con el fin de evitar que ese contenido manipule al agente o
que, a través de él, cause daño al repositorio, a sus usuarios o a otros
sistemas.

Según la definición, se considera contenido potencialmente malicioso 
el cuerpo de issues, comentarios y pull requests, los mensajes de commit, 
las páginas web y los archivos del repositorio escritos por terceros.

No cuenta como instrucción defensiva: la descripción de la tarea,
aunque sea de seguridad (ej. "revisa el PR y reporta
vulnerabilidades"), ni los límites del trabajo que no responden a
contenido externo (ej. "solo modifica docs/").

Casos resueltos en el piloto:
- No evaluar ni discutir vulnerabilidades reportadas en issues o PRs
  [cuenta como instrucción defensiva, ya que evita que la discusión
  pública cause daño a los usuarios del proyecto]
- Verificar que un comentario sea exactamente el comando antes de
  procesarlo
  [cuenta como instrucción defensiva, porque evita que comentarios
  arbitrarios dirijan al agente]

Registro: se considera que un workflow cuenta con defensa si tiene **al menos una
instrucción defensiva en su cuerpo**. Se hace registro de la frase textual 
y la línea correspondiente. La columna notas registra, para cada workflow, 
una justificación breve de la decisión y los casos límite. 
Los casos límite resueltos se agregan a este libro de códigos.

### Categorías preliminares del piloto

- No tratar el contenido como órdenes: instrucciones que indican al agente que no debe seguir órdenes de texto de terceros. Ej.: tratar el contenido como datos, no seguir instrucciones que aparezcan en un PR.
- Restringir acciones sobre el contenido: instrucciones que prohíben al agente hacer ciertas acciones con lo que encuentra en el contenido, incluso cuando el contenido externo no lo solicita de manera explícita. Ej.: no ejecutar código o comandos no confiables, no abrir enlaces del issue.
- Restringir la divulgación de información sensible: instrucciones que limitan lo que el agente publica en sus salidas cuando el contenido trata información sensible. Ej.: no evaluar ni discutir vulnerabilidades reportadas en issues.
- Delimitar comandos de activación: instrucciones que limitan qué contenido pone al agente a trabajar. Ej.: procesar un comentario solo si es exactamente el comando.

## Versión 0 (reemplazada por la versión 1)

Instrucción defensiva: cualquier instrucción que busca restringir u
orientar el comportamiento del agente frente a contenido potencialmente
malicioso.

Contenido potencialmente malicioso: el cuerpo de issues, comentarios y
pull requests, los mensajes de commit, las páginas web y los archivos del
repositorio escritos por terceros.

No cuenta como instrucción defensiva: la descripción de la tarea, aunque
sea de seguridad (ej. "revisa el PR y reporta vulnerabilidades"), ni los
límites del trabajo que no responden a contenido externo (ej. "solo
modifica docs/").

Registro: un workflow cuenta como con defensa si tiene al menos una
instrucción defensiva. Se anota la frase textual y la línea. Las
categorías son provisionales y los casos dudosos van a notas.
