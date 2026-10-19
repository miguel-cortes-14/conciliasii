# ADR-0003 · Exportación a Excel con openpyxl

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto

Contabilidad y Auditoría trabajan con Excel. El PRD deja "Exportar el detalle a Excel" fuera de alcance y lo condiciona a la decisión P6. Por otro lado, la persistencia local de la demo es efímera (ADR-0001) y una descarga es la forma más simple de conservar el resultado.

## Decisión

Incluir la exportación en la Capa 1. El módulo `export/excel.py` genera el `.xlsx` con **openpyxl** y devuelve `bytes`, sin importar Streamlit. La página de revisión lo entrega con `st.download_button`. El libro tiene una hoja `Resumen`, una hoja por categoría y una hoja `Sugerencias`; desde la Capa 2 incorpora comentarios (columna y hoja `Comentarios`) y el estado de aprobación.

Esta decisión adelanta una necesidad que el PRD dejaba pendiente; el PRD debe actualizarse (alcance y P6) al validar el diseño.

## Alternativas consideradas

- **Solo CSV.** Más simple, pero sin formato, hojas ni totales.
- **pandas `to_excel` solo.** Útil para volcar tablas, pero con poco control de formato; pandas puede usar openpyxl como motor, y se usa openpyxl directo para formato y filtros.
- **XlsxWriter.** Buena opción de escritura, pero no lee; openpyxl también sirve para verificar el archivo en las pruebas.
- **No exportar hasta cerrar P6.** Deja la demo sin forma de conservar resultados.

## Consecuencias

- Dependencia nueva: `openpyxl` en `requirements.txt`.
- La función es pura y se prueba abriendo los bytes generados con openpyxl.
- Se amplía el alcance respecto del PRD, lo que debe validar el PO.
- Para volúmenes de cientos o pocos miles de filas el rendimiento es suficiente.
