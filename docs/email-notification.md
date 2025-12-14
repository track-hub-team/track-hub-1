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
