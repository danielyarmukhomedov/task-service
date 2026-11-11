# Контракт задач

| Поле | Тип | Назначение |
| --- | --- | --- |
| id | integer | Назначается PostgreSQL при создании |
| title | string | Название, от 1 до 255 символов |
| description | string | Описание, не более 255 символов |
| priority | string | High, Medium или Low |
| completed | boolean | Статус выполнения, false при создании |

GET /tasks — список; POST /tasks — создание (201); PUT /tasks/{id} — изменение
названия, описания и приоритета (200); PATCH /tasks/{id}/completion — изменение
completed (200); DELETE /tasks/{id} — удаление (204).

Некорректные поля возвращают 400, обращение к отсутствующей задаче — 404.
Java-сервис находится в api-service/. Полные примеры запросов приведены в README.md.
