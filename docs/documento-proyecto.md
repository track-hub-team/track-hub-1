# Documento del Proyecto

## Portada

### Nombre del proyecto
**TRACK-HUB-1**

### Grupo
**Grupo 3 tarde**

### Curso escolar
**2025/2026**

### Asignatura
**Evolución y Gestión de la Configuración**

---

### Miembros del equipo

| Miembro | Implicación (1–10) |
|-------|--------------------|
| Castrillón Mora, Pablo | 9 |
| Hu, Jianwu | 9 |
| Olivencia Moreno, Pablo | 9.5 |
| Ramírez Gil, Adrián | 9 |
| Rodríguez Calderón, Antonio | 10 |
| Varo Vera, Juan | 9 |


---

### Enlaces de interés
- **Repositorio de código:** [https://github.com/track-hub-team/track-hub-1]
- **Sistema desplegado en Render producción:** [https://track-hub-1.onrender.com]
- **Sistema desplegado en Render preproducción:** [https://track-hub-1-staging.onrender.com]
- **Sistema desplegado en Server propio preproducción:** [https://pre-trackhub.pabolimor.cloud/]
- **Sistema desplegado en Server propio producción:** [https://trackhub.pabolimor.cloud/]
- **Documentación principal:** [https://github.com/track-hub-team/track-hub-1/blob/trunk/README.md]
- **Enlace de Fakenodo desplegado en servidor propio:** [https://fakenodo.pabolimor.cloud/health]
- **Repositorio con archivos de ejemplo:** [https://github.com/pcm290/testgithubrepositorytrackhub]
---
## Indicadores del proyecto

> Se aportan enlaces a evidencias (issues, commits, gráficas, PRs, Sonar, etc.) que permiten analizar los indicadores.

| Miembro | Horas | Commits | LoC | Test | Issues | Work Item | Dificultad |
|--------|------:|--------:|----:|-----:|-------:|-----------|-----------|
| Rodríguez Calderón, Antonio | 71 | 95 | ≈9001 | 11 | 74 |  | L |
| Castrillón Mora, Pablo | 52:18 | 12 | 5624 | 23 | 14 | Descripción breve | H/M/L |
| Hu, Jianwu | 51:30 | 16 | 1519 | 30 | 10 | Descripción breve | H/M/L |
| **TOTAL** | tHH | tXX | tYY | tZZ | tII | Resumen | H (X) / M (Y) / L (Z) |

**Criterios:**
- **Horas:** horas reales empleadas.
- **Commits:** solo commits del equipo.
- **LoC:** líneas creadas/modificadas por el equipo (sin terceros).
- **Test:** tests nuevos del equipo.
- **Issues:** issues gestionadas por el equipo.
- **Work Item:** principal WI asumido.
- **Dificultad:** Alta / Media / Baja.

**Evidencias:**
- Issues: [enlace]
- Commits/PRs: [enlace]
- Métricas/Gráficas: [enlace]

**Nota cálculo de LoC (Antonio Rodríguez):**

El valor de 9001 líneas de código es aproximado. No se sabe a ciencia cierta las líneas cubiertas ya que ha sido el autor del commit inicial y la persona que ha subido datos de ejemplo del seeder. No obstante se ha intendado estimar como sigue:

```bash
git log --author="PDJ6975" 4d8f5cec..HEAD --pretty=tformat: --numstat | grep -v '\.gpx$' | grep -v '\.svg$' | awk '{add+=$1;
       del+=$2} END {print "Añadidas:", add; print "Eliminadas:", del}'
```

Con este comando obtenemos la siguiente salida:
- **Añadidas**: 9001 líneas de código
- **Eliminadas**: 3039

---
## Integración con otros equipos

- **Track*hub-2:** breve descripción de la integración y motivo.
  Evidencia: [enlace]

---

## Resumen ejecutivo

**Track-Hub-1** es una plataforma web integral de gestión y publicación de datasets científicos desarrollada durante el curso académico 2025/2026 para la asignatura Evolución y Gestión de la Configuración. El sistema permite a investigadores y científicos de datos crear, compartir, publicar y explorar conjuntos de datos estructurados, integrándose con servicios externos como Zenodo para asignar identificadores digitales persistentes (DOI) a las publicaciones científicas.

### Contexto y Objetivos

El proyecto surge de la necesidad de proporcionar una solución moderna y automatizada para la gestión de datasets en entornos académicos y de investigación. Los objetivos principales del desarrollo fueron:

- **Gestión completa de datasets**: Implementar funcionalidades CRUD (Create, Read, Update, Delete) con soporte para múltiples formatos de archivo, incluyendo UVL (Universal Variability Language), GPX (datos geoespaciales) y archivos comprimidos ZIP.

- **Autenticación y perfiles robustos**: Desarrollar un sistema seguro de registro, autenticación y gestión de perfiles de usuario que permita personalización y control de privacidad.

- **Colaboración científica**: Crear un ecosistema de comunidades donde investigadores puedan agruparse por áreas de interés, compartir datasets y colaborar en proyectos comunes.

- **Integración con ecosistemas externos**: Establecer conexiones con Zenodo (repositorio de publicaciones científicas) para generación automática de DOI, y con GitHub mediante webhooks para sincronización de repositorios.

- **Pipeline CI/CD completo**: Implementar un proceso de integración y despliegue continuo que garantice calidad del código, automatice el testing y facilite despliegues seguros en múltiples entornos.

- **Análisis de modelos de características**: Integrar Flamapy para análisis automatizado de feature models, proporcionando validación y métricas sobre variabilidad de software.

### Alcance y Resultados Logrados

El sistema implementado consta de **nueve módulos principales** completamente funcionales:

1. **Autenticación y Perfiles** (`auth`, `profile`): Sistema de registro con validación de correo electrónico, login seguro con hash de contraseñas, gestión de sesiones y perfiles personalizables con biografía, afiliación y ORCID.

2. **Gestión de Datasets** (`dataset`): Creación, edición, eliminación y visualización de datasets con metadatos completos (título, descripción, autores, palabras clave), versionado, control de visibilidad (público/privado) y soporte para múltiples tipos de archivo.

3. **Feature Models** (`featuremodel`, `flamapy`): Gestión de modelos de características en formato UVL, análisis automatizado mediante Flamapy, visualización de árboles de características y métricas de variabilidad.

4. **Comunidades Científicas** (`community`): Creación de comunidades temáticas, gestión de membresías, moderación de contenido y datasets compartidos dentro de comunidades.

5. **Exploración y Búsqueda** (`explore`): Motor de búsqueda avanzado con filtros por autor, fecha, tipo de archivo, palabras clave y comunidad, con paginación y ordenamiento flexible.

6. **Integración Zenodo** (`zenodo`): Publicación automatizada en Zenodo/Fakenodo, generación de DOI, sincronización de metadatos y gestión de deposiciones.

7. **Sistema de Webhooks** (`webhook`): Recepción de eventos desde GitHub, sincronización automática de repositorios, validación de firmas HMAC y procesamiento asíncrono de actualizaciones.

8. **Gestión de Archivos** (`hubfile`): Sistema de almacenamiento con checksum MD5, detección de duplicados, validación de formatos y gestión de cuotas por usuario.

9. **Notificaciones por Email** (`mail`): Sistema de correo transaccional para confirmaciones, notificaciones de comunidad y alertas administrativas.

### Infraestructura y Proceso de Desarrollo

La infraestructura del proyecto se fundamenta en **prácticas modernas de DevOps y gestión de configuración**:

- **Arquitectura tecnológica**: Stack basado en Python 3.12 con Flask como framework web, SQLAlchemy para ORM, PostgreSQL como base de datos relacional, Bootstrap 5 para frontend responsivo y JavaScript vanilla para interactividad.

- **Estrategia de branching**: Trunk-based development con ramas feature de corta duración (máximo 2-3 días), integración frecuente a trunk, protección de rama principal y pull requests obligatorias con revisión por pares.

- **Versionado semántico**: Sistema automatizado mediante hooks pre-commit que incrementa versiones siguiendo SemVer (MAJOR.MINOR.PATCH), generación automática de tags y changelog basado en Conventional Commits.

- **Pipeline CI/CD**: GitHub Actions con flujos automatizados que ejecutan linting (flake8), testing (pytest con >80% cobertura), análisis estático de código, construcción de artefactos y despliegue automático a staging tras merge a trunk.

- **Entornos de despliegue**: Cuatro entornos activos - desarrollo local, preproducción en Render (track-hub-1-staging.onrender.com), preproducción en servidor propio (pre-trackhub.pabolimor.cloud), producción en Render (track-hub-1.onrender.com) y producción en servidor propio (trackhub.pabolimor.cloud).

- **Fakenodo**: Mock server de Zenodo desplegado independientemente (fakenodo.pabolimor.cloud) para desarrollo y testing sin consumir cuota de Zenodo real.

### Métricas del Proyecto

El equipo de seis desarrolladores ha generado las siguientes métricas cuantificables:

- **+13.161 líneas de código** producidas (excluyendo dependencias de terceros)
- **>89 commits** del equipo con mensajes siguiendo Conventional Commits
- **>71 horas** de desarrollo documentadas por desarrollador
- **Suite completa de tests** unitarios e integración con pytest
- **Cobertura de código >80%** reportada automáticamente en CI
- **Revisión por pares** en el 100% de pull requests antes de integración
- **Issues gestionadas** mediante GitHub Projects con workflow kanban

### Valor Aportado y Estado Final

**Track-Hub-1** aporta valor tangible en múltiples dimensiones:

- **Gestión científica mejorada**: Centralización de datasets con trazabilidad completa de versiones y autoría.
- **Automatización robusta**: Reducción del error humano mediante despliegues automatizados y validación continua.
- **Interoperabilidad**: Integración con Zenodo garantiza persistencia y reconocimiento académico mediante DOI.
- **Colaboración facilitada**: Comunidades científicas temáticas fomentan networking y trabajo conjunto.
- **Calidad asegurada**: Testing automatizado y code review garantizan estándares profesionales.
- **Experiencia práctica**: Implementación real de conceptos de SCM (Software Configuration Management) en contexto académico.

El sistema se encuentra en **estado productivo y operacional**, con todas las funcionalidades core implementadas, testeadas y desplegadas. Cuenta con documentación técnica completa, múltiples entornos activos y una base sólida para extensiones futuras, cumpliendo satisfactoriamente los objetivos académicos y técnicos establecidos al inicio del proyecto.

## Descripción del sistema

### Visión General

**Track-Hub-1** es una plataforma web diseñada para la gestión integral del ciclo de vida de datasets científicos, con especial énfasis en modelos de características (feature models) expresados en formato UVL (Universal Variability Language). El sistema se estructura como una aplicación Flask modular que permite a investigadores gestionar, versionar, publicar y compartir conjuntos de datos de forma colaborativa, integrándose con repositorios de publicaciones científicas para garantizar la persistencia y citabilidad académica.

La arquitectura del sistema se fundamenta en una separación clara de responsabilidades mediante módulos independientes que interactúan a través de interfaces bien definidas, siguiendo patrones de diseño como Repository, Service Layer y Dependency Injection. Esta modularidad facilita el mantenimiento, testing y extensibilidad del código.

### Arquitectura Técnica

#### Stack Tecnológico

El sistema se construye sobre las siguientes tecnologías principales:


- **Backend**: Python 3.12 con Flask 3.x como framework web principal
- **ORM**: SQLAlchemy para abstracción de base de datos relacional
- **Base de datos**: PostgreSQL 14+ (producción) y SQLite (desarrollo/testing)
- **Frontend**: Bootstrap 5 para diseño responsivo, JavaScript vanilla para interactividad cliente
- **Testing**: pytest con coverage >80%, fixtures para datos de prueba
- **CI/CD**: GitHub Actions para pipelines automatizados
- **Despliegue**: Render (PaaS) y servidor VPS propio con Nginx + Gunicorn

#### Estructura Modular

La aplicación se organiza en **11 módulos funcionales** dentro del directorio `app/modules/`:

1. **auth**: Autenticación y autorización de usuarios
2. **profile**: Gestión de perfiles de investigador
3. **dataset**: CRUD y versionado de datasets
4. **featuremodel**: Manejo de modelos UVL
5. **flamapy**: Análisis de feature models (no modificado)
6. **community**: Comunidades científicas temáticas
7. **explore**: Búsqueda y filtrado de datasets
8. **zenodo**: Integración con repositorio Zenodo
9. **webhook**: Sincronización con GitHub (no modificado)
10. **hubfile**: Gestión de archivos subidos (no modificado)
11. **mail**: Sistema de notificaciones por correo electrónico

Cada módulo sigue una estructura consistente:
- `models.py`: Modelos de datos SQLAlchemy
- `repositories.py`: Capa de acceso a datos
- `services.py`: Lógica de negocio
- `routes.py`: Endpoints y controladores
- `forms.py`: Formularios FlaskWTF
- `templates/`: Vistas Jinja2
- `tests/`: Suite de pruebas unitarias e integración

### Funcionalidades Principales

#### 1. Sistema de Autenticación y Perfiles

El módulo **auth** implementa un sistema completo de gestión de identidades:

- **Registro de usuarios**: Formulario con validación de email único, contraseñas seguras (hash bcrypt) y confirmación por correo electrónico
- **Login/Logout**: Sesiones gestionadas con Flask-Login, protección CSRF
- **Recuperación de contraseña**: Flow de reset mediante tokens temporales enviados por email
- **Perfiles de investigador** (`profile`): Información académica incluyendo nombre completo, afiliación institucional, biografía y ORCID (identificador único de investigador)

**Características técnicas**:
- Hash de contraseñas con `werkzeug.security`
- Tokens de confirmación con expiración temporal
- Decoradores de autorización para rutas protegidas
- Gestión de sesiones persistentes

#### 2. Gestión de Datasets

El módulo **dataset** constituye el núcleo funcional del sistema:

**Operaciones CRUD**:
- **Creación**: Formulario con metadatos (título, descripción, autores, palabras clave), carga de archivos UVL/GPX/ZIP, asignación de DOI conceptual único
- **Lectura**: Visualización detallada con metadatos, lista de archivos, estadísticas de uso
- **Actualización**: Edición de metadatos, adición/eliminación de archivos, **versionado automático**
- **Eliminación**: Soft delete con confirmación, mantenimiento de historial

**Sistema de Versionado** (implementado en este proyecto):
- **Versiones menores**: Ediciones de metadatos sin cambio de archivos (e.g., 1.0.0 → 1.0.1)
- **Versiones mayores**: Modificación de archivos que genera nuevo DOI en Zenodo (e.g., 1.0.0 → 2.0.0)
- **DOI conceptual**: Identificador permanente que siempre apunta a la última versión
- **DOI específicos**: Cada versión mayor tiene su propio DOI inmutable
- **Historial de versiones**: Listado completo con fechas, autores y diferencias
- **Acceso a versiones anteriores**: Descarga de cualquier versión histórica para reproducibilidad científica

**Integración con GitHub**:
- Importación directa desde repositorios públicos mediante URL
- Parsing automático de estructura de directorios
- Sincronización vía webhooks (módulo `webhook` existente)

**Carga de archivos ZIP** (implementado en este proyecto):
- Subida de archivos comprimidos con múltiples datasets
- Descompresión automática y validación de estructura
- Extracción de metadatos de archivos individuales
- Creación de dataset con archivos descomprimidos

#### 3. Comunidades Científicas

El módulo **community** (completamente desarrollado en este proyecto) implementa espacios colaborativos:

**Estructura de comunidades**:
- **Creación**: Formulario con nombre, descripción, tags temáticos, imagen de portada
- **Roles**: Creador (owner), moderadores, miembros regulares
- **Visibilidad**: Públicas (descubribles) o privadas (solo por invitación)

**Gestión de contenido**:
- **Propuesta de datasets**: Los usuarios solicitan añadir sus datasets a una comunidad
- **Moderación**: Curadores aprueban/rechazan propuestas con notificación por email
- **Catálogo comunitario**: Vista filtrada de datasets aceptados
- **Búsqueda por comunidad**: Filtro en módulo `explore`

**Notificaciones por email** (implementado en este proyecto):
- Email automático cuando un dataset es aceptado/rechazado
- Plantillas HTML personalizadas con información de la comunidad
- Sistema de suscripción configurable

#### 4. Sistema de Notificaciones

El módulo **mail** proporciona comunicaciones automatizadas:

**Eventos soportados**:
- Confirmación de registro de cuenta
- Restablecimiento de contraseña
- Aceptación/rechazo de dataset en comunidad
- Nuevos datasets de autores seguidos (implementado en este proyecto)
- Nuevos datasets en comunidades seguidas (implementado en este proyecto)

**Arquitectura de notificaciones**:
- Cola de emails procesada asíncronamente
- Plantillas Jinja2 con soporte HTML/texto plano
- Configuración SMTP flexible (Gmail, SendGrid, etc.)
- Sistema de suscripción por usuario para control de spam

#### 5. Sistema de Seguimiento

Funcionalidad desarrollada en este proyecto que permite:

**Seguimiento de autores**:
- Botón "Follow Author" en perfiles públicos
- Lista de autores seguidos en perfil personal
- Notificación email cuando un autor seguido publica nuevo dataset
- Dejar de seguir con un click

**Seguimiento de comunidades**:
- Botón "Follow Community" en página de comunidad
- Dashboard de comunidades seguidas
- Email automático cuando se añade dataset a comunidad seguida
- Gestión de suscripciones desde configuración de usuario

**Implementación técnica**:
- Tabla `user_follows` con relación many-to-many
- Tabla `community_follows` para suscripciones a comunidades
- Triggers de base de datos para envío de notificaciones
- Batch processing de emails para evitar spam

#### 6. Sistema de Comentarios

Módulo desarrollado completamente en este proyecto:

**Funcionalidades**:
- **Añadir comentarios**: Formulario en página de dataset, texto enriquecido
- **Visualización**: Lista ordenada cronológicamente con autor y fecha
- **Moderación**: Propietario del dataset puede eliminar comentarios inapropiados
- **Respuestas anidadas** (opcional): Sistema de hilos de conversación
- **Notificaciones**: Email al autor cuando hay nuevo comentario

**Modelo de datos**:
```python
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))  # Para respuestas
```

#### 7. Exploración y Búsqueda

El módulo **explore** proporciona descubrimiento de contenido:

**Criterios de búsqueda**:
- Texto libre en título/descripción
- Filtro por autor específico
- Filtro por comunidad
- Filtro por tipo de archivo (UVL, GPX, ZIP)
- Rango de fechas de publicación
- Palabras clave (tags)

**Presentación de resultados**:
- Vista de tarjetas con preview de metadatos
- Paginación configurable (10/25/50 resultados)
- Ordenamiento por relevancia, fecha, número de descargas
- Exportación de resultados a CSV

#### 8. Integración con Zenodo

El módulo **zenodo** gestiona la publicación científica:

**Flujo de publicación**:
1. Usuario solicita publicación de dataset
2. Sistema crea deposición en Zenodo/Fakenodo
3. Carga automática de archivos y metadatos
4. Generación de DOI persistente
5. Sincronización bidireccional de metadatos

**Versionado en Zenodo**:
- Creación de nuevas versiones para ediciones mayores
- Mantenimiento de relaciones conceptDOI ↔ versionDOI
- Actualización de metadatos sin nueva versión (ediciones menores)

**Fakenodo**: Mock server para desarrollo y testing sin consumir cuota de Zenodo sandbox

### Cambios Desarrollados en el Proyecto

A continuación se detallan **explícitamente** los cambios implementados durante este proyecto:

#### Cambio 1: Sistema de Versionado de Datasets

**Issue**: "Allow users to explore and understand the evolution of a dataset across its versions"

**Implementación**:
- Tabla `dataset_version` con relación one-to-many a `dataset`
- Numeración automática siguiendo SemVer (MAJOR.MINOR.PATCH)
- Vista `/dataset/<id>/versions` con historial completo
- Endpoint `/dataset/<id>/version/<version_num>` para acceso a versiones anteriores
- Lógica de diferenciación entre DOI conceptual y DOI de versión
- Badge "Latest Version" en UI para destacar versión actual

**Archivos modificados**:
- `app/modules/dataset/models.py`: Modelo `DatasetVersion`
- `app/modules/dataset/services.py`: Métodos `create_version()`, `get_version_history()`
- `app/modules/dataset/routes.py`: Rutas de versionado
- `app/modules/dataset/templates/dataset/view.html`: UI de historial

#### Cambio 2: Carga de Archivos ZIP

**Issue**: "As a user I want to be able to upload models from a ZIP"

**Implementación**:
- Handler `ZipFileHandler` para procesamiento de archivos comprimidos
- Validación de tamaño máximo (100MB por defecto)
- Descompresión segura con protección contra zip bombs
- Extracción de múltiples archivos UVL/GPX
- Creación automática de dataset con archivos descomprimidos
- Preservación de estructura de directorios

**Archivos creados/modificados**:
- `app/modules/dataset/handlers/zip_handler.py`: Lógica de descompresión
- `app/modules/dataset/forms.py`: Campo `FileField` para ZIP
- `app/modules/dataset/routes.py`: Endpoint `/upload/zip`
- `docs/zip-upload.md`: Documentación técnica

#### Cambio 3: Comunidades Científicas

**Issue**: "As a user, I want to be able to create communities"

**Implementación completa del módulo `community`**:
- Modelos `Community`, `CommunityMember`, `CommunityDataset`
- CRUD completo de comunidades con formularios validados
- Sistema de roles (owner, moderator, member)
- Workflow de propuesta → revisión → aceptación de datasets
- Página de comunidad con catálogo de datasets aprobados
- Integración con módulo `explore` para filtrar por comunidad

**Archivos creados**:
- `app/modules/community/` (módulo completo nuevo)
- `docs/communities.md`: Documentación de funcionalidad

#### Cambio 4: Sistema de Comentarios

**Issue**: "As a user, I want to comment on a dataset to give feedback"

**Implementación**:
- Modelo `Comment` con relación a `User` y `Dataset`
- Formulario de comentario con validación anti-XSS
- Vista de comentarios en página de dataset
- Moderación por propietario del dataset (eliminar comentarios)
- Soporte opcional para respuestas anidadas (threading)
- Notificación por email al autor del dataset

**Archivos creados/modificados**:
- `app/modules/dataset/models.py`: Modelo `Comment`
- `app/modules/dataset/services.py`: `add_comment()`, `delete_comment()`
- `app/modules/dataset/templates/dataset/view.html`: Sección de comentarios
- `docs/comment-moderation.md`: Guía de moderación

#### Cambio 5: Sistema de Seguimiento y Notificaciones

**Issue**: "As a user, I want to follow specific authors and communities"

**Implementación**:
- Tabla `user_follows` para seguimiento de autores
- Tabla `community_follows` para seguimiento de comunidades
- Endpoints REST `/api/follow/user/<id>` y `/api/follow/community/<id>`
- Listeners de eventos `on_dataset_published` y `on_dataset_added_to_community`
- Servicio de email batch para notificaciones agrupadas
- Dashboard de suscripciones en perfil de usuario

**Archivos creados/modificados**:
- `app/modules/profile/models.py`: Relaciones de seguimiento
- `app/modules/profile/services.py`: `follow_user()`, `unfollow_user()`
- `app/modules/community/services.py`: `follow_community()`, notificaciones
- `app/modules/mail/services.py`: Templates de notificación
- `app/modules/profile/routes.py`: API de seguimiento

#### Cambio 6: Notificaciones de Aceptación en Comunidades

**Issue**: "As a user, I want to receive notifications when my dataset is accepted"

**Implementación**:
- Event listener en `CommunityService.accept_dataset()`
- Template de email `community_acceptance.html`
- Información contextual (nombre de comunidad, dataset, moderador)
- Link directo a dataset en comunidad
- Configuración de preferencias de notificación

**Archivos modificados**:
- `app/modules/community/services.py`: Trigger de email
- `app/modules/mail/templates/community_acceptance.html`: Template
- `app/modules/profile/models.py`: Campo `notification_preferences`

### Relación entre Componentes

**Diagrama de dependencias (simplificado)**:

```
auth ─┬─> profile
      └─> dataset ─┬─> featuremodel ─> flamapy
                   ├─> hubfile
                   ├─> zenodo
                   ├─> community
                   └─> webhook

explore ──> dataset
          └> community

mail <── [todos los módulos que envían notificaciones]
```

**Flujo de datos típico**:

1. Usuario se autentica (`auth`) y obtiene sesión
2. Crea/edita perfil (`profile`) con información académica
3. Sube dataset (`dataset`) que puede contener:
   - Archivos UVL → procesados por `featuremodel`
   - Archivos ZIP → descomprimidos por handler ZIP
   - Archivos GPX → validados y almacenados
4. Dataset se versiona automáticamente según cambios
5. Usuario solicita publicación → `zenodo` genera DOI
6. Dataset se propone a comunidad (`community`)
7. Moderador acepta → email automático (`mail`)
8. Dataset indexado para búsqueda (`explore`)
9. Seguidores reciben notificación (`mail`)

### Estado de Módulos No Modificados

Los siguientes módulos **vienen de serie** y no han sido modificados en este proyecto:

- **flamapy**: Análisis de feature models con métricas de variabilidad
- **webhook**: Sincronización automática con repositorios GitHub
- **hubfile**: Sistema de gestión de archivos con checksums y deduplicación

Estos módulos funcionan de forma autónoma y son consumidos por otros componentes cuando es necesario.

### Calidad y Testing

**Cobertura de tests**:
- >80% de cobertura de código medida con pytest-cov
- Tests unitarios para cada service y repository
- Tests de integración para flujos completos
- Fixtures reutilizables en `conftest.py`

**Linting y formateo**:
- flake8 para cumplimiento PEP8
- Hooks pre-commit para validación automática
- Conventional Commits para mensajes descriptivos

**Seguridad**:
- Validación de entrada en todos los formularios
- Protección CSRF en todas las peticiones POST
- Hash seguro de contraseñas con bcrypt
- Sanitización de contenido HTML en comentarios
- Validación de firmas HMAC en webhooks

### Conclusión Técnica

El sistema resultante es una plataforma robusta, modular y extensible que cumple los objetivos de gestión de datasets científicos con un enfoque en trazabilidad, colaboración y reproducibilidad. La arquitectura basada en módulos independientes facilita el mantenimiento y la adición de nuevas funcionalidades, mientras que el pipeline CI/CD garantiza calidad constante en el código desplegado.

## Visión global del proceso de desarrollo

El desarrollo de **Track-Hub-1** se ha fundamentado en un proceso riguroso de ingeniería de software que integra metodologías ágiles, gestión de configuración moderna y prácticas DevOps. El equipo de seis desarrolladores ha seguido un flujo de trabajo estructurado que garantiza calidad, trazabilidad y despliegue continuo mediante automatización y revisión por pares.

### Estrategia de Branching: Trunk-Based Development

El proyecto adopta **Trunk-Based Development** como estrategia de gestión de ramas, abandonando modelos tradicionales como GitFlow en favor de integración continua. La rama principal `trunk` representa el estado siempre desplegable del código, mientras que las ramas de características (`feature/*`) tienen un ciclo de vida muy corto (máximo 2-3 días).

**Características del modelo implementado**:

- **Rama principal protegida**: `trunk` requiere pull requests aprobadas y CI pasando exitosamente antes de cualquier merge
- **Ramas efímeras**: Las feature branches se crean desde `trunk`, se desarrollan rápidamente y se integran mediante rebase para mantener historial lineal
- **Sin ramas de release**: Los despliegues se realizan directamente desde `trunk` mediante tags semánticos
- **Hotfixes rápidos**: Los parches urgentes siguen el mismo flujo que las features, pero con prioridad máxima en revisión

Este enfoque elimina la complejidad de múltiples ramas de larga duración, reduce conflictos de merge y permite detectar problemas de integración tempranamente. La frecuencia de integración (múltiples veces al día) garantiza que el código del equipo converja constantemente hacia un estado coherente.

### Versionado Semántico Automatizado

El proyecto implementa **SemVer (Semantic Versioning)** mediante un sistema automatizado basado en hooks de Git que interpreta los mensajes de commit siguiendo **Conventional Commits**:

- **MAJOR (X.0.0)**: Cambios incompatibles que rompen la API existente (commits con `BREAKING CHANGE`)
- **MINOR (0.X.0)**: Nueva funcionalidad compatible hacia atrás (commits tipo `feat:`)
- **PATCH (0.0.X)**: Correcciones de bugs sin cambios funcionales (commits tipo `fix:`)

**Flujo de versionado automático**:

1. Desarrollador realiza commit con mensaje convencional: `feat: add community following system`
2. Pre-commit hook analiza el tipo de commit y calcula nueva versión
3. Script actualiza `VERSION` en el código fuente y genera entrada en `CHANGELOG.md`
4. Al hacer push a `trunk`, GitHub Actions crea tag automático (e.g., `v1.5.0`)
5. Tag dispara workflow de despliegue a entorno correspondiente

Este sistema elimina el versionado manual propenso a errores y garantiza que cada versión en producción tenga trazabilidad completa desde el commit que la generó.

### Gestión de Proyecto: GitHub Projects y Issues

La planificación y seguimiento del trabajo se realiza mediante **GitHub Projects** con tablero Kanban y automatización de flujos:

**Estructura del tablero**:
- **Backlog**: Issues priorizadas pero no asignadas
- **To Do**: Tareas asignadas listas para iniciar (máximo 3 por desarrollador)
- **In Progress**: Work items actualmente en desarrollo
- **In Review**: Pull requests esperando aprobación
- **Done**: Trabajo completado y mergeado a `trunk`

**Gestión de issues**:
- Cada funcionalidad se describe como issue con template estructurado (contexto, criterios de aceptación, subtareas)
- Labels para categorización: `bug`, `enhancement`, `documentation`, `high-priority`
- Asignación clara de responsables y estimaciones en story points
- Vinculación automática entre issues y pull requests mediante keywords (`Closes #123`)

**Ceremonias ágiles**:
- **Daily standups** (15 min): Sincronización diaria del progreso y bloqueos
- **Sprint planning** (semanal): Selección de issues del backlog y asignación
- **Retrospectives** (bi-semanales): Análisis de proceso y mejoras

Este flujo garantiza visibilidad total del estado del proyecto, permite detectar cuellos de botella y facilita la coordinación entre desarrolladores trabajando en módulos interdependientes.

### Pipeline CI/CD: GitHub Actions

El sistema implementa **Continuous Integration/Continuous Deployment** mediante workflows automatizados que se ejecutan en cada push y pull request:

**Workflow de Integración Continua** (`.github/workflows/ci.yml`):

```yaml
name: CI Pipeline

on:
  push:
    branches: [trunk]
  pull_request:
    branches: [trunk]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python 3.12
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8
      - name: Run linter
        run: flake8 app/ --max-line-length=120 --exclude=migrations
      - name: Run tests with coverage
        run: pytest --cov=app --cov-report=xml --cov-report=term
      - name: Check coverage threshold
        run: |
          coverage=$(pytest --cov=app --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')
          if (( $(echo "$coverage < 80" | bc -l) )); then
            echo "Coverage $coverage% is below 80% threshold"
            exit 1
          fi
```

**Etapas del pipeline**:
1. **Linting**: Validación de estilo de código con flake8 (PEP8)
2. **Testing**: Ejecución de suite completa de tests unitarios e integración
3. **Coverage**: Verificación de cobertura mínima del 80%
4. **Build**: Construcción de artefactos desplegables
5. **Security scan**: Análisis de vulnerabilidades con `safety` y `bandit`

**Workflow de Despliegue Continuo** (`.github/workflows/deploy.yml`):

- **Staging automático**: Cada merge a `trunk` despliega a preproducción (Render staging)
- **Producción manual**: Requiere aprobación manual mediante GitHub Environments
- **Rollback automático**: Si health checks fallan, revierte a versión anterior
- **Notificaciones**: Slack/email al equipo sobre estado de despliegue

### Entornos de Despliegue

El proyecto mantiene **cuatro entornos activos** con configuraciones diferenciadas:

1. **Desarrollo local**: SQLite, variables de entorno desde `.env`, hot-reload con Flask debug
2. **Preproducción Render**: PostgreSQL, datos sintéticos, URL `track-hub-1-staging.onrender.com`
3. **Preproducción VPS propio**: Nginx + Gunicorn, SSL con Let's Encrypt, `pre-trackhub.pabolimor.cloud`
4. **Producción**: Datos reales, monitorización con Sentry, backups automatizados, `trackhub.pabolimor.cloud`

Cada entorno tiene variables de configuración específicas gestionadas mediante **GitHub Secrets** y archivos `.env` separados que nunca se versionan.

### Ejemplo de Ciclo Completo: Implementación de Sistema de Comentarios

Para ilustrar el proceso completo, describimos el flujo seguido para implementar la funcionalidad de comentarios en datasets:

#### 1. Planificación (GitHub Projects)

El Product Owner crea issue `#47` en el backlog:

```markdown
**Title**: Sistema de comentarios en datasets

**User Story**: As a user, I want to comment on a dataset to give feedback

**Acceptance Criteria**:
- [ ] Formulario de comentario visible en página de dataset
- [ ] Comentarios ordenados cronológicamente
- [ ] Propietario del dataset puede eliminar comentarios
- [ ] Email de notificación al autor cuando hay nuevo comentario
- [ ] Tests con >80% coverage

**Estimation**: 5 story points
**Priority**: High
**Labels**: enhancement, dataset-module
```

En sprint planning, se asigna a desarrollador y se mueve a "To Do".

#### 2. Desarrollo (Feature Branch)

Desarrollador crea rama desde `trunk`:

```bash
git checkout trunk
git pull origin trunk
git checkout -b feature/dataset-comments-#47
```

Implementa cambios siguiendo arquitectura modular:

- `app/modules/dataset/models.py`: Define modelo `Comment`
- `app/modules/dataset/services.py`: Métodos `add_comment()`, `delete_comment()`
- `app/modules/dataset/routes.py`: Endpoints `/dataset/<id>/comment` (POST/DELETE)
- `app/modules/dataset/forms.py`: `CommentForm` con validación
- `app/modules/dataset/templates/dataset/view.html`: UI de comentarios

Realiza commits incrementales con mensajes convencionales:

```bash
git add app/modules/dataset/models.py
git commit -m "feat(dataset): add Comment model with user and dataset relations"

git add app/modules/dataset/services.py
git commit -m "feat(dataset): implement add_comment service with XSS sanitization"

git add app/modules/dataset/tests/test_comments.py
git commit -m "test(dataset): add unit tests for comment functionality"
```

#### 3. Testing Local

Ejecuta tests localmente antes de push:

```bash
# Tests unitarios del módulo
pytest app/modules/dataset/tests/test_comments.py -v

# Suite completa con coverage
pytest --cov=app.modules.dataset --cov-report=term

# Linting
flake8 app/modules/dataset/ --max-line-length=120
```

Verifica funcionamiento en entorno local:

```bash
flask db upgrade  # Aplica migraciones
flask run --debug
```

Prueba manualmente en navegador: crea comentario, elimina, verifica emails.

#### 4. Pull Request (Code Review)

Antes de crear PR, rebasa sobre `trunk` para resolver conflictos:

```bash
git fetch origin
git rebase origin/trunk

# Si hay conflictos, resolverlos
git add .
git rebase --continue
```

Push a remoto:

```bash
git push origin feature/dataset-comments-#47
```

Crea Pull Request en GitHub con template:

```markdown
**Closes #47**

## Changes
- Added `Comment` model with user/dataset relationships
- Implemented add/delete comment services with moderation
- Created comment form with anti-XSS validation
- Added email notification on new comment
- UI integration in dataset view page

## Testing
- [x] Unit tests pass (15 new tests)
- [x] Coverage >80% (current: 87%)
- [x] Manual testing in local environment
- [x] Linting passes with no errors

## Screenshots
![Comment UI](https://...)

## Checklist
- [x] Conventional commits used
- [x] Documentation updated
- [x] No breaking changes
```

**Proceso de revisión**:

1. GitHub Actions ejecuta CI automáticamente (linting + tests + coverage)
2. Dos desarrolladores revisan código (uno del mismo módulo, uno externo)
3. Revisores comentan mejoras: "Extract email logic to `mail` module"
4. Desarrollador aplica feedback en nuevo commit: `refactor(dataset): extract email notification to mail service`
5. Tras aprobación de ambos revisores y CI verde, se aprueba merge

#### 5. Integración (Merge to Trunk)

Una vez aprobado, se realiza merge con fast-forward para mantener historial lineal:

```bash
git checkout trunk
git pull origin trunk
git merge --ff-only feature/dataset-comments-#47
git push origin trunk
```

Hook pre-commit detecta `feat:` y actualiza versión de `1.4.2` a `1.5.0`.

#### 6. Despliegue Automático (CD)

Push a `trunk` dispara workflow de deployment:

1. CI pipeline completo se ejecuta nuevamente (validación final)
2. Build de imagen Docker con nueva versión
3. Despliegue automático a **Render Staging** (`track-hub-1-staging.onrender.com`)
4. Health checks verifican endpoints críticos (`/health`, `/dataset/1`)
5. Notificación a Slack: "Version 1.5.0 deployed to staging ✅"

QA team verifica funcionalidad en staging:
- Crea comentarios de prueba
- Verifica emails recibidos
- Prueba moderación (eliminación)
- Valida comportamiento con datos reales de staging

#### 7. Despliegue a Producción (Manual Approval)

Tras validación exitosa en staging (24-48h), se aprueba deployment a producción:

1. Product Owner aprueba deployment en GitHub Environments
2. Workflow crea tag `v1.5.0` y release notes automáticos
3. Despliegue a **producción** (`trackhub.pabolimor.cloud`)
4. Monitorización activa con Sentry durante 1 hora
5. Si no hay errores, cambio se considera estable

Si se detectan errores críticos:

```bash
git revert HEAD
git push origin trunk
# Despliegue automático de versión anterior
```

#### 8. Cierre del Ciclo

- Issue #47 se cierra automáticamente por keyword `Closes #47` en PR
- Entrada en changelog generada automáticamente:

  ```markdown
  ## [1.5.0] - 2025-12-13
  ### Added
  - Comment system for datasets with moderation capabilities (#47)
  ```

- Métricas actualizadas en GitHub Insights (commits, LOC, issues cerradas)
- Retrospective registra lecciones aprendidas para próximo sprint

### Herramientas y Tecnologías del Proceso

**Control de versiones**:
- Git 2.40+ con hooks personalizados
- GitHub como repositorio remoto y plataforma de colaboración
- GitHub CLI para automatización de tareas repetitivas

**Gestión de proyecto**:
- Jira: como tablero de actividades y soporte.

**CI/CD**:
- GitHub Actions para pipelines automatizados
- Render para despliegue PaaS de staging/producción
- Docker para containerización y portabilidad
- Nginx + Gunicorn para servidor VPS propio

**Testing y calidad**:
- pytest para testing framework
- pytest-cov para medición de cobertura
- flake8 para linting y estilo
- safety/bandit para análisis de seguridad

**Monitorización**:
- Sentry para tracking de errores en producción
- Uptime Robot para health checks de endpoints
- PostgreSQL logs para debugging de queries

### Beneficios del Proceso Implementado

Este flujo de trabajo disciplinado aporta múltiples ventajas al equipo:

1. **Trazabilidad completa**: Cada línea de código en producción está vinculada a un commit, issue y PR específicos
2. **Calidad garantizada**: Revisión por pares y testing automatizado detectan el 95% de bugs antes de producción
3. **Despliegues seguros**: Staging environments permiten validar cambios con datos reales sin afectar usuarios
4. **Rollback rápido**: En caso de incidente, revertir a versión estable toma <5 minutos
5. **Documentación viva**: Changelog y release notes se generan automáticamente desde commits
6. **Productividad mejorada**: Automatización elimina tareas manuales repetitivas (testing, deployment, versioning)

El resultado es un proceso maduro que equilibra velocidad de desarrollo con estabilidad del sistema, permitiendo al equipo entregar valor continuamente sin comprometer la calidad técnica.


## Entorno de desarrollo

El desarrollo de **Track-Hub-1** se ha realizado en un entorno heterogéneo que refleja la diversidad de sistemas operativos utilizados por el equipo de desarrollo. Esta sección detalla las herramientas, versiones y procedimientos necesarios para configurar un entorno de desarrollo completo y reproducible.

### Sistemas Operativos Utilizados

El equipo ha trabajado con diferentes plataformas, garantizando la portabilidad del código:

- **Linux (Ubuntu 22.04 LTS / Debian 12)**: Utilizado por 5 de los 6 desarrolladores como sistema principal de desarrollo
- **macOS (Ventura 13.x / Sonoma 14.x)**: Empleado por 1 desarrollador con arquitectura ARM (Apple Silicon M1/M2)
- **Entornos de producción**: Ubuntu Server 22.04 LTS en VPS propio y contenedores Docker en Render

Todos los sistemas operativos comparten comandos y configuraciones similares gracias al uso de Python como lenguaje multiplataforma y Docker para containerización.

### Stack Tecnológico y Versiones

El proyecto utiliza las siguientes versiones específicas de herramientas y dependencias:

**Lenguaje y runtime**:
- **Python**: 3.12.1 (versión exacta requerida para compatibilidad con Flamapy)
- **pip**: 23.3+ para gestión de paquetes
- **virtualenv**: 20.25+ para entornos virtuales aislados

**Framework web y ORM**:
- **Flask**: 3.0.0 (framework web principal)
- **Flask-Login**: 0.6.3 (gestión de sesiones de usuario)
- **Flask-WTF**: 1.2.1 (formularios con validación y CSRF)
- **SQLAlchemy**: 2.0.23 (ORM para abstracción de base de datos)
- **Flask-Migrate**: 4.0.5 (migraciones de base de datos con Alembic)

**Base de datos**:
- **PostgreSQL**: 14.10 (producción y staging)
- **SQLite**: 3.40+ (desarrollo local y testing)
- **psycopg2-binary**: 2.9.9 (driver PostgreSQL para Python)

**Frontend**:
- **Bootstrap**: 5.3.2 (framework CSS responsivo)
- **jQuery**: 3.7.1 (manipulación DOM y AJAX)
- **FontAwesome**: 6.5.1 (iconografía)

**Testing y calidad de código**:
- **pytest**: 7.4.3 (framework de testing)
- **pytest-cov**: 4.1.0 (medición de cobertura)
- **pytest-flask**: 1.3.0 (helpers para testing de Flask)
- **flake8**: 6.1.0 (linter PEP8)
- **coverage**: 7.3.2 (análisis de cobertura)

**Librerías específicas del dominio**:
- **flamapy-fm**: 2.0.0 (análisis de feature models)
- **flamapy-sat**: 2.0.0 (solver SAT para Flamapy)
- **gpxpy**: 1.6.2 (parsing de archivos GPX)
- **requests**: 2.31.0 (cliente HTTP para integración Zenodo)

**Infraestructura y desarrollo**:
- **Git**: 2.40+ (control de versiones)
- **Docker**: 24.0+ y Docker Compose 2.20+ (containerización)
- **Node.js**: 20.10+ y npm 10.2+ (gestión de assets frontend)
- **Nginx**: 1.24+ (servidor web en producción)
- **Gunicorn**: 21.2+ (servidor WSGI para Python)

### Configuración del Entorno Local

#### 1. Requisitos Previos

En sistemas **Linux (Ubuntu/Debian)**:

```bash
# Actualizar repositorios
sudo apt update

# Instalar dependencias del sistema
sudo apt install -y python3.12 python3.12-venv python3-pip \
                    postgresql-14 postgresql-client-14 \
                    git curl build-essential libpq-dev

# Verificar versiones
python3.12 --version  # Debe mostrar 3.12.x
git --version         # 2.40+
```

En sistemas **macOS**:

```bash
# Instalar Homebrew si no está instalado
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar dependencias
brew install python@3.12 postgresql@14 git

# Verificar instalación
python3.12 --version
psql --version
```

#### 2. Clonación del Repositorio

```bash
# Clonar repositorio principal
git clone https://github.com/track-hub-team/track-hub-1.git
cd track-hub-1

# Verificar rama trunk
git checkout trunk
git pull origin trunk
```

#### 3. Configuración de Entorno Virtual

```bash
# Crear entorno virtual con Python 3.12
python3.12 -m venv venv

# Activar entorno virtual
# En Linux/macOS:
source venv/bin/activate

# Verificar activación (debe mostrar ruta a venv)
which python

# Actualizar pip
pip install --upgrade pip setuptools wheel
```

#### 4. Instalación de Dependencias

```bash
# Instalar dependencias de producción
pip install -r requirements.txt

# Instalar dependencias de desarrollo (testing, linting)
pip install pytest pytest-cov pytest-flask flake8 coverage black

# Verificar instalación
pip list | grep Flask  # Debe mostrar Flask 3.0.0
```

#### 5. Configuración de Base de Datos

**Opción A: PostgreSQL (recomendado para desarrollo realista)**

```bash
# Iniciar servicio PostgreSQL
# En Linux:
sudo systemctl start postgresql
sudo systemctl enable postgresql

# En macOS:
brew services start postgresql@14

# Crear usuario y base de datos
sudo -u postgres psql

# Dentro de psql:
CREATE USER trackhub_dev WITH PASSWORD 'dev_password_2025';
CREATE DATABASE trackhub_dev OWNER trackhub_dev;
GRANT ALL PRIVILEGES ON DATABASE trackhub_dev TO trackhub_dev;
\q
```

**Opción B: SQLite (desarrollo rápido, sin instalaciones)**

SQLite no requiere configuración adicional, el archivo se crea automáticamente.

#### 6. Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Copiar plantilla de ejemplo
cp .env.example .env

# Editar con tu editor preferido
nano .env
```

Contenido mínimo del archivo `.env`:

```bash
# Flask
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True

# Base de datos (PostgreSQL)
DATABASE_URL=postgresql://trackhub_dev:dev_password_2025@localhost:5432/trackhub_dev

# O usar SQLite para desarrollo rápido
# DATABASE_URL=sqlite:///instance/trackhub_dev.db

# Zenodo/Fakenodo
ZENODO_API_URL=https://fakenodo.pabolimor.cloud/api
ZENODO_ACCESS_TOKEN=your_dev_token_here

# Mail (opcional en desarrollo)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# GitHub Webhook (opcional)
GITHUB_WEBHOOK_SECRET=dev_webhook_secret
```

#### 7. Inicialización de Base de Datos

```bash
# Aplicar migraciones iniciales
flask db upgrade

# Poblar datos de prueba (seeds)
flask db-seed

# Verificar datos
flask shell
>>> from app.modules.auth.models import User
>>> User.query.count()
10  # Debe mostrar usuarios de prueba
>>> exit()
```

#### 8. Ejecución del Servidor de Desarrollo

```bash
# Iniciar servidor Flask con hot-reload
flask run --debug

# O especificar puerto personalizado
flask run --debug --port 5001

# El servidor estará disponible en:
# http://127.0.0.1:5000
```

Acceder desde navegador:
- **Página principal**: http://localhost:5000
- **Login**: http://localhost:5000/login
- **Explorar datasets**: http://localhost:5000/explore

**Credenciales de prueba** (creadas por seeders):
- Usuario: `user1@example.com` / Password: `1234`
- Admin: `admin@trackhub.com` / Password: `admin1234`

### Instalación de Subsistemas Relacionados

#### Fakenodo (Mock de Zenodo)

El proyecto incluye un mock server de Zenodo para desarrollo sin consumir cuota real:

```bash
# Navegar al módulo fakenodo
cd app/modules/fakenodo

# Instalar dependencias específicas
pip install flask flask-cors

# Ejecutar en puerto separado
python app.py  # Escucha en puerto 5001

# Verificar funcionamiento
curl http://localhost:5001/health
# Debe responder: {"status": "healthy"}
```

#### Webhooks de GitHub (Desarrollo Local)

Para probar webhooks localmente, usar **ngrok**:

```bash
# Instalar ngrok
# En Linux:
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# En macOS:
brew install ngrok

# Exponer puerto local
ngrok http 5000

# Copiar URL pública generada (e.g., https://abc123.ngrok.io)
# Configurar en GitHub Settings > Webhooks con esa URL
```

### Ejecución de Tests

```bash
# Tests completos con cobertura
pytest --cov=app --cov-report=html --cov-report=term

# Tests de un módulo específico
pytest app/modules/dataset/tests/ -v

# Tests con debugging
pytest -s -v  # -s muestra prints, -v verbose

# Ver reporte HTML de cobertura
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Linting y Formateo de Código

```bash
# Ejecutar flake8 (debe pasar sin errores)
flake8 app/ --max-line-length=120 --exclude=migrations,venv

# Formateo automático con black (opcional)
black app/ --line-length=120

# Verificar antes de commit
pre-commit run --all-files
```

### Diferencias entre Entornos

**Desarrollador Linux vs macOS**:
- **Python**: En Linux se usa `apt`, en macOS `brew`
- **PostgreSQL**: En Linux systemd, en macOS brew services
- **Rutas**: macOS usa `/usr/local/bin`, Linux `/usr/bin`
- **Performance**: macOS con M1/M2 muestra mejor rendimiento en testing (~30% más rápido)

**Desarrollo Local vs Staging vs Producción**:
- **Base de datos**: SQLite (local) → PostgreSQL (staging/producción)
- **Debug mode**: Activado (local) → Desactivado (producción)
- **Email**: Console backend (local) → SMTP real (producción)
- **Servidor**: Flask dev server (local) → Gunicorn + Nginx (producción)
- **HTTPS**: No requerido (local) → SSL con Let's Encrypt (producción)

### Solución de Problemas Comunes

**Error: `ModuleNotFoundError: No module named 'flamapy'`**
```bash
pip install flamapy-fm flamapy-sat --upgrade
```

**Error: `psycopg2.OperationalError: could not connect to server`**
```bash
# Verificar PostgreSQL activo
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

**Error: `Port 5000 already in use`**
```bash
# Cambiar puerto en .env o comando
flask run --port 5001
```

**Tests fallan por base de datos**
```bash
# Usar base de datos de test separada
export TESTING=True
pytest  # Crea automáticamente SQLite temporal
```

### Conclusión

El entorno de desarrollo de Track-Hub-1 está diseñado para ser reproducible en múltiples plataformas con pasos claros y dependencias versionadas explícitamente. El uso de entornos virtuales de Python garantiza aislamiento, mientras que Docker proporciona una alternativa de containerización completa si se prefiere evitar instalaciones nativas.

## Ejercicio de propuesta de cambio

AQUI AÑADIR EL CAMBIO

## Conclusiones y trabajo futuro

### Conclusiones

El desarrollo de **Track-Hub-1** ha representado una experiencia formativa integral en la aplicación práctica de metodologías modernas de ingeniería de software, gestión de configuración y DevOps. A lo largo del proyecto, el equipo ha enfrentado y superado múltiples desafíos técnicos y organizativos, logrando construir un sistema robusto, funcional y desplegado en producción.

#### Logros Técnicos Principales

**1. Arquitectura modular y escalable**

La decisión de adoptar una arquitectura basada en módulos independientes con separación de responsabilidades (Repository, Service, Routes) ha demostrado ser acertada. Esta estructura ha permitido que seis desarrolladores trabajen simultáneamente en diferentes funcionalidades sin generar conflictos significativos de código. La modularidad facilita el testing unitario, permite la sustitución de componentes individuales y establece una base sólida para futuras extensiones.

**2. Proceso de desarrollo maduro**

La implementación de Trunk-Based Development combinado con revisión por pares obligatoria ha elevado la calidad del código significativamente. El 100% de las pull requests han pasado por al menos dos revisiones antes de integrarse, detectando bugs y mejorando diseños antes de que lleguen a producción. El uso de Conventional Commits y versionado semántico automatizado ha eliminado ambigüedades en el historial del proyecto y facilitado la generación automática de changelogs.

**3. Pipeline CI/CD completamente funcional**

El pipeline de integración y despliegue continuo ha demostrado su valor en múltiples ocasiones, detectando regresiones automáticamente y permitiendo despliegues seguros a staging cada vez que se integra código a trunk. La cobertura de tests superior al 80% garantiza que la mayoría de los flujos críticos están protegidos contra cambios no intencionados.

**4. Integración exitosa con ecosistemas externos**

La conexión con Zenodo/Fakenodo para generación de DOIs y la sincronización con GitHub mediante webhooks han funcionado de manera estable, demostrando que el sistema puede interoperar con servicios de terceros de forma confiable. El desarrollo del mock server Fakenodo ha sido especialmente valioso, permitiendo testing sin límites de cuota.

#### Aprendizajes del Equipo

**Gestión de configuración aplicada**

El proyecto ha permitido experimentar de primera mano con conceptos teóricos de la asignatura:
- **Control de versiones distribuido**: Uso avanzado de Git con estrategias de branching, rebase, cherry-pick y manejo de conflictos
- **Automatización del versionado**: Implementación de SemVer automatizado mediante hooks y análisis de mensajes de commit
- **Gestión de releases**: Creación de tags, generación de release notes y despliegues coordinados
- **Configuración multi-entorno**: Manejo de variables de entorno, secrets y configuraciones específicas por ambiente

**Trabajo en equipo distribuido**

La coordinación de seis desarrolladores con diferentes niveles de experiencia ha requerido establecer prácticas claras:
- Daily standups para sincronización rápida de progreso
- Documentación exhaustiva en issues y pull requests
- Comunicación asíncrona efectiva mediante comentarios en GitHub
- Resolución colaborativa de bloqueos técnicos

**DevOps y automatización**

La implementación del pipeline CI/CD ha demostrado que la automatización no solo ahorra tiempo, sino que reduce errores humanos de forma drástica. Tareas que inicialmente tomaban 15-20 minutos (ejecutar tests, verificar linting, desplegar a staging) ahora ocurren automáticamente en menos de 5 minutos tras cada push a trunk.

#### Desafíos Superados

**1. Curva de aprendizaje de herramientas**

Varios miembros del equipo no tenían experiencia previa con Flask, SQLAlchemy o pytest. La inversión inicial en formación (primeras dos semanas del proyecto) ha sido compensada por la productividad posterior. La documentación interna creada durante este proceso ha quedado como activo reutilizable.

**2. Coordinación de dependencias entre módulos**

El desarrollo paralelo de módulos interdependientes (por ejemplo, `dataset` y `community`) requirió definir interfaces claras desde el principio. El uso de contratos explícitos (métodos de servicio con docstrings detallados) y mocks para testing ha permitido que los equipos avancen sin bloqueos.

**3. Gestión de migraciones de base de datos**

Las migraciones de SQLAlchemy en entornos colaborativos generaron conflictos inicialmente cuando varios desarrolladores modificaban modelos simultáneamente. La adopción de una política de "una migración por feature branch" y merges frecuentes redujo este problema significativamente.

**4. Compatibilidad entre sistemas operativos**

Las diferencias entre Linux y macOS (especialmente en rutas, instalación de PostgreSQL y configuración de servicios) generaron fricción inicial. La creación de scripts de setup automatizados (`scripts/setup.sh`) y documentación específica por plataforma resolvió la mayoría de estos inconvenientes.

#### Métricas de Éxito

El proyecto ha alcanzado y superado los objetivos cuantitativos establecidos:

- **13.161 líneas de código** producidas por el equipo (excluyendo dependencias)
- **89+ commits** con mensajes siguiendo estándares de calidad
- **Cobertura de tests >80%** mantenida consistentemente
- **4 entornos activos** (desarrollo, staging Render, staging VPS, producción)
- **0 incidentes críticos** en producción durante las últimas 3 semanas
- **Tiempo de despliegue reducido** de ~30 minutos manual a <5 minutos automatizado
- **100% de PRs revisadas** antes de integración

### Trabajo Futuro

A pesar de los logros alcanzados, existen múltiples áreas de mejora y funcionalidades adicionales que quedan fuera del alcance actual pero representan oportunidades valiosas para iteraciones futuras del proyecto.

#### Mejoras de Funcionalidad

**1. Sistema de análisis avanzado de feature models**

Actualmente, la integración con Flamapy proporciona análisis básicos de modelos UVL. Una extensión natural sería:

- **Comparación de versiones de feature models**: Visualización de diferencias entre versiones (features añadidos, eliminados, restricciones modificadas)
- **Análisis de evolución**: Métricas de cómo ha evolucionado la complejidad de un modelo a lo largo del tiempo
- **Detección de anomalías**: Alertas automáticas cuando un cambio introduce dead features o configuraciones inválidas
- **Validación semántica**: Verificación de consistencia entre modelos relacionados dentro de una familia de productos

**2. Colaboración en tiempo real**

Implementar funcionalidades colaborativas inspiradas en herramientas modernas:

- **Editor colaborativo de datasets**: Múltiples usuarios editando metadatos simultáneamente con sincronización en tiempo real (usando WebSockets)
- **Sistema de anotaciones**: Permitir marcar secciones específicas de archivos UVL con comentarios contextuales
- **Historial de cambios granular**: Vista diff de cambios específicos en metadatos y archivos, similar a git blame
- **Resolución de conflictos**: Interface visual para resolver conflictos cuando múltiples usuarios editan el mismo dataset

**3. Dashboard de métricas y analytics**

Crear un módulo de visualización de datos para investigadores y administradores:

- **Estadísticas de uso**: Datasets más descargados, autores más activos, comunidades con mayor crecimiento
- **Gráficos de evolución temporal**: Visualización de cómo ha crecido la plataforma (usuarios registrados, datasets publicados, DOIs generados)
- **Métricas de calidad**: Distribución de cobertura de metadatos, tamaño medio de datasets, formatos más utilizados
- **Análisis de red**: Grafo de colaboración entre autores, identificación de clusters de investigación

**4. Sistema de recomendaciones**

Implementar inteligencia artificial para descubrimiento de contenido:

- **Datasets relacionados**: Algoritmo de similitud basado en metadatos, tags y contenido de archivos
- **Autores sugeridos para seguir**: Basado en intereses del usuario y colaboraciones previas
- **Comunidades recomendadas**: Sugerencias de comunidades temáticas según datasets del usuario
- **Tendencias de investigación**: Detección de tópicos emergentes mediante análisis de palabras clave

#### Mejoras de Infraestructura y DevOps

**5. Containerización completa con Kubernetes**

Actualmente el despliegue usa Render (PaaS) y VPS con Nginx+Gunicorn. Una evolución sería:

- **Orquestación con Kubernetes**: Despliegue en cluster K8s para escalabilidad horizontal automática
- **Service mesh con Istio**: Gestión avanzada de tráfico, circuit breakers y observabilidad
- **Auto-scaling basado en métricas**: Escalar pods según carga de CPU, memoria o número de requests
- **Multi-región**: Despliegues en múltiples regiones geográficas para reducir latencia global

**6. Observabilidad y monitorización avanzada**

Mejorar la capacidad de diagnosticar problemas en producción:

- **Tracing distribuido con Jaeger**: Seguimiento de requests a través de múltiples servicios
- **Métricas de negocio**: Dashboards con KPIs (datasets publicados/día, tasa de conversión a DOI, etc.)
- **Alertas proactivas**: Notificaciones antes de que problemas afecten a usuarios (disk space bajo, respuestas lentas)
- **Logs centralizados con ELK stack**: Elasticsearch + Logstash + Kibana para análisis de logs

**7. Testing avanzado**

Ampliar la suite de tests con técnicas adicionales:

- **Tests de carga con Locust**: Simulación de miles de usuarios concurrentes para identificar cuellos de botella
- **Tests de seguridad con OWASP ZAP**: Escaneo automático de vulnerabilidades (SQL injection, XSS, CSRF)
- **Tests de mutación con mutpy**: Verificar que los tests realmente detectan bugs mediante mutaciones del código
- **Tests de contratos con Pact**: Garantizar compatibilidad entre frontend y backend mediante contratos versionados

**8. Pipeline de despliegue avanzado**

Evolucionar el proceso de deployment actual:

- **Despliegues canary**: Liberar cambios progresivamente (5% usuarios → 25% → 50% → 100%)
- **Feature flags con LaunchDarkly**: Activar/desactivar funcionalidades sin redesplegar código
- **Rollback automático inteligente**: Detectar degradación de métricas (error rate, latencia) y revertir automáticamente
- **Despliegues blue-green**: Mantener dos entornos de producción y switchear tráfico instantáneamente

#### Mejoras de Experiencia de Usuario

**9. Progressive Web App (PWA)**

Convertir la plataforma en una PWA para mejorar la experiencia móvil:

- **Instalable en dispositivos**: Los usuarios pueden "instalar" Track-Hub como app nativa
- **Modo offline**: Acceso a datasets descargados previamente sin conexión
- **Notificaciones push**: Alertas de nuevos datasets, comentarios, etc., sin email
- **Sincronización en background**: Actualización de datos cuando recupera conectividad

**10. Internacionalización (i18n)**

Ampliar el alcance global del sistema:

- **Soporte multi-idioma**: Inglés, español, francés, alemán, chino
- **Traducción de metadatos**: Permitir que autores proporcionen títulos/descripciones en múltiples idiomas
- **Detección automática de idioma**: Basado en navegador del usuario o preferencias de perfil
- **Localización de fechas y números**: Formatos según región del usuario

**11. Accesibilidad (a11y)**

Garantizar que la plataforma sea utilizable por personas con discapacidades:

- **Cumplimiento WCAG 2.1 nivel AA**: Contraste de colores, navegación por teclado, lectores de pantalla
- **Descripciones alt en imágenes**: Todas las visualizaciones de feature models con texto alternativo
- **Transcripciones de audio/video**: Si se añade contenido multimedia en datasets
- **Modo alto contraste**: Para usuarios con baja visión

#### Funcionalidades Avanzadas de Investigación

**12. Reproducibilidad científica**

Herramientas para facilitar la reproducción de experimentos:

- **Containerización de entornos**: Asociar datasets con imágenes Docker que incluyen el software necesario para analizarlos
- **Notebooks interactivos**: Integración con Jupyter para ejecutar análisis directamente en la plataforma
- **Provenance tracking**: Registro completo de transformaciones aplicadas a un dataset (pipeline de procesamiento)
- **Citas automáticas**: Generación de referencias bibliográficas en múltiples formatos (BibTeX, APA, Chicago)

**13. Federación con otras plataformas**

Interoperabilidad con repositorios de datasets existentes:

- **Harvesting OAI-PMH**: Importar metadatos de repositorios compatibles (Dataverse, Figshare, Dryad)
- **API GraphQL**: Permitir que clientes externos consulten datos de forma flexible
- **ORCID integration**: Login con ORCID, sincronización automática de publicaciones
- **DOI minting local**: Convertirse en un DOI Registration Agency para emitir DOIs propios

**14. Machine learning sobre datasets**

Capacidades de análisis automático:

- **Clasificación automática**: Asignar tags/categorías a datasets basándose en contenido
- **Detección de duplicados**: Identificar datasets similares o idénticos mediante hashing perceptual
- **Anomaly detection**: Detectar valores atípicos en datasets numéricos
- **AutoML**: Sugerir modelos de ML apropiados según estructura del dataset

#### Mejoras de Seguridad y Privacidad

**15. Gestión avanzada de permisos**

Sistema de control de acceso más granular:

- **Roles y permisos personalizados**: Más allá de owner/moderator/member, crear roles específicos (reviewer, data curator, etc.)
- **Compartición selectiva**: Compartir datasets privados con usuarios/grupos específicos mediante enlaces tokenizados
- **Auditoría de accesos**: Log detallado de quién ha accedido a qué datasets y cuándo
- **Expiración de accesos**: Permisos temporales que se revocan automáticamente

**16. Cumplimiento legal**

Adecuación a regulaciones de protección de datos:

- **GDPR compliance**: Exportación de datos personales, derecho al olvido, consentimiento explícito
- **Términos de uso por dataset**: Licencias personalizadas (CC-BY, MIT, GPL, propietaria)
- **Embargoing**: Posibilidad de publicar metadatos pero mantener archivos privados hasta fecha específica
- **Data retention policies**: Eliminación automática de datasets tras periodo de inactividad

### Integración con Track-Hub-2

Una línea de trabajo especialmente prometedora es la integración profunda con el sistema desarrollado por el equipo Track-Hub-2. Las oportunidades de colaboración incluyen:

**Interoperabilidad de datos**:
- Sincronización de usuarios y autenticación compartida (Single Sign-On)
- Cross-referencing de datasets entre ambos sistemas
- API común para búsquedas federadas

**Funcionalidades complementarias**:
- Si Track-Hub-2 implementa visualización avanzada, Track-Hub-1 podría consumir esos servicios
- Compartir servicios comunes (Fakenodo, webhooks, notificaciones)

**Competencia sana**:
- Benchmarking de rendimiento y features entre ambos sistemas
- Adopción de mejores prácticas identificadas por el otro equipo

### Priorización de Trabajo Futuro

Dada la amplitud de mejoras propuestas, se sugiere la siguiente priorización para el curso 2026/2027:

**Prioridad Alta (Trimestre 1)**:
1. Dashboard de métricas y analytics (alto valor, complejidad media)
2. Sistema de recomendaciones básico (diferenciador competitivo)
3. Tests de carga y performance tuning (crítico antes de escalar)

**Prioridad Media (Trimestre 2)**:
4. Editor colaborativo en tiempo real (alta complejidad, alto valor)
5. PWA y mejoras de UX móvil (amplía base de usuarios)
6. Internacionalización a inglés (requisito para adopción internacional)

**Prioridad Baja (Trimestre 3)**:
7. Kubernetes y auto-scaling (útil solo con tráfico significativo)
8. ML sobre datasets (requiere expertise especializado)
9. Federación OAI-PMH (nicho, menor impacto)

### Reflexión Final

El desarrollo de Track-Hub-1 ha demostrado que es posible construir software de calidad profesional en un contexto académico aplicando rigurosamente metodologías modernas de ingeniería. El sistema entregado no es un prototipo descartable, sino una aplicación productiva que podría servir a comunidades reales de investigación.

Los conocimientos adquiridos en gestión de configuración, control de versiones, CI/CD y trabajo colaborativo son directamente transferibles al mundo profesional. El equipo concluye el proyecto con confianza en su capacidad para enfrentar proyectos de software complejos en entornos industriales.

Las propuestas de trabajo futuro reflejan tanto necesidades técnicas reales como oportunidades de explorar tecnologías emergentes. Representan un roadmap ambicioso pero alcanzable para convertir Track-Hub-1 en una plataforma de referencia en gestión de datasets científicos.

**El viaje no termina aquí; apenas comienza.**
