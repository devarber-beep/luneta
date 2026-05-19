# Requisitos funcionales Luneta

Especificación funcional unificada tras las reuniones de producto. Los bloques **RF-1** a **RF-9** recogen el alcance vigente acordado; **RF-10** mantiene el bloque de **auditoría y trazabilidad**, que sigue en vigor con la misma intención que en versiones anteriores del documento.

---

## Roles

Los permisos de cada rol **heredan** los del nivel inferior, salvo las **excepciones** indicadas. El detalle operativo de cada capacidad se desarrolla en los bloques **RF-1** a **RF-9**; la **trazabilidad** de actuaciones relevantes, en **RF-10**.

### Usuario anónimo

Persona que accede al sistema **sin cuenta ni sesión**. Solo accede a consultar los escenarios **publicados**.

**Permisos:**

- Listar y leer escenarios **publicados** (**RF-7.2**).
- Buscar escenarios publicados con los filtros previstos en lectura pública (**RF-7.3**).

### Usuario registrado

Persona con **cuenta verificada** que participa en la comunidad: aporta **valoración ética** sobre escenarios publicados.

**Permisos:**

- Todo lo del **usuario anónimo**.
- **Evaluar** escenarios publicados (**RF-8**).

### Investigador

**Usuario registrado** habilitado por el **admin** para elaborar y gestionar escenarios sobre usos de **gafas inteligentes** con **niños**.

**Permisos:**

- Todo lo del **usuario registrado**, **excepto** evaluar escenarios de los que sea **propietario**.
- **Crear** escenarios (**RF-3**).
- **Editar** escenarios donde sea **propietario** (y, como **colaborador**, según **RF-4**).
- **Enviar a revisión** cuando sea **propietario** (**RF-3.5**, **RF-5**).
- **Consultar** las evaluaciones éticas de los escenarios de los que es **propietario** (**RF-8.5**).
- **Realizar sugerencias** en otros escenarios **publicados** (**RF-4**).

### Revisor

**Investigador** con función de **validación** sobre los escenarios de los **investigadores** asignados a su cargo.

**Permisos:**

- Todo lo del **investigador** en uso cotidiano de la plataforma.
- **Revisar** escenarios en revisión de investigadores **a su cargo** (**RF-5**, **RF-6**).
- **Publicar**, **devolver para cambios** o **marcar como no apto** esos escenarios.
- **Participar en sugerencias** sobre escenarios ajenos a su cartera; **no** formular sugerencias sobre escenarios **publicados** de investigadores **a su cargo**.

### Admin

Responsable de la plataforma: **identidades**, **roles**, **asignaciones** revisor–investigador, **supervisión global** del flujo y del **registro de actividad**. Puede intervenir en **cualquier** escenario como un **revisor** sin límite de cartera.

**Permisos:**

- Todo lo previsto para **revisor** e **investigador**, **sin restricciones** de cartera ni de propiedad del escenario.
- **Gestionar usuarios:** crear **investigadores**, cambiar **roles**, activar/desactivar cuentas (**RF-1**).
- **Asignar** investigadores a cargo de cada **revisor** (**RF-6**).
- **Consultar** el registro de actividad / eventos del sistema (**RF-10**).
- **Consultar** evaluaciones de usuarios sobre escenarios y **moderarlas** (**RF-8**).
- **Mantener** catálogos editables (categorías, riesgos éticos, etc.; **RF-3.6**, **RF-8.1**).

### Propietario y colaborador

**No** son roles de la plataforma, pero tienen un papel central en el sistema.

- **Propietario:** usuario **responsable** del escenario. **Dirige** el contenido, **envía a revisión**, **acepta o rechaza** sugerencias y decide sobre **colaboradores** (**RF-3**, **RF-4**, **RF-5**).
- **Colaborador:** usuario que, tras una **contribución reconocida** (sugerencia **aceptada** en un escenario **publicado**), obtiene la **autoría** dentro del escenario (**RF-4**).

---

## RF-1. Gestión de usuarios y roles

Las cuentas **investigador** solo existen por creación del **admin** o decisión explícita del **admin**; el registro público no crea investigadores.

### RF-1.1 Registro y alta de usuarios

