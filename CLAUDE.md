# CLAUDE.md

Este archivo entrega orientación a Claude Code (claude.ai/code) para trabajar con el código de este repositorio.

## Estado del proyecto

ConciliaSII es una PoC que concilia el Registro de Compras (RCV) del SII contra un libro de compras de Business Central. **A la fecha de redacción, el repositorio contiene solo documentación de diseño: aún no existen `app.py`, `src/` ni `tests/`.** Todo lo descrito bajo "Arquitectura" corresponde a la estructura *planificada* definida en `docs/arquitectura.md`, no a código que se pueda ejecutar o probar hoy. Antes de asumir que un módulo existe, verifica si realmente fue creado.

Lee en este orden al comenzar a trabajar: `docs/PRD.md` (problema, alcance, reglas de negocio RF-xx/RN-xx, decisiones abiertas P1-P8) → `docs/historias.md` (más de 15 historias de usuario con criterios de aceptación, HU-xx) → `docs/arquitectura.md` (diseño completo) → `docs/adr/` (por qué se tomó cada decisión importante).

## Comandos (una vez que exista el código)

```bash
pip install -r requirements-dev.txt
ruff check .             # lint (E, F, I, B, UP)
ruff format --check .    # verifica el formato sin modificar
pytest                   # ejecuta todos los tests
pytest tests/test_x.py::test_name   # ejecuta un solo test
streamlit run app.py     # ejecuta la app localmente
```

La configuración de Ruff está en `pyproject.toml` (line-length 100, target py311). Ver ADR-0004.

## Arquitectura (planificada, según docs/arquitectura.md)

**Dirección de dependencias (de afuera hacia adentro, nunca al revés):**
```
pages/, app.py  ->  workflow, engine, ingest, export, erp (port), storage (interface)  ->  domain
```

Principios fundamentales:
1. **La lógica de negocio nunca importa Streamlit.** El motor (`ingest`, `engine`, `export`, `workflow`) es puro y se puede probar solo con pytest; los `pages/*.py` se mantienen delgados: solo llaman a una función de servicio y muestran el resultado.
2. **El ERP está detrás de un port.** `erp/port.py` define `ErpLedgerPort` (un `Protocol`); `erp/csv_adapter.py` lo implementa hoy, y `erp/bc_api_adapter.py` es un stub para la API real de Business Central (HU-15, bloqueada por la decisión abierta P7). Ver ADR-0002.
3. **Todo acceso a datos pasa por `storage/repository.py`.** Ningún otro módulo habla directamente con SQLite; cambiar el backend de almacenamiento nunca toca el engine, el workflow ni las pages. Ver ADR-0001 (SQLite es local/efímero por diseño: el sistema de archivos de Streamlit Community Cloud no persiste entre reinicios).
4. **La entrega se hace en tres capas utilizables de forma independiente** — ver ADR-0005:
   - **Capa 1 (núcleo + exportación a Excel):** cargar el CSV del SII, obtener el libro del ERP mediante el port, filtrar, cruzar, clasificar, sugerir cruces aproximados, ver resumen/detalle y descargar Excel.
   - **Capa 2 (comentarios + aprobación):** comentarios por documento (Tesorero, Analista Contable, Jefa de Contabilidad) y flujo de aprobación de dos niveles (Jefa de Contabilidad → GAF), con comentarios obligatorios en cada diferencia antes de la aprobación de nivel 1.
   - **Capa 3 (historial + versiones):** listado de períodos/versiones, re-conciliación que preserva los comentarios por clave y vista de solo lectura de versiones anteriores.

**Núcleo de cruce/clasificación** (`engine/matcher.py`, `engine/classifier.py`):
- Clave de cruce = `rut|tipo_doc|folio` (RUT normalizado: sin puntos, con guion, dígito verificador en mayúscula) — RN-03.
- Cada documento cae en exactamente una categoría, en este orden de precedencia: **Solo en SII** → **Solo en ERP** → **Diferencia de período** (también prevalece sobre las diferencias de monto cuando se dan ambas, RN-06) → **Diferencia de monto** → **Cuadrado**.
- Las sugerencias de cruce aproximado (RN-08) solo emparejan documentos Solo en SII con documentos Solo en ERP que comparten RUT + monto total; al confirmar una, ambos pasan a Diferencia de monto.
- Invariante: la suma de documentos de todas las categorías es igual al universo filtrado (útil como aserción en tests).

