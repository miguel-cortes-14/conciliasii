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