# Guía de Codificación de Campos de Seguridad (RQ1)

### 1. Definición
Un campo de seguridad es aquel cuya configuración modifica las capacidades,
el acceso o las restricciones aplicadas al agente, de manera que puede
aumentar o reducir el daño que el agente puede causar al repositorio, a sus
secretos, a otros sistemas o en costos para el dueño de la cuenta si es
manipulado o actúa de forma no deseada.


### 2. Reglas de codificación
- Leer solo la descripción del schema de cada ruta. Los campos sin descripciones
quedan descartados del alcance.
- Escribir `true` o `false` en is_security_field.
- Escribir en rationale una frase explicando por qué.
- Si hay duda, elegir igual `true` o `false` y explicar la duda en notes.
- Debe codificarse sin ver los resultados del otro codificador, por ende, solo 
debe hacerse push cuando toda la planilla esté completa.

### 3. Qué cuenta como capacidades, acceso y restricciones
Se refieren a lo que la configuración le permite al agente, no a las
habilidades del modelo.
- Capacidades: acciones que el agente tiene habilitadas. Ejemplos: herramientas
que puede usar (ejecutar comandos, editar archivos, navegar), permisos del
token (leer o escribir issues, pull requests, contenido), salidas que puede
producir sobre el repositorio (crear issues, comentar, abrir pull requests).
- Acceso: recursos que el agente puede alcanzar. Ejemplos: repositorios
(el propio u otros, públicos o privados), secretos, tokens y credenciales,
red y dominios externos, servidores MCP, volúmenes o puertos del entorno
donde corre.
- Restricciones: límites sobre lo anterior. Ejemplos: sandbox o firewall,
listas de dominios o comandos permitidos, modo strict, aislamiento del
contenedor, limpieza de credenciales, y topes a lo que el agente puede gastar
o ejecutar (créditos de IA, turnos, ejecuciones, tiempo).

### 4. Reglas para casos límites
- Se asume siempre que el agente puede ser manipulado o actuar de forma no
deseada. Eso no se cuenta como un paso del razonamiento.
- Un campo es de seguridad solo si cambiar su valor cambia directamente, en un
paso, lo que el agente puede hacer, a qué puede acceder o qué se le restringe.
- Ejemplo: si cambio un campo y dejo todo lo demás igual, ¿cambia la
lista de cosas que el agente puede hacer o tocar, o el tope de lo que puede
gastar o ejecutar? Si no cambia, es false.
- Si para conectarlo con la seguridad se necesita encadenar más de un paso
(por ejemplo, "elige el motor -> cada motor tiene otras habilidades -> ..."),
es false.
- Elegir un motor o modelo distinto no es de seguridad por sí solo, porque no
cambia lo que el agente tiene permitido.
- Los límites que ponen un tope a lo que el agente puede gastar o ejecutar
(créditos de IA, turnos, ejecuciones, tiempo) son true, y se escribe "límite
de consumo" en notes para poder reportarlos aparte.
- Caché, concurrencia, memoria del contenedor o tamaño del runner son false:
afectan el rendimiento o la máquina, no ponen un tope a lo que el agente puede
gastar o ejecutar.
- En campos de valor libre (por ejemplo, argumentos o variables), se decide
según lo que la descripción dice que hace el campo, no según lo que alguien
podría escribir en él. Si la descripción dice que pasa secretos, comandos
permitidos o permisos, es true. Si solo dice que pasa valores, es false.
- Padres e hijos se codifican por separado, cada uno por su propia
descripción. Un padre no es de seguridad solo porque tenga hijos que lo son,
y un hijo no lo es solo porque su padre lo sea.
