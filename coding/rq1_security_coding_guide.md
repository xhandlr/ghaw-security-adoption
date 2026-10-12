# Guía de Codificación de Campos de Seguridad (RQ1)

### 1. Definición
Un campo de seguridad es aquel que configura los privilegios del agente o
los mecanismos con que GH-AW los limita: qué privilegios se le asignan, por
qué canales puede comunicarse, qué tokens o credenciales recibe, o qué
controles se aplican al contenido que recibe o a las salidas que produce,
cómo se aísla el entorno donde corre, o qué validaciones exigen que la
configuración cumpla requisitos de seguridad.

Basada en las Capas 1, 2 y 3 de "Security Architecture"
de GH-AW. Para esta definición, el motor de IA se considera parte del agente.

### 2. Reglas de codificación
- Leer solo la descripción del schema de cada ruta. Los campos sin descripciones
quedan descartados del alcance.
- Escribir `true` o `false` en is_security_field.
- Escribir en rationale una frase explicando por qué.
- Si hay duda, elegir igual `true` o `false` y explicar la duda en notes.
- Debe codificarse sin ver los resultados del otro codificador, por ende, solo 
debe hacerse push cuando toda la planilla esté completa.

### 3. Qué cuenta en cada parte de la definición
Se refiere a lo que la configuración le permite al agente, no a las
habilidades del modelo.
- Privilegios: operaciones que el agente tiene permitidas, como los permisos
del token que usa, las herramientas o comandos que puede ejecutar y lo que
puede escribir o crear.
- Canales: la red (dominios permitidos por el firewall) y las conexiones a
servidores MCP a través del gateway.
- Tokens o credenciales: los que la configuración entrega al agente o al motor.
- Controles sobre contenido y salidas: mecanismos que filtran o revisan lo que
el agente recibe o produce, incluidos los que restringen quién puede activar
al agente.
- Aislamiento: configuración del entorno aislado donde corre el agente, cuando
la descripción dice que aísla al agente o limita lo que puede tocar en la
máquina. Un entorno para otros pasos del workflow no cuenta.
- Validaciones: mecanismos que exigen que la configuración cumpla requisitos
de seguridad antes de ejecutarse.

### 4. Reglas para casos límites
- Activación: los campos que restringen quién puede hacer que el agente corra
(roles, usuarios, bots, aprobación de una persona) son true. Los campos que
solo eligen qué eventos lo activan son false.
- Pasos fijos: los campos que configuran pasos que corren antes o después del
agente sin entregarle privilegios, canales ni credenciales son false. Esto
incluye las credenciales que usa solo un paso fijo y que no llegan al agente,
según lo que diga la descripción.
- Límites operacionales: los campos que establecen límites de tiempo,
turnos, ejecuciones o gasto son false, porque no configuran privilegios
ni ninguno de los mecanismos de seguridad descritos en la arquitectura de
GH-AW. Se escribe "límite de consumo" en notes para poder reportarlos
aparte.
- Padres e hijos se codifican por separado, cada uno por su propia
descripción. Un padre no es de seguridad solo porque tenga hijos que lo son,
y un hijo no lo es solo porque su padre lo sea.
