import logging
import os
import smtplib
import socket
import ssl
import time
from contextlib import contextmanager
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from threading import Lock
from typing import Dict
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notifications")
app = FastAPI(title="Task Console Notifications", docs_url=None, redoc_url=None)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise RuntimeError("Invalid boolean setting: " + name)
    return value in {"true", "1", "yes"}


SMTP_HOST = os.getenv("SMTP_HOST", "mailpit").strip() or "mailpit"
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_SSL = env_bool("SMTP_SSL", False)
SMTP_PORT = int(os.getenv("SMTP_PORT", "").strip() or
                ("1025" if SMTP_HOST == "mailpit" else "465" if SMTP_SSL else "587"))
SMTP_SSL = env_bool("SMTP_SSL", SMTP_PORT == 465)
SMTP_STARTTLS = env_bool("SMTP_STARTTLS", SMTP_HOST != "mailpit" and not SMTP_SSL)
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USER or "no-reply@task-service.local"
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "10"))
if SMTP_SSL and SMTP_STARTTLS:
    raise RuntimeError("Choose SMTP_SSL or SMTP_STARTTLS")
if bool(SMTP_USER) != bool(SMTP_PASSWORD):
    raise RuntimeError("SMTP_USER and SMTP_PASSWORD must be set together")
if SMTP_USER and not (SMTP_SSL or SMTP_STARTTLS):
    raise RuntimeError("SMTP authentication requires TLS")
if not 1 <= SMTP_PORT <= 65535 or not 0 < SMTP_TIMEOUT <= 30:
    raise RuntimeError("Invalid SMTP port or timeout")
if "\r" in SMTP_FROM or "\n" in SMTP_FROM or "@" not in SMTP_FROM:
    raise RuntimeError("Invalid SMTP_FROM")

jobs: Dict[str, dict] = {}
jobs_lock = Lock()
MAX_RECORDS, MAX_PENDING, RETENTION_SECONDS = 500, 50, 3600


class Notification(BaseModel):
    email: EmailStr
    message: str = Field(min_length=1, max_length=10000)
    subject: str = Field(default="Уведомление Task Console", min_length=1, max_length=180)


@contextmanager
def smtp_connection():
    if SMTP_SSL:
        client = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT,
                                  context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
    try:
        client.ehlo()
        if SMTP_STARTTLS:
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if SMTP_USER:
            client.login(SMTP_USER, SMTP_PASSWORD)
        yield client
    finally:
        # QUIT failure after successful DATA must not mark accepted mail as failed.
        try:
            client.quit()
        except (OSError, smtplib.SMTPException):
            client.close()


def deliver(notification_id: str, notification: Notification):
    with jobs_lock:
        jobs[notification_id]["status"] = "sending"
    try:
        message = EmailMessage()
        message["From"] = SMTP_FROM
        message["To"] = str(notification.email)
        message["Subject"] = notification.subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain="task-service.local")
        message.set_content(notification.message, charset="utf-8")
        with smtp_connection() as client:
            client.send_message(message, from_addr=SMTP_FROM,
                                to_addrs=[str(notification.email)])
        with jobs_lock:
            jobs[notification_id].update(status="sent", finished_at=time.time())
        logger.info("SMTP accepted notification_id=%s", notification_id)
    except Exception as exc:
        with jobs_lock:
            jobs[notification_id].update(status="failed", finished_at=time.time(),
                error="SMTP-сервер не подтвердил приём. Проверьте настройки и логи.")
        logger.error("SMTP failed notification_id=%s error_type=%s", notification_id,
                     type(exc).__name__)


@app.get("/")
def root():
    return {"service": "notifications", "status": "running"}


@app.get("/health")
def health():
    try:
        with socket.create_connection((SMTP_HOST, SMTP_PORT), timeout=2):
            pass
    except OSError:
        raise HTTPException(status_code=503, detail="SMTP connection unavailable")
    return {"status": "ok", "smtp": "reachable",
            "mode": "mailpit" if SMTP_HOST == "mailpit" else "external"}


@app.post("/notify", status_code=status.HTTP_202_ACCEPTED)
def notify(notification: Notification, background_tasks: BackgroundTasks):
    if not notification.message.strip() or not notification.subject.strip():
        raise HTTPException(status_code=422, detail="Тема и текст не должны быть пустыми")
    if "\r" in notification.subject or "\n" in notification.subject:
        raise HTTPException(status_code=422, detail="Недопустимый заголовок письма")
    notification_id, now = str(uuid4()), time.time()
    with jobs_lock:
        expired = [key for key, job in jobs.items()
                   if job["status"] in {"sent", "failed"}
                   and now - job["finished_at"] > RETENTION_SECONDS]
        for key in expired:
            del jobs[key]
        pending = sum(job["status"] in {"queued", "sending"} for job in jobs.values())
        if pending >= MAX_PENDING:
            raise HTTPException(status_code=429, detail="Очередь отправки заполнена")
        if len(jobs) >= MAX_RECORDS:
            finished = next((key for key, job in jobs.items()
                             if job["status"] in {"sent", "failed"}), None)
            if finished:
                del jobs[finished]
        result = {"notification_id": notification_id, "status": "queued",
                  "sent_to": str(notification.email), "created_at": now}
        jobs[notification_id] = dict(result)
    background_tasks.add_task(deliver, notification_id, notification)
    return result


@app.get("/notify/{notification_id}")
def notification_status(notification_id: str):
    with jobs_lock:
        job = jobs.get(notification_id)
        if not job:
            raise HTTPException(status_code=404, detail="Статус истёк или сервис перезапущен")
        return dict(job)
