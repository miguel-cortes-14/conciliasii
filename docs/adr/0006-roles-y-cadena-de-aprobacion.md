# ADR-0006 · Roles y cadena de aprobación

- **Estado:** Aceptada (confirmada por el usuario el 2026-10-19)
- **Fecha:** 2026-10-19

## Contexto

El PRD v0.2 definía tres roles (Analista de conciliación, Aprobador y Administrador) y una sola aprobación de Contabilidad. El PO indicó que los usuarios reales son cuatro (Tesoreros, Analista Contable, Jefa de Contabilidad y el Gerente de Administración y Finanzas, GAF), que la aprobación tiene dos niveles y que los flujos deben dejar claro quién es responsable de cada paso (por ejemplo, la conciliación la hacen los tesoreros).

## Decisión

Adoptar estos roles y esta cadena, confirmados por el usuario el 2026-10-19:

1. **Tesorero (Tesorería):** responsable de la conciliación. Carga el CSV del SII, concilia, decide las sugerencias de calce, comenta diferencias, descarga el Excel y envía el período a revisión contable.
2. **Analista Contable (Contabilidad):** revisa las diferencias, las comenta (el comentario es obligatorio por diferencia) y envía a aprobación de la Jefa. Es el único que puede devolver el período a Tesorería, con motivo.
3. **Jefa de Contabilidad (1er aprobador, nivel 1):** también puede comentar mientras evalúa. Al aprobar, el sistema valida que toda diferencia tenga comentario. Si rechaza, el período vuelve al Analista Contable. Recibe los rechazos del GAF y reabre un período aprobado, sin necesitar visto bueno del GAF.
4. **Gerente de Administración y Finanzas (GAF), 2.º y último aprobador (nivel 2):** superior jerárquico de la Jefa de Contabilidad. Su aprobación deja la versión inmutable; si rechaza, el período vuelve a la Jefa. Lee los comentarios pero no comenta (supuesto menor, no consultado).
5. **Administrador (TI):** solo configura la conexión con BC (HU-15); en la PoC se resuelve por variables de entorno.

Estados: `Borrador` -> `EnRevisionContable` -> `PendienteJefaContabilidad` -> `PendienteGAF` -> `Aprobado`. Se comenta en `Borrador`, `EnRevisionContable` y `PendienteJefaContabilidad`. Todo rechazo exige motivo. La regla de comentario obligatorio (PRD, P1) se valida en `aprobar_nivel1` y se repite en `aprobar_nivel2`; la UI deshabilita el botón y el envío a la Jefa no se bloquea (solo advierte). Los permisos se validan en el servicio (`workflow/approval.py`), no solo en la UI. Capa 1: rol Tesorero; Capa 2: Analista Contable, Jefa de Contabilidad, GAF y el permiso de comentar del Tesorero (los comentarios son HU-11, de la Capa 2).

## Alternativas consideradas

- **Mantener Analista y Aprobador como en el PRD v0.2.** No refleja a los cuatro usuarios ni la doble aprobación.
- **Que los rechazos del GAF vuelvan al Analista Contable o a Tesorería.** Descartada por el usuario: el destino es la Jefa de Contabilidad.
- **Que el GAF reabra períodos.** Descartada por el usuario: reabre la Jefa de Contabilidad.
- **Que solo comente el Analista Contable.** Descartada por el usuario: comentan Tesorero, Analista Contable y Jefa de Contabilidad.
- **Bloquear el envío a la Jefa si faltan comentarios.** Descartada por el usuario: solo se advierte.
- **Validar los comentarios al enviar desde el Analista Contable.** Descartada: el PRD condiciona la *aprobación* a los comentarios, y la Jefa es quien aprueba el nivel 1.

## Consecuencias

- Las responsabilidades de cada paso quedan explícitas en los diagramas y en la matriz de permisos de [arquitectura.md](../arquitectura.md#roles-y-responsabilidades).
- `PRD.md` (v0.4), `historias.md` (HU-02 a HU-14 y la nueva HU-16) y los issues #4 a #16 se alinearon con esta decisión. HU-01 y HU-15 (issues #3 y #17) siguen genéricas.
- Queda como supuesto menor que el GAF no comenta.
- Si el PO corrige algún punto, el cambio se concentra en la tabla de permisos y en las transiciones de `workflow/approval.py`.
- Sin autenticación real en la PoC, cualquiera puede elegir cualquier rol en el selector.
