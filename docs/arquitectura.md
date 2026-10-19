# Arquitectura · Conciliador RCV SII vs Business Central

**Fecha:** 2026-10-19 · **Fase:** 2 · Diseño · **Product Owner:** Miguel Cortés · Fuentes: [PRD.md](PRD.md), [historias.md](historias.md)

Este documento define cómo se construye la PoC de ConciliaSII: una app Python + Streamlit que cruza el Registro de Compras (RCV) del SII contra el libro de compras de Business Central (BC), simulado con un CSV detrás de un adaptador. Las decisiones con alternativas y consecuencias están en los [ADR](adr/README.md).

Convenciones: los IDs `RF-xx` y `RN-xx` son los del PRD; `HU-xx` son las historias; `P1`..`P7` son las decisiones pendientes del PRD. Lo que el PRD no define se marca como **Supuesto** (resumen en [Supuestos y brechas](#supuestos-y-brechas-respecto-del-prd)).

## Principios

1. **Lógica pura separada de Streamlit.** El motor (`ingest`, `engine`, `export`, `workflow`) nunca importa `streamlit`; las páginas de `pages/` son delgadas: leen entradas, llaman a un servicio y dibujan el resultado. Todo lo importante se prueba con `pytest` sin levantar la UI.
2. **El ERP detrás de un puerto.** El motor depende de `ErpLedgerPort`, no de un ERP concreto. Hoy lo implementa `csv_adapter`; mañana `bc_api_adapter` (HU-15). Ver [ADR-0002](adr/0002-erp-detras-de-puerto-adaptador.md).
3. **Todo acceso a datos pasa por `storage/repository.py`.** Ningún otro módulo conoce SQLite. Esto permite cambiar el respaldo sin tocar motor, flujo ni páginas. Ver [ADR-0001](adr/0001-persistencia-sqlite-local.md).
4. **Entrega incremental en tres capas**, cada una usable por sí sola. Ver [ADR-0005](adr/0005-entrega-en-tres-capas.md) y [Capas de entrega](#capas-de-entrega).

## Estructura de carpetas

```text
conciliasii/
├── app.py                          # entrada Streamlit: configuración de página, usuario y rol activo, navegación
├── pages/
│   ├── 1_Cargar_y_Conciliar.py     # período, carga CSV SII, traer libro ERP, ejecutar
│   ├── 2_Revision.py               # resumen, detalle por categoría, sugerencias, comentarios, descarga Excel
│   ├── 3_Aprobacion.py             # enviar a revisión, aprobar, rechazar, reabrir
│   └── 4_Historial.py              # períodos, versiones, vista solo lectura
├── src/conciliasii/
│   ├── config.py                   # parámetros (ver "Configuración"); sin dependencias de Streamlit
│   ├── domain/
│   │   ├── models.py               # Periodo, Documento, Categoria, Resultado, Sugerencia, Comentario...
│   │   └── errors.py               # ArchivoInvalidoError, ComentariosFaltantesError, TransicionInvalidaError...
│   ├── ingest/
│   │   └── sii_csv.py              # lectura y validación del CSV del SII; normalización de RUT
│   ├── erp/
│   │   ├── port.py                 # ErpLedgerPort (Protocol)
│   │   ├── csv_adapter.py          # libro de BC simulado desde CSV
│   │   └── bc_api_adapter.py       # stub de la API real (HU-15)
│   ├── engine/
│   │   ├── matcher.py              # filtro de universo, llave, cruce, vecinos, duplicados, sugerencias
│   │   └── classifier.py           # asigna una categoría por documento (RN-05, RN-06)
│   ├── export/
│   │   └── excel.py                # arma el libro Excel con openpyxl (devuelve bytes)
│   ├── workflow/
│   │   └── approval.py             # estados, permisos por rol, comentarios obligatorios, aprobar/rechazar/reabrir
│   └── storage/
│       ├── schema.sql              # DDL de SQLite
│       └── repository.py           # interfaz del repositorio + implementación SQLite
├── data/samples/                   # CSV de ejemplo del SII y del libro de BC simulado
├── tests/                          # pytest: ingest, matcher, classifier, excel, approval, repository
├── requirements.txt                # streamlit, pandas, openpyxl
├── requirements-dev.txt            # ruff, pytest
└── pyproject.toml                  # configuración de ruff
```

Reglas de dependencia (de afuera hacia adentro; nunca al revés):

```text
pages/ , app.py  ->  workflow, engine, ingest, export, erp (puerto), storage (interfaz)  ->  domain
```

`domain` no importa nada del proyecto. `engine` no conoce `storage` ni `erp.csv_adapter`: recibe listas de `Documento` ya cargadas. Un servicio de aplicación (función `ejecutar_conciliacion(...)` en `engine/` o `workflow/`, sin Streamlit) orquesta ingest, puerto, matcher, clasificador y repositorio; las páginas solo lo invocan.

Instalación de dependencias y calidad de código:

```bash
pip install -r requirements-dev.txt
ruff check .             # lint (E, F, I, B, UP)
ruff format --check .    # verifica formato sin modificar
pytest
```

La configuración de ruff vive en [`pyproject.toml`](../pyproject.toml) (línea de 100, `py311`). Ver [ADR-0004](adr/0004-ruff-lint-formato.md).

## Roles y responsabilidades

El flujo tiene tres roles de negocio en cadena: el **Tesorero** concilia, el **Analista contable** revisa, comenta y da la primera aprobación, y el **GAF** da la aprobación final. Cada acción de la app la ejecuta un solo rol; el [flujo](#flujo-completo) y la [máquina de estados](#flujo-de-aprobación) lo muestran paso a paso.

**Supuesto a confirmar:** la cadena exacta Tesorero -> Analista contable -> GAF y que el Analista contable escribe los comentarios obligatorios es una interpretación del PO y no está confirmada. La nomenclatura difiere del PRD y de las historias; ver la [equivalencia](#equivalencia-con-los-roles-del-prd-y-las-historias) y [Supuestos y brechas](#supuestos-y-brechas-respecto-del-prd).

| Rol | Área | Qué hace | Qué NO puede hacer | Estados en los que actúa |
| --- | --- | --- | --- | --- |
| Tesorero | Tesorería | Responsable de la conciliación: elige el período, carga el CSV del SII, trae el libro del ERP y ejecuta la conciliación, acepta o descarta sugerencias de calce, vuelve a conciliar tras corregir en BC, descarga el Excel y envía el período a revisión | Comentar diferencias, aprobar, rechazar ni reabrir | `Borrador` |
| Analista contable | Contabilidad | Revisa las diferencias, escribe el comentario obligatorio de cada una, hace la primera aprobación (nivel 1) o rechaza con motivo devolviendo el período a Tesorería | Conciliar, cargar archivos, decidir sugerencias, dar la aprobación final ni reabrir | `EnRevisionContable` |
| GAF (último aprobador) | Por confirmar | Aprobación final del período; tras ella la versión queda inmutable. Puede rechazar con motivo (vuelve a Tesorería) y reabrir un período aprobado | Conciliar, comentar ni dar la primera aprobación | `PendienteGAF` y `Aprobado` (reabrir) |
| Administrador | TI | Configura la conexión con la API de Business Central (HU-15). Está en el PRD (sección "Usuarios y roles", con "supuesto") | No participa del flujo de conciliación ni de aprobación | Ninguno |

El Administrador (TI) se mantiene porque el PRD lo define y HU-15 lo usa. En la PoC no tiene pantalla: la configuración del adaptador se lee de variables de entorno o `st.secrets` (ver [Configuración](#configuración)), de modo que el selector de rol de la app ofrece solo Tesorero, Analista contable y GAF.

### Matriz de permisos por acción

`Ejecuta` = puede hacerlo; `Consulta` = solo lectura; `-` = no puede. El estado indica cuándo se puede ejecutar. El servicio (`workflow/approval.py`) valida rol y estado en cada acción; la UI solo oculta o deshabilita lo que no corresponde.

| Acción | Tesorero | Analista contable | GAF | Administrador (TI) | Estado requerido | Capa |
| --- | --- | --- | --- | --- | --- | --- |
| Seleccionar período y cargar el CSV del SII | Ejecuta | - | - | - | Sin versión vigente, o `Borrador` | 1 |
| Conciliar (traer libro del ERP y cruzar) | Ejecuta | - | - | - | Sin versión vigente, o `Borrador` | 1 |
| Aceptar o descartar sugerencia de calce | Ejecuta | - | - | - | `Borrador` | 1 |
| Ver resumen y detalle | Consulta | Consulta | Consulta | - | Cualquiera | 1 |
| Descargar Excel | Ejecuta | Ejecuta | Ejecuta | - | Cualquiera | 1 |
| Comentar una diferencia | - | Ejecuta | - | - | `EnRevisionContable` | 2 |
| Enviar a revisión | Ejecuta | - | - | - | `Borrador` | 2 |
| Aprobar nivel 1 | - | Ejecuta | - | - | `EnRevisionContable` | 2 |
| Aprobar final | - | - | Ejecuta | - | `PendienteGAF` | 2 |
| Rechazar (con motivo) | - | Ejecuta | Ejecuta | - | `EnRevisionContable` (Analista contable) o `PendienteGAF` (GAF) | 2 |
| Reabrir un período aprobado | - | - | Ejecuta | - | `Aprobado` | 2 |
| Volver a conciliar (nueva versión) | Ejecuta | - | - | - | `Borrador`, o `Aprobado` tras reabrir | 3 |
| Ver historial y versiones | Consulta | Consulta | Consulta | - | Cualquiera | 3 |
| Configurar la conexión con BC | - | - | - | Ejecuta | No aplica | 1 (variables de entorno y stub) |

Los permisos por rol se entregan por capa: en la **Capa 1** solo existe el Tesorero (el selector ofrece ese rol; no hay flujo de aprobación todavía); en la **Capa 2** se agregan el Analista contable y el GAF junto con `workflow/approval.py`, la tabla de permisos y los errores de rol; en la **Capa 3** los tres roles consultan el historial.

### Equivalencia con los roles del PRD y las historias

El PRD (sección "Usuarios y roles") y las historias usan otra nomenclatura. No se modificaron `PRD.md` ni `historias.md`; esta es la equivalencia que usa el diseño:

| En el PRD y las historias | En este diseño |
| --- | --- |
| Analista de conciliación (Tesorería) / "analista de Tesorería" | Tesorero |
| Aprobador (Contabilidad) / "aprobador de Contabilidad" | Analista contable (primera aprobación) y GAF (aprobación final) |
| Administrador (TI) | Administrador (TI), sin cambios |

Casos puntuales: HU-11 (Comentar un documento) dice "analista de Tesorería" y aquí lo hace el Analista contable; HU-09, HU-13 y HU-14 dicen "aprobador de Contabilidad" y aquí intervienen el Analista contable y el GAF (HU-14 se cumple en dos niveles); el escenario "Analista no puede aprobar" de HU-14 equivale a "el Tesorero no puede aprobar"; HU-12 (volver a conciliar) la ejecuta el Tesorero.

## Flujo completo

Cada carril indica quién ejecuta el paso. "Sistema" agrupa lo que hace la app sin intervención de una persona.

```mermaid
flowchart TD
  subgraph TES["Tesorero (Tesorería)"]
    A["Elige el período (RF-01)"]
    B[Sube el CSV del SII]
    S2["Confirma o descarta sugerencias (RF-08)"]
    X["Descarga el Excel"]
    ENV[Envía el período a revisión]
    COR["Corrige en BC y vuelve a conciliar (RF-10)"]
  end
  subgraph SIS[Sistema]
    C["ingest/sii_csv: leer y validar<br/>columnas, RUT y período (RF-02)"]
    E1[Mensaje de error y rechazo del archivo]
    D["Filtrar universo SII<br/>tipos 33 y 34, estado Registro (RF-04)"]
    P["ErpLedgerPort.get_purchase_ledger(período)<br/>más períodos vecinos (RF-03)"]
    E2[Error y reintento sin perder el CSV]
    F["Filtrar universo ERP<br/>tipos 33 y 34 y documentos sin llave"]
    M["engine/matcher: cruce por RUT + tipo + folio (RN-03)"]
    S["Genera sugerencias de calce aproximado"]
    K["engine/classifier: una categoría por documento (RN-05)"]
    R[("storage/repository<br/>periodo, ejecucion, resultado")]
    V["Resumen y detalle (RF-06, RF-07)<br/>visibles para los tres roles"]
    VAL{"Valida que toda diferencia<br/>tenga comentario"}
    H["Historial y versiones (RF-11)<br/>consultan los tres roles"]
  end
  subgraph ANA["Analista contable (Contabilidad)"]
    REV[Revisa las diferencias]
    COM["Escribe el comentario de cada diferencia (RF-09)"]
    AP1[Solicita la aprobación nivel 1]
    RJ1[Rechaza con motivo]
  end
  subgraph GAF["GAF (último aprobador)"]
    G{"Decide la aprobación final"}
    RJ2[Rechaza con motivo]
    OK["Aprobado: versión inmutable"]
    REA[Reabre el período aprobado]
  end
  A --> B --> C
  C -->|archivo inválido| E1
  C -->|válido| D
  A --> P
  P -->|ERP no responde| E2
  P --> F
  D --> M
  F --> M
  M --> S --> S2
  M --> K
  S2 --> K
  K --> R --> V
  V --> X
  V --> ENV --> REV --> COM --> AP1 --> VAL
  VAL -->|faltan comentarios| COM
  VAL -->|completo, pasa a PendienteGAF| G
  G -->|aprueba| OK --> H
  G -->|rechaza| RJ2 --> COR
  RJ1 --> COR
  REV --> RJ1
  OK --> REA --> COR
  COR --> P
  classDef c1 fill:#e8f1ff,stroke:#3b6fd4;
  classDef c2 fill:#fff1e0,stroke:#d4893b;
  classDef c3 fill:#e6f6e8,stroke:#3b9a4a;
  class A,B,S2,X,C,E1,D,P,E2,F,M,S,K,R,V c1;
  class ENV,REV,COM,AP1,RJ1,VAL,G,RJ2,OK,REA c2;
  class COR,H c3;
```

Colores: azul = Capa 1, naranja = Capa 2, verde = Capa 3. El ciclo de corrección (RF-10) lo hace siempre el Tesorero: si el Analista contable o el GAF rechazan, o si el GAF reabre un período aprobado, el período vuelve a Tesorería, que corrige en Business Central, trae el libro de nuevo y cruza una versión nueva. La validación del comentario obligatorio ocurre en la aprobación de nivel 1 del Analista contable (ver [Flujo de aprobación](#flujo-de-aprobación)).

## Contratos de entrada

Todos los CSV son UTF-8, separados por `;`, con montos enteros en CLP (sin decimales ni separador de miles) y fechas `AAAA-MM-DD`.

### Registro de Compras del SII (propuesto)

El PRD no define columnas; esta es la propuesta para la PoC (**Supuesto**, PRD: "el formato del CSV del SII se mantiene estable").

| Columna | Uso |
| --- | --- |
| `Tipo Doc` | Tipo de documento (33, 34; el resto se excluye, RF-04) |
| `RUT Proveedor` | RUT emisor; parte de la llave (RN-03), se normaliza |
| `Razon Social` | Nombre del proveedor (informativo) |
| `Folio` | Parte de la llave |
| `Fecha Docto` | Fecha de emisión (campo comparado, RN-04) |
| `Fecha Recepcion` | Fecha de recepción en el SII (informativa) |
| `Monto Exento` | Campo comparado (RN-04) |
| `Monto Neto` | Campo comparado (RN-04) |
| `Monto IVA Recuperable` | Campo comparado (RN-04) |
| `Monto Total` | Campo comparado (RN-04); base del calce aproximado (RN-08) |

Brechas de este contrato frente al PRD (todas **Supuesto**, se cierran con los CSV reales del SII):

- RF-02 exige validar RUT y período del archivo, y RF-04 exige filtrar por estado "Registro". La lista propuesta no trae esos datos. Para la PoC el archivo incluye tres columnas adicionales: `RUT Receptor`, `Periodo` (`AAAA-MM`) y `Estado` (`Registro`, `Pendiente`, `Reclamado`, `No incluir`). Si el export real no las trae, el RUT y el período saldrían del nombre del archivo o de un formulario, y el estado de la pestaña del portal desde donde se descargó.
- RN-04 también valida IVA no recuperable (código y monto), IVA de uso común y otros impuestos (código, tasa y monto). Quedan como columnas opcionales (`Codigo IVA No Rec`, `Monto IVA No Rec`, `Monto IVA Uso Comun`, `Codigo Otro Impuesto`, `Tasa Otro Impuesto`, `Monto Otro Impuesto`); si faltan se asumen en cero. El conjunto de campos comparados es una lista en `config.py` para ampliarla sin tocar el clasificador.
- La detección de formato (HU-02, "Formato no reconocido") usa las diez columnas propuestas como obligatorias y reporta cuáles faltan.

### Libro de compras de BC simulado (propuesto)

| Columna | Uso |
| --- | --- |
| `Entry No.` | Número interno del movimiento; se muestra en alertas de duplicado (RN-09) y en "Sin llave" (HU-03) |
| `Posting Date` | Fecha de registro contable; candidata a definir el período (P2) |
| `Document Date` | Fecha del documento; candidata a definir el período (P2) y se compara con `Fecha Docto` |
| `Document No.` | Número del documento en BC (informativo) |
| `External Document No.` | Número del documento del proveedor (respaldo para derivar tipo y folio, ver P7) |
| `VAT Registration No.` | RUT del proveedor; parte de la llave |
| `Vendor Name` | Nombre del proveedor (informativo) |
| `DTE Type` | Tipo de documento; parte de la llave |
| `DTE Folio` | Folio; parte de la llave |
| `Amount Excl. VAT` | Base imponible o exenta (ver mapeo) |
| `VAT Amount` | IVA |
| `Amount Incl. VAT` | Total |

Mapeo del adaptador a `Documento` (**Supuesto**, el PRD no define los campos de BC): `Amount Excl. VAT` es `monto_neto` en documentos 33 y `monto_exento` en documentos 34; `VAT Amount` es `monto_iva_recuperable`; `Amount Incl. VAT` es `monto_total`. Así un tipo 34 con IVA distinto de cero en BC queda en Diferencia de monto con el campo "IVA" distinto (HU-05, RN-04). Solo se leen facturas registradas (RN-02); el CSV simulado ya las contiene.

Si P7 muestra que la API estándar de BC no expone tipo de documento ni folio, `bc_api_adapter` los deriva de `External Document No.` (y el RUT del proveedor desde la ficha). Esa derivación queda encapsulada en `erp/`: el motor sigue recibiendo `Documento` con `rut`, `tipo_doc` y `folio`. Si falta alguno, el documento se informa como "Sin llave" y no participa del cruce (HU-03, HU-15).

## Puerto del ERP

```python
class ErpLedgerPort(Protocol):
    def get_purchase_ledger(self, period: Periodo) -> list[Documento]:
        """Facturas de compra registradas cuyo período (ERP_PERIOD_DATE_FIELD) coincide con `period`."""
```

- `csv_adapter` lee el CSV simulado, aplica el mapeo y filtra por el período según `ERP_PERIOD_DATE_FIELD`.
- `bc_api_adapter` es un stub que lanza `NotImplementedError` con un mensaje claro; su forma (autenticación, paginación, derivación de llave) se diseña cuando se cierre P7.
- Los períodos vecinos (RN-07) los resuelve el servicio de aplicación llamando al puerto una vez por período del rango; el puerto no conoce la lógica de vecinos.
- La fecha y hora de extracción y la cantidad de documentos (RF-03) las mide el servicio de aplicación y se guardan en la ejecución.
- Los errores del ERP se propagan como `ErpNoDisponibleError` con la causa; el CSV del SII ya cargado se conserva para reintentar (HU-03).

## Configuración

`config.py` lee variables de entorno (con `st.secrets` solo en la capa de las páginas, nunca en el motor).

| Parámetro | Valor por defecto | Decisión relacionada |
| --- | --- | --- |
| `EMPRESA_RUT` | RUT de la empresa de ejemplo | RF-02: validar el RUT receptor del archivo |
| `ERP_BACKEND` | `csv` (`bc_api` más adelante) | HU-15 |
| `ERP_CSV_PATH` | `data/samples/libro_bc.csv` | |
| `ERP_PERIOD_DATE_FIELD` | `posting_date` (o `document_date`) | **P2**: qué fecha define el período. El valor por defecto es un supuesto |
| `AMOUNT_TOLERANCE` | `0` (comparación exacta) | **P3**: exacto o ±$1 |
| `NEIGHBOR_PERIODS` | `2,1` (2 anteriores y 1 siguiente) | **P4**: propuesta del PRD |
| `STORAGE_BACKEND` | `sqlite` | ADR-0001 |
| `SQLITE_PATH` | `data/conciliasii.db` | ADR-0001 |
| `CAMPOS_COMPARADOS` | lista de RN-04 disponible en los CSV | RN-04 |

Las decisiones P2, P3 y P4 se cierran cambiando un valor, no código. P5 (volumen) solo afecta el rendimiento esperado: con unos cientos de documentos al mes el cruce en memoria con pandas o diccionarios toma segundos. P6 (Excel) se trata en [Exportación a Excel](#exportación-a-excel).

## Motor de conciliación

1. **Normalizar la llave** (RN-03): RUT sin puntos, con guion y dígito verificador en mayúscula; llave = `rut|tipo_doc|folio`.
2. **Filtrar el universo** (RN-01, RF-04): SII solo tipos 33 y 34 en estado Registro; ERP solo tipos 33 y 34. Se cuentan los excluidos por tipo y por estado. Los documentos de BC sin llave van a una lista aparte "Sin llave".
3. **Detectar duplicados** (RN-09): una llave repetida dentro de la misma fuente se marca como alerta dentro de su categoría y conserva los `Entry No.`.
4. **Cruzar**: por llave, contra el ERP del período y los períodos vecinos (RN-07).
5. **Clasificar** (`classifier.py`, RN-05 y RN-06), con esta precedencia para que cada documento caiga en exactamente una categoría (RF-05):
   - llave solo en SII (ni en el período ni en los vecinos de BC): **Solo en SII**;
   - llave solo en BC dentro del período: **Solo en ERP**;
   - llave en ambos, pero BC la tiene en otro período: **Diferencia de período** (si además hay montos distintos, igual es Diferencia de período y el detalle lista los campos distintos, RN-06);
   - llave en ambos y en el mismo período con algún campo distinto (según `AMOUNT_TOLERANCE`): **Diferencia de monto**;
   - llave en ambos y todos los campos iguales: **Cuadrado**.
6. **Sugerir calces aproximados** (`matcher.py`, RN-08, RF-08): solo entre Solo en SII y Solo en ERP con el mismo RUT y el mismo monto total. Una sugerencia no cambia nada hasta que el usuario la confirme; al confirmar, ambos documentos pasan a Diferencia de monto con folio o tipo como campo distinto. Un descarte no vuelve a mostrarse en ese período.

Invariante verificable (HU-05): la suma de documentos de todas las categorías es igual al universo filtrado.

**Supuesto:** la búsqueda en períodos vecinos se hace del SII hacia BC, porque el CSV cargado cubre un solo período. Un documento de BC del período que no está en el CSV es Solo en ERP, aunque el SII lo tenga en otro mes; detectar ese caso exigiría otros CSV del SII. Conviene confirmarlo con el PO al cerrar P4.

## Exportación a Excel

`export/excel.py` expone una función pura que recibe la ejecución, sus resultados (y, desde la Capa 2, comentarios y estado) y devuelve los bytes de un `.xlsx` armado con **openpyxl**. No importa Streamlit. La página `2_Revision.py` lo entrega con `st.download_button`, de modo que el usuario se lleva el resultado aunque la base local se pierda (ver [Limitaciones conocidas](#limitaciones-conocidas)). Detalle de la decisión en [ADR-0003](adr/0003-exportacion-excel-openpyxl.md).

Hojas del libro:

| Hoja | Contenido |
| --- | --- |
| `Resumen` | Período, versión, estado, fecha de extracción del ERP, universo y excluidos por tipo y por estado; por categoría: cantidad y montos SII vs ERP (RF-06) con totales; "Sin llave"; desde la Capa 2, avance de comentarios |
| `Cuadrado`, `Diferencia de monto`, `Diferencia de período`, `Solo en SII`, `Solo en ERP` | Una hoja por categoría, una fila por documento: llave, valores SII y ERP lado a lado, campos distintos, diferencia calculada, alerta de duplicado y `Entry No.`; filtros automáticos y fila de encabezado fija |
| `Sugerencias` | Calces aproximados con su estado (pendiente, confirmada, descartada) |
| `Comentarios` (Capa 2) | Un comentario por fila: llave, autor, fecha y hora, texto |

Desde la Capa 2 las hojas de categoría suman una columna "Comentarios" (comentarios concatenados por documento) y el resumen incluye el estado y, si existe, quién aprobó y cuándo.

**Conflicto con el PRD:** el PRD deja fuera de alcance "Exportar el detalle a Excel" y lo condiciona a la decisión **P6** (`PRD.md`, línea 48 y línea 125). Se incluye en la Capa 1 por decisión de arquitectura del PO en esta fase; P6 queda registrada como respondida de hecho y debe actualizarse en el PRD al validar este diseño.

## Modelo de datos (SQLite)

Cinco tablas del diseño base más una auxiliar para las sugerencias de calce (**Supuesto**: HU-07 exige recordar quién confirmó o descartó y no mostrar de nuevo un descarte). El DDL vive en `storage/schema.sql`.

```mermaid
erDiagram
  periodo ||--o{ ejecucion : "versiones"
  periodo ||--o{ comentario : "por llave"
  periodo ||--o{ sugerencia : "por par de llaves"
  ejecucion ||--o{ resultado : "uno por llave"
  ejecucion ||--o{ aprobacion : "decisiones"
  periodo {
    int id PK
    text rut_empresa
    int anio
    int mes
  }
  ejecucion {
    int id PK
    int periodo_id FK
    int version
    text estado
    text creado_por
    text creado_en
    text extraido_erp_en
    text nombre_csv
    text parametros_json
    text resumen_json
  }
  resultado {
    int id PK
    int ejecucion_id FK
    text llave
    text categoria
    text periodo_erp
    text campos_distintos_json
    text valores_sii_json
    text valores_erp_json
    int alerta_duplicado
  }
  comentario {
    int id PK
    int periodo_id FK
    text llave
    int ejecucion_id
    text autor
    text rol
    text creado_en
    text texto
  }
  aprobacion {
    int id PK
    int ejecucion_id FK
    text decision
    text usuario
    text rol
    int nivel
    text decidido_en
    text motivo
  }
  sugerencia {
    int id PK
    int periodo_id FK
    text llave_sii
    text llave_erp
    text estado
    text decidido_por
    text decidido_en
  }
```

| Tabla | Notas |
| --- | --- |
| `periodo` | Único por `(rut_empresa, anio, mes)`. Una empresa en el MVP. |
| `ejecucion` | Una fila por versión (`version` 1, 2, 3...) de un período (RN-10). `estado` toma `Borrador`, `EnRevisionContable`, `PendienteGAF` o `Aprobado`. Guarda el nombre del CSV, la fecha de extracción del ERP, los parámetros usados (tolerancia, campo de período, vecinos), el resumen y los conteos de excluidos y de "Sin llave". La versión vigente es la de mayor `version`. |
| `resultado` | Un documento clasificado en una versión: exactamente una `categoria` (RF-05), `alerta_duplicado`, valores SII y ERP y campos distintos. `UNIQUE(ejecucion_id, llave)`. |
| `comentario` | Solo se inserta, nunca se actualiza ni se borra (RF-09). `autor` y `rol` registran quién comentó (hoy solo el Analista contable; la columna `rol` permite habilitar a otros roles sin cambiar el esquema). Se asocia al `periodo_id` y la `llave`, no a una versión: así se conservan al volver a conciliar (RF-10, RN-10). `ejecucion_id` registra en qué versión se escribió; una versión N solo muestra comentarios de versiones menores o iguales a N, por lo que una versión aprobada no cambia. |
| `aprobacion` | Registro de decisiones sobre una versión: `AprobadoNivel1` (`nivel` 1, Analista contable), `AprobadoFinal` (`nivel` 2, GAF), `Rechazado` (con `motivo` obligatorio; `nivel` indica quién rechazó) o `Reabierto` (GAF), con `usuario`, `rol` y fecha y hora (HU-14). No es una pista de auditoría completa (fuera de alcance, P6). |
| `sugerencia` | Par `(llave_sii, llave_erp)` con estado `Pendiente`, `Confirmada` o `Descartada`, y quién y cuándo decidió (HU-07). Pertenece al período, de modo que un descarte persiste entre versiones. |

El nombre del usuario y su rol (Tesorero, Analista contable o GAF) se obtienen de un selector en la barra lateral (**Supuesto**: sin autenticación real en la PoC; el PRD marca la gestión de usuarios como supuesto del Administrador). En la Capa 1 el selector solo ofrece Tesorero.

### Interfaz del repositorio

Todo el acceso a datos pasa por una interfaz (`Protocol`) definida en `storage/repository.py`; `SqliteRepository` es la única implementación de la PoC. Motor, flujo y páginas dependen de la interfaz, nunca de `sqlite3`. Las páginas obtienen la instancia con una fábrica que lee `STORAGE_BACKEND`.

```python
class ConciliacionRepository(Protocol):
    # Capa 1
    def obtener_o_crear_periodo(self, rut: str, anio: int, mes: int) -> Periodo: ...
    def crear_ejecucion(
        self, periodo_id: int, meta: MetaEjecucion, resultados: list[Resultado]
    ) -> Ejecucion: ...
    def ejecucion_vigente(self, periodo_id: int) -> Ejecucion | None: ...
    def listar_resultados(self, ejecucion_id: int) -> list[Resultado]: ...
    def guardar_decision_sugerencia(self, periodo_id: int, sugerencia: Sugerencia) -> None: ...
    def listar_sugerencias(self, periodo_id: int) -> list[Sugerencia]: ...
    # Capa 2
    def agregar_comentario(
        self, periodo_id: int, llave: str, ejecucion_id: int, autor: str, rol: Rol, texto: str
    ) -> Comentario: ...
    def listar_comentarios(self, periodo_id: int, hasta_version: int) -> list[Comentario]: ...
    def cambiar_estado(self, ejecucion_id: int, estado: Estado) -> None: ...
    def registrar_decision(
        self,
        ejecucion_id: int,
        decision: Decision,
        usuario: str,
        rol: Rol,
        nivel: int | None,
        motivo: str | None,
    ) -> None: ...
    # Capa 3
    def listar_periodos(self) -> list[ResumenPeriodo]: ...
    def listar_ejecuciones(self, periodo_id: int) -> list[Ejecucion]: ...
```

Las firmas son una propuesta; lo que se fija es la frontera (nada fuera de `storage/` sabe cómo se persiste). Cada operación que cambia varias filas (crear ejecución con sus resultados, aprobar) debe ser atómica dentro del repositorio.

## Flujo de aprobación

Los estados viven en `ejecucion.estado` y las transiciones en `workflow/approval.py`. Cada transición la dispara un rol concreto (ver la [matriz de permisos](#matriz-de-permisos-por-acción)).

```mermaid
stateDiagram-v2
  [*] --> Borrador : Tesorero concilia (nueva versión)
  Borrador --> EnRevisionContable : Tesorero envía a revisión
  EnRevisionContable --> PendienteGAF : Analista contable aprueba nivel 1 (valida comentarios)
  EnRevisionContable --> Borrador : Analista contable rechaza (motivo obligatorio)
  PendienteGAF --> Aprobado : GAF aprueba final
  PendienteGAF --> Borrador : GAF rechaza (motivo obligatorio)
  Aprobado --> [*]
  note right of Aprobado
    GAF puede reabrir. La versión aprobada queda intacta
    y el Tesorero concilia una versión nueva en Borrador.
  end note
```

Reglas (P1, HU-14):

- **Quién puede qué.** El Tesorero concilia, decide las sugerencias de calce y envía a revisión (`Borrador` a `EnRevisionContable`). El Analista contable comenta, aprueba el nivel 1 (`EnRevisionContable` a `PendienteGAF`) o rechaza. El GAF aprueba el nivel final (`PendienteGAF` a `Aprobado`), rechaza o reabre. Ver [Roles y responsabilidades](#roles-y-responsabilidades).
- **Comentario obligatorio por diferencia: se valida en la aprobación de nivel 1.** El PRD condiciona la aprobación a los comentarios: P1 (`PRD.md`, línea 120: Contabilidad "no puede aprobar si quedan diferencias sin comentario") y la métrica "Diferencias sin comentario al cierre = 0" (línea 111). Como el Analista contable representa a Contabilidad y es quien escribe los comentarios, `aprobar_nivel1()` solo procede si todo `resultado` cuya categoría no es Cuadrado tiene al menos un comentario no vacío (tras `strip()`) para su llave. Si no, lanza `ComentariosFaltantesError` con la lista de documentos pendientes y la cantidad que falta (HU-14). El GAF recibe el período ya comentado.
- **Doble barrera.** La UI deshabilita "Aprobar nivel 1" mientras haya pendientes, y el servicio vuelve a validar al ejecutar. Por seguridad, `aprobar_final()` repite la validación (los comentarios no se pueden borrar, así que en la práctica no falla). La regla no depende de la interfaz.
- **Permisos por rol.** El servicio recibe el rol del actor y consulta la tabla de permisos; si el rol no corresponde lanza `RolNoAutorizadoError`, y si el estado no corresponde, `TransicionInvalidaError`. Un Tesorero no ve la opción de aprobar.
- **Rechazo.** Lo hace el Analista contable (desde `EnRevisionContable`) o el GAF (desde `PendienteGAF`). Exige un motivo (texto no vacío) y devuelve la versión a `Borrador`, es decir, a Tesorería; el motivo, el rol y el nivel quedan en `aprobacion`.
- **Inmutabilidad.** Una versión `Aprobado` no admite nuevos comentarios, cambios de sugerencias ni modificaciones de resultados; el servicio lanza `TransicionInvalidaError`. Una corrección es una **versión nueva**. Los comentarios solo se escriben en `EnRevisionContable`.
- **Reabrir (Supuesto).** HU-14 dice que "Contabilidad debe reabrirlo" pero el PRD no define el mecanismo ni quién. Se modela como una decisión `Reabierto` del GAF sobre la versión aprobada, que habilita al Tesorero a crear una versión nueva en `Borrador`; la versión aprobada queda intacta.
- **Reconciliar.** Un período con versión vigente `Aprobado` (y sin `Reabierto` posterior) no se puede volver a conciliar. Mientras la versión está en `EnRevisionContable` o `PendienteGAF` tampoco: primero debe rechazarse.

Errores del módulo (`domain/errors.py`): `ComentariosFaltantesError`, `RolNoAutorizadoError`, `TransicionInvalidaError`, `MotivoRequeridoError`.

## Capas de entrega

Cada capa deja la app usable y se puede liberar por separado. Detalle y alternativas en [ADR-0005](adr/0005-entrega-en-tres-capas.md).

- **Capa 1 · Núcleo con descarga Excel.** Cargar el CSV del SII, traer el libro del ERP por el puerto, filtrar, cruzar, clasificar, sugerir calces, ver resumen y detalle, y descargar el Excel.
- **Capa 2 · Comentarios y aprobación.** Comentarios por documento (Analista contable) y aprobación del período en dos niveles (Analista contable y GAF) con comentario obligatorio por diferencia. Agrega los roles Analista contable y GAF; la Capa 1 solo conoce al Tesorero.
- **Capa 3 · Historial y versiones.** Lista de períodos, versiones, volver a conciliar conservando comentarios y vista de versiones anteriores en solo lectura.

### Historias por capa

Cada historia está en exactamente una capa. Los issues #3 a #17 corresponden a HU-01 a HU-15 en ese orden (issue = HU + 2).

| Issue | HU | Título | MoSCoW | Capa | Justificación breve | Dependencias / decisiones pendientes |
| --- | --- | --- | --- | --- | --- | --- |
| [#3](https://github.com/miguel-cortes-14/conciliasii/issues/3) | HU-01 | Seleccionar el período a conciliar | Must | 1 | Todo lo demás cuelga del período; sin él no hay carga ni cruce | Repositorio (`periodo`); el escenario "período ya conciliado" muestra la última versión guardada |
| [#4](https://github.com/miguel-cortes-14/conciliasii/issues/4) | HU-02 | Cargar el CSV del Registro de Compras | Must | 1 | Primer insumo del cruce (`ingest/sii_csv.py`) | HU-01; formato del CSV (supuesto, ver contratos) |
| [#5](https://github.com/miguel-cortes-14/conciliasii/issues/5) | HU-03 | Traer el libro de compras desde Business Central | Must | 1 | Segundo insumo, vía `ErpLedgerPort` y `csv_adapter` | HU-01; **P2**; **P7** (campos de llave) |
| [#6](https://github.com/miguel-cortes-14/conciliasii/issues/6) | HU-04 | Filtrar el universo a conciliar | Must | 1 | Define el universo que se cruza (RN-01) | HU-02, HU-03 |
| [#7](https://github.com/miguel-cortes-14/conciliasii/issues/7) | HU-05 | Cruzar y clasificar documentos | Must | 1 | Núcleo del producto (`matcher`, `classifier`) | HU-04; **P3** |
| [#8](https://github.com/miguel-cortes-14/conciliasii/issues/8) | HU-06 | Detectar diferencias de período | Should | 1 | Es una de las 5 categorías de RN-05 y el clasificador la necesita desde el inicio; no vale la pena una segunda pasada sobre el motor | HU-05; **P4**, **P2** |
| [#9](https://github.com/miguel-cortes-14/conciliasii/issues/9) | HU-07 | Sugerir calces aproximados | Could | 1 | Es lógica del cruce (`matcher`) sobre Solo en SII y Solo en ERP; se registra quién decide con el usuario del selector | HU-05; tabla `sugerencia` |
| [#10](https://github.com/miguel-cortes-14/conciliasii/issues/10) | HU-08 | Alertar documentos duplicados | Could | 1 | Se detecta al armar el cruce (RN-09); costo marginal bajo | HU-05 |
| [#11](https://github.com/miguel-cortes-14/conciliasii/issues/11) | HU-09 | Ver el resumen por categoría | Must | 1 | Primera vista de resultados y base de la hoja `Resumen` del Excel | HU-05; el escenario "avance de comentarios" se activa en la Capa 2 |
| [#12](https://github.com/miguel-cortes-14/conciliasii/issues/12) | HU-10 | Ver el detalle de diferencias | Must | 1 | Permite investigar la causa, valores lado a lado | HU-05; el filtro "sin comentario" se activa en la Capa 2 |
| [#13](https://github.com/miguel-cortes-14/conciliasii/issues/13) | HU-11 | Comentar un documento | Must | 2 | Primer paso de la revisión contable: lo escribe el Analista contable (el PRD y la historia dicen "analista de Tesorería", ver equivalencia); requiere tabla `comentario`, usuario y rol | HU-10 |
| [#14](https://github.com/miguel-cortes-14/conciliasii/issues/14) | HU-12 | Volver a conciliar un período | Should | 3 | Gestión de versiones y traspaso de comentarios por llave (RN-10); presupone comentarios (Capa 2) | HU-05, HU-11; `ejecucion.version` |
| [#15](https://github.com/miguel-cortes-14/conciliasii/issues/15) | HU-13 | Consultar conciliaciones anteriores | Should | 3 | Historial por período (RF-11), solo consulta | HU-01, HU-12, HU-14 (estado en la lista) |
| [#16](https://github.com/miguel-cortes-14/conciliasii/issues/16) | HU-14 | Aprobar el período | Must | 2 | Cierra el ciclo con comentario obligatorio (P1) en dos niveles: Analista contable (valida comentarios) y GAF (final); depende de los comentarios | HU-11; P1 resuelta |
| [#17](https://github.com/miguel-cortes-14/conciliasii/issues/17) | HU-15 | Configurar la conexión con Business Central | Must | 1 | Habilitador del adaptador del ERP: en la PoC se materializa como `config.py` más el stub `bc_api_adapter`; la conexión real vive detrás del puerto | HU-03; **P7** |

Recuento: 15 historias, 15 filas. Capa 1 = HU-01, 02, 03, 04, 05, 06, 07, 08, 09, 10 y 15 (11 historias); Capa 2 = HU-11 y HU-14 (2); Capa 3 = HU-12 y HU-13 (2). Total 15.

Notas de asignación:

- HU-15 incluye en la PoC solo lo que se puede construir sin un BC real: parámetros, selección del adaptador y el stub. Los escenarios de "probar la conexión", "credenciales inválidas" y "campos de llave" se validan cuando exista `bc_api_adapter` real (depende de P7). Las credenciales nunca se escriben en el repositorio; se leen de variables de entorno o `st.secrets`.
- HU-09 y HU-10 tienen un escenario cada una que depende de comentarios (avance de comentarios; filtro "sin comentario"). Quedan en la Capa 1 con ese escenario inactivo; se completa al entregar HU-11.
- HU-01 incluye el escenario "período ya conciliado", que depende de persistir la ejecución; por eso la Capa 1 ya incluye las tablas `periodo`, `ejecucion` y `resultado`.

### Módulos y archivos por capa

| Capa | Módulos y archivos que se entregan |
| --- | --- |
| 1 | `app.py`; `pages/1_Cargar_y_Conciliar.py`; `pages/2_Revision.py` (resumen, detalle, sugerencias, descarga); `src/conciliasii/config.py`; `domain/models.py` y `domain/errors.py`; `ingest/sii_csv.py`; `erp/port.py`, `erp/csv_adapter.py`, `erp/bc_api_adapter.py` (stub); `engine/matcher.py`, `engine/classifier.py`; `export/excel.py` (hojas `Resumen`, categorías y `Sugerencias`); `storage/schema.sql` y `storage/repository.py` (`periodo`, `ejecucion`, `resultado`, `sugerencia`); `data/samples/`; `tests/`; `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` |
| 2 | `workflow/approval.py`; `pages/3_Aprobacion.py`; panel de comentarios en `pages/2_Revision.py`; tablas `comentario` y `aprobacion` en `schema.sql` y sus métodos en el repositorio; hoja `Comentarios` y columna de comentarios en `export/excel.py`; selector de rol con Analista contable y GAF, permisos por rol (`Rol`, `RolNoAutorizadoError`) y estados `EnRevisionContable` y `PendienteGAF` |
| 3 | `pages/4_Historial.py`; en el servicio de conciliación, traspaso de comentarios por llave entre versiones y vista de versiones anteriores en solo lectura (`listar_periodos`, `listar_ejecuciones`); acción "volver a conciliar" con versión nueva |

### Coherencia con el MVP del PRD

El conjunto Must del PRD son las historias HU-01 a HU-05, HU-09, HU-10, HU-11, HU-14 y HU-15. Con esta asignación, todas caen en las Capas 1 y 2 y ninguna Must queda en la Capa 3. Pero la Capa 1 por sí sola no cumple el MVP mínimo: faltan HU-11 y HU-14 (Capa 2), que son las que reemplazan el cierre con Contabilidad y el GAF. El MVP completo del PRD es Capa 1 + Capa 2; la Capa 3 contiene solo historias Should (HU-12, HU-13). Además la Capa 1 adelanta tres historias no Must (HU-06 Should; HU-07 y HU-08 Could) porque forman parte del motor de cruce, y la descarga de Excel, que el PRD deja fuera de alcance (P6).

## Limitaciones conocidas

- **La base SQLite local no persiste en Streamlit Community Cloud.** El sistema de archivos de esa plataforma es efímero: los datos se pierden al reiniciar, redesplegar, reconstruir la app o cuando la app "se duerme" por inactividad. Por lo tanto, la demo pública no ofrece historial durable, versiones ni aprobaciones que sobrevivan. Esto es una decisión consciente para una PoC, no un defecto; se registra en [ADR-0001](adr/0001-persistencia-sqlite-local.md).
- **Mitigaciones:** la descarga de Excel (ver arriba) permite llevarse el resultado; los CSV de ejemplo en `data/samples/` permiten recargar los datos de la demo; el repositorio es la única frontera de acceso a datos.
- **Mejora futura:** migrar a una base externa administrada (por ejemplo Postgres administrado o Supabase) implementando otro `ConciliacionRepository` y cambiando `STORAGE_BACKEND`, sin tocar motor, flujo ni páginas.
- El libro de BC es simulado con CSV; la integración real depende de P7.
- Sin autenticación real: el usuario y el rol (Tesorero, Analista contable, GAF) se eligen en la barra lateral, de modo que cualquiera puede asumir cualquier rol. No apto para datos reales.
- Una sola empresa y un solo ambiente de BC, como en el alcance del MVP.

## Verificación contra el PRD

Se comparó la lista de categorías usada en el diseño base con la regla **RN-05** del PRD (`docs/PRD.md`, línea 94, sección "Reglas de negocio").

| # | Categoría en el diseño | Categoría en el PRD (RN-05) | Definición en el PRD | Resultado |
| --- | --- | --- | --- | --- |
| 1 | Cuadrado | **Cuadrado** | llave y campos iguales | Coincide |
| 2 | Diferencia de monto | **Diferencia de monto** | llave igual, algún campo distinto | Coincide |
| 3 | Diferencia de período | **Diferencia de período** | llave igual, período distinto | Coincide |
| 4 | Solo en SII | **Solo en SII** | está en el RCV y no en Business Central | Coincide |
| 5 | Solo en ERP | **Solo en ERP** | está en Business Central y no en el RCV | Coincide |

- **Cantidad:** cinco en ambos. RF-05 (línea 76) exige que cada documento quede en exactamente una categoría; RN-06 (línea 95) fija la precedencia de Diferencia de período sobre Diferencia de monto.
- **Nombres:** idénticos, incluidas tildes y mayúsculas ("Diferencia de período", "Solo en SII", "Solo en ERP").
- **Definiciones:** el diseño usa las de RN-05. Dos precisiones del PRD ya incorporadas: "llave" es RUT emisor + tipo de documento + folio (RN-03, línea 92) y "campos" son los de RN-04 (línea 93).
- **Lo que no es categoría:** la alerta de duplicado (RN-09, línea 98) es una marca dentro de la categoría y los documentos de BC "Sin llave" (HU-03) se informan aparte y no participan del cruce. La sugerencia de calce (RN-08, línea 97) tampoco es una categoría: al confirmarla los documentos pasan a Diferencia de monto.
- **Reglas citadas en este documento** y verificadas contra el PRD: RF-01 a RF-11 (líneas 72 a 82), RN-01 a RN-10 (líneas 90 a 99), P1 a P7 (líneas 120 a 126).

Diferencias encontradas: ninguna en las categorías. Las brechas del PRD que sí requieren decisión se listan a continuación.

## Supuestos y brechas respecto del PRD

| Tema | Supuesto adoptado | Cómo se cierra |
| --- | --- | --- |
| Excel (P6) | El PRD lo deja fuera de alcance; se incluye en la Capa 1 por decisión de esta fase | Actualizar PRD (alcance y P6) al validar el diseño |
| Columnas del CSV del SII | Diez columnas propuestas más `RUT Receptor`, `Periodo`, `Estado` | Contrastar con un export real del SII |
| Campos de RN-04 no cubiertos | Columnas opcionales, en cero si faltan | Confirmar con un CSV real |
| Mapeo del libro de BC | `Amount Excl. VAT` como neto (tipo 33) o exento (tipo 34) | Confirmar con P7 |
| P2 | `ERP_PERIOD_DATE_FIELD` por defecto `posting_date` | Respuesta del PO |
| P3 | `AMOUNT_TOLERANCE = 0` | Respuesta del PO |
| P4 | `NEIGHBOR_PERIODS = 2,1` (propuesta del PRD), búsqueda del SII hacia BC | Respuesta del PO |
| P7 | Si falta tipo o folio en la API estándar, se derivan de `External Document No.` dentro de `erp/` | Exploración de la API |
| Cadena de roles (**a confirmar**) | Tesorero concilia, Analista contable revisa y da la primera aprobación, GAF da la aprobación final. Es una interpretación del PO no confirmada; el PRD define una sola aprobación de Contabilidad (P1) | Confirmar con el PO; ver [ADR-0006](adr/0006-roles-y-cadena-de-aprobacion.md) |
| Quién comenta (**a confirmar**) | Solo el Analista contable escribe los comentarios obligatorios. El PRD (`PRD.md`, línea 21) y HU-11 dicen que comenta Tesorería | Confirmar; `comentario.rol` permite habilitar también al Tesorero |
| Dónde se valida el comentario | En la aprobación de nivel 1 (Analista contable), re-validado en la final | Confirmar junto con la cadena |
| Nomenclatura de roles | PRD e historias usan Analista de conciliación / Aprobador; el diseño usa Tesorero / Analista contable / GAF. `PRD.md`, `historias.md` y los issues no se modificaron | Actualizar PRD, historias e issues si se valida |
| Área del GAF | No definida; se muestra como "por confirmar" | Respuesta del PO |
| Usuarios y roles en la app | Selector en la barra lateral, sin autenticación | Fuera de la PoC |
| Reabrir un período | Decisión `Reabierto` del GAF que habilita al Tesorero a crear una versión nueva (HU-14 dice "Contabilidad") | Confirmar con el PO |
| Tabla `sugerencia` | Se agrega a las cinco tablas base | Revisar al implementar HU-07 |
