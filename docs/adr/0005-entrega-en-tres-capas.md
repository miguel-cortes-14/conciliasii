# ADR-0005 · Entrega en tres capas

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto

Las 15 historias del PRD forman un ciclo completo, pero conviene liberar valor en incrementos que se puedan demostrar por separado. Las dependencias reales entre historias son: el cruce necesita ambas fuentes; los comentarios necesitan el detalle; la aprobación necesita los comentarios; las versiones necesitan comentarios que traspasar.

## Decisión

Entregar en tres capas, cada una usable:

1. **Capa 1 · Núcleo con descarga Excel:** período, carga del CSV del SII, libro del ERP por el puerto, filtro, cruce, clasificación (con diferencias de período, sugerencias y duplicados), resumen, detalle y descarga de Excel. HU-01 a HU-10 y HU-15. Solo existe el rol Tesorero.
2. **Capa 2 · Comentarios y aprobación:** HU-11 y HU-14. Incorpora los roles Analista contable y GAF y los permisos por rol (ver [ADR-0006](0006-roles-y-cadena-de-aprobacion.md)).
3. **Capa 3 · Historial y versiones:** HU-12 y HU-13.

La asignación completa por issue está en [arquitectura.md](../arquitectura.md#historias-por-capa). El orden de construcción es 1, 2, 3.

## Alternativas consideradas

- **Seguir los 4 grupos y el habilitador del PRD.** Los grupos organizan la lectura, no las dependencias entre entregas.
- **Entregar solo por prioridad MoSCoW** (todas las Must primero). Obligaría a construir comentarios y aprobación sin haber validado antes el cruce con Tesorería.
- **Una sola entrega.** Más riesgo y feedback tardío.

## Consecuencias

- La Capa 1 se puede probar con Tesorería (rol Tesorero) sin esperar el flujo de revisión contable y del GAF.
- El MVP mínimo del PRD (todas las Must) queda completo recién con la Capa 1 más la Capa 2; la Capa 3 solo tiene historias Should.
- La Capa 1 incluye historias no Must (HU-06, HU-07, HU-08) por ser parte del motor, y la exportación Excel, que el PRD dejaba fuera de alcance (P6).
- HU-09 y HU-10 tienen un escenario cada una que se completa en la Capa 2.