**Máquina de estados de aprobación** (`workflow/approval.py`); los estados viven en `ejecucion.estado`:
```
Borrador -> EnRevisionContable -> PendienteJefaContabilidad -> PendienteGAF -> Aprobado
```
Rechazos: si GAF rechaza, vuelve a la Jefa (`PendienteJefaContabilidad`); si la Jefa rechaza, vuelve al Analista (`EnRevisionContable`); solo el Analista Contable puede devolver un período a Tesorería (`Borrador`). La Jefa de Contabilidad puede reabrir un período `Aprobado` sin visación de GAF, lo que genera una nueva versión. Una versión `Aprobado` es inmutable. La aprobación de nivel 1 debe validar que todo resultado distinto de `Cuadrado` tenga al menos un comentario no vacío (de lo contrario, `ComentariosFaltantesError`); esta es una regla de negocio del PRD (RN-11), no solo una comodidad de la UI, por lo que debe revalidarse en la capa de servicio aunque la UI también deshabilite el botón.

**Cuatro roles de negocio**, impuestos por `workflow/approval.py` (no solo ocultos en la UI): Tesorero (concilia, Capa 1), Analista Contable (revisa/comenta, deriva a la Jefa), Jefa de Contabilidad (aprobadora de nivel 1, reabre), GAF (aprobador de nivel 2/final, superior a la Jefa, solo lectura sobre los comentarios). Un quinto rol, Administrador (TI), configura la conexión con BC pero no tiene pantalla en la PoC. Ver la matriz completa de permisos en `docs/arquitectura.md`, sección "Matriz de permisos por acción".

**Config** (`config.py`, planificado): lee desde variables de entorno / `st.secrets`, nunca valores fijos en el código; incluye `ERP_BACKEND`, `ERP_PERIOD_DATE_FIELD` (decisión abierta P2), `AMOUNT_TOLERANCE` (P3), `NEIGHBOR_PERIODS` (P4), `STORAGE_BACKEND`, `SQLITE_PATH`.

## Decisiones abiertas (P2-P5, P7) y supuestos

Varios puntos del diseño están marcados explícitamente como **Supuesto** en `docs/arquitectura.md`, a la espera de datos reales del SII/BC o de la aprobación del PO; por ejemplo, las columnas exactas del CSV del SII, el mapeo de campos de BC a `Documento`, qué fecha define el período (P2), la tolerancia de monto en el cruce (P3) y cuántos períodos vecinos se buscan (P4). Al implementar cualquier cosa que toque estos puntos, revisa primero la tabla "Supuestos y brechas respecto del PRD" al final de `docs/arquitectura.md`; no elijas en silencio un comportamiento distinto al documentado allí.

## Convenciones de trabajo

- El español es el idioma de toda la documentación, de los mensajes de commit en el historial de este proyecto, de los términos de dominio y del texto de la UI (p. ej. `Periodo`, `Documento`, `Cuadrado`). Respétalo al escribir documentación, modelos de dominio o texto de cara al usuario; los identificadores de código en la arquitectura planificada mezclan sustantivos de dominio en español con términos técnicos en inglés, como se muestra arriba: sigue la nomenclatura que ya existe en `docs/arquitectura.md` en lugar de traducirla.
- Los IDs `RF-xx` (requisitos funcionales) y `RN-xx` (reglas de negocio) se refieren a `docs/PRD.md`; `HU-xx` se refiere a las historias de usuario en `docs/historias.md`; `ADR-xxxx` se refiere a `docs/adr/`. Referencia estos IDs al implementar o discutir un requisito para mantener la trazabilidad hacia el PRD.
- `Bitacora.md` es un registro de sesiones que la persona mantiene a mano (una entrada por sesión de trabajo: qué se hizo, qué hizo la IA, qué se corrigió, qué se aprendió). No escribas en él a menos que se te pida explícitamente.
