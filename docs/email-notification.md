
# Email Notification: Dataset Accepted in Community

## General Description

The Track Hub email notification system automatically sends an email to the user when one of their datasets has been accepted into a community. This feature improves the user experience by immediately informing them of the approval and encouraging active participation in communities.

---

## Location

- **Main service:**
  - `services.py` → `MailService.send_dataset_approved_notification`
- **Approval logic:**
  - `services.py` → `CommunityService.approve_request`
- **Mail configuration:**
  - `__init__.py` (Flask-Mail SendGrid)
- **Unit tests:**
  - `test_unit.py`

## Architecture

### MailService

Class responsible for managing and sending emails:

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


### Approval Flow

1) A curator approves the request to include a dataset in a community
2) `CommunityService.approve_request` calls `MailService.send_dataset_approved_notification`
3) The email is generated and sent to the requesting user


## Main Functionality

Approval Notification Sending

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


- **Subject:** `Dataset aprobado en <nombre_comunidad>`
- **Recipient:** Requesting user's email
- **Content:** Personalized message with the user's name, dataset, and community


#### Example HTML email:

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


## Configuration

- **SMTP server:** SendGrid is used (configured via environment variables)
- **Relevant variables:**
  - `MAIL_SERVER`
  - `MAIL_PORT`
  - `MAIL_USE_TTL`
  - `MAIL_USE_SSL`
  - `MAIL_USERNAME`
  - `MAIL_PASSWORD`
  - `MAIL_DEFAULT_SENDER`


## Tests

- **Coverage:** `test_send_dataset_approved_notification_format` in `test_unit.py` checks:
  - That the email is sent correctly
  - That the subject and recipient are correct

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


- If an error occurs while sending the email, it is logged and an error message is returned
- The approval flow continues even if the email fails to send, but the event is recorded in the logs


## Flow summary

```
Curator approves request
  ↓
CommunityService.approve_request()
  ↓
MailService.send_dataset_approved_notification()
  ↓
User receives approval email
```


## Limitations

- The email is only sent to the requesting user, not to other community members
- No notification is sent in case of rejection (only in case of approval)

---


This feature ensures that users are informed in real time about the acceptance of their datasets in communities, reinforcing transparency and motivation to contribute.


## Email Notification: New Dataset in Followed Communities

## General Description

TrackHub automatically sends an email notification to users who **follow a community** when a new dataset is added to that community.

This feature allows members to be informed in real time about new contributions within the communities they follow, encouraging participation and the discovery of new relevant datasets.

---


## Location

- **Mail service:**
  - `services.py` → `MailService.send_new_dataset_in_community_notification`
- **Event trigger logic:**
  - `services.py` → `CommunityService.approve_request`
- **Involved repositories:**
  - `repositories.py` → `CommunityFollowerRepository.get_followers_users`
- **Mail configuration:**
  - `__init__.py` (Flask-Mail + SendGrid)
- **Unit tests:**
  - `test_unit.py` (MailService)

---


## Architecture

### MailService

Sending emails to community followers is centralized in the mail service using the following method:

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

This method is responsible for:
- Building the email subject
- Generating the HTML and plain text content
- Delegating the sending to MailService.send_email


### Dataset approval flow

1. A user proposes a dataset to a community through a request.
2. A community curator reviews the request and approves it.

3. The system officially adds the dataset to the community.
4. The users who follow that community are obtained.
5. An email notification is sent to all followers.

Simplified flow:

```text
Curator approves request
  ↓
CommunityService.approve_request()
  ↓
Add dataset to community
  ↓
Get community followers
  ↓
MailService.send_new_dataset_in_community_notification()
  ↓
Followers receive email
```


## Main Functionality

### Sending notification to community followers

When a dataset is approved and incorporated into a community, the system sends an email notification to all users who follow that community.

The functionality is implemented in the mail service using the following method:

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

#### Email details

- **Subject:**
  `Nuevo dataset en <nombre_comunidad>`
- **Recipients:**
  Users who follow the community (**To** field)
- **Message content:**
  - Name of the community where the dataset was published
  - Name of the added dataset
  - Informative and neutral message

The email is sent in HTML format and includes an alternative plain text version to ensure compatibility with different email clients.

---


#### Example HTML email

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


## Obtaining recipients

The recipients of the email are obtained from the users who follow the community where the new dataset has been approved.

Followers are obtained through the community follower repository:

```python
followers = self.follower_repository.get_followers_users(community_id)
```


From this list of users, the final list of email addresses is built:

```python
recipients = sorted({u.email for u in followers if u.email})
```


### Process characteristics

