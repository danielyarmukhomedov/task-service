from fastapi import FastAPI
from pydantic import BaseModel
import logging

# Настройка логирования 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

app = FastAPI()

class Notification(BaseModel):
    email: str
    message: str

@app.get("/")
def health_check():
    return {"status": "Notification Service is running"}

@app.post("/notify")
def send_notification(notification: Notification):
    # Имитация бурной деятельности и логирование
    logger.info(f"📨 ОТПРАВКА EMAIL -> {notification.email}: {notification.message}")
    return {"status": "success", "sent_to": notification.email}
