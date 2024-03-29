from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import FavoriteRecipes, ShoppingCart, Subscription, User


@admin.register(FavoriteRecipes)
class FavoriteRecipesAdmin(admin.ModelAdmin):
    """Модель избранных рецептов для админки"""
    list_display = (
        'user', 'recipe',
    )
    search_fields = ('user',)
    list_filter = ('user', 'recipe')
    list_display_links = ('user',)
    list_select_related = ('user', 'recipe')


class FavoriteRecipesInline(admin.StackedInline):
    """Inline-формат для избранных рецептов"""
    model = FavoriteRecipes
    extra = 0
    fk_name = 'user'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Модель списка покупок для админки"""
    list_display = (
        'user', 'recipe',
    )
    search_fields = ('user',)
    list_filter = ('user', 'recipe')
    list_display_links = ('user',)
    list_select_related = ('user', 'recipe')


class ShoppingCartInline(admin.StackedInline):
    """Inline-формат для списка покупок"""
    model = ShoppingCart
    extra = 0
    fk_name = 'user'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Модель подписок для админки"""
    list_display = (
        'user', 'following',
    )
    search_fields = ('user',)
    list_filter = ('user', 'following')
    list_display_links = ('user',)
    list_select_related = ('user', 'following')


class SubscriptionInline(admin.StackedInline):
    """Inline-формат для подписок"""
    model = Subscription
    extra = 0
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    """Модель пользователя для админки"""
    inlines = (
        FavoriteRecipesInline,
        ShoppingCartInline,
        SubscriptionInline,
    )
    list_filter = ('email', 'username')


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