- **RF-1.1.1:** El sistema permitirá el autorregistro de nuevos usuarios con rol inicial **usuario registrado**.
- **RF-1.1.2:** El sistema validará la unicidad del **correo electrónico** y del **nombre de usuario** proporcionados antes del alta en el sistema.
- **RF-1.1.3:** El sistema creará las cuentas nuevas con la **verificación del correo electrónico pendiente**.
- **RF-1.1.4:** El sistema enviará un correo de verificación tras el registro, indicando al usuario que se ha registrado correctamente.

### RF-1.2 Administración de usuarios

- **RF-1.2.1:** El **admin** podrá crear cuentas con rol **investigador** de forma directa.
- **RF-1.2.2:** En la alta directa de **investigador**, el sistema asignará una contraseña inicial temporal aleatoria.
- **RF-1.2.3:** Las cuentas creadas como **investigador** por el **admin** quedarán marcadas para cambio obligatorio de contraseña en el primer acceso exitoso.
- **RF-1.2.4:** Hasta completar el cambio de contraseña obligatorio, el sistema limitará el uso de la aplicación.
- **RF-1.2.5:** El **admin** podrá cambiar el rol de un **usuario registrado** a **investigador**.
- **RF-1.2.6:** En cada momento, un usuario tendrá un **único** rol activo.
- **RF-1.2.7:** El **admin** podrá activar y desactivar cuentas.
- **RF-1.2.8:** La desactivación impedirá el acceso al sistema y conservará la trazabilidad histórica.

---

## RF-2. Login y perfil de usuario

El sistema deberá autenticar usuarios verificados y permitir gestión básica del perfil.

### RF-2.1 Login

- **RF-2.1.1:** El sistema permitirá al usuario iniciar sesión con sus credenciales, siempre que la cuenta esté **verificada**.
- **RF-2.1.2:** El sistema establecerá una **sesión válida** tras un inicio de sesión correcto.
- **RF-2.1.3:** El sistema actualizará la **fecha y hora del último acceso** en cada inicio de sesión correcto.
- **RF-2.1.4:** El sistema rechazará el login de cuentas **no verificadas** o **desactivadas**.

### RF-2.2 Perfil de usuario

- **RF-2.2.1:** El usuario podrá consultar su perfil.
- **RF-2.2.2:** El usuario podrá actualizar los datos de su perfil.
- **RF-2.2.3:** El usuario podrá cambiar su contraseña.
- **RF-2.2.4:** El perfil de usuario incluirá, como mínimo, **nombre**, **organización**, **foto** y **breve biografía**.

### RF-2.4 Restricciones de edición de perfil

- **RF-2.4.1:** Solo el **propietario** del perfil o un **admin** podrá modificar los datos del perfil.
- **RF-2.4.2:** Las cuentas desactivadas no podrán consultar ni modificar perfil hasta su reactivación.
- **RF-2.4.3:** El **admin** podrá consultar, activar y desactivar cualquier perfil.

---

## RF-3. Gestión de escenarios

El sistema deberá permitir crear, editar, validar y gestionar escenarios.

### RF-3.1 Datos de los escenarios

- **RF-3.1.1:** El escenario deberá incluir, como mínimo, un **título**, una **descripción**, una **imagen de portada**, una **categoría**, una **subcategoría** y el **etiquetado de los riesgos éticos**.
- **RF-3.1.2:** El sistema permitirá completar datos complementarios, como **otras imágenes** y **etiquetas** útiles para su clasificación (si participan otros usuarios o solo los niños, edad para la que está dirigido, si ocurre en un espacio interior o exterior, etc.).
- **RF-3.1.3:** El escenario podrá incluir información sobre **beneficios** ofrecidos por el escenario.

### RF-3.2 Creación de escenarios en borrador

- **RF-3.2.1:** Los roles con permiso de creación (**investigador**, **revisor** y **admin**) podrán crear nuevos escenarios.
- **RF-3.2.2:** Cada escenario describe un uso potencial de las **gafas inteligentes** en un contexto donde participan **niños**.
- **RF-3.2.3:** El escenario se creará inicialmente en estado de **borrador**.
- **RF-3.2.4:** Para guardar un borrador, el sistema exigirá únicamente **título** y **descripción**, permitiendo completar el resto de datos más adelante.
- **RF-3.2.5:** El creador quedará registrado automáticamente como **propietario** del escenario.

### RF-3.3 Eliminación de borradores

- **RF-3.3.1:** El **propietario** podrá eliminar escenarios en **borrador**.
- **RF-3.3.2:** La eliminación será **lógica**: el borrador dejará de mostrarse visible pero seguirá en el sistema.

