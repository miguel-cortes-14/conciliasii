# ADR-0006 · Roles y cadena de aprobación

- **Estado:** Propuesto (interpretación por confirmar con el PO)
- **Fecha:** 2026-10-19

## Contexto

El PRD define tres roles: Analista de conciliación (Tesorería), Aprobador (Contabilidad) y Administrador (TI, supuesto), con una sola aprobación de Contabilidad (P1). Al revisar el diseño, el PO indicó que intervienen tesoreros, analistas contables y el GAF como último aprobador, y que los flujos deben dejar claro quién es responsable de cada paso (por ejemplo, la conciliación la hacen los tesoreros). La cadena exacta y quién escribe los comentarios son una **interpretación** de ese mensaje y no están confirmadas.

## Decisión

Adoptar, de forma provisoria, estos roles y esta cadena:

1. **Tesorero (Tesorería):** responsable de la conciliación. Carga el CSV del SII, concilia, decide las sugerencias de calce, descarga el Excel y envía el período a revisión.
2. **Analista contable (Contabilidad):** revisa las diferencias, escribe el comentario obligatorio por cada una y hace la primera aprobación (o rechaza con motivo).
3. **GAF (último aprobador):** aprobación final; la versión aprobada queda inmutable. Puede rechazar con motivo y reabrir.
4. **Administrador (TI):** se mantiene solo para configurar la conexión con BC (HU-15); en la PoC se resuelve por variables de entorno.

Estados: `Borrador` -> `EnRevisionContable` -> `PendienteGAF` -> `Aprobado`; los rechazos (con motivo) vuelven a `Borrador`, es decir, a Tesorería. La regla de comentario obligatorio (PRD, P1) se valida en la aprobación de nivel 1 del Analista contable y se repite en la final. Los permisos se validan en el servicio (`workflow/approval.py`), no solo en la UI. Se entrega en la Capa 1 el rol Tesorero y en la Capa 2 el Analista contable y el GAF.

## Alternativas consideradas

- **Mantener Analista y Aprobador como en el PRD.** No distingue a Tesorería de Contabilidad en los pasos ni refleja al GAF.
- **Dos roles con una sola aprobación (Tesorero y Aprobador).** Más simple, pero no modela la aprobación final.
- **Que Tesorería también comente (como dicen el PRD y HU-11).** Posible; `comentario.rol` lo permite sin cambiar el esquema. Queda como opción a confirmar.
- **Validar los comentarios en la aprobación final del GAF.** Descartada: el PRD condiciona la aprobación de Contabilidad a los comentarios y el GAF debe recibir el período ya comentado.

## Consecuencias

- Las responsabilidades de cada paso quedan explícitas en los diagramas y en la matriz de permisos de [arquitectura.md](../arquitectura.md#roles-y-responsabilidades).
- Hay una discrepancia de nomenclatura con `PRD.md`, `historias.md` y los issues #3 a #17 (Analista y Aprobador). No se modificaron; si el PO valida esta cadena, hay que actualizarlos.
- HU-11 y HU-14 cambian de actor respecto de su texto actual (ver la equivalencia en la arquitectura).
- Si el PO corrige la cadena, el cambio se concentra en la tabla de permisos y en las transiciones de `workflow/approval.py`.
- Sin autenticación real en la PoC, cualquiera puede elegir cualquier rol en el selector.
