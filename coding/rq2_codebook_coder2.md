# Libro de códigos RQ2, versión 1 (segundo codificador)

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