### RF-3.4 Detección de escenarios similares

- **RF-3.4.1:** El sistema comprobará la similitud del nuevo escenario que se desea crear con escenarios existentes, para no crear duplicados.
- **RF-3.4.2:** En caso de similitud, el sistema mostrará escenarios **potencialmente similares** para evitar duplicidades.
- **RF-3.4.3:** Si el **investigador** detecta un escenario muy similar al que quería crear pero necesita modificaciones, podrá hacer **sugerencias** al **propietario** del escenario; si se le aceptan, pasará a ser **colaborador** en dicho escenario (**RF-4**).

### RF-3.5 Envío a revisión

- **RF-3.5.1:** Una vez terminado el escenario, el **propietario** deberá **enviarlo a revisión**. El escenario **no será visible al público** hasta completar el flujo de revisión y publicación.
- **RF-3.5.2:** Para enviarlo a publicación, el escenario debe tener **título**, **descripción**, **imagen de portada**, **categoría**, **subcategoría** y **etiquetado de riesgos**.

### RF-3.6 Clasificación de los escenarios

- **RF-3.6.1:** Cada escenario podrá asociarse a **una o más** categorías de clasificación.
- **RF-3.6.2:** El **admin** podrá consultar, añadir, modificar y desactivar categorías del catálogo; solo las categorías **activas** estarán disponibles al crear o editar escenarios.

**Categorías:**

- Aprendizaje y creatividad  
- Salud  
- Entretenimiento y ocio  
- Vida diaria  
- Psicología y bienestar  
- Personas y relaciones sociales  
- Toma de decisiones  
- Supervisión  
- Investigación científica sobre los niños  

### RF-3.7 Control de versiones de escenarios publicados

- **RF-3.7.1:** El sistema permitirá al **propietario** de un escenario **publicado** realizar cambios sobre el mismo.
- **RF-3.7.2:** Los cambios realizados sobre los datos del escenario en la **versión de trabajo** se reflejarán en la versión **publicada** solo cuando el escenario complete de nuevo el flujo de **revisión** y **publicación**.
- **RF-3.7.3:** La versión pública mostrará únicamente la información **aprobada** para publicación, sin exponer datos internos del proceso de revisión.
- **RF-3.7.4:** El sistema conservará el **historial de versiones** del escenario. Cuando una nueva versión sea aprobada y publicada, la lectura pública mostrará la **última versión aprobada** como vigente, sustituyendo la anterior en lo que ve el público.

---

## RF-4. Gestión de sugerencias de cambio y colaboradores

El sistema deberá permitir **sugerencias de cambio** sobre escenarios, como **revisor** o como **investigador**.

### RF-4.1 Condiciones generales

- **RF-4.1.1:** **Revisión previa a la publicación:** cuando un **borrador** es enviado a revisión, el **revisor** podrá proponer sugerencias de cambio antes de su publicación.
- **RF-4.1.2:** **Escenario ya publicado:** un **investigador** puede proponer sugerencias de cambio sobre un escenario existente para incorporarse como **colaborador** (por ejemplo, al crear un escenario similar o al consultar escenarios publicados).
- **RF-4.1.3:** Las sugerencias **no** serán visibles en la parte **pública** del sistema.
- **RF-4.1.4:** El estado de las sugerencias será accesible solo al **propietario**, al **sugerente** y a los **revisores** asignados al **propietario** del escenario.

### RF-4.2 Tipos de sugerencia

- **RF-4.2.1:** El sistema admitirá sugerencias de tipo **escenario** (comentario sobre el escenario completo).
- **RF-4.2.2:** El sistema admitirá sugerencias de tipo **párrafo** (comentario o **texto alternativo** para ese párrafo).
- **RF-4.2.3:** Los **investigadores** que deseen colaborar en un escenario existente **solo** podrán hacer sugerencias de **texto alternativo**.

### RF-4.3 Estados y ciclo de vida

