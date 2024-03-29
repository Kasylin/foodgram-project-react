from csv import DictReader

from django.core.management import BaseCommand

# Import the model
from recipes.models import Tag

ALREDY_LOADED_ERROR_MESSAGE = """
If you need to reload the child data from the CSV file,
first delete the db.sqlite3 file to destroy the database.
Then, run `python manage.py migrate` for a new empty
database with tables"""


class Command(BaseCommand):
    """Кастомная команда для загрузки данных из CSV-файлов в БД"""
    help = "Loads data from tags.csv"

    def handle(self, *args, **options):
        if Tag.objects.exists():
            print('category data already loaded...exiting.')
            print(ALREDY_LOADED_ERROR_MESSAGE)
            return
        print("Loading tag data")
        for row in DictReader(open('../data/tags.csv', encoding='utf-8')):
            ingredient = Tag(name=row['name'],
                             color=row['color'],
                             slug=row['slug'])
            ingredient.save()
