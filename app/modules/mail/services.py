import logging

from flask import current_app
from flask_mail import Message

from app import mail

logger = logging.getLogger(__name__)


class MailService:

    @staticmethod
    def send_email(subject, recipients, html_body, text_body=None):
        try:
            msg = Message(
                subject=subject,
                recipients=recipients,
                html=html_body,
                body=text_body or html_body,
                sender=("TrackHub - Notificaciones", current_app.config["MAIL_DEFAULT_SENDER"]),
            )

            mail.send(msg)
            logger.info(f"Email enviado correctamente a {recipients}")
            return True, None

        except Exception as e:
            error_msg = f"Error al enviar email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_new_dataset_in_community_notification(recipients, community_name, dataset_name):
        subject = f"Nuevo dataset en {community_name}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{
                    background-color: #6366f1;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .highlight {{ color: #6366f1; font-weight: bold; }}
                .footer {{ margin-top: 20px; text-align: center; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Nuevo dataset publicado</h1>
                </div>
                <div class="content">
                    <p>
                        Se ha añadido un nuevo dataset a la comunidad
                        <span class="highlight">{community_name}</span>.
                    </p>

                    <p>
                        Dataset: <span class="highlight">{dataset_name}</span>
                    </p>

                    <p>Saludos,<br>El equipo de TrackHub</p>
                </div>
                <div class="footer">
                    <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Nuevo dataset publicado

        Se ha añadido un nuevo dataset a la comunidad {community_name}.
        Dataset: {dataset_name}

        Saludos,
        El equipo de TrackHub
        """

        return MailService.send_email(
            subject=subject,
            recipients=recipients,
            html_body=html_body,
            text_body=text_body,
        )

    @staticmethod
    def send_new_dataset_by_followed_user_notification(
        recipients,
        author_name,
        dataset_name,
    ):
        subject = f"Nuevo dataset publicado por {author_name}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body>
            <p>
                <strong>{author_name}</strong> ha publicado un nuevo dataset:
            </p>

            <p>
                <strong>{dataset_name}</strong>
            </p>

            <p>
                Puedes acceder a la plataforma para verlo.
            </p>

            <p>
                Saludos,<br>
                El equipo de TrackHub
            </p>
        </body>
        </html>
        """

        text_body = f"""
        {author_name} ha publicado un nuevo dataset.

        Dataset: {dataset_name}

        Saludos,
        El equipo de TrackHub
        """

        from flask import current_app
        from flask_mail import Message

        from app import mail

        msg = Message(
            subject=subject,
            recipients=[current_app.config["MAIL_DEFAULT_SENDER"]],
            bcc=recipients,
            html=html_body,
            body=text_body,
            sender=("TrackHub - Notificaciones", current_app.config["MAIL_DEFAULT_SENDER"]),
        )

        try:
            mail.send(msg)
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def send_dataset_approved_notification(requester_email, requester_name, dataset_name, community_name):
        subject = f"Dataset aprobado en {community_name}"

        # Template HTML del correo
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 5px 5px;
                }}
                .highlight {{ color: #4CAF50; font-weight: bold; }}
                .footer {{ margin-top: 20px; text-align: center; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Enhorabuena!</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{requester_name}</strong>,</p>

                    <p>
                        Tu dataset <span class="highlight">{dataset_name}</span> ha sido <strong>aceptado</strong>
                        en la comunidad <span class="highlight">{community_name}</span>.
                    </p>

                    <p>Tu contribución ayudará a enriquecer esta comunidad. ¡Gracias por tu participación!</p>

                    <p>Saludos,<br>El equipo de TrackHub</p>
                </div>
                <div class="footer">
                    <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Versión texto plano (fallback)
        text_body = f"""
        Enhorabuena {requester_name},

        Tu dataset {dataset_name} ha sido aceptado en {community_name}.

        Saludos,
        El equipo de TrackHub
        """

        return MailService.send_email(
            subject=subject, recipients=[requester_email], html_body=html_body, text_body=text_body
        )
