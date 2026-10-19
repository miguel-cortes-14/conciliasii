# ADR-0006 · Roles y cadena de aprobación

- **Estado:** Propuesto (roles confirmados por el PO; detalle de la cadena por confirmar)
- **Fecha:** 2026-10-19

## Contexto

El PRD define tres roles: Analista de conciliación (Tesorería), Aprobador (Contabilidad) y Administrador (TI, supuesto), con una sola aprobación de Contabilidad (P1). El PO indicó que los usuarios reales son cuatro: Tesoreros (Tesorería), Analista Contable (Contabilidad), Jefa de Contabilidad (1er aprobador) y GAF (2.º aprobador, aprobación final), y pidió que los flujos dejen claro quién es responsable de cada paso (por ejemplo, la conciliación la hacen los tesoreros). El PO no precisó quién escribe los comentarios, a dónde vuelve cada rechazo ni quién reabre un período aprobado; eso es propuesta de este diseño.

## Decisión

Adoptar estos roles y esta cadena:

1. **Tesorero (Tesorería):** responsable de la conciliación. Carga el CSV del SII, concilia, decide las sugerencias de calce, descarga el Excel y envía el período a revisión contable.
2. **Analista Contable (Contabilidad):** revisa las diferencias, escribe el comentario obligatorio de cada una y envía a aprobación de la Jefa; si la conciliación está mal, devuelve a Tesorería con motivo.
3. **Jefa de Contabilidad (1er aprobador, nivel 1):** aprueba el nivel 1, momento en que el sistema valida que toda diferencia tenga comentario, o rechaza con motivo.
4. **GAF (2.º aprobador, nivel 2 y final):** aprobación final; la versión queda inmutable. Puede rechazar con motivo y reabrir (propuesto).
5. **Administrador (TI):** se mantiene solo para configurar la conexión con BC (HU-15); en la PoC se resuelve por variables de entorno.

Estados: `Borrador` -> `EnRevisionContable` -> `PendienteJefaContabilidad` -> `PendienteGAF` -> `Aprobado`. Los rechazos de la Jefa y del GAF vuelven a `EnRevisionContable` (Analista Contable), porque lo habitual es corregir comentarios sin reconciliar; solo el Analista Contable devuelve a `Borrador` (Tesorería). Todo rechazo exige motivo. La regla de comentario obligatorio (PRD, P1) se valida en `aprobar_nivel1` y se repite en `aprobar_nivel2`; la UI deshabilita el botón. Los permisos se validan en el servicio (`workflow/approval.py`), no solo en la UI. Capa 1: rol Tesorero; Capa 2: Analista Contable, Jefa de Contabilidad y GAF.

## Alternativas consideradas

- **Mantener Analista y Aprobador como en el PRD.** No refleja a los cuatro usuarios ni la doble aprobación.
- **Validar los comentarios al enviar desde el Analista Contable.** Descartada: el PRD condiciona la *aprobación* a los comentarios, y la Jefa es quien aprueba por Contabilidad.
- **Que el rechazo de la Jefa o del GAF vuelva siempre a Tesorería.** Obliga a reconciliar aun cuando solo falta un comentario; se reserva para la devolución del Analista Contable.
- **Que Tesorería también comente (como dicen el PRD y HU-11).** Posible; `comentario.rol` lo permite sin cambiar el esquema. A confirmar.
- **Que la Jefa de Contabilidad reabra períodos aprobados.** Posible; se propone el GAF por ser el último aprobador. A confirmar.

## Consecuencias

- Las responsabilidades de cada paso quedan explícitas en los diagramas y en la matriz de permisos de [arquitectura.md](../arquitectura.md#roles-y-responsabilidades).
- Discrepancias con `PRD.md`, `historias.md` y los issues #3 a #17, que no se modificaron: usan Analista y Aprobador; el PRD tiene una sola aprobación y aquí hay dos niveles; HU-11 asigna los comentarios a Tesorería y aquí los hace el Analista Contable. Si el PO valida esta cadena, hay que actualizarlos.
- Si el PO corrige algún detalle, el cambio se concentra en la tabla de permisos y en las transiciones de `workflow/approval.py`.
- Sin autenticación real en la PoC, cualquiera puede elegir cualquier rol en el selector.
