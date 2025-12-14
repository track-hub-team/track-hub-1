# Notificación por Correo: Dataset Aceptado en Comunidad

## Descripción General

El sistema de notificaciones por correo electrónico de Track Hub envía automáticamente un email al usuario cuando uno de sus datasets ha sido aceptado en una comunidad.
Esta funcionalidad mejora la experiencia del usuario, informando de manera inmediata sobre la aprobación y fomentando la participación activa en las comunidades.

---

## Ubicación

- **Servicio principal:**
  - `services.py` → `MailService.send_dataset_approved_notification`

- **Lógica de aprobación:**
  - `services.py` → `CommunityService.approve_request`

- **Configuración de correo:**
  - `__init__.py` (Flask-Mail SendGrid)

- **Tests unitarios:**
  - `test_unit.py`


## Arquitectura

### MailService

Clase encargada de la gestión y envío de correos electrónicos:

```python
class MailService:
    @staticmethod
    def send_dataset_approved_notification(
        requester_email,
        requester_name,
        dataset_name,
        community_name
    ):
        # Genera y envía el correo de notificación
```

### Flujo de aprobación

1) Un curador aprueba la solicitud de inclusión de un dataset en una comunidad
2) `CommunityService.approve_request` llama a `MailService.send_dataset_approved_notification`
3) Se genera y envía el correo al usuario solicitante

## Funcionalidad principal

Envío de Notificación de Aprobación

```python
def send_dataset_approved_notification(requester_email, requester_name, dataset_name, community_name):
    subject = f"Dataset aprobado en {community_name}"
    # Cuerpo HTML y texto plano personalizados
    return MailService.send_email(
        subject=subject,
        recipients=[requester_email],
        html_body=html_body,
        text_body=text_body
    )
```

- **Asunto:** `Dataset aprobado en <nombre_comunidad>`

- **Destinatario:** Email del usuario solicitante

- **Contenido:** Mensaje personalizado con el nombre del usuario, dataset y comunidad