- **RF-4.3.1:** Una sugerencia podrá estar en estado **pendiente**, **aceptada** o **rechazada**.
- **RF-4.3.2:** Solo el **propietario** podrá aceptar o rechazar sugerencias.
- **RF-4.3.3:** Si el **propietario** **rechaza** una sugerencia del **revisor**, el escenario **no** se **publica**.
- **RF-4.3.4:** Si el **propietario** **rechaza** una sugerencia del **investigador**, **no** se le acepta como **colaborador**.
- **RF-4.3.5:** Si el **propietario** **acepta** una sugerencia de **texto alternativo**, el texto propuesto se añadirá a un **nuevo borrador de trabajo** del escenario y el escenario deberá **enviarse de nuevo a revisión**, salvo sugerencias del **revisor** en revisión previa a la publicación, que **no** requieren trámite adicional.
- **RF-4.3.6:** Si el **propietario** **acepta** una sugerencia de **comentario**, deberá realizar los cambios en el escenario o párrafo y **enviar de nuevo a revisión**; el comentario **no** se eliminará hasta que el **revisor** lo valide.

### RF-4.4 Efectos de aceptación

- **RF-4.4.1:** La aceptación quedará registrada en el **historial de versiones** y en el **registro de actividad**; los cambios aceptados solo afectarán a la **versión de borrador** y no se mostrarán en el escenario público hasta completar de nuevo la **revisión** y la **publicación**.

### RF-4.5 Notificaciones

- **RF-4.5.1:** Al crear una sugerencia, el sistema notificará al **propietario** del escenario.
- **RF-4.5.2:** Al aceptar o rechazar una sugerencia, el sistema notificará al **sugerente**.
- **RF-4.5.3:** Las notificaciones se emitirán por **correo electrónico** y por el **canal interno** de la aplicación.

---

## RF-5. Flujo de revisión

El sistema deberá gestionar el flujo completo de revisión de escenarios.

### RF-5.1 Estados del workflow

- **RF-5.1.1:** El escenario podrá encontrarse en los estados: **borrador**, **en cola de revisión**, **en revisión**, **con cambios requeridos**, **realizando los cambios requeridos**, **publicado** y **no apto**.
- **RF-5.1.2:** El estado **no apto** representará escenarios **bloqueados** para publicación y edición por marcado de un **revisor** o el **admin** (salvo **reapertura** por **admin**, **RF-5.9**).

### RF-5.2 Borrador

- **RF-5.2.1:** Solo el **propietario** puede acceder a sus borradores.
- **RF-5.2.2:** Solo el **propietario** puede enviarlo a revisar.

### RF-5.3 Cola de revisión

- **RF-5.3.1:** Un escenario pasa a **en cola de revisión** cuando está en **borrador** y se envía a revisar, o cuando se han realizado cambios sugeridos que requieren nueva revisión.
- **RF-5.3.2:** El **propietario** podrá enviar a revisión un escenario **publicado** cuando le apliquen modificaciones y exista una **versión de trabajo** actualizada que deba revisarse.
- **RF-5.3.3:** El sistema notificará a los **revisores** correspondientes.
- **RF-5.3.4:** El **revisor** podrá consultar la cola de escenarios en revisión de investigadores **a su cargo**.
- **RF-5.3.5:** El **admin** podrá consultar la misma cola, con **alcance global**.
- **RF-5.3.6:** La cola se ordenará de **más reciente** a **más antiguo** por fecha de envío.
- **RF-5.3.7:** La cola soportará filtrado por **propietario** y **rango de fechas**, manteniendo orden descendente.
- **RF-5.3.8:** El sistema ofrecerá una sección de escenarios **ya revisados**.

### RF-5.4 En revisión

- **RF-5.4.1:** El **revisor** **acepta** el escenario y pasa a **publicado**.
- **RF-5.4.2:** El **revisor** puede modificar el **borrador** del escenario **mínimamente** antes de publicarlo.
- **RF-5.4.3:** El **revisor** **rechaza** el escenario y pasa a **no apto**.
- **RF-5.4.4:** El **revisor** realiza **sugerencias de cambio** y pasa a **con cambios requeridos** (**RF-4**).
- **RF-5.4.5:** El sistema notificará al **propietario** del escenario el **resultado** de la revisión.

### RF-5.5 Con cambios requeridos

- **RF-5.5.1:** El escenario tiene **cambios requeridos** indicados por el **revisor** para su publicación, o sugeridos por otro **investigador** que quiere colaborar en ese escenario.
- **RF-5.5.2:** El sistema almacenará una **nota estructurada** con los cambios requeridos del **revisor** para el escenario.
- **RF-5.5.3:** El sistema notificará al **propietario**.

### RF-5.6 Realizando los cambios requeridos

