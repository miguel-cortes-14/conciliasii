# ADR-0002 · ERP detrás de un puerto con adaptadores

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto

El PRD define Business Central como ERP y su API como fuente del libro de compras (RF-03), pero la PoC no tiene acceso a un ambiente real. Además P2 (qué fecha define el período) y P7 (si la API estándar expone RUT, tipo y folio) siguen abiertas.

## Decisión

El motor depende de un puerto, `ErpLedgerPort` (un `Protocol` de Python) con `get_purchase_ledger(period) -> list[Documento]`. Hay dos adaptadores en `erp/`: `csv_adapter` (libro simulado desde CSV, usado ahora) y `bc_api_adapter` (stub para la API real, HU-15). Cualquier derivación de campos propia de BC, como obtener tipo y folio desde `External Document No.` si P7 lo exige, queda encapsulada dentro del adaptador. El adaptador activo se elige con `ERP_BACKEND`.

## Alternativas consideradas

- **Leer el CSV directamente desde el motor.** Más corto hoy, pero obliga a reescribir el motor al conectar la API real.
- **Construir `bc_api_adapter` completo sin acceso a BC.** Sería código sin poder probarse y con supuestos sobre P7.
- **Clase base abstracta (ABC).** Equivalente, pero el `Protocol` evita herencia y facilita dobles de prueba.

## Consecuencias

- El motor y las pruebas no cambian al pasar de CSV a API.
- Los datos de ejemplo cumplen el mismo contrato que la API real, por lo que la demo es representativa.
- Hay que mantener el contrato de `Documento` estable y probar cada adaptador contra él.
- El stub deja HU-15 parcialmente verificable hasta cerrar P7.
