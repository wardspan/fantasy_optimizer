from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import httpx

from ..settings import get_settings


async def send_slack_message(text: str) -> bool:
    settings = get_settings()
    if not settings.slack_webhook_url:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.slack_webhook_url, json={"text": text})
        return r.status_code // 100 == 2


def send_sms_via_email(to_number_at_gateway: str, text: str) -> bool:
    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_pass and settings.smtp_from):
        return False
    msg = MIMEText(text)
    msg["From"] = settings.smtp_from
    msg["To"] = to_number_at_gateway
    msg["Subject"] = "Fantasy Optimizer Alert"
    with smtplib.SMTP(settings.smtp_host) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_pass)
        server.sendmail(settings.smtp_from, [to_number_at_gateway], msg.as_string())
    return True

