from django.db.models import Case, F, Sum, When
from django.http import Http404
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from api.permissions import IsAuthorOrAdminOrReadOnly, IsCurrentUserOrAdmin
from api.renderers import TextShoppingCartRenderer
from api.serializers import (FavoriteRecipesSerializer, IngredientSerializer,
                             IngredientsShoppingCartSerializer,
                             RecipeDetailSerializer, ShoppingCartSerializer,
                             TagSerializer)
from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для тегов"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов"""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None
    filter_backends = [filters.SearchFilter,]
    search_fields = ['^name']


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов"""

    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    serializer_class = RecipeDetailSerializer
    pagination_class = LimitOffsetPagination
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']

    def get_queryset(self):
        queryset = Recipe.objects.prefetch_related(
            'tags', 'ingredients', 'is_fav', 'is_in_cart'
        )
        if self.request.user.is_authenticated:
            queryset = queryset.alias(
                is_favorited=Case(
                    When(is_fav__user=self.request.user, then=1),
                    default=0,
                ),
                is_in_shopping_cart=Case(
                    When(is_in_cart__user=self.request.user, then=1),
                    default=0,
                ),
            )
        else:
            queryset = queryset.alias(
                is_favorited=Case(
                    default=0,
                ),
                is_in_shopping_cart=Case(
                    default=0,
                ),
            )

        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None:
            queryset = queryset.filter(is_favorited=is_favorited)
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        if is_in_shopping_cart is not None:
            queryset = queryset.filter(is_in_shopping_cart=is_in_shopping_cart)
        author = self.request.query_params.get('author')
        if author is not None:
            queryset = queryset.filter(author=author)
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def check_object_permissions(self, request, obj):
        """Проверка доступов к объектам

        Т.к. в разных действиях (actions) обрабатываются разные объекты,
        передаем на проверку соответствующие объекты:
        - для действий со списком покупок - объект ShoppingCart
        - для действий со списком избранного - объект FavoriteRecipes
        - дефолтный вариант для остальных действий - объект Recipe
        """
        if self.action == 'shopping_cart':
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user_id=request.user.id,
                    recipe_id=self.kwargs[self.lookup_field]
                )
                return super().check_object_permissions(request, shopping_cart)
            except ShoppingCart.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        elif self.action == 'favorite':
            try:
                favorite_recipes = FavoriteRecipes.objects.get(
                    user_id=request.user.id,
                    recipe_id=self.kwargs[self.lookup_field]
                )
                return super().check_object_permissions(request,
                                                        favorite_recipes)
            except FavoriteRecipes.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        return super().check_object_permissions(request, obj)

    @action(["post", "delete"], detail=True,
            permission_classes=[IsCurrentUserOrAdmin,],
            serializer_class=ShoppingCartSerializer,
            pagination_class=None
            )
    def shopping_cart(self, request, *args, **kwargs):
        """Кастомное действие над объектом рецепта: добавление или удаление из
        списка покупок
        """
        if self.request.method == 'POST':
            try:
                serializer = self.get_serializer(
                    data={'user': request.user.id,
                          'recipe': self.get_object().id},
                    context={'request': request,
                             'recipe': self.get_object()}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(user=self.request.user,
                                recipe=self.get_object())
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED,
                                headers=headers)
            except Http404 as exc:
                return Response(*(exc.args),
                                status=status.HTTP_400_BAD_REQUEST)
        if self.request.method == 'DELETE':
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user_id=self.request.user.id,
                    recipe_id=self.get_object().id
                )
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ShoppingCart.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)

    def get_shopping_cart_ingredients(self):
        """Создается queryset для скачиваемого списка покупок"""

        return IngredientRecipe.objects.filter(
            recipe__is_in_cart__user=self.request.user
        ).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(amount_sum=Sum('amount'))

    @action(detail=False, methods=["get"],
            renderer_classes=[TextShoppingCartRenderer,])
    def download_shopping_cart(self, request, *args, **kwargs):
        """Кастомное действие: скачать список покупок"""

        shopping_cart_ingredients = self.get_shopping_cart_ingredients()

        now = timezone.now()
        file_name = (
            f'shopping_cart_{now:%Y-%m-%d_%H-%M-%S}.'
            f'{request.accepted_renderer.format}'
        )
        serializer = IngredientsShoppingCartSerializer(
            shopping_cart_ingredients, many=True)
        return Response(
            serializer.data,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"'
            })

    @action(["post", "delete"], detail=True,
            permission_classes=[IsCurrentUserOrAdmin,],
            serializer_class=FavoriteRecipesSerializer,
            pagination_class=None
            )
    def favorite(self, request, *args, **kwargs):
        """Кастомное действие над объектом рецепта: добавление или удаление из
        списка избранного
        """
        if self.request.method == 'POST':
            try:
                serializer = self.get_serializer(
                    data={'user': request.user.id,
                          'recipe': self.get_object().id},
                    context={'request': request,
                             'recipe': self.get_object()}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(user=self.request.user,
                                recipe=self.get_object())
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED,
                                headers=headers)
            except Http404 as exc:
                return Response(*(exc.args),
                                status=status.HTTP_400_BAD_REQUEST)
        if self.request.method == 'DELETE':
            try:
                shopping_cart = FavoriteRecipes.objects.get(
                    user_id=self.request.user.id,
                    recipe_id=self.get_object().id
                )
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except FavoriteRecipes.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
