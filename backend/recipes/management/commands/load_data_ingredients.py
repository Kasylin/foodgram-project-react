from csv import DictReader

from django.core.management import BaseCommand

# Import the model
from recipes.models import Ingredient

ALREDY_LOADED_ERROR_MESSAGE = """
If you need to reload the child data from the CSV file,
first delete the db.sqlite3 file to destroy the database.
Then, run `python manage.py migrate` for a new empty
database with tables"""


class Command(BaseCommand):
    """Кастомная команда для загрузки данных из CSV-файлов в БД"""
    help = "Loads data from ingredients.csv"

    def handle(self, *args, **options):
        if Ingredient.objects.exists():
            print('category data already loaded...exiting.')
            print(ALREDY_LOADED_ERROR_MESSAGE)
            return
        print("Loading ingredient data")
        for row in DictReader(open('../data/ingredients.csv', encoding='utf-8')):
            ingredient = Ingredient(name=row['name'],
                                    measurement_unit=row['measurement_unit'])
            ingredient.save()
