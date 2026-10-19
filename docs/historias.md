# Historias de usuario · Conciliador RCV SII vs Business Central

**Fecha:** 2026-10-16 · **Product Owner:** Miguel Cortés · Fuente: [PRD.md](PRD.md)

15 historias en 5 grupos cubren todos los requisitos y reglas del PRD. Las que dependen de una decisión pendiente lo indican junto a su criterio.

Roles de la app: Tesorero (Tesorería), Analista Contable (Contabilidad), Jefa de Contabilidad (1er aprobador) y GAF (2.º aprobador, superior jerárquico de la Jefa de Contabilidad), más el Administrador (TI). HU-01 y HU-15 se mantienen con su redacción genérica. HU-11 y HU-14 conservan su texto original hasta su revisión; deben alinearse con los comentarios del Tesorero y del Analista Contable y con la aprobación en dos niveles (RF-12, RN-11).

## Mapa de historias

La prioridad MoSCoW está validada por el PO: las Must forman el MVP mínimo que reemplaza los 2 días de trabajo manual.

| ID | Historia | Grupo | Prioridad | Trazabilidad |
| --- | --- | --- | --- | --- |
| HU-01 | Seleccionar el período a conciliar | 1 · Preparar | Must | RF-01 |
| HU-02 | Cargar el CSV del Registro de Compras | 1 · Preparar | Must | RF-02 |
| HU-03 | Traer el libro de compras desde Business Central | 1 · Preparar | Must | RF-03, RN-02 |
| HU-04 | Filtrar el universo a conciliar | 1 · Preparar | Must | RF-04, RN-01 |
| HU-05 | Cruzar y clasificar documentos | 2 · Conciliar | Must | RF-05, RN-03 a RN-06 |
| HU-06 | Detectar diferencias de período | 2 · Conciliar | Should | RN-07 |
| HU-07 | Sugerir calces aproximados | 2 · Conciliar | Could | RF-08, RN-08 |
| HU-08 | Alertar documentos duplicados | 2 · Conciliar | Could | RN-09 |
| HU-09 | Ver el resumen por categoría | 3 · Revisar | Must | RF-06 |
| HU-10 | Ver el detalle de diferencias | 3 · Revisar | Must | RF-07 |
| HU-11 | Comentar un documento | 3 · Revisar | Must | RF-09 |
| HU-12 | Volver a conciliar un período | 4 · Ciclo | Should | RF-10, RN-10 |
| HU-13 | Consultar conciliaciones anteriores | 4 · Ciclo | Should | RF-11 |
| HU-14 | Aprobar el período | 4 · Ciclo | Must | P1 |
| HU-15 | Configurar la conexión con Business Central | Habilitador | Must | RF-03, P7 |

## Grupo 1 · Preparar la conciliación

### HU-01 · Seleccionar el período a conciliar

**Como** analista de Tesorería, **quiero** elegir el mes y año tributario, **para** que todo lo que cargue y concilie quede asociado a ese período.

```gherkin
Escenario: Período seleccionado habilita la carga
  Dado que estoy en la pantalla de conciliación
  Cuando selecciono el período "2026-09"
  Entonces se habilitan la carga del CSV y la extracción desde Business Central
  Y el período "2026-09" se muestra en el encabezado

Escenario: Sin período no se puede avanzar
  Dado que no he seleccionado un período
  Cuando intento cargar un archivo o conciliar
  Entonces la acción está deshabilitada
  Y veo el mensaje "Selecciona un período tributario"

Escenario: Período ya conciliado
  Dado que el período "2026-08" ya tiene una conciliación
  Cuando lo selecciono
  Entonces veo la última versión de esa conciliación con su resumen
```

### HU-02 · Cargar el CSV del Registro de Compras

**Como** Tesorero, **quiero** subir el archivo que descargo del portal del SII, **para** no tener que transcribir los documentos.