- Only users with a valid email address are included.
- Duplicate email addresses are removed.
- If there are no followers, no email is sent.
- Obtaining recipients does not block the main dataset approval flow.


## Error handling

If an error occurs during email sending, the system handles the exception in a controlled manner.

- The error is logged for later analysis.
- The dataset **remains approved** even if the email fails to send.
- The notification failure **does not affect system consistency** or the main flow.

Example of error handling:

```python
if not success:
    logger.warning(
        "Failed to send new-dataset email to community followers"
    )
```


### Flow summary

```text
Dataset approved in community
  ↓
Get community followers
  ↓
Send notification email
  ↓
Followers informed
```


# Email Notification: New Dataset from Followed Users

## General Description

TrackHub automatically sends an email notification to users who follow another user when that user publishes a new dataset on the platform. This feature allows users to stay informed about new contributions made by the authors they follow, promoting the discovery of relevant datasets and interaction within the platform. The user-following logic is already implemented and documented elsewhere, so this section focuses exclusively on email notification sending.

---

## Location

- Mail service:
  - `services.py` → `MailService.send_new_dataset_by_followed_user_notification`
- Event trigger logic:
  - `dataset_service.py` → `DataSetService.create_from_form`
- Involved repository:
  - `repositories.py` → `FollowerRepository.get_followers_users`
- Mail configuration:
  - `__init__.py` (Flask-Mail + SendGrid)

---

## Architecture

Notifications to followers of a user are sent automatically after a dataset is successfully created. The DataSetService, specifically in the create_from_form function, detects the publication event and coordinates the notification process. The responsibility for building and sending the email is delegated to the MailService, via the `send_new_dataset_by_followed_user_notification` function, thus maintaining a clear separation between business logic and notification sending.

---

## Dataset Publication Flow

1. A user creates a new dataset using the creation form.
2. The system validates the data and persists the dataset and its metadata.
3. At the end of the `DataSetService.create_from_form` function, the author's followers are obtained using `FollowerRepository.get_followers_users`.
4. The author's name and the title of the newly created dataset are built.
5. The `MailService.send_new_dataset_by_followed_user_notification` function is called to send the notification.
6. The follower users receive the informational email.

Simplified flow:

```text
Dataset publication
↓
DataSetService.create_from_form
↓
FollowerRepository.get_followers_users
↓
MailService.send_new_dataset_by_followed_user_notification
↓
Followers receive email
```

## Main Functionality

Once the dataset is created, the `DataSetService.create_from_form` function obtains the author's followers by calling `FollowerRepository.get_followers_users(author_id)`. With the information obtained, the service builds the necessary data for the notification, including:
- The author's name (from their profile or, failing that, their email).
- The name of the published dataset.

Next, the `MailService.send_new_dataset_by_followed_user_notification` function is executed, which receives as parameters the list of recipients, the author's name, and the dataset name, and is responsible for generating and sending the email.

---

## Email Details

- Subject:
  New dataset published by <author_name>
- Recipients:
  Users who follow the dataset author, included via blind carbon copy (BCC).
- Privacy:
  The use of BCC in the MailService.send_new_dataset_by_followed_user_notification function prevents followers from seeing other users' email addresses.
- Message content:
  - Name of the author who published the dataset.
  - Name of the published dataset.
  - Informative message inviting to check the dataset on the platform.

The email is sent in HTML format and includes an alternative plain text version to ensure compatibility with different email clients.

---

## Example Email Content

The message informs the user that one of the authors they follow has published a new dataset, clearly showing the author's name and the dataset title, along with a message inviting them to access the platform to check it out.

---

## Obtaining Recipients

The recipients of the email are obtained from the `FollowerRepository.get_followers_users` function, which returns the users who follow the dataset author. From this set of users, the `DataSetService.create_from_form` function builds the final list of email addresses to be passed to `MailService.send_new_dataset_by_followed_user_notification`.

Process characteristics:
- Only users with a valid email address are included.
- Duplicate email addresses are removed.
- The order of recipients is deterministic.
- If the author has no followers, no email is sent.
- Obtaining recipients does not block the main dataset creation flow.

---

## Error Handling

The call to `MailService.send_new_dataset_by_followed_user_notification` is made within an exception handling block. If an error occurs during email sending:
- The error is logged in the system logs.
- The `DataSetService.create_from_form` function continues its normal execution.
- The dataset is created correctly and remains available on the platform.
- The notification failure does not affect system consistency or the publication process.

This approach ensures that errors in external services, such as the mail system, do not negatively impact the user experience.

## Flow Summary

```text
Dataset uploaded by a user
        ↓
Get user's followers
        ↓
Send notification email
        ↓
Followers informed
```
