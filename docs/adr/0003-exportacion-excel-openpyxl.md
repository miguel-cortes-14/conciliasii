# ADR-0003 · Exportación a Excel con openpyxl

- **Estado:** Aceptada (P6 resuelta por el usuario el 2026-10-19: la exportación a Excel queda incluida en el alcance del MVP)
- **Fecha:** 2026-10-19

## Contexto

Contabilidad y Auditoría trabajan con Excel. El PRD v0.2 dejaba "Exportar el detalle a Excel" fuera de alcance y lo condicionaba a la decisión P6; el usuario la resolvió el 2026-10-19 incluyéndola en el MVP (RF-13 en el PRD v0.4). Por otro lado, la persistencia local de la demo es efímera (ADR-0001) y una descarga es la forma más simple de conservar el resultado.

## Decisión

Incluir la exportación en la Capa 1; corresponde a RF-13 del PRD y a HU-16. El módulo `export/excel.py` genera el `.xlsx` con **openpyxl** y devuelve `bytes`, sin importar Streamlit. La página de revisión lo entrega con `st.download_button`. El libro tiene una hoja `Resumen`, una hoja por categoría y una hoja `Sugerencias`; desde la Capa 2 incorpora comentarios (columna y hoja `Comentarios`) y el estado de aprobación.

El PRD ya refleja esta decisión (alcance, RF-13 y P6 resuelta). Pueden descargar el Excel el Tesorero, el Analista Contable, la Jefa de Contabilidad y el Gerente de Administración y Finanzas (GAF).

## Alternativas consideradas

- **Solo CSV.** Más simple, pero sin formato, hojas ni totales.
- **pandas `to_excel` solo.** Útil para volcar tablas, pero con poco control de formato; pandas puede usar openpyxl como motor, y se usa openpyxl directo para formato y filtros.
- **XlsxWriter.** Buena opción de escritura, pero no lee; openpyxl también sirve para verificar el archivo en las pruebas.
- **No exportar hasta cerrar P6.** Deja la demo sin forma de conservar resultados.

## Consecuencias

- Dependencia nueva: `openpyxl` en `requirements.txt`.
- La función es pura y se prueba abriendo los bytes generados con openpyxl.
- Ya no hay conflicto con el PRD: la exportación es parte del alcance.
- Para volúmenes de cientos o pocos miles de filas el rendimiento es suficiente.
