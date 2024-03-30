# Ссылка на проект
https://testthemeow.webhop.me/

# Доступ к админке
Логин: DjangoAdmin<br/>
Пароль: DjangoAdmin<br/>
Почта: admin@admin.ru

---

![example workflow](https://github.com/Kasylin/foodgram-project-react/actions/workflows/main.yml/badge.svg)


# Описание

«Фудграм» — сайт, на котором пользователи будут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Пользователям сайта также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

### Стек
Django 3.2, React 17.0, Postgres, Docker

# Структура приложения
- Приложение recipes: модели рецептов, тегов и ингредиентов
- Приложение users: модели пользователей, подписок, списка покупок и избранного

# Как работает API
## Структура 
- Приложение api:
    - маршрутизация
    - вьюсеты и сериализаторы для: рецептов, тегов, ингредиентов, списка покупок и избранного
    - настройки api
- Приложение users:
    - вьюсеты и сериализаторы для: пользователей и подписок

## Вьюсеты и сериализаторы
- Ингредиенты и теги имеют стандартные модельные вьюсеты и сериализаторы
- Действия со списком покупок и избранного добавлены во вьюсет рецептов (RecipeViewSet) - см. далее
- Действия с подписками добавлены во вьюсет пользователей (UsersViewSet) - см. далее

### Вьюсет рецептов (RecipeViewSet)
#### Допольнительные/кастомные действия
- /shopping_cart - добавление или удаление из списка покупок
- /download_shopping_cart - скачать список покупок
- /favorite - добавление или удаление из списка избранного

#### Доступы
Т.к. в кастомных действиях обрабатываются объекты списка покупок и избранного, передаем на проверку соответствующие объекты:
- для действий со списком покупок - объект ShoppingCart
- для действий со списком избранного - объект FavoriteRecipes
- дефолтный вариант для остальных действий - объект Recipe

#### Сериализация
Дефолтный сериализатор вьюсета - RecipeDetailSerializer.

Для объектов рецептов есть два сериализатора: 
- RecipeSerializer - в нем задается список полей, их валидация и методы создания и обновления рецепта.
- RecipeDetailSerializer, наследующийся от RecipeSerializer - переопределяет формат вывода данных.

Для кастомных действий подключаются отдельные сериализаторы:
- /shopping_cart - ShoppingCartSerializer
- /download_shopping_cart - IngredientsShoppingCartSerializer
- /favorite - FavoriteRecipesSerializer


### Вьюсет пользователей (UsersViewSet)
UsersViewSet наследуется от стандартного djoser.views.UserViewSet из Djoser.

#### Допольнительные/кастомные действия
- /me - действие задано в стандартном вьюсете, только переопределяем доступы
- /subscribe - создание или удаление подписки
- /subscriptions - вывести подписки пользователя

#### Доступы
Т.к. в кастомных действиях обрабатываются объекты подписок, передаем на проверку соответствующие объекты:
- для действий с подписками - объект Subscription
- дефолтный вариант для остальных действий - объект Use

#### Сериализация

Для объектов пользователей есть два сериализатора: 
- UserCreationSerializer - в нем задается список полей, их валидация и метод создания пользователя
- UsersSerializer, наследующийся от UserCreationSerializer - добавляется поле is_subscribed

Для кастомных действий подключаются отдельные сериализаторы:
- /subscribe - SubscriptionRequestSerializer
- /subscriptions - SubscriptionResponseSerializer

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
