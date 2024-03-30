from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """Кастомная пагинация с номером и длиной страницы"""
    page_size_query_param = 'limit'
