GUÍA DE CODIFICACIÓN DE CAMPOS DE SEGURIDAD (RQ1)

1. Definición
Un campo de seguridad es aquel cuya configuración modifica las capacidades,
el acceso o las restricciones aplicadas al agente, de manera que puede
aumentar o reducir el daño que el agente puede causar al repositorio, a sus
secretos o a otros sistemas si es manipulado o actúa de forma no deseada.


2. Reglas de codificación
- Leer solo la descripción del schema de cada ruta. Los campos sin descripciones
quedan descartados del alcance.
- Escribir `true` o `false` en is_security_field.
- Escribir en rationale una frase explicando por qué.
- Si hay duda, elegir igual `true` o `false` y explicar la duda en notes.
- Debe codificarse sin ver los resultados del otro codificador, por ende, solo 
debe hacerse push cuando toda la planilla esté completa.
