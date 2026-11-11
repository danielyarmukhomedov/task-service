# Запуск и демонстрация Task Service в Ubuntu

Это инструкция для работы с готовыми файлами репозитория. Описание системы,
API и технологий находится в [README.md](README.md).

## 1. Открыть терминал и каталог проекта

Нажмите **Ctrl + Alt + T**. Вставка команд в терминал — **Ctrl + Shift + V**.

Для уже скачанного проекта:

```bash
cd ~/task-service
```

Если проекта ещё нет:

```bash
git clone https://github.com/danielyarmukhomedov/task-service.git
cd task-service
```

Нужны Docker Engine и Docker Compose v2. Для примеров запросов нужен curl,
для автоматической проверки — Python 3. При вводе пароля sudo символы
в терминале не отображаются.

## 2. Проверить конфигурацию и запустить

```bash
sudo docker compose version
sudo docker compose config --quiet
sudo docker compose up -d --build --wait --wait-timeout 600
sudo docker compose ps -a
```

Первый запуск скачивает образы и зависимости, поэтому занимает несколько минут.
В окружении семь сервисов: gateway, api, notifications, analytics, db, redis и mailpit.
Для всех настроены healthchecks.

Java-код и его Dockerfile теперь находятся в `api-service/`.
Compose собирает этот каталог через `build: ./api-service`.

## 3. Открыть приложение

В браузере Ubuntu откройте:

- Панель: http://127.0.0.1:8088/
- Почта через Nginx: http://127.0.0.1:8088/mail/
- Почта напрямую: http://127.0.0.1:8025/mail/

Используйте **http://**. Если браузер автоматически включает HTTPS, разрешите
HTTP для этого локального сайта. Gateway не настраивает TLS в учебном окружении.

При работе в виртуальной машине адрес 127.0.0.1 относится к этой виртуальной
машине. Браузер на основной машине без туннеля не увидит loopback-порты Ubuntu.

## 4. Проверить систему и сохранить настоящий вывод

Из каталога проекта:

```bash
sudo bash scripts/check.sh --check-persistence
```

Скрипт запускает Compose и проверяет:

1. Доступность шлюза, Java API, Python, Go и Mailpit.
2. Создание, чтение, изменение и завершение задачи.
3. Ответы 400 на некорректные данные.
4. Увеличение счётчика Go.
5. SMTP-отправку и появление сообщения в Mailpit.
6. Сохранение задачи и письма после пересоздания контейнеров db и mailpit.
7. Удаление тестовой задачи и ответ 404 на повторное удаление.

Пересоздание сохраняет тома. Остальные задачи не удаляются; доступность базы
и API кратковременно прерывается. Письмо проверки остаётся в Mailpit.

Логи находятся в `docs/evidence/runtime/`:

| Файл | Содержание |
| --- | --- |
| compose-version.txt | Версия Docker Compose |
| compose-up.txt | Настоящий вывод сборки и запуска |
| compose-ps.txt | Состояние контейнеров |
| api-check.txt | HTTP-статусы, JSON и результаты проверок |
| compose-logs.txt | Последние сообщения сервисов |

Каталог runtime исключён из Git, чтобы случайно не сохранять рабочие логи.
Для сдачи можно выбрать файлы после просмотра и положить их, например,
в `docs/evidence/ubuntu-run/`. Скриншоты успешного запуска уже включены
в [docs/evidence/README.md](docs/evidence/README.md).

Для проверки работающего API без пересоздания контейнеров:

```bash
python3 scripts/verify.py
```

## 5. Короткий сценарий защиты

1. Показать состояние контейнеров и панель задач.
2. Создать задачу, выбрать приоритет, показать поиск и фильтры.
3. Завершить задачу, обновить страницу и показать сохранённый статус.
4. Отправить уведомление и открыть письмо в Mailpit.
5. Показать примеры curl из README и результаты api-check.txt.
6. Объяснить C4: Context — система целиком; Container — сервисы и хранилища;
   Component — контроллер, репозиторий и модель внутри Java API.

## 6. Повторный запуск, остановка и логи

```bash
sudo docker compose up -d --wait --wait-timeout 600
sudo docker compose stop
sudo docker compose logs --tail=100 api notifications gateway
```

Команда `stop` сохраняет данные. Не используйте `docker compose down -v`,
если задачи и письма должны остаться: этот флаг удаляет постоянные тома.

## 7. Исправление файлов через nano

Например, открыть Compose:

```bash
nano docker-compose.yml
```

Сохранить — **Ctrl + O**, затем **Enter**. Выйти — **Ctrl + X**.
После изменения кода или Dockerfile требуется пересборка:

```bash
sudo docker compose up -d --build --wait --wait-timeout 600
```

У Gateway внешний порт 8088, у Mailpit — 8025. Внутренний порт Nginx остаётся 80.
Если порт 80 занят другим проектом, останавливать тот проект не требуется.

При ошибке чтения файлов после переноса через ZIP:

```bash
chmod 755 frontend gateway notification-service
chmod 644 frontend/index.html gateway/nginx.conf notification-service/main.py
```

Dockerfile Python также явно задаёт права main.py перед запуском от USER 10001.

## 8. Что важно объяснять точно

- Java хранит задачи в PostgreSQL; `db_data` сохраняет их между контейнерами.
- Mailpit принимает SMTP локально. Письмо не уходит автоматически во внешний ящик.
- Go считает события с момента запуска, а не записи PostgreSQL.
- Redis присутствует в Compose, но Java-кеш пока не реализован.
- Пользователи, проекты, теги и долговечная очередь уведомлений — планы развития.

Актуальная архитектура: [SVG](docs/architecture.svg) и [PNG](docs/architecture.png).
Исходная авторская схема сохранена как [architecture-original.png](architecture-original.png).