- **RF-5.6.1:** El **propietario** puede consultar qué escenarios tienen cambios requeridos y seleccionar uno para trabajar en esos cambios, pasando a **realizando los cambios requeridos**.
- **RF-5.6.2:** El **propietario** acepta o rechaza los cambios y realiza las **modificaciones** que se requieren (**RF-4**).
- **RF-5.6.3:** Después de ello, el escenario pasa de nuevo a **en revisión** (o **en cola de revisión**, según el flujo).

### RF-5.7 Publicado

- **RF-5.7.1:** Cuando un escenario está **publicado**, otro rol autorizado puede formular **sugerencias de cambio** (**RF-4**), por ejemplo al detectar un escenario similar o una mejora necesaria.
- **RF-5.7.2:** Tras sugerencias de cambio, el escenario puede pasar a **con cambios requeridos**.
- **RF-5.7.3:** Si el **propietario** **edita** un escenario **publicado**, se crea un **nuevo borrador de trabajo** con la versión actualizada (**RF-3.7**).

### RF-5.8 No apto

- **RF-5.8.1:** Un **revisor** o el **admin** podrá marcar un escenario como **no apto**.
- **RF-5.8.2:** El estado **no apto** bloquea la publicación y la edición del escenario.
- **RF-5.8.3:** El sistema notificará al **propietario**.

### RF-5.9 Reapertura de escenarios no aptos

- **RF-5.9.1:** Solo el **admin** podrá reabrir escenarios en estado **no apto**.
- **RF-5.9.2:** La reapertura cambiará el estado de **no apto** a **borrador**.
- **RF-5.9.3:** El sistema notificará la reapertura al **propietario**.

---

## RF-6. Reglas de revisión y cola de revisión

### RF-6.1 Asignación

- **RF-6.1.1:** Solo el **admin** podrá asignar a un **revisor** los **investigadores** que tiene a su cargo. Cuando uno de esos investigadores cree o modifique un escenario, deberá revisarlo el revisor correspondiente.
- **RF-6.1.2:** Un **investigador** podrá estar asignado a **uno o más** revisores.

### RF-6.2 Permisos de revisión

- **RF-6.2.1:** El **revisor** solo podrá revisar escenarios de investigadores **a su cargo**.
- **RF-6.2.2:** El **admin** no estará limitado y podrá **revisar**, **publicar**, **devolver** o **marcar** cualquier escenario.

---

## RF-7. Búsqueda y lectura de escenarios

### RF-7.1 Búsqueda de escenarios propios

- **RF-7.1.1:** El **investigador** o el **revisor** podrá consultar su listado de escenarios.
- **RF-7.1.2:** El listado incluirá escenarios donde sea **propietario** o **colaborador**.
- **RF-7.1.3:** El sistema no mostrará escenarios sin relación con el usuario en este listado.

### RF-7.2 Lectura pública de escenarios publicados

- **RF-7.2.1:** Los usuarios **no autenticados** podrán listar y leer el detalle de escenarios **publicados**, **excepto** los **riesgos etiquetados**.
- **RF-7.2.2:** En la lectura pública **no** se permitirá valorar la ética del escenario (**RF-8**).

### RF-7.3 Búsqueda pública de escenarios

- **RF-7.3.1:** El sistema permitirá **búsqueda por texto**.
- **RF-7.3.2:** El sistema permitirá **filtrar** por **propietario**, **fecha** y **etiquetas**.
- **RF-7.3.3:** El sistema permitirá **filtrar** por **propiedades** del escenario.
- **RF-7.3.4:** El orden por defecto de resultados será de **más reciente** a **más antiguo**.
- **RF-7.3.5:** El sistema aplicará **paginación** en resultados de búsqueda.
- **RF-7.3.6:** Todo usuario **autenticado** podrá listar escenarios **publicados** de otros investigadores.

---

## RF-8. Análisis ético de escenarios

El sistema deberá permitir la evaluación ética de escenarios **publicados** por **usuarios registrados**.

### RF-8.1 Catálogo de riesgos éticos

- **RF-8.1.1:** El sistema mantendrá un **catálogo de riesgos éticos**.
- **RF-8.1.2:** El catálogo será **editable por el admin**.

**Catálogo:**

