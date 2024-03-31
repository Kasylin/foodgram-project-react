from rest_framework import permissions

from users.models import User


class IsAuthorOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Доступы к объектам рецептов."""

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )


class IsCurrentUserOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Доступы к объектам пользователей."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if isinstance(obj, User) and obj == user:
            return True
        return request.method in permissions.SAFE_METHODS


class IsCurrentUser(permissions.IsAuthenticated):
    """Доступы к many-to-many моделям."""

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.user == request.user
        )


class IsAdmin(permissions.IsAdminUser):

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_staff
