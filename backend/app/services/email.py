import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger("documind.email")


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("Email to %s | %s\n%s", to, subject, body)


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if self._settings.smtp_user:
                smtp.login(self._settings.smtp_user, self._settings.smtp_password)
            smtp.send_message(message)


def get_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    return ConsoleEmailSender()


def send_verification_email(sender: EmailSender, to: str, link: str) -> None:
    sender.send(
        to,
        "Verify your DocuMind email",
        f"Welcome to DocuMind.\n\nVerify your email address by opening this link:\n{link}\n\n"
        "If you didn't create an account, you can ignore this email.",
    )


def send_password_reset_email(sender: EmailSender, to: str, link: str) -> None:
    sender.send(
        to,
        "Reset your DocuMind password",
        f"Someone asked to reset the password for your DocuMind account.\n\n"
        f"Choose a new password by opening this link:\n{link}\n\n"
        "If you didn't ask for this, you can ignore this email.",
    )
