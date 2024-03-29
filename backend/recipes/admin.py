from django.contrib import admin

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Модель ингредиентов для админки"""
    list_display = (
        'name',
        'measurement_unit',
    )
    list_display_links = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Модель тегов для админки"""
    list_display = (
        'name',
        'color',
        'slug',
    )
    list_display_links = ('name',)
    search_fields = ('name', 'slug')


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    """Модель ингредиентов в рецептах (IngredientRecipe) для админки"""
    list_display = (
        'ingredient', 'recipe', 'amount', 'ingredient__measurement_unit'
    )
    readonly_fields = ('ingredient__measurement_unit',)
    search_fields = ('ingredient', 'recipe')
    list_filter = ('ingredient', 'recipe')
    list_display_links = ('ingredient',)
    list_select_related = ('ingredient', 'recipe')

    def ingredient__measurement_unit(self, obj):
        return obj.ingredient.measurement_unit

    ingredient__measurement_unit.short_description = 'Единица измерения'


class IngredientRecipeInline(admin.StackedInline):
    """Inline-формат ингредиентов в рецептах (IngredientRecipe)"""
    model = IngredientRecipe
    extra = 0
    fk_name = 'recipe'
    fields = (
        'ingredient', 'recipe', 'amount', 'ingredient__measurement_unit'
    )
    readonly_fields = ('ingredient__measurement_unit',)

    def ingredient__measurement_unit(self, obj):
        return obj.ingredient.measurement_unit

    ingredient__measurement_unit.short_description = 'Единица измерения'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Модель рецептов для админки"""
    inlines = (IngredientRecipeInline,)
    fields = (
        'name',
        'text',
        'cooking_time',
        'author',
        'tags',
        'image',
        'pub_date',
        'is_favorited_count',
    )
    readonly_fields = ('pub_date', 'is_favorited_count')
    list_display = (
        'name',
        'author',
    )
    search_fields = ('name',)
    list_filter = ('name', 'author', 'tags')
    list_display_links = ('name',)
    list_select_related = ('author',)

    def is_favorited_count(self, obj):
        return obj.is_fav.count()

    is_favorited_count.short_description = 'Число добавлений в избранное'
