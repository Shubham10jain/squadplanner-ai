"""Async email sending via Gmail SMTP."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


async def send_email(to: str, subject: str, body: str) -> None:
    msg = MIMEMultipart()
    msg["From"]    = settings.smtp_user
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
    logger.info("Email sent to %s", to)


async def send_trip_invite(to: str, trip_name: str, invite_code: str) -> None:
    subject = f"You've been invited to join a trip: {trip_name}"
    body = (
        f"Hey there!\n\n"
        f"You've been invited to join a squad trip: {trip_name}\n\n"
        f"Use this invite code to join: {invite_code}\n\n"
        f"See you on the trip!\n"
        f"— The SquadPlanner Team"
    )
    await send_email(to, subject, body)
