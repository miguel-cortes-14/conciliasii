# ADR-0006 · Roles y cadena de aprobación

- **Estado:** Aceptada (confirmado por el usuario el 2026-10-19; quedan dos puntos pendientes, ver abajo)
- **Fecha:** 2026-10-19

## Contexto

El PRD v0.2 definía tres roles (Analista de conciliación, Aprobador y Administrador) y una sola aprobación de Contabilidad. El PO indicó que los usuarios reales son cuatro (Tesoreros, Analista Contable, Jefa de Contabilidad y GAF), que la aprobación tiene dos niveles y que los flujos deben dejar claro quién es responsable de cada paso (por ejemplo, la conciliación la hacen los tesoreros).

## Decisión

Adoptar estos roles y esta cadena. Confirmado por el usuario el 2026-10-19:

1. **Tesorero (Tesorería):** responsable de la conciliación. Carga el CSV del SII, concilia, decide las sugerencias de calce, comenta diferencias, descarga el Excel y envía el período a revisión contable.
2. **Analista Contable (Contabilidad):** revisa las diferencias, las comenta (el comentario es obligatorio por diferencia) y envía a aprobación de la Jefa. Tanto el Tesorero como el Analista Contable pueden comentar.
3. **Jefa de Contabilidad (1er aprobador, nivel 1):** al aprobar, el sistema valida que toda diferencia tenga comentario. Recibe los rechazos del GAF y es quien reabre un período aprobado.
4. **GAF (2.º aprobador, nivel 2 y final):** superior jerárquico de la Jefa de Contabilidad. Su aprobación deja la versión inmutable; si rechaza, el período vuelve a la Jefa.
5. **Administrador (TI):** solo configura la conexión con BC (HU-15); en la PoC se resuelve por variables de entorno.

Estados: `Borrador` -> `EnRevisionContable` -> `PendienteJefaContabilidad` -> `PendienteGAF` -> `Aprobado`. Todo rechazo exige motivo. La regla de comentario obligatorio (PRD, P1) se valida en `aprobar_nivel1` y se repite en `aprobar_nivel2`; la UI deshabilita el botón. Los permisos se validan en el servicio (`workflow/approval.py`), no solo en la UI. Capa 1: rol Tesorero; Capa 2: Analista Contable, Jefa de Contabilidad, GAF y el permiso de comentar del Tesorero (los comentarios son HU-11, de la Capa 2).

**Puntos pendientes de confirmar** (propuestos, sin respuesta del usuario; ver la tabla de supuestos en [arquitectura.md](../arquitectura.md#supuestos-y-brechas-respecto-del-prd) y P8 en el PRD):

- El rechazo de la propia Jefa vuelve al Analista Contable (`EnRevisionContable`). Pregunta: cuando la Jefa rechaza, ¿vuelve al Analista Contable o directo a Tesorería?
- El Analista Contable puede devolver a Tesorería (`Borrador`) con motivo. Pregunta: ¿puede hacerlo, o solo la Jefa?
- Además: ¿la reapertura requiere aviso o visto bueno del GAF?

## Alternativas consideradas

- **Mantener Analista y Aprobador como en el PRD v0.2.** No refleja a los cuatro usuarios ni la doble aprobación.
- **Que los rechazos del GAF vuelvan al Analista Contable o a Tesorería.** Descartada por el usuario: el destino es la Jefa de Contabilidad.
- **Que el GAF reabra períodos.** Descartada por el usuario: reabre la Jefa de Contabilidad.
- **Que solo comente el Analista Contable.** Descartada por el usuario: comentan Tesorero y Analista Contable.
- **Validar los comentarios al enviar desde el Analista Contable.** Descartada: el PRD condiciona la *aprobación* a los comentarios, y la Jefa es quien aprueba el nivel 1.

## Consecuencias

- Las responsabilidades de cada paso quedan explícitas en los diagramas y en la matriz de permisos de [arquitectura.md](../arquitectura.md#roles-y-responsabilidades).
- `PRD.md` (v0.3: roles, RF-09, RF-12, RN-11, P1, P8) y `historias.md` (HU-02 a HU-10, HU-12 y HU-13) se alinearon con esta decisión. HU-01 y HU-15 siguen genéricas; HU-11 y HU-14 conservan su texto original hasta su revisión. Los issues de GitHub no se modificaron.
- Si el PO corrige algún punto pendiente, el cambio se concentra en la tabla de permisos y en las transiciones de `workflow/approval.py`.
- Sin autenticación real en la PoC, cualquiera puede elegir cualquier rol en el selector.
