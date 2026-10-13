# Microservice Task System (Final Project)

Распределенная микросервисная система управления задачами. Финальный проект курса «Разработка облачных приложений».
Система реализует паттерн **API Gateway**, использует полиглот-программирование (Java + Python) и инфраструктуру данных (PostgreSQL + Redis).

## 🏗 Архитектура (C4 Model)

![Architecture Diagram](architecture.png)

Система состоит из 3-х независимых микросервисов:

1.  **API Gateway (Nginx)** — Единая точка входа (Port 80). Маршрутизирует запросы и скрывает внутреннюю сеть.
2.  **Task Service (Java Spring Boot)** — Основная бизнес-логика, работа с БД и кэшем.
3.  **Notification Service (Python FastAPI)** — Сервис отправки уведомлений (имитация Email).

## 🛠 Технологический стек
*   **Java 11 / Spring Boot** (Backend)
*   **Python 3.9 / FastAPI** (Notifications)
*   **Nginx** (Reverse Proxy / Gateway)
*   **PostgreSQL 16** (Persistent Database)
*   **Redis** (Cache)
*   **Docker & Docker Compose** (Orchestration)

## 🚀 Запуск одной командой

1. Сборка Java-приложения:
   ```bash
   mvn clean package
   ```

2. Поднятие инфраструктуры:
   ```bash
   docker compose up -d --build
   ```

## ✅ Тестирование API

**1. Создать задачу (Java Service):**
```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"title":"Final Exam","description":"Microservices Architecture","priority":"High"}' \
http://localhost/tasks
```

**2. Отправить уведомление (Python Service):**
```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"email":"professor@univ.edu", "message":"Project Completed!"}' \
http://localhost/notify
```
