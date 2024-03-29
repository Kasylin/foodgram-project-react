import re

from django.core.paginator import Paginator
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

from recipes.models import Recipe
from users.models import Subscription, User


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


class RecipeSubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для кратких сведений о рецептах"""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


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
        serializer = RecipeSubscriptionSerializer(recipes, many=True)

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
            self.context.get('subscription'),
            context={'request': self.context.get('request')}
        ).to_representation(self.context.get('subscription'))
