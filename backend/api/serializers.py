import base64

from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart
from users.serializers import UsersSerializer


class Base64ImageField(serializers.ImageField):
    """Поле для изображения закодированного в строку base64"""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов"""

    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели IngredientRecipe"""

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
    """Сериализатор для рецептов"""

    ingredients = IngredientRecipeSerializer(many=True, required=True)
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all(),
                                              required=True)
    image = Base64ImageField(required=True, allow_null=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_favorited(self, obj):
        if (
            self.context.get('request').user.is_authenticated
            and obj.is_fav.filter(
                user=self.context.get('request').user).exists()
        ):
            return True
        else:
            return False

    def get_is_in_shopping_cart(self, obj):
        if (
            self.context.get('request').user.is_authenticated
            and obj.is_in_cart.filter(
                user=self.context.get('request').user).exists()
        ):
            return True
        else:
            return False

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

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')
        read_only_fields = ('author',)
        extra_kwargs = {
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags_list = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient_data in ingredients:
            try:
                ingredient = Ingredient.objects.get(pk=ingredient_data['id'])
                IngredientRecipe.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=ingredient_data['amount']
                )
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    'В рецепте присутствуют несуществующие ингридинеты.',
                    code=400
                )
        recipe.tags.set(tags_list)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags_list = validated_data.pop('tags')
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if ingredients:
            IngredientRecipe.objects.filter(recipe=instance).delete()
            for ingredient_data in ingredients:
                try:
                    ingredient = Ingredient.objects.get(
                        pk=ingredient_data['id'])
                    IngredientRecipe.objects.create(
                        recipe=instance,
                        ingredient=ingredient,
                        amount=ingredient_data['amount']
                    )
                except Ingredient.DoesNotExist:
                    raise serializers.ValidationError(
                        'В рецепте присутствуют несуществующие ингридинеты.',
                        code=400
                    )
        if tags_list:
            instance.tags.set(tags_list)
        return instance


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

    def to_internal_value(self, data):
        """Входные данные сериализуются через RecipeSerializer"""
        return RecipeSerializer(context=self.context).to_internal_value(data)

    def to_representation(self, obj):
        """Сериализация рецептов

        Корректируем данные об ингредиентах:
        делаем из вложенного массива плоский.
        """
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
