from http import HTTPStatus

from django.db import IntegrityError, transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart
from users.serializers import UsersSerializer


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=True)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте"""

    id = serializers.UUIDField(required=True)
    ingredient = IngredientSerializer()
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount', 'ingredient')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientRecipeSerializer(many=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all(),
                                              required=True)
    image = Base64ImageField(required=True)

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список ингридиентов не может быть пустым.'
            )
        ingredient_ids = [ingredient['id'] for ingredient in value]
        if not len(set(ingredient_ids)) == len(ingredient_ids):
            raise serializers.ValidationError(
                'Ингридиенты не могут повторяться.'
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список тегов не может быть пустым.'
            )
        if not len(set(value)) == len(value):
            raise serializers.ValidationError(
                'Теги не могут повторяться.'
            )
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Картинка не может быть пустой.'
            )
        return value

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'name', 'image',
                  'text', 'cooking_time')
        read_only_fields = ('author',)
        extra_kwargs = {
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        try:
            with transaction.atomic():
                ingredients = validated_data.pop('ingredients')
                tags_list = validated_data.pop('tags')
                recipe = Recipe.objects.create(**validated_data)

                ingredient_list = [
                    IngredientRecipe(
                        recipe=recipe,
                        ingredient_id=ingredient['id'],
                        amount=ingredient['amount']
                    ) for ingredient in ingredients
                ]
                IngredientRecipe.objects.bulk_create(ingredient_list)
                recipe.tags.set(tags_list)
                return recipe
        except IntegrityError as err:
            raise serializers.ValidationError(
                err.args, code=HTTPStatus.BAD_REQUEST)

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                ingredients = validated_data.pop('ingredients')
                tags_list = validated_data.pop('tags')
                for key, value in validated_data.items():
                    setattr(instance, key, value)
                instance.save()
                if ingredients:
                    IngredientRecipe.objects.filter(recipe=instance).delete()
                    ingredient_list = [
                        IngredientRecipe(
                            recipe=instance,
                            ingredient_id=ingredient['id'],
                            amount=ingredient['amount']
                        ) for ingredient in ingredients
                    ]
                    IngredientRecipe.objects.bulk_create(ingredient_list)
                if tags_list:
                    instance.tags.set(tags_list)
                return instance
        except IntegrityError as err:
            raise serializers.ValidationError(
                err.args, code=HTTPStatus.BAD_REQUEST)


class RecipeDetailSerializer(RecipeSerializer):
    """
    Сериализатор для вывода данных о рецептах

    Наследуется от основного сериализатора для рецептов.
    Поля с внешними ключами моделей переопределяются для
    вывода подробных сведений о связанных объектах.
    """

    tags = TagSerializer(many=True)
    author = UsersSerializer()
    ingredients = IngredientInRecipeSerializer(many=True)
    is_favorited = serializers.BooleanField(required=False)
    is_in_shopping_cart = serializers.BooleanField(required=False)

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + (
            'is_favorited', 'is_in_shopping_cart')

    def to_internal_value(self, data):
        """Входные данные сериализуются через RecipeSerializer"""
        return RecipeSerializer(context=self.context).to_internal_value(data)

    def to_representation(self, obj):
        """Сериализация рецептов

        Корректируем данные об ингредиентах:
        делаем из вложенного массива плоский.
        """
        if self.context.get('request').method == 'POST':
            if not hasattr(obj, 'is_favorited'):
                obj.is_favorited = False
            if not hasattr(obj, 'is_in_shopping_cart'):
                obj.is_in_shopping_cart = False
        representation = super().to_representation(obj)
        ingredients = representation.pop('ingredients')
        ingredients_new = []
        for ingredient in ingredients:
            ingredient_detail = ingredient.pop('ingredient')
            ingredient_detail['amount'] = ingredient['amount']
            ingredients_new.append(ingredient_detail)
        representation['ingredients'] = ingredients_new

        return representation


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для укороченного списка полей рецепта"""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class IngredientsShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для скачиваемого списка покупок"""

    amount_sum = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit', 'amount_sum')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления и удаления из списка покупок"""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def to_representation(self, data):
        """На выход отдаем данные о рецептах в списке покупок"""

        return RecipeShortSerializer(
            self.context.get('recipe'),
            context={'request': self.context.get('request')}
        ).to_representation(self.context.get('recipe'))


class FavoriteRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного"""

    class Meta:
        model = FavoriteRecipes
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def to_representation(self, data):
        """На выход отдаем данные о рецептах в списке избранного"""

        return RecipeShortSerializer(
            self.context.get('recipe'),
            context={'request': self.context.get('request')}
        ).to_representation(self.context.get('recipe'))
