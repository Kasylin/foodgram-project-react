from django.db.models import Exists, F, OuterRef, Sum, Value
from django.http import FileResponse
from django.utils import timezone
from djoser.permissions import CurrentUserOrAdmin
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import (IsAdmin, IsAuthorOrReadOnly, IsCurrentUser,
                             IsCurrentUserOrReadOnly)
from api.renderers import TextShoppingCartRenderer
from api.serializers import (FavoriteRecipesSerializer, IngredientSerializer,
                             IngredientsShoppingCartSerializer,
                             RecipeSerializer, ShoppingCartSerializer,
                             SubscriptionRequestSerializer,
                             SubscriptionResponseSerializer, TagSerializer,
                             UserCreationSerializer, UsersSerializer)
from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart, Subscription, User


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class ManyToManyMixin:
    @action(detail=True,
            permission_classes=(IsCurrentUser | IsAdmin,),
            serializer_class=None,
            pagination_class=None
            )
    def add_to_many_to_many(self, request, object_model, field_name,
                            *args, **kwargs):
        try:
            instance = object_model.objects.get(
                pk=self.kwargs[self.lookup_field])
            serializer = self.get_serializer(
                data={'user': request.user.id,
                      field_name: instance.id},
                context={'request': request,
                         field_name: instance}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED,
                            headers=headers)
        except object_model.DoesNotExist as exc:
            return Response(*(exc.args),
                            status=status.HTTP_400_BAD_REQUEST)

    @add_to_many_to_many.mapping.delete
    def delete_from_many_to_many(self, request, model, object_model,
                                 field_name, *args, **kwargs):
        try:
            object_instance = object_model.objects.get(
                pk=self.kwargs[self.lookup_field])
            instance = model.objects.get(
                **{field_name: object_instance.id,
                   'user_id': self.request.user.id}
            )
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except object_model.DoesNotExist as exc:
            return Response(*(exc.args),
                            status=status.HTTP_404_NOT_FOUND)
        except model.DoesNotExist as exc:
            return Response(*(exc.args),
                            status=status.HTTP_400_BAD_REQUEST)


class RecipeViewSet(viewsets.ModelViewSet, ManyToManyMixin):
    permission_classes = (IsAuthorOrReadOnly | IsAdmin,)
    serializer_class = RecipeSerializer
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    filterset_class = RecipeFilter

    def get_queryset(self):
        if self.action == 'shopping_cart':
            return ShoppingCart.objects.all()
        elif self.action == 'favorite':
            return FavoriteRecipes.objects.all()

        queryset = Recipe.objects.prefetch_related(
            'tags', 'ingredients', 'is_fav', 'is_in_cart'
        )
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    FavoriteRecipes.objects.filter(recipe_id=OuterRef('id'),
                                                   user=self.request.user)),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(recipe_id=OuterRef('id'),
                                                user=self.request.user))
            )
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(['post'], detail=True,
            serializer_class=ShoppingCartSerializer,
            filterset_class=None
            )
    def shopping_cart(self, request, *args, **kwargs):
        """Кастомное действие над объектом рецепта: добавление в
        список покупок
        """
        return self.add_to_many_to_many(request, object_model=Recipe,
                                        field_name='recipe', *args, **kwargs)

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, *args, **kwargs):
        return self.delete_from_many_to_many(
            request, model=ShoppingCart,
            object_model=Recipe, field_name='recipe_id',
            *args, **kwargs
        )

    def get_shopping_cart_ingredients(self):
        """Создается queryset для скачиваемого списка покупок"""

        return IngredientRecipe.objects.filter(
            recipe__is_in_cart__user=self.request.user
        ).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(amount_sum=Sum('amount'))

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request, *args, **kwargs):
        shopping_cart_ingredients = self.get_shopping_cart_ingredients()

        now = timezone.now()
        file_name = (
            f'shopping_cart_{now:%Y-%m-%d_%H-%M-%S}.txt'
        )
        serializer = IngredientsShoppingCartSerializer(
            shopping_cart_ingredients, many=True)
        ret = TextShoppingCartRenderer.render(self=self, data=serializer.data)
        return FileResponse(
            ret, as_attachment=True, filename=file_name,
            headers={
                'Content-Disposition': f'attachment; filename="{file_name}"',
                'Content-Type': 'text/plain'
            }
        )

    @action(['post'], detail=True,
            permission_classes=(IsCurrentUser | IsAdmin,),
            serializer_class=FavoriteRecipesSerializer,
            pagination_class=None,
            filterset_class=None
            )
    def favorite(self, request, *args, **kwargs):
        """Кастомное действие над объектом рецепта: добавление в
        спискок избранного
        """
        return self.add_to_many_to_many(request, object_model=Recipe,
                                        field_name='recipe', *args, **kwargs)

    @favorite.mapping.delete
    def delete_from_favorites(self, request, *args, **kwargs):
        return self.delete_from_many_to_many(
            request, model=FavoriteRecipes,
            object_model=Recipe, field_name='recipe',
            *args, **kwargs)


class UsersViewSet(DjoserUserViewSet, ManyToManyMixin):
    """Вьюсет для объектов пользователей"""

    serializer_class = UsersSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsCurrentUserOrReadOnly | IsAdmin,)
    queryset = User.objects.all()

    def get_queryset(self):
        if self.request.method == 'GET':
            if self.request.user.is_authenticated:
                queryset = User.objects.prefetch_related('followers')
                queryset = queryset.annotate(
                    is_subscribed=Exists(
                        Subscription.objects.filter(
                            user_id=self.request.user,
                            following=OuterRef('id')
                        )
                    )
                ).order_by('id')
                if self.action == 'subscriptions':
                    return queryset.filter(is_subscribed=True)
                return queryset.distinct()
            else:
                queryset = User.objects.prefetch_related('followers')
                queryset = queryset.annotate(
                    is_subscribed=Value(False)
                ).order_by('id')
                return queryset.distinct()

        return User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreationSerializer
        return super().get_serializer_class()

    @action(['post'], detail=True,
            permission_classes=(IsCurrentUser | IsAdmin,),
            serializer_class=SubscriptionRequestSerializer,
            pagination_class=LimitOffsetPagination
            )
    def subscribe(self, request, *args, **kwargs):
        """Кастомное действие над объектом пользователя:
        создание или удаление подписки
        """
        return self.add_to_many_to_many(request, object_model=User,
                                        field_name='following',
                                        *args, **kwargs)

    @subscribe.mapping.delete
    def unsubscribe(self, request, *args, **kwargs):
        return self.delete_from_many_to_many(
            request, model=Subscription,
            object_model=User, field_name='following_id',
            *args, **kwargs)

    @action(["get"], detail=False,
            permission_classes=(CurrentUserOrAdmin,),
            serializer_class=SubscriptionResponseSerializer,
            pagination_class=LimitOffsetPagination
            )
    def subscriptions(self, request, *args, **kwargs):
        """Кастомное действие: вывести подписки пользователя

        Queryset переопределяется в методе get_queryset().
        """
        return super().list(request, *args, **kwargs)
