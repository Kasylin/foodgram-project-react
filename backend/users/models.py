from django.contrib.auth import get_user_model
from django.db import models

from recipes.models import Recipe

User = get_user_model()


class Subscription(models.Model):
    """Модель подписок"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='following',
        verbose_name='Пользователь, оформивший подписку')
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='followers',
        verbose_name='Подписка пользователя')

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(fields=['user', 'following'],
                                    name='unique_following'),
            models.CheckConstraint(check=~models.Q(user=models.F('following')),
                                   name='following_oneself_not_allowed'),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.following}'


class FavoriteRecipes(models.Model):
    """Модель списка избранных рецептов"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorite_recipes',
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='is_fav',
        verbose_name='Рецепт в списке избранного')

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'],
                                    name='unique_favorites'),
        ]

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в Избранное'


class ShoppingCart(models.Model):
    """Модель списка покупок"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_cart',
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='is_in_cart',
        verbose_name='Рецепт в списке покупок')

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Покупки'
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'],
                                    name='unique_shopping_cart'),
        ]

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в Список покупок'
