from django.core.management.base import BaseCommand
from src.Data_base.database import init_db


class Command(BaseCommand):
    help = 'Create missing security tables and apply additive ecommerce schema updates.'

    def handle(self, *args, **options):
        init_db()
        self.stdout.write(self.style.SUCCESS('Database schema is ready.'))