- Sesgo algorítmico y discriminación  
- Violación de la privacidad  
- Falta de transparencia algorítmica  
- Manipulación conductual  
- Dependencia excesiva  
- Desinformación y contenido engañoso  
- Brecha de responsabilidad  
- Exceso de confianza  
- Antropomorfismo  
- Daño emocional o físico  
- Erosión de competencias cognitivas  
- Violación de la propiedad intelectual  
- Erosión de competencias sociales  
- Contenido inadecuado  
- Falta de identificación como agente artificial  
- Simulación de humanidad  
- Generación interesada de vínculos emocionales  
- Diseño deshumanizante  
- Diseño de comportamiento adictivo  
- Diseño negligente  
- Problemas con los principios éticos que usa la IA  
- Generación de desigualdad  
- Control de la IA sobre el niño  

### RF-8.2 Evaluación

- **RF-8.2.1:** El **usuario registrado** podrá realizar una evaluación de los escenarios **publicados**.
- **RF-8.2.2:** Indicará una **puntuación de riesgo ético** de **1 a 10** (1 = muy bajo, 10 = muy alto).
- **RF-8.2.3:** Indicará una **puntuación de beneficio** de **1 a 10** (1 = muy bajo, 10 = muy alto).
- **RF-8.2.4:** Seleccionará los **riesgos éticos** que detecta en el escenario, elegidos del catálogo; deberá incluir **al menos un** riesgo del catálogo.
- **RF-8.2.5:** Podrá añadir un **comentario libre**.
- **RF-8.2.6:** Solo las evaluaciones **completas** podrán enviarse.

### RF-8.3 Aspectos a considerar

- **RF-8.3.1:** **Edad de los niños:** qué ocurre en cada rango de edad.
- **RF-8.3.2:** **Duración y frecuencia:** para cada rango de edad, durante cuánto tiempo y con qué frecuencia sería aceptable el uso del escenario.
- **RF-8.3.3:** **Número de niños y niñas:** si participan varios, cuál sería el mínimo y el máximo recomendado.
- **RF-8.3.4:** **Personas físicamente presentes:** quiénes están presentes en persona.
- **RF-8.3.5:** **Personas presentes de forma en línea o virtual.**
- **RF-8.3.6:** **Uso de las gafas:** quiénes de los presentes usan las gafas.
- **RF-8.3.7:** **Lugar de ejecución:** cómo afecta el lugar al desarrollo del escenario.
- **RF-8.3.8:** **Circunstancias especiales** del niño o la niña (discapacidades, enfermedad, etc.).
- **RF-8.3.9:** **Consentimiento:** quién da el consentimiento para que se ejecute el escenario.

### RF-8.4 Reglas de evaluación

- **RF-8.4.1:** Cada usuario podrá realizar **una única** evaluación por escenario.
- **RF-8.4.2:** La evaluación **no** será editable una vez enviada.

### RF-8.5 Visibilidad de las evaluaciones

- **RF-8.5.1:** El sistema mostrará para los **investigadores** la **media global** de la puntuación de **riesgo** y de **beneficio** del escenario y las **etiquetas de riesgo**.
- **RF-8.5.2:** El **administrador** y el **propietario** del escenario podrán consultar el **detalle** de cada evaluación.
- **RF-8.5.3:** El **administrador** y el **propietario** podrán ver la **identidad** del usuario evaluador.

### RF-8.6 Moderación y control

- **RF-8.6.1:** El **administrador** podrá **ocultar** o **eliminar** evaluaciones.

---

## RF-9. Asistencia con IA

### RF-9.2 Validación de datos sensibles

- **RF-9.2.1:** Antes de **enviar a revisión**, el sistema revisará el contenido para detectar indicios de **datos sensibles** o información **identificable**.
- **RF-9.2.2:** Si la revisión detecta problemas, el sistema **impedirá continuar** y pedirá que se corrija el contenido de forma explícita.
- **RF-9.2.3:** Los mensajes explicarán el motivo del bloqueo o de la advertencia **sin reproducir** en el mensaje los datos sensibles detectados.

### RF-9.3 Detección de duplicados

- **RF-9.3.1:** Cuando el usuario **cree** o **edite** un escenario y exista contenido suficiente para el análisis (como mínimo **título** y **descripción**), el sistema solicitará a la **IA** una comprobación de **similitud** con otros escenarios.
- **RF-9.3.2:** El sistema mostrará al usuario los escenarios **candidatos a ser similares**, con la información necesaria para decidir.
- **RF-9.3.3:** El resultado de la detección se presentará como **sugerencia**; el usuario decidirá si continúa con un escenario nuevo, lo modifica o inicia otra acción (por ejemplo, sugerencias al **propietario**, **RF-4**).
- **RF-9.3.4:** Cada ejecución de detección quedará **registrada** (escenario analizado, resultado, fecha y hora y usuario).

