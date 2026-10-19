# ADR-0001 · Persistencia en SQLite local

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto

La app necesita guardar períodos, versiones de cada conciliación, resultados, comentarios y aprobaciones (RN-10, RF-09, RF-11, P1). Es una PoC de una sola empresa, con unos cientos de documentos al mes y sin presupuesto de infraestructura. La demo pública se publicaría en Streamlit Community Cloud, cuyo sistema de archivos es efímero: un archivo SQLite local se pierde al reiniciar, redesplegar, reconstruir la app o cuando la app se duerme por inactividad.

## Decisión

Usar **SQLite en un archivo local** como respaldo de datos de la PoC. Es una decisión **consciente**: la demo pública en Streamlit Community Cloud es **efímera por diseño** y los datos pueden perderse en cualquier reinicio, redespliegue o suspensión. Para una PoC eso es aceptable.

Todo acceso a datos queda detrás de `storage/repository.py`, con una interfaz (`ConciliacionRepository`) y una implementación SQLite. Ningún otro módulo importa `sqlite3`.

Una **base de datos externa** (por ejemplo Postgres administrado o Supabase) se registra como **mejora futura**: bastará con implementar la misma interfaz y cambiar `STORAGE_BACKEND`.

## Alternativas consideradas

- **Postgres administrado o Supabase desde el inicio.** Persistencia real, pero agrega cuenta, credenciales, red y costo antes de validar el producto. Descartada por ahora.
- **Archivos CSV o JSON en disco.** Más simple, pero sin transacciones ni consultas por llave y con el mismo problema de efimeridad.
- **Solo `st.session_state`.** No sobrevive a recargas del navegador y no sirve para historial. Descartada.
- **Almacenamiento en la nube de archivos (S3, Drive).** Mismo costo de credenciales que una base externa, con peores consultas.

## Consecuencias

- Positivas: arranque inmediato sin infraestructura, pruebas rápidas con bases temporales, consultas SQL por llave y versión, y ejecución local con datos persistentes.
- Negativas: **la demo pública no tiene historial durable**; versiones, comentarios y aprobaciones pueden desaparecer. No debe usarse para un cierre real.
- Mitigaciones: la descarga de Excel permite llevarse el resultado (ADR-0003); los CSV de `data/samples/` permiten recargar la demo; la frontera del repositorio hace barata la migración futura (solo una implementación nueva y un parámetro).
- Se documenta en la sección "Limitaciones conocidas" de [arquitectura.md](../arquitectura.md#limitaciones-conocidas).
