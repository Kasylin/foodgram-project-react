import io

from rest_framework import renderers


class TextShoppingCartRenderer(renderers.BaseRenderer):
    """Создание текстового файла со списком покупок."""

    media_type = "text/plain"
    format = "txt"

    def render(self, data, accepted_media_type=None, renderer_context=None):

        text_buffer = io.StringIO()

        for ingredient_data in data:
            shopping_cart_string = (
                f'{ingredient_data["name"]} '
                f'({ingredient_data["measurement_unit"]})'
                f' — {ingredient_data["amount_sum"]}'
            )
            text_buffer.write(shopping_cart_string + '\n')

        return text_buffer.getvalue()
