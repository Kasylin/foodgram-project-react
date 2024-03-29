![example workflow](https://github.com/Kasylin/foodgram-project-react/actions/workflows/main.yml/badge.svg)

# Описание

«Фудграм» — сайт, на котором пользователи будут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Пользователям сайта также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

### Стек
Django 3.2, React 17.0, Postgres, Docker

# Как развернуть проект

Копируем к себе файл docker-compose.production.yml

Создаем файл .env с переменными среды

### Что должно быть в файле .env
- Логин-пароль для Postgres:
    - POSTGRES_USER
    - POSTGRES_PASSWORD
    - POSTGRES_DB=django
- Хост и порт для Postgres:
    - DB_HOST=db
    - DB_PORT
- Переменные для настроек Django:
    - SECRET_KEY
    - DEBUG
    - ALLOWED_HOSTS
    - DJANGO_DATABASE - если имеет значение 'postgres', то дефолтная БД в DATABASES будет задаваться как postgres. В других случаях - sqlite.

Разворачиваем контейнеры:
```
docker compose -f docker-compose.production.yml up
```

Запускаем миграции
```
docker compose -f docker-compose.production.yml exec backend python manage.py migrate
```

Перекладываем статику в нужную папку
```
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

# Авторы
Авторы [исходного репозитория](https://github.com/yandex-praktikum/foodgram-project-react), [Kasylin](https://github.com/Kasylin)
