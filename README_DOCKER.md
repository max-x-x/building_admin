# Docker Setup для Admin Panel

## Запуск проекта

### 1. Сборка и запуск контейнера
```bash
docker-compose up --build
```

### 2. Создание суперпользователя (в отдельном терминале)
```bash
docker-compose exec web python manage.py createsuperuser
```

### 3. Доступ к приложению
- Веб-приложение: http://localhost:8000
- База данных: SQLite (файл db.sqlite3)

## Остановка
```bash
docker-compose down
```

## Полезные команды

### Выполнение Django команд
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic
docker-compose exec web python manage.py shell
```

### Просмотр логов
```bash
docker-compose logs web
```

## Переменные окружения

- `DEBUG` - режим отладки (по умолчанию: True)