---

## RF-10. Registro de actividad y trazabilidad

El sistema llevará un **registro** de las actuaciones relevantes para la **trazabilidad**, la **supervisión** y el **control de cambios** (incluidas las de carácter administrativo). Este bloque **sigue vigente** además del alcance reducido de **RF-1** a **RF-9**.

### RF-10.1 Alcance

- **RF-10.1.1:** El registro incluirá las actuaciones que este documento marque como obligatorias, así como otras que el producto considere auditables.
- **RF-10.1.2:** El **admin** podrá **consultar** el registro.

### RF-10.2 Contenido mínimo de cada anotación

- **RF-10.2.1:** Cada anotación incluirá, como mínimo: **quién** actuó, **qué tipo de acción** fue, **sobre qué elemento** y **cuándo** ocurrió.
- **RF-10.2.2:** Cuando corresponda, se guardará la información **antes y después** del cambio.
- **RF-10.2.3:** Cuando corresponda, se guardará el **estado anterior** y el **estado nuevo** (por ejemplo, en cambios de flujo de un escenario).

### RF-10.3 Actuaciones administrativas que deben quedar registradas

- **RF-10.3.1:** Alta de cuentas de **investigador** por parte del **admin**.
- **RF-10.3.2:** Cambios de **rol** de usuario.
- **RF-10.3.3:** **Activación** y **desactivación** de cuentas.
- **RF-10.3.4:** **Asignación**, **desasignación** y **reasignación** de **investigadores** a **revisores**.
- **RF-10.3.5:** Acciones de **moderación** sobre evaluaciones éticas (**ocultar** o **eliminar**).

### RF-10.4 Actuaciones sobre escenarios que deben quedar registradas

- **RF-10.4.1:** Creación de escenario.
- **RF-10.4.2:** Ediciones relevantes y **nueva entrada** en el historial de versiones del escenario.
- **RF-10.4.3:** Incorporación y retirada de **colaboradores**.
- **RF-10.4.4:** **Borrado lógico** de borradores.
- **RF-10.4.5:** **Envío a revisión**.

### RF-10.5 Actuaciones del flujo de revisión que deben quedar registradas

- **RF-10.5.1:** **Publicación** del escenario.
- **RF-10.5.2:** **Rechazo** en el marco de la revisión, incluyendo la **nota** asociada cuando exista.
- **RF-10.5.3:** **Solicitud de cambios** al propietario.
- **RF-10.5.4:** Marcado como **no apto** y **reapertura** de escenarios **no aptos**.

### RF-10.6 Actuaciones sobre sugerencias que deben quedar registradas

- **RF-10.6.1:** Creación de sugerencia.
- **RF-10.6.2:** Aceptación de sugerencia.
- **RF-10.6.3:** Rechazo de sugerencia.
- **RF-10.6.4:** En sugerencias sobre un **párrafo**, la anotación identificará **qué párrafo** estaba afectado.

### RF-10.7 Evaluación ética

- **RF-10.7.1:** Alta de una **evaluación ética** (quién evalúa, escenario evaluado y momento).

### RF-10.8 Consulta del registro

- **RF-10.8.1:** Consulta por **rango de fechas**.
- **RF-10.8.2:** Consulta por **autor de la acción** y por **tipo de acción**.
- **RF-10.8.3:** Consulta por **objeto** relacionado (por ejemplo, **usuario**, **escenario**, **sugerencia** o **evaluación**).

### RF-10.9 Asistencia de inteligencia artificial (constancia en el registro)

- **RF-10.9.1:** Generación de una sugerencia de asistencia (con enlace al escenario y a la persona solicitante).
- **RF-10.9.2:** Aplicación de una sugerencia de asistencia al escenario.
- **RF-10.9.3:** Descarte **explícito** de una sugerencia de asistencia por la persona usuaria.
- **RF-10.9.4:** Imposibilidad de aplicar una sugerencia por **desactualización** o **incompatibilidad** con el escenario.

### RF-10.10 Comprobación de datos sensibles (constancia en el registro)

- **RF-10.10.1:** Cada ejecución del análisis previo a **envío a revisión** sobre un escenario.
- **RF-10.10.2:** El **resultado** del análisis **por tipo** de hallazgo (según la política del producto).
- **RF-10.10.3:** El registro **no** incluirá datos sensibles detectados en el contenido analizado.
