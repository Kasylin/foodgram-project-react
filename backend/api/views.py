from django.db.models import Exists, F, OuterRef, Sum, Value
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAdmin, IsAuthorOrReadOnly, IsCurrentUser
from api.renderers import TextShoppingCartRenderer
from api.serializers import (FavoriteRecipesSerializer, IngredientSerializer,
                             IngredientsShoppingCartSerializer,
                             RecipeDetailSerializer, ShoppingCartSerializer,
                             TagSerializer)
from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
from users.models import FavoriteRecipes, ShoppingCart


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


class ManyToManyMixin():
    @action(detail=True,
            permission_classes=(IsCurrentUser | IsAdmin,),
            serializer_class=None,
            pagination_class=None,
            filterset_class=None
            )
    def add_to_many_to_many(self, request, *args, **kwargs):
        try:
            recipe = Recipe.objects.get(pk=self.kwargs[self.lookup_field])
            serializer = self.get_serializer(
                data={'user': request.user.id,
                      'recipe': recipe.id},
                context={'request': request,
                         'recipe': recipe}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=self.request.user,
                            recipe=recipe)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED,
                            headers=headers)
        except Recipe.DoesNotExist as exc:
            return Response(*(exc.args),
                            status=status.HTTP_400_BAD_REQUEST)
        except Http404 as exc:
            return Response(*(exc.args),
                            status=status.HTTP_400_BAD_REQUEST)

    @add_to_many_to_many.mapping.delete
    def delete_from_many_to_many(self, request, model, *args, **kwargs):
        try:
            recipe = Recipe.objects.get(pk=self.kwargs[self.lookup_field])
            shopping_cart = model.objects.get(
                user_id=self.request.user.id,
                recipe_id=recipe.id
            )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Recipe.DoesNotExist as exc:
            return Response(*(exc.args),
                            status=status.HTTP_404_NOT_FOUND)
        except model.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RecipeViewSet(viewsets.ModelViewSet, ManyToManyMixin):
    permission_classes = (IsAuthorOrReadOnly | IsAdmin,)
    serializer_class = RecipeDetailSerializer
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
        else:
            queryset = queryset.annotate(
                is_favorited=Value(0),
                is_in_shopping_cart=Value(0),
            )
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(['post'], detail=True,
            serializer_class=ShoppingCartSerializer
            )
    def shopping_cart(self, request, *args, **kwargs):
        """Кастомное действие над объектом рецепта: добавление в
        список покупок
        """
        return self.add_to_many_to_many(request, *args, **kwargs)

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, *args, **kwargs):
        return self.delete_from_many_to_many(request, model=ShoppingCart,
                                             *args, **kwargs)

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
                'content_type': 'text/plain'
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
        return self.add_to_many_to_many(request, *args, **kwargs)

    @favorite.mapping.delete
    def delete_from_favorites(self, request, *args, **kwargs):
        return self.delete_from_many_to_many(request, model=FavoriteRecipes,
                                             *args, **kwargs)
