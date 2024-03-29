from django.db import IntegrityError
from rest_framework import status
from rest_framework.views import Response, exception_handler


def custom_exception_handler(exc, context):
    """
    Кастомный exception_handler

    Дополнительно к дефолтному exception_handler
    обрабатывает IntegrityError базы данных.
    """

    response = exception_handler(exc, context)

    if isinstance(exc, IntegrityError) and not response:
        response = Response(
            {
                'Database integrity error': exc.args
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    return response
