from django.db.models import Case, When
from djoser.permissions import CurrentUserOrAdmin
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from api.permissions import IsAdmin, IsCurrentUser, IsCurrentUserOrReadOnly
from users.models import Subscription, User
from users.serializers import (SubscriptionRequestSerializer,
                               SubscriptionResponseSerializer,
                               UserCreationSerializer, UsersSerializer)


class UsersViewSet(DjoserUserViewSet):
    """Вьюсет для объектов пользователей"""

    serializer_class = UsersSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsCurrentUserOrReadOnly | IsAdmin,)
    queryset = User.objects.all()

    def get_queryset(self):
        if self.request.method == 'GET':
            if self.request.user.is_authenticated:
                queryset = User.objects.prefetch_related('followers')
                queryset = queryset.alias(
                    is_subscribed=Case(
                        When(followers__user=self.request.user, then=True),
                        default=False,
                    )
                ).order_by('id')
                if self.action == 'subscriptions':
                    return queryset.filter(is_subscribed=True)
                return queryset.distinct()
            else:
                queryset = User.objects.prefetch_related('followers')
                queryset = queryset.alias(
                    is_subscribed=Case(
                        default=False,
                    )
                ).order_by('id')
                return queryset.distinct()

        return User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreationSerializer
        return super().get_serializer_class()

    def check_object_permissions(self, request, obj):
        """Проверка доступов к объектам

        Т.к. в разных действиях (actions) обрабатываются разные объекты,
        передаем на проверку соответствующие объекты:
        - для действий с подписками - объект Subscription
        - дефолтный вариант для остальных действий - объект User
        """
        if self.action == 'subscribe':
            try:
                subscription = Subscription.objects.get(
                    user_id=request.user.id,
                    following_id=self.kwargs[self.lookup_field]
                )
                return super().check_object_permissions(request, subscription)
            except Subscription.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        return super().check_object_permissions(request, obj)

    @action(["get", "put", "patch", "delete"], detail=False,
            permission_classes=(CurrentUserOrAdmin,))
    def me(self, request, *args, **kwargs):
        """Переопределяем доступы для действия /me"""
        return super().me(request, *args, **kwargs)

    @action(["post", "delete"], detail=True,
            permission_classes=(IsCurrentUser | IsAdmin,),
            serializer_class=SubscriptionRequestSerializer,
            pagination_class=LimitOffsetPagination
            )
    def subscribe(self, request, *args, **kwargs):
        """Кастомное действие над объектом пользователя:
        создание или удаление подписки
        """
        if self.request.method == 'POST':
            serializer = self.get_serializer(
                data={'user': request.user.id,
                      'following': self.get_object().id},
                context={'request': request,
                         'subscription': self.get_object()})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=self.request.user,
                            following=self.get_object())
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)
        if self.request.method == 'DELETE':
            try:
                subscription = Subscription.objects.get(
                    user_id=self.request.user.id,
                    following_id=self.get_object().id
                )
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Subscription.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)

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
