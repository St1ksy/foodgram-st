#!/bin/bash

# Запуск контейнеров в фоновом режиме
echo "Starting Docker containers..."
docker-compose up -d --build

# Выполнение миграций
echo "Running makemigrations..."
docker compose exec backend python manage.py makemigrations recipes

echo "Running migrations..."
docker compose exec backend python manage.py migrate

# Сборка статических файлов
echo "Collecting static files..."
docker compose exec backend python manage.py collectstatic --noinput

# Импорт данных ингредиентов
echo "Importing ingredients..."
docker compose exec backend python manage.py import_ingredients

echo "Project setup completed!"
