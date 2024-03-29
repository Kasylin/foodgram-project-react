from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиентов"""
    name = models.CharField(max_length=64, verbose_name='Название')
    measurement_unit = models.CharField(max_length=16,
                                        verbose_name='Единица измерения')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Tag(models.Model):
    """Модель тегов"""
    name = models.CharField(max_length=64,
                            unique=True,
                            verbose_name='Название')
    color = models.CharField(max_length=16,
                             unique=True,
                             verbose_name='Цвет')
    slug = models.SlugField(max_length=50,
                            unique=True,
                            verbose_name='Слаг')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'


class Recipe(models.Model):
    """Модель рецептов"""
    name = models.CharField(max_length=200, verbose_name='Название')
    text = models.TextField(verbose_name='Описание')
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Время приготовления в минутах'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор публикации'
    )
    ingregients = models.ManyToManyField(Ingredient,
                                         through='IngredientRecipe',
                                         related_name='recipes',
                                         verbose_name='Ингредиенты')
    tags = models.ManyToManyField(Tag,
                                  related_name='recipes',
                                  verbose_name='Теги')
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        default=None,
        verbose_name='Картинка'
    )
    pub_date = models.DateTimeField(auto_now_add=True,
                                    verbose_name='Дата публикации')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)


class IngredientRecipe(models.Model):
    """Модель для many-to-many связи ингредиентов и рецептов"""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE,
                                   related_name='in_recipe',
                                   verbose_name='Ингредиент')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               related_name='ingredients',
                               verbose_name='Рецепт')
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                         verbose_name='Количество')

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'

    class Meta:
        verbose_name = 'ингредиенты в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredients_in_recipe'
            )
        ]
