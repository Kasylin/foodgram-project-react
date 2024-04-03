import re

from django.core.paginator import Paginator
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart, Subscription, User


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'

    def to_internal_value(self, data):
        if isinstance(data, int):
            try:
                tag = Tag.objects.get(pk=data)
            except Tag.DoesNotExist:
                raise serializers.ValidationError(
                    'Список тегов не может быть пустым.'
                )
            return tag.__dict__
        if isinstance(data, dict):
            return super().to_internal_value(data)


class UserCreationSerializer(serializers.ModelSerializer):
    """Сериализатор для объектов пользователей."""

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )
        extra_kwargs = {
            'username': {
                'required': True,
                'validators': [UniqueValidator(queryset=User.objects.all())]
            },
            'email': {
                'required': True,
                'validators': [UniqueValidator(queryset=User.objects.all())]
            },
            'first_name': {'required': True},
            'last_name': {'required': True},
            'id': {'read_only': True},
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def validate_username(self, value):
        if value == 'me':
            raise serializers.ValidationError(
                'Invalid username.'
            )
        elif not re.match(r"^[\w.@+-]+\Z", value):
            raise serializers.ValidationError(
                'Invalid username.'
            )
        return value


class UsersSerializer(UserCreationSerializer):
    """Сериализатор для объектов пользователей с доп. полем is_subscribed"""

    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserCreationSerializer.Meta):
        fields = UserCreationSerializer.Meta.fields + ('is_subscribed',)

    def get_is_subscribed(self, obj):
        if (
            self.context.get('request').user.is_authenticated
            and obj.followers.filter(
                user=self.context.get('request').user).exists()
        ):
            return True
        else:
            return False


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте"""

    id = serializers.UUIDField(required=True)
    ingredient = IngredientSerializer(required=False)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount', 'ingredient')

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        ingredient_detail = representation.pop('ingredient')
        ingredient_detail['amount'] = representation['amount']
        return ingredient_detail


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientInRecipeSerializer(many=True, required=True)
    tags = TagSerializer(many=True, required=True)
    author = UsersSerializer(required=False)
    image = Base64ImageField(required=True)
    is_favorited = serializers.BooleanField(required=False, default=False)
    is_in_shopping_cart = serializers.BooleanField(required=False,
                                                   default=False)

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
        tag_ids = [tag['id'] for tag in value]
        if not len(set(tag_ids)) == len(tag_ids):
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
                  'text', 'cooking_time', 'is_favorited',
                  'is_in_shopping_cart')
        read_only_fields = ('author',)
        extra_kwargs = {
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True}
        }

    def create_ingredients(self, recipe, ingredients):
        ingredient_list = [
            IngredientRecipe(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(ingredient_list)

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags_list = validated_data.pop('tags')
        validated_data.pop('is_favorited')
        validated_data.pop('is_in_shopping_cart')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(recipe, ingredients)
        recipe.tags.set([tag['id'] for tag in tags_list])
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        if not {'ingredients', 'tags', 'name', 'image', 'text'}.issubset(
            validated_data
        ):
            raise serializers.ValidationError(
                'Необходимы все поля рецепта.'
            )
        ingredients = validated_data.pop('ingredients')
        tags_list = validated_data.pop('tags')
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if ingredients:
            IngredientRecipe.objects.filter(recipe=instance).delete()
            self.create_ingredients(instance, ingredients)
        if tags_list:
            instance.tags.set([tag['id'] for tag in tags_list])
        return instance


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
                queryset=FavoriteRecipes.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def to_representation(self, data):
        """На выход отдаем данные о рецептах в списке избранного"""

        return RecipeShortSerializer(
            self.context.get('recipe'),
            context={'request': self.context.get('request')}
        ).to_representation(self.context.get('recipe'))


class SubscriptionResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для объектов подписок"""

    recipes = serializers.SerializerMethodField('paginated_recipes')
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        if (
            self.context.get('request').user.is_authenticated
            and obj.followers.filter(
                user=self.context.get('request').user).exists()
        ):
            return True
        else:
            return False

    def get_recipes_count(self, obj):
        return obj.recipes.distinct().count()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count')
        read_only_fields = ('email', 'username', 'first_name', 'last_name',
                            'is_subscribed', 'recipes', 'recipes_count')

    def paginated_recipes(self, obj):
        page_size = (self.context['request'].query_params.get('recipes_limit')
                     or 10)
        paginator = Paginator(obj.recipes.all(), page_size)
        page = 1

        recipes = paginator.page(page)
        serializer = RecipeShortSerializer(recipes, many=True)

        return serializer.data


class SubscriptionRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для входных данных о подписках"""

    def validate_following(self, value):
        if value == self.initial_data['user']:
            raise serializers.ValidationError(
                'Подписка не может быть оформлена на самого себя.'
            )
        return value

    class Meta:
        model = Subscription
        fields = ('user', 'following')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=['user', 'following']
            )
        ]

    def to_representation(self, data):
        return SubscriptionResponseSerializer(
            self.context.get('following'),
            context={'request': self.context.get('request')}
        ).to_representation(self.context.get('following'))
