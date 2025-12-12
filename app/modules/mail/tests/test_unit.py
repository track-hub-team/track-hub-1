import os
from unittest.mock import patch

import pytest

from app import create_app
from app.modules.mail.services import MailService


class TestMailService:
    """Tests unitarios para el servicio de correo"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        yield
        self.app_context.pop()

    @patch("app.modules.mail.services.mail.send")
    def test_send_email_calls_mail_send(self, mock_send):
        """Test unitario con mock: verifica que se llama a mail.send()"""
        success, error = MailService.send_email(
            subject="Test", recipients=["test@example.com"], html_body="<p>Test</p>"
        )

        assert success is True
        assert mock_send.called
        assert mock_send.call_count == 1

    @patch("app.modules.mail.services.mail.send")
    def test_send_dataset_approved_notification_format(self, mock_send):
        """Verifica que la notificación tiene el formato correcto"""
        success, error = MailService.send_dataset_approved_notification(
            requester_email="user@test.com",
            requester_name="Test User",
            dataset_name="Test Dataset",
            community_name="Test Community",
        )

        assert success is True

        # Verificar que se llamó con los parámetros correctos
        call_args = mock_send.call_args[0][0]  # primer argumento (Message object)
        assert "Test Community" in call_args.subject
        assert call_args.recipients == ["user@test.com"]

    # Test de integración REAL
    @pytest.mark.integration
    @staticmethod
    def _is_sendgrid_configured() -> bool:
        """Verifica si SendGrid está configurado correctamente"""
        mail_password = os.getenv("MAIL_PASSWORD") or ""  # ← mypy acepta esto
        mail_sender = os.getenv("MAIL_DEFAULT_SENDER") or ""
        return bool(mail_password.startswith("SG.") and mail_sender)

    @pytest.mark.skipif(
        not _is_sendgrid_configured.__func__(),  # ← mypy acepta esto ahora
        reason="SendGrid no está configurado en las variables de entorno",
    )
    def test_send_real_email(self):
        """
        Test de integración: envía correo real si SendGrid está configurado
        """
        app = create_app("development")
        with app.app_context():
            success, error = MailService.send_dataset_approved_notification(
                requester_email="pabcasmor1@alum.us.es",
                requester_name="Pablo Test",
                dataset_name="Dataset Test - Integración",
                community_name="Test Community",
            )

            assert success is True, f"El envío de correo falló: {error}"
            print("\nCorreo real enviado correctamente")
            print("Revisa la bandeja: pabcasmor1@alum.us.es")

    @patch("app.modules.mail.services.mail.send")
    def test_send_new_dataset_in_community_notification_calls_mail_send(self, mock_send):
        """Verifica que se envía email al notificar nuevo dataset en comunidad"""
        recipients = ["user1@test.com", "user2@test.com"]

        success, error = MailService.send_new_dataset_in_community_notification(
            recipients=recipients,
            community_name="Test Community",
            dataset_name="Test Dataset",
        )

        assert success is True
        assert error is None
        assert mock_send.called
        assert mock_send.call_count == 1

        message = mock_send.call_args[0][0]
        assert set(message.recipients) == set(recipients)

    @patch("app.modules.mail.services.mail.send")
    def test_send_new_dataset_by_followed_user_notification_calls_mail_send(self, mock_send):
        """Verifica que se envía email cuando un usuario seguido publica dataset"""
        recipients = ["follower@test.com"]

        success, error = MailService.send_new_dataset_by_followed_user_notification(
            recipients=recipients,
            author_name="Test Author",
            dataset_name="Dataset X",
        )

        assert success is True
        assert error is None
        assert mock_send.called
        assert mock_send.call_count == 1

        message = mock_send.call_args[0][0]
        assert set(message.bcc) == set(recipients)

    @patch(
        "app.modules.mail.services.mail.send",
        side_effect=Exception("SMTP error"),
    )
    def test_new_dataset_notification_handles_exception(self, mock_send):
        """Verifica que el servicio maneja excepciones al enviar correo"""
        success, error = MailService.send_new_dataset_in_community_notification(
            recipients=["user@test.com"],
            community_name="Fail Community",
            dataset_name="Fail Dataset",
        )

        assert success is False
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
