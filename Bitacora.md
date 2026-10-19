# Bitácora ConciliaSII

## Cómo uso este archivo
Una entrada por sesión de trabajo. Campos: fecha, fase, tiempo, qué hizo la IA, qué corregí yo, qué aprendí.

## Estimación de referencia
Tiempo que habría tomado con un equipo tradicional (completar al terminar cada fase): pendiente

---

## 2026-10-15 | Fase 0: entorno | Tiempo: __ h

**Qué hice**
- Instalé Claude Code, Git y GitHub CLI; configuré mi identidad y creé el repo conciliasii.
- Subí el primer README desde la terminal (prueba de humo manual).

**Qué hizo la IA**
- Diagnosticó los errores de la terminal y me guió paso a paso.

**Qué corregí / decidí yo**
- Decidí postergar el pago de Claude Pro hasta la fase de construcción, porque el plan gratis no incluye Claude Code. Hago primero las fases gratuitas (entorno, Slack, requisitos, diseño).
- Cambié la prueba de humo: en vez de pedirle el README a Claude Code, lo hice a mano.

**Problemas y aprendizajes**
- `claude` no se reconocía: la carpeta de instalación no estaba en el PATH de Windows. Se resolvió agregándola.
- Al copiar comandos desde el PDF, las líneas se pegaron juntas y fallaron. Aprendizaje: ejecutar un comando por vez.
- Claude Code exige un plan de pago o saldo en Console; no se puede usar con la cuenta gratis.

   ---

   ## 19-10-2026 | Fase 1: requisitos | Tiempo: 15:00 h

   **Qué hice**
   - Creé el Proyecto ConciliaSII en claude.ai y fui entrevistado por Claude como Business Analyst.
   - Obtuve el PRD, las historias de usuario y 15 Issues en GitHub (#3 a #17), con avisos en Slack.

   **Qué hizo la IA**
   - Entrevista de requisitos, redacción del PRD y de las historias con criterios de aceptación, creación de los Issues y publicación de los documentos en el repo.

   **Qué corregí / decidí yo**
   - ERP: Business Central, simulado en la PoC por no tener acceso real.
   - Alcance del MVP: DTE 33 y 34, solo "registrados"; cruce por RUT + tipo + folio.
   - Flujo: Tesorería carga, Contabilidad aprueba dentro de la app con comentario obligatorio por diferencia.
   - Validé la priorización MoSCoW.
   - Errores de la IA que detecté: (completar)

   **Aprendizajes**
   - Entendimiento de uso de ramas, apoyado por Claude

   ---

   ## 19-10-2026 | Fase 2: diseño | Tiempo: __ h

   **Qué hice**
   - Pedí el diseño de la arquitectura a partir del PRD, las historias y los Issues #3 a #17.
   - Revisé y pedí ajustes al diseño base.

   **Qué hizo la IA**
   - Redactó `docs/arquitectura.md` (carpetas, contratos de los CSV, modelo de datos, flujo de aprobación, diagramas Mermaid y capas de entrega) y cinco ADR en `docs/adr/`.
   - Creó la configuración mínima: `requirements.txt`, `requirements-dev.txt` y `pyproject.toml` (ruff).
   - Verificó las cinco categorías contra el PRD (RN-05): coinciden en nombres, cantidad y definiciones.

   **Qué corregí / decidí yo**
   - SQLite local es una decisión consciente: la demo en Streamlit Community Cloud es efímera por diseño y la base externa queda como mejora futura; todo el acceso a datos va detrás de `repository.py`.
   - Entrega en tres capas: 1 núcleo con descarga Excel, 2 comentarios y aprobación, 3 historial y versiones.
   - Exportación a Excel con openpyxl desde la Capa 1 (el PRD la dejaba fuera de alcance, P6; falta actualizar el PRD).
   - Ruff como linter y formateador.
   - Roles y responsables (confirmado 2026-10-19): Tesorero, Analista Contable, Jefa de Contabilidad (1er aprobador) y GAF (2.º aprobador, superior de la Jefa); comentan Tesorero y Analista Contable, los rechazos van a la Jefa y ella reabre; ajusté PRD e historias (salvo HU-01, HU-11, HU-14 y HU-15) y dejé pendiente el destino del rechazo de la Jefa y la devolución a Tesorería (ADR-0006, P8).

   **Aprendizajes**
   - Separar la lógica de Streamlit y poner el ERP detrás de un puerto permite cambiar el respaldo o el adaptador sin tocar el motor.