#### Ejemplo de email HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { background-color: #f9f9f9; padding: 30px; }
        .highlight { color: #4CAF50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>¡Enhorabuena!</h1>
    </div>
    <div class="content">
        <p>Hola <strong>Pablo</strong>,</p>
        <p>
            Tu dataset <span class="highlight">Rutas de senderismo</span> ha sido <strong>aceptado</strong>
            en la comunidad <span class="highlight">Montañismo</span>.
        </p>
        <p>¡Gracias por tu participación!</p>
    </div>
</body>
</html>
```

## Configuración

- **Servidor SMTP:** Se utiliza SendGrid (configurado en variables de entorno)
- **Variables relevantes:**
  - `MAIL_SERVER`
  - `MAIL_PORT`
  - `MAIL_USE_TTL`
  - `MAIL_USE_SSL`
  - `MAIL_USERNAME`
  - `MAIL_PASSWORD`
  - `MAIL_DEFAULT_SENDER`

## Tests

- **Cobertura:** `test_send_dataset_approved_notification_format`en `test_unit.py` verifica:
    - Que el email se envía correctamente
    - QUe el asunto y destinatario son correctos

```python
def test_send_dataset_approved_notification_format(self, mock_send):
    success, error = MailService.send_dataset_approved_notification(
        requester_email="user@test.com",
        requester_name="Test User",
        dataset_name="Test Dataset",
        community_name="Test Community",
    )
    assert success is True
    # Verifica asunto y destinatario
```

## Manejo de errores

- Si ocurre un error al enviar el correo, se registra en logs y se devuelve un mensaje de error
- El flujo de aprobación continúa aunque falle el envío del email, pero se deja constancia en los logs

## Resumen del flujo

```
Curador aprueba solicitud
    ↓
CommunityService.approve_request()
    ↓
MailService.send_dataset_approved_notification()
    ↓
Usuario recibe email de aprobación
```

## Limitaciones

- El email solo se envía al usuario solicitante, no a tros miembros de la comunidad
- No se envía notificación en caso de rechazo (solo en caso de aprobación)

---

Esta funcionalidad garantiza que los usuarios estén informados en tiempo real sobre la aceptación de sus datasets en comunidades, reforzando la transparencia y la motivación para contribuir.

## Notificación por Correo: Nuevo Dataset en Comunidades Seguidas

## Descripción General

TrackHub envía automáticamente una notificación por correo electrónico a los usuarios que **siguen una comunidad** cuando un nuevo dataset es añadido a dicha comunidad.

Esta funcionalidad permite a los miembros estar informados en tiempo real de las nuevas contribuciones dentro de las comunidades que siguen, fomentando la participación y el descubrimiento de nuevos datasets relevantes.

---

## Ubicación

- **Servicio de correo:**
  - `services.py` → `MailService.send_new_dataset_in_community_notification`

- **Lógica de disparo del evento:**
  - `services.py` → `CommunityService.approve_request`

- **Repositorios implicados:**
  - `repositories.py` → `CommunityFollowerRepository.get_followers_users`

- **Configuración de correo:**
  - `__init__.py` (Flask-Mail + SendGrid)

- **Tests unitarios**
  - `test_unit.py` (MailService)

---

## Arquitectura

### MailService

El envío del correo a los seguidores de una comunidad se centraliza en el servicio de correo mediante el siguiente método:

```python
class MailService:
    @staticmethod
    def send_new_dataset_in_community_notification(
        recipients,
        community_name,
        dataset_name
    ):
        """
        Envía un correo a los usuarios que siguen una comunidad cuando
        se añade un nuevo dataset.
        """
        ...
```
Este método se encarga de:
- Construir el asunto del correo
- Generar el contenido HTML y texto plano
- Delegar el envío a MailService.send_email

### Flujo de aprobación del dataset

1. Un usuario propone un dataset a una comunidad mediante una solicitud.
2. Un curador de la comunidad revisa la solicitud y la aprueba.
3. El sistema añade el dataset de forma oficial a la comunidad.
4. Se obtienen los usuarios que siguen dicha comunidad.
5. Se envía una notificación por correo electrónico a todos los seguidores.

Flujo simplificado:

```text
Curador aprueba solicitud
    ↓
CommunityService.approve_request()
    ↓
Añadir dataset a la comunidad
    ↓
Obtener seguidores de la comunidad
    ↓
MailService.send_new_dataset_in_community_notification()
    ↓
Seguidores reciben email
```

## Funcionalidad principal

### Envío de notificación a seguidores de la comunidad

Cuando un dataset es aprobado e incorporado a una comunidad, el sistema envía una notificación por correo electrónico a todos los usuarios que siguen dicha comunidad.

La funcionalidad se implementa en el servicio de correo mediante el siguiente método:

```python
def send_new_dataset_in_community_notification(
    recipients,
    community_name,
    dataset_name
):
    subject = f"Nuevo dataset en {community_name}"

    return MailService.send_email(
        subject=subject,
        recipients=recipients,
        html_body=html_body,
        text_body=text_body,
    )
```
#### Detalles del correo

- **Asunto:**
  `Nuevo dataset en <nombre_comunidad>`

- **Destinatarios:**
  Usuarios que siguen la comunidad (campo **To**)

- **Contenido del mensaje:**
  - Nombre de la comunidad en la que se ha publicado el dataset
  - Nombre del dataset añadido
  - Mensaje informativo y neutral

El correo se envía en formato HTML e incluye una versión alternativa en texto plano para garantizar la compatibilidad con distintos clientes de correo.

---

#### Ejemplo de email HTML

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Nuevo dataset publicado</h1>
    <p>
        Se ha añadido un nuevo dataset a la comunidad
        <strong>Software Engineering Research</strong>.
    </p>
    <p>
        Dataset: <strong>Sample dataset 2</strong>
    </p>
    <p>
        Saludos,<br>
        El equipo de TrackHub
    </p>
</body>
</html>

## Obtención de destinatarios

Los destinatarios del correo se obtienen a partir de los usuarios que siguen la comunidad en la que se ha aprobado el nuevo dataset.

La obtención de seguidores se realiza a través del repositorio de seguimiento de comunidades:

```python
followers = self.follower_repository.get_followers_users(community_id)
```

A partir de esta lista de usuarios se construye el listado final de direcciones de correo electrónico:

```python
recipients = sorted({u.email for u in followers if u.email})
```

### Características del proceso

- Solo se incluyen usuarios que disponen de una dirección de correo válida.
- Se eliminan direcciones de correo duplicadas.
- Si no existen seguidores, no se envía ningún correo.
- La obtención de destinatarios no bloquea el flujo principal de aprobación del dataset.

## Manejo de errores

Si ocurre un error durante el envío del correo electrónico, el sistema maneja la excepción de forma controlada.

- El error se registra en los logs del sistema para su posterior análisis.
- El dataset **permanece aprobado** aunque falle el envío del correo.
- El fallo en la notificación **no afecta a la consistencia del sistema** ni al flujo principal.

Ejemplo de manejo de errores:

```python
if not success:
    logger.warning(
        "Failed to send new-dataset email to community followers"
    )
```

### Resumen del flujo

```text
Dataset aprobado en comunidad
        ↓
Obtener seguidores de la comunidad
        ↓
Enviar correo de notificación
        ↓
Seguidores informados
```

## Notificación por Correo: Nuevo Dataset de Usuarios Seguidos

## Descripción General

TrackHub envía automáticamente una notificación por correo electrónico a los usuarios que **siguen a otro usuario** cuando este publica un nuevo dataset en la plataforma.

Esta funcionalidad permite a los usuarios mantenerse informados de las nuevas contribuciones realizadas por los autores que siguen, favoreciendo el descubrimiento de datasets relevantes y la interacción dentro de la plataforma.

La lógica de seguimiento entre usuarios ya se encuentra implementada y documentada en otro apartado, por lo que esta sección se centra exclusivamente en el envío de notificaciones por correo.

---

## Ubicación

- Servicio de correo:
  - `services.py` → `MailService.send_new_dataset_by_followed_user_notification`

- Lógica de disparo del evento:
  - `dataset_service.py` → `DataSetService.create_from_form`

- Repositorio implicado:
  - `repositories.py` → `FollowerRepository.get_followers_users`

- Configuración de correo:
  - `__init__.py` (Flask-Mail + SendGrid)

---

## Arquitectura

El envío de notificaciones a seguidores de un usuario se realiza de forma automática tras la creación correcta de un dataset.

El servicio DataSetService, concretamente en la función create_from_form, detecta el evento de publicación y se encarga de coordinar el proceso de notificación.

La responsabilidad de construir y enviar el correo se delega al servicio MailService, mediante la función `send_new_dataset_by_followed_user_notification`, manteniendo así una separación clara entre la lógica de negocio y el envío de notificaciones.

---

## Flujo de publicación del dataset

1. Un usuario crea un nuevo dataset mediante el formulario de creación.
2. El sistema valida los datos y persiste el dataset y su metadata.
3. Al finalizar la función `DataSetService.create_from_form`, se obtienen los seguidores del autor utilizando `FollowerRepository.get_followers_users`.
4. Se construye el nombre del autor y el título del dataset recién creado.
5. Se invoca la función `MailService.send_new_dataset_by_followed_user_notification` para enviar la notificación.
6. Los usuarios seguidores reciben el correo informativo.

Flujo simplificado:

```text
Publicación de dataset
↓
DataSetService.create_from_form
↓
FollowerRepository.get_followers_users
↓
MailService.send_new_dataset_by_followed_user_notification
↓
Seguidores reciben email
```

## Funcionalidad principal

Una vez creado el dataset, la función `DataSetService.create_from_form` obtiene los seguidores del autor llamando a `FollowerRepository.get_followers_users(author_id)`.

Con la información obtenida, el servicio construye los datos necesarios para la notificación, incluyendo:
- El nombre del autor (a partir de su perfil o, en su defecto, su email).
- El nombre del dataset publicado.

A continuación, se ejecuta la función `MailService.send_new_dataset_by_followed_user_notification`, que recibe como parámetros la lista de destinatarios, el nombre del autor y el nombre del dataset, y se encarga de generar y enviar el correo.

---

## Detalles del correo

- Asunto:
  Nuevo dataset publicado por <nombre_del_autor>

- Destinatarios:
  Usuarios que siguen al autor del dataset, incluidos mediante copia oculta (BCC).

- Privacidad:
  El uso de BCC en la función MailService.send_new_dataset_by_followed_user_notification evita que los seguidores puedan ver las direcciones de correo de otros usuarios.

- Contenido del mensaje:
  - Nombre del autor que ha publicado el dataset.
  - Nombre del dataset publicado.
  - Mensaje informativo invitando a consultar el dataset en la plataforma.

El correo se envía en formato HTML e incluye una versión alternativa en texto plano para garantizar la compatibilidad con distintos clientes de correo.

---

## Ejemplo de contenido del correo

El mensaje informa al usuario de que uno de los autores a los que sigue ha publicado un nuevo dataset, mostrando claramente el nombre del autor y el título del dataset, junto con un mensaje invitando a acceder a la plataforma para consultarlo.

---

## Obtención de destinatarios

Los destinatarios del correo se obtienen a partir de la función FollowerRepository.get_followers_users, que devuelve los usuarios que siguen al autor del dataset.

A partir de este conjunto de usuarios, la función DataSetService.create_from_form construye la lista final de direcciones de correo electrónico que se pasará a MailService.send_new_dataset_by_followed_user_notification.

Características del proceso:

- Solo se incluyen usuarios que disponen de una dirección de correo válida.
- Se eliminan direcciones de correo duplicadas.
- El orden de los destinatarios es determinista.
- Si el autor no tiene seguidores, no se envía ningún correo.
- La obtención de destinatarios no bloquea el flujo principal de creación del dataset.

---

## Manejo de errores

La llamada a MailService.send_new_dataset_by_followed_user_notification se realiza dentro de un bloque de control de excepciones.

Si ocurre un error durante el envío del correo electrónico:

- El error se registra en los logs del sistema.
- La función DataSetService.create_from_form continúa su ejecución normal.
- El dataset se crea correctamente y permanece disponible en la plataforma.
- El fallo en la notificación no afecta a la consistencia del sistema ni al proceso de publicación.

Este enfoque garantiza que los errores en servicios externos, como el sistema de correo, no impacten negativamente en la experiencia de los usuarios.

## Resumen del flujo

```text
Dataset subido por un usuario
        ↓
Obtener seguidores del usuario
        ↓
Enviar correo de notificación
        ↓
Seguidores informados
```