```gherkin
Escenario: Carga válida
  Dado que seleccioné el período "2026-09"
  Y tengo el CSV del Registro de Compras de la empresa para "2026-09"
  Cuando subo el archivo
  Entonces el sistema lo acepta
  Y muestra la cantidad de documentos leídos

Escenario: RUT distinto al de la empresa
  Dado que seleccioné el período "2026-09"
  Cuando subo un CSV cuyo RUT receptor no es el de la empresa
  Entonces el archivo se rechaza
  Y veo el mensaje "El RUT del archivo no corresponde a la empresa"

Escenario: Período distinto al seleccionado
  Dado que seleccioné el período "2026-09"
  Cuando subo un CSV del período "2026-08"
  Entonces el archivo se rechaza
  Y veo el mensaje indicando el período del archivo y el seleccionado

Escenario: Formato no reconocido
  Dado que seleccioné un período
  Cuando subo un archivo que no tiene las columnas del Registro de Compras del SII
  Entonces el archivo se rechaza
  Y veo qué columnas faltan

Escenario: Reemplazar un archivo ya cargado
  Dado que ya cargué un CSV para el período "2026-09"
  Cuando subo un nuevo CSV para el mismo período
  Entonces el sistema me pide confirmar el reemplazo
  Y al confirmar, el nuevo archivo reemplaza al anterior
```

### HU-03 · Traer el libro de compras desde Business Central

**Como** Tesorero, **quiero** obtener el libro de compras del período directamente desde Business Central, **para** no exportarlo ni transformarlo a mano.

```gherkin
Escenario: Extracción exitosa
  Dado que seleccioné el período "2026-09"
  Y la conexión con Business Central está configurada
  Cuando solicito traer el libro de compras
  Entonces el sistema obtiene las facturas de compra registradas del período
  Y muestra la fecha y hora de extracción y la cantidad de documentos

Escenario: Business Central no responde
  Dado que la API de Business Central no está disponible
  Cuando solicito traer el libro de compras
  Entonces veo un mensaje de error con la causa informada por la API
  Y puedo reintentar sin perder el CSV ya cargado

Escenario: Documento sin datos de llave
  Dado que una factura de Business Central no tiene RUT, tipo o folio
  Cuando se extrae el libro
  Entonces esa factura se informa como "Sin llave" con su número interno
  Y no participa del cruce
```

> Pendiente P2: qué fecha de Business Central define el período.

### HU-04 · Filtrar el universo a conciliar

**Como** Tesorero, **quiero** que el sistema deje solo los documentos que entran en la conciliación, **para** no revisar documentos fuera de alcance.

```gherkin
Escenario: Filtro por tipo y estado
  Dado que cargué el CSV y traje el libro de Business Central
  Cuando el sistema prepara el universo
  Entonces solo quedan documentos tipo 33 y 34
  Y del lado SII solo los que están en estado "Registro"

Escenario: Informe de excluidos
  Dado que el CSV incluye notas de crédito tipo 61 y documentos en estado "Pendiente"
  Cuando el sistema prepara el universo
  Entonces veo cuántos documentos se excluyeron por tipo
  Y cuántos se excluyeron por estado
```

## Grupo 2 · Conciliar

### HU-05 · Cruzar y clasificar documentos

**Como** Tesorero, **quiero** que el sistema cruce ambos libros y clasifique cada documento, **para** dedicar mi tiempo solo a las excepciones.

```gherkin
Escenario: Documento cuadrado
  Dado un documento con RUT "76.123.456-7", tipo 33 y folio 1050 en el SII
  Y uno con RUT "76123456-7", tipo 33 y folio 1050 en Business Central
  Y todos sus campos tienen el mismo valor
  Cuando ejecuto la conciliación
  Entonces el documento queda en la categoría "Cuadrado"

Escenario: RUT con distinto formato se considera la misma llave
  Dado un RUT "76.123.456-k" en el SII y "76123456-K" en Business Central
  Cuando ejecuto la conciliación
  Entonces ambos RUT se reconocen como la misma llave

Escenario: Diferencia de monto
  Dado un documento con la misma llave en ambas fuentes
  Y el IVA recuperable es 19.000 en el SII y 18.900 en Business Central
  Cuando ejecuto la conciliación
  Entonces el documento queda en "Diferencia de monto"
  Y el campo "IVA recuperable" se marca como distinto

Escenario: Solo en SII
  Dado un documento que está en el SII y no en Business Central
  Cuando ejecuto la conciliación
  Entonces el documento queda en "Solo en SII"

Escenario: Solo en ERP
  Dado un documento que está en Business Central y no en el SII
  Cuando ejecuto la conciliación
  Entonces el documento queda en "Solo en ERP"

Escenario: Factura exenta con IVA
  Dado un documento tipo 34 con IVA distinto de cero en Business Central
  Cuando ejecuto la conciliación
  Entonces el documento queda en "Diferencia de monto"
  Y el campo "IVA" se marca como distinto

Escenario: Cada documento en una sola categoría
  Dado un período conciliado
  Cuando reviso el resultado
  Entonces la suma de documentos de todas las categorías es igual al universo filtrado
```

