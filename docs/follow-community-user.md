# Seguimiento de Usuarios (Follow / Unfollow Users)

## Descripción General

TrackHub permite a los usuarios **seguir a otros usuarios (autores de datasets)** para mantenerse informados sobre su actividad dentro de la plataforma.

Cuando un usuario sigue a otro, el sistema registra esta relación y permite:
- Mostrar el estado de seguimiento en la vista de datasets
- Listar los usuarios seguidos en el perfil
- Dejar de seguir usuarios desde distintas vistas (dataset y perfil)

Esta funcionalidad fomenta el descubrimiento de autores relevantes y facilita el seguimiento de sus contribuciones sin necesidad de búsquedas manuales.

---

## Ubicación

- **Modelos de datos:**
  - `models.py` → `Follower`

- **Repositorio de acceso a datos:**
  - `repositories.py` → `FollowerRepository`

- **Servicio principal:**
  - `services.py` → `CommunityService`

- **Rutas HTTP:**
  - `routes.py` → Rutas `/community/user/<id>/follow` y `/community/user/<id>/unfollow`

- **Integración en vistas:**
  - `dataset/view_dataset.html`
  - `profile/summary.html`

---

## Arquitectura

### Modelo Follower

Representa la relación de seguimiento entre usuarios (User → User):

```python
def __repr__(self):
    return f"Follower<follower_id={self.follower_id}, followed_id={self.followed_id}>"

```
Cada registro indica que un usuario (`follower_id`) sigue a otro (`followed_id`).

Restricciones:
- Un usuario solo puede seguir a otro una vez
- No se permite seguirse a uno mismo


### FollowerRepository

Repositorio encargado del acceso a la base de datos para el seguimiento de usuarios.

Funciones principales:

- `follow(follower_id, followed_id)`
- `unfollow(follower_id, followed_id)`
- `is_following(follower_id, followed_id)`
- `get_followed_users(user_id)`

Este repositorio encapsula toda la lógica de persistencia y consulta relacionada con el seguimiento.

---

### CommunityService

El servicio de comunidades centraliza también la lógica de seguimiento de usuarios, ya que fue diseñado conjuntamente con el seguimiento de comunidades.

Funciones principales utilizadas:

- `follow_user(follower_id, followed_id)`
- `unfollow_user(follower_id, followed_id)`
- `is_following_user(follower_id, followed_id)`
- `get_followed_users(user_id)`

Este servicio valida reglas de negocio como:
- Evitar que un usuario se siga a sí mismo
- Evitar duplicados
- Gestionar errores de consistencia

---

## Funcionalidad Principal

### Seguir Usuario

Permite a un usuario autenticado comenzar a seguir a otro usuario.

Ruta utilizada:

`def follow_user(followed_id):`

Flujo:
1. El usuario pulsa el botón “Follow” en la vista de un dataset
2. Se envía una petición POST a la ruta correspondiente
3. `CommunityService.follow_user` valida y crea la relación
4. Se devuelve el nuevo estado de seguimiento
5. La interfaz se actualiza dinámicamente mediante JavaScript

---

### Dejar de Seguir Usuario

Permite eliminar una relación de seguimiento existente.

Ruta utilizada:

`def unfollow_user(followed_id):`

Flujo:
1. El usuario pulsa el botón “Unfollow”
2. Se elimina la relación en base de datos
3. Se devuelve el estado actualizado
4. La interfaz refleja inmediatamente el cambio

---

### Comprobación de Seguimiento

Para mostrar correctamente el estado del botón en la vista de dataset, se utiliza:

`def is_following_user(follower_id, followed_id):`

Esta función se evalúa al cargar la vista para decidir si mostrar “Follow” o “Unfollow”.

---

## Integración en Dataset

En la vista de un dataset:
- Se muestra un botón de seguimiento junto al autor
- El botón cambia dinámicamente según el estado actual
- La acción se realiza sin recargar la página (AJAX)

Esto permite seguir autores directamente desde sus publicaciones.

---

## Integración en el Perfil

En el perfil del usuario:
- Se muestra un listado de usuarios seguidos
- Cada elemento incluye información básica del usuario
- Se permite dejar de seguir directamente desde el listado

El listado se genera dinámicamente a partir de:

`def get_followed_users(user_id):`

---

## Manejo de Errores

- No se permite seguirse a uno mismo
- No se crean relaciones duplicadas
- Si ocurre un error en la base de datos, se devuelve un mensaje controlado
- Las acciones AJAX devuelven siempre un estado de éxito o error

---

## Resumen del Flujo

```text
Usuario pulsa “Follow” en dataset
↓
Ruta /community/user/<id>/follow
↓
CommunityService.follow_user
↓
FollowerRepository.follow
↓
Se crea la relación de seguimiento
↓
La interfaz se actualiza dinámicamente
```

## Limitaciones

- Actualmente no se envían notificaciones por correo al usuario seguido
- El seguimiento es unidireccional (no implica reciprocidad)
- No existe aún una vista pública del perfil del usuario seguido

---

Esta funcionalidad permite a los usuarios construir una red de autores de interés, facilitando el seguimiento de nuevas publicaciones y mejorando la experiencia de descubrimiento dentro de TrackHub.
