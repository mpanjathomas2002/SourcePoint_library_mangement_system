"""
Management Command: clear_mock_data
Removes all seeded/mock data from the database.
"""
from django.core.management.base import BaseCommand
from users.models import User
from library.models import Category, Book, Borrowing, Rating


class Command(BaseCommand):
    help = 'Remove all mock/seed data from the database (records with is_mock_data=True).'

    def handle(self, *args, **options):
        self.stdout.write('🧹 Clearing mock data...')

        r = Rating.objects.filter(is_mock_data=True).delete()[0]
        b = Borrowing.objects.filter(is_mock_data=True).delete()[0]
        bk = Book.objects.filter(is_mock_data=True).delete()[0]
        c = Category.objects.filter(is_mock_data=True).delete()[0]
        u = User.objects.filter(is_mock_data=True).delete()[0]

        self.stdout.write(self.style.SUCCESS(
            f'✅ Cleared: {u} users, {bk} books, {c} categories, {b} borrowings, {r} ratings'
        ))