> Pendiente P3: si la comparación de montos es exacta o acepta ±$1.

### HU-06 · Detectar diferencias de período

**Como** Tesorero, **quiero** saber si un documento faltante está registrado en otro período, **para** no tratar un desfase como un error.

```gherkin
Escenario: Documento registrado en el período siguiente
  Dado un documento en el SII del período "2026-09"
  Y el mismo documento registrado en Business Central en "2026-10"
  Cuando concilio "2026-09"
  Entonces el documento queda en "Diferencia de período"
  Y veo ambos períodos en el detalle

Escenario: Diferencia de período y de monto a la vez
  Dado un documento con diferencia de período
  Y su monto total también es distinto
  Cuando concilio
  Entonces el documento queda en "Diferencia de período"
  Y el detalle muestra además los campos con diferencia

Escenario: Fuera del rango de búsqueda
  Dado un documento del SII que está en Business Central en un período fuera del rango configurado
  Cuando concilio
  Entonces el documento queda en "Solo en SII"
```

> Pendiente P4: cuántos períodos vecinos se revisan.

### HU-07 · Sugerir calces aproximados

**Como** Tesorero, **quiero** que el sistema me sugiera posibles pares cuando no hay calce exacto, **para** detectar errores de digitación en folio o tipo.

```gherkin
Escenario: Sugerencia por RUT y monto
  Dado un documento "Solo en SII" con RUT "76123456-7", folio 1050 y total 119.000
  Y un documento "Solo en ERP" con el mismo RUT, folio 1005 y total 119.000
  Cuando ejecuto la conciliación
  Entonces veo una sugerencia de calce entre ambos
  Y ninguno cambia de categoría hasta que yo decida

Escenario: Confirmar una sugerencia
  Dado una sugerencia de calce
  Cuando la confirmo
  Entonces ambos documentos pasan a "Diferencia de monto"
  Y el campo "Folio" se marca como distinto
  Y queda registrado quién confirmó y cuándo

Escenario: Descartar una sugerencia
  Dado una sugerencia de calce
  Cuando la descarto
  Entonces los documentos se mantienen en "Solo en SII" y "Solo en ERP"
  Y la sugerencia no vuelve a aparecer en ese período
```

### HU-08 · Alertar documentos duplicados

**Como** Tesorero, **quiero** ver cuándo una misma llave aparece dos veces en una fuente, **para** detectar facturas registradas dos veces.

```gherkin
Escenario: Duplicado en Business Central
  Dado que Business Central tiene dos facturas con la misma llave
  Cuando ejecuto la conciliación
  Entonces el documento muestra una alerta de duplicado
  Y veo los números internos de ambas facturas
```

## Grupo 3 · Revisar y comentar

### HU-09 · Ver el resumen por categoría

**Como** Tesorero, Analista Contable, Jefa de Contabilidad o GAF, **quiero** ver un resumen por categoría, **para** entender de un vistazo cuánto cuadra y cuánto hay que revisar.

```gherkin
Escenario: Resumen del período
  Dado un período conciliado
  Cuando abro el resumen
  Entonces veo, por cada categoría, la cantidad de documentos
  Y los montos totales según el SII y según Business Central
  Y el total general de documentos y montos

Escenario: Avance de comentarios
  Dado un período con documentos fuera de "Cuadrado"
  Cuando abro el resumen
  Entonces veo cuántos de esos documentos tienen comentario y cuántos no
```

### HU-10 · Ver el detalle de diferencias

**Como** Tesorero o Analista Contable, **quiero** ver cada documento de una categoría con sus valores lado a lado, **para** encontrar la causa de la diferencia sin abrir otros sistemas.

```gherkin
Escenario: Detalle de una diferencia de monto
  Dado un documento en "Diferencia de monto"
  Cuando abro su detalle
  Entonces veo los valores del SII y de Business Central campo a campo
  Y los campos distintos aparecen destacados con la diferencia calculada

Escenario: Filtrar dentro de una categoría
  Dado que estoy en el detalle de una categoría
  Cuando filtro por RUT de proveedor o por "sin comentario"
  Entonces solo veo los documentos que cumplen el filtro
```

### HU-11 · Comentar un documento

**Como** analista de Tesorería, **quiero** dejar un comentario en cada documento con diferencia, **para** que Contabilidad sepa la causa y la acción tomada.

