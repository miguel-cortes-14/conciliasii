# Registro de decisiones de arquitectura (ADR)

Decisiones de arquitectura de ConciliaSII en formato MADR resumido: título, estado, fecha, contexto, decisión, alternativas consideradas y consecuencias. El diseño completo está en [arquitectura.md](../arquitectura.md).

| ADR | Decisión | Estado |
| --- | --- | --- |
| [0001](0001-persistencia-sqlite-local.md) | Persistencia en SQLite local (efímera en la demo pública, a propósito) | Aceptada |
| [0002](0002-erp-detras-de-puerto-adaptador.md) | ERP detrás de un puerto con adaptadores | Aceptada |
| [0003](0003-exportacion-excel-openpyxl.md) | Exportación a Excel con openpyxl | Aceptada |
| [0004](0004-ruff-lint-formato.md) | Ruff como linter y formateador | Aceptada |
| [0005](0005-entrega-en-tres-capas.md) | Entrega en tres capas | Aceptada |
| [0006](0006-roles-y-cadena-de-aprobacion.md) | Roles y cadena de aprobación (Tesorero, Analista Contable, Jefa de Contabilidad, GAF) | Propuesto |

Para agregar una decisión nueva, crea `NNNN-titulo-corto.md` con la misma estructura y súmala a esta tabla.
