from django.urls import include, path
from rest_framework import routers

from api.views import IngredientViewSet, RecipeViewSet, TagViewSet
from users.views import UsersViewSet

router_v1 = routers.DefaultRouter()
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredient')
router_v1.register(r'tags', TagViewSet, basename='tag')
router_v1.register(r'recipes', RecipeViewSet, basename='recipe')
router_v1.register(
    r'users', UsersViewSet, basename='users'
)

urlpatterns_v1 = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls)),
]

urlpatterns = [
    path('', include(urlpatterns_v1))
]