```gherkin
Escenario: Agregar un comentario
  Dado un documento en cualquier categoría distinta de "Cuadrado"
  Cuando escribo un comentario y lo guardo
  Entonces el comentario queda asociado al documento
  Y registra mi nombre, la fecha y la hora

Escenario: Varios comentarios en un documento
  Dado un documento que ya tiene un comentario
  Cuando agrego otro
  Entonces veo ambos en orden cronológico

Escenario: Los comentarios no se borran
  Dado un comentario guardado
  Cuando intento eliminarlo
  Entonces la opción no está disponible
```

## Grupo 4 · Ciclo del período

### HU-12 · Volver a conciliar un período

**Como** Tesorero, **quiero** volver a ejecutar la conciliación después de corregir en Business Central, **para** confirmar que la corrección resolvió la diferencia.

```gherkin
Escenario: Nueva versión conserva comentarios
  Dado un período conciliado con comentarios en algunos documentos
  Y corregí una factura en Business Central
  Cuando traigo de nuevo el libro y vuelvo a conciliar
  Entonces se crea una nueva versión de la conciliación
  Y los comentarios se mantienen en los documentos con la misma llave

Escenario: Documento corregido pasa a cuadrado
  Dado un documento en "Diferencia de monto" que corregí en Business Central
  Cuando vuelvo a conciliar
  Entonces el documento queda en "Cuadrado"
  Y sus comentarios anteriores siguen visibles

Escenario: Versiones anteriores
  Dado un período con dos versiones
  Cuando consulto el período
  Entonces veo la versión vigente por defecto
  Y puedo abrir la versión anterior en modo solo lectura
```

### HU-13 · Consultar conciliaciones anteriores

**Como** Tesorero, Analista Contable, Jefa de Contabilidad o GAF, **quiero** ver la lista de períodos conciliados, **para** revisar el historial ante una consulta o auditoría.

```gherkin
Escenario: Lista de períodos
  Dado que existen conciliaciones de varios períodos
  Cuando abro el historial
  Entonces veo cada período con su fecha de última conciliación, su resumen y su estado
  Y la lista está ordenada del más reciente al más antiguo
```

### HU-14 · Aprobar el período

> Decisión P1: la aprobación ocurre dentro de la app y exige comentario en todas las diferencias.

**Como** aprobador de Contabilidad, **quiero** aprobar la conciliación de un período, **para** dejar constancia de que la revisé antes de declarar el F29.

```gherkin
Escenario: Aprobación con todas las diferencias comentadas
  Dado un período donde todos los documentos fuera de "Cuadrado" tienen comentario
  Cuando apruebo el período
  Entonces el período queda en estado "Aprobado"
  Y se registra quién aprobó y cuándo

Escenario: Diferencias sin comentario impiden aprobar
  Dado un período con documentos fuera de "Cuadrado" sin comentario
  Cuando intento aprobarlo
  Entonces la aprobación se rechaza
  Y veo cuántos documentos faltan por comentar

Escenario: Analista no puede aprobar
  Dado que tengo el rol de analista de Tesorería
  Cuando abro un período conciliado
  Entonces no veo la opción de aprobar

Escenario: Período aprobado no se modifica
  Dado un período aprobado
  Cuando intento volver a conciliarlo
  Entonces el sistema lo impide
  Y me indica que Contabilidad debe reabrirlo
```

## Habilitador técnico

### HU-15 · Configurar la conexión con Business Central

**Como** administrador de TI, **quiero** configurar la conexión con la API de Business Central, **para** que Tesorería pueda traer el libro de compras sin intervención de TI.

```gherkin
Escenario: Conexión válida
  Dado que ingreso el tenant, el ambiente, la empresa y las credenciales de la aplicación
  Cuando pruebo la conexión
  Entonces veo un mensaje de conexión exitosa
  Y la configuración queda guardada

Escenario: Credenciales inválidas
  Dado que ingreso credenciales incorrectas
  Cuando pruebo la conexión
  Entonces veo el error devuelto por Business Central
  Y la configuración no se guarda

Escenario: Campos de llave disponibles
  Dado una conexión válida
  Cuando el sistema lee una factura de compra de prueba
  Entonces confirma que obtiene RUT del proveedor, tipo de documento y folio
  Y si falta alguno, indica cuál

Escenario: Credenciales protegidas
  Dado una configuración guardada
  Cuando un usuario la consulta
  Entonces las credenciales no se muestran en texto plano
```

> Pendiente P7: si esos campos vienen de la API estándar o de una extensión de localización chilena.
