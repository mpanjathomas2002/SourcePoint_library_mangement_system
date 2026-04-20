"""
SourcePoint Management Command: seed_data
==========================================
Populates the database with realistic mock data for testing and demo purposes.

Usage:
    python manage.py seed_data

Creates:
    - 1 super admin
    - 5 admin accounts
    - 20 regular users
    - 8 book categories
    - 40 books across categories
    - 60 borrowing records
    - 80 ratings

All mock records have is_mock_data=True and can be cleared via:
    - Admin dashboard "Clear Mock Data" button
    - API: DELETE /api/v1/library/mock-data/ and DELETE /api/v1/auth/mock-data/
    - python manage.py clear_mock_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from slugify import slugify

from users.models import User, UserPreference
from library.models import Category, Book, Borrowing, Rating, BorrowSetting


CATEGORIES_DATA = [
    {'name': 'Computer Science', 'icon': '💻', 'color': '#3B82F6', 'description': 'Programming, algorithms, software engineering, and computing theory.'},
    {'name': 'Mathematics', 'icon': '📐', 'color': '#8B5CF6', 'description': 'Pure and applied mathematics, statistics, and mathematical logic.'},
    {'name': 'Literature & Fiction', 'icon': '📖', 'color': '#EC4899', 'description': 'Novels, short stories, poetry, and literary criticism.'},
    {'name': 'Science', 'icon': '🔬', 'color': '#10B981', 'description': 'Physics, chemistry, biology, and interdisciplinary sciences.'},
    {'name': 'History', 'icon': '🏛️', 'color': '#F59E0B', 'description': 'World history, biographies, and historical analysis.'},
    {'name': 'Business & Economics', 'icon': '📊', 'color': '#EF4444', 'description': 'Business strategy, economics, finance, and entrepreneurship.'},
    {'name': 'Philosophy', 'icon': '🧠', 'color': '#6366F1', 'description': 'Ethics, metaphysics, epistemology, and philosophical thought.'},
    {'name': 'Health & Medicine', 'icon': '⚕️', 'color': '#14B8A6', 'description': 'Medical science, health, nutrition, and wellness.'},
]

BOOKS_DATA = [
    # Computer Science
    {'title': 'Clean Code: A Handbook of Agile Software Craftsmanship', 'author': 'Robert C. Martin', 'category': 'Computer Science', 'year': 2008, 'pages': 431, 'type': 'textbook', 'description': 'A seminal guide to writing maintainable, readable, and efficient code. Martin shares his experience and best practices for software craftsmanship.'},
    {'title': 'The Pragmatic Programmer', 'author': 'David Thomas & Andrew Hunt', 'category': 'Computer Science', 'year': 2019, 'pages': 352, 'type': 'textbook', 'description': 'From journeyman to master - practical wisdom for programmers at every level.'},
    {'title': 'Introduction to Algorithms', 'author': 'Cormen, Leiserson, Rivest & Stein', 'category': 'Computer Science', 'year': 2009, 'pages': 1292, 'type': 'textbook', 'description': 'The authoritative reference on algorithms, used in universities worldwide. Covers sorting, graph algorithms, dynamic programming, and more.'},
    {'title': 'Designing Data-Intensive Applications', 'author': 'Martin Kleppmann', 'category': 'Computer Science', 'year': 2017, 'pages': 616, 'type': 'textbook', 'description': 'The big ideas behind reliable, scalable, and maintainable systems. A must-read for backend engineers.'},
    {'title': 'Python Crash Course', 'author': 'Eric Matthes', 'category': 'Computer Science', 'year': 2023, 'pages': 544, 'type': 'textbook', 'description': 'A hands-on, project-based introduction to programming with Python. Perfect for beginners.'},
    # Mathematics
    {'title': 'Calculus: Early Transcendentals', 'author': 'James Stewart', 'category': 'Mathematics', 'year': 2020, 'pages': 1392, 'type': 'textbook', 'description': 'The gold standard textbook for calculus, covering limits, derivatives, integrals, and series.'},
    {'title': 'The Art of Problem Solving Vol. 1', 'author': 'Sandor Lehoczky & Richard Rusczyk', 'category': 'Mathematics', 'year': 2006, 'pages': 272, 'type': 'textbook', 'description': 'An introduction to mathematical competition problem solving techniques.'},
    {'title': 'Gödel, Escher, Bach: An Eternal Golden Braid', 'author': 'Douglas Hofstadter', 'category': 'Mathematics', 'year': 1979, 'pages': 777, 'type': 'book', 'description': 'A Pulitzer Prize-winning book exploring loops, strange attractors, and self-reference in mathematics, art, and music.'},
    # Literature
    {'title': 'Things Fall Apart', 'author': 'Chinua Achebe', 'category': 'Literature & Fiction', 'year': 1958, 'pages': 209, 'type': 'book', 'description': 'A masterpiece of African literature depicting the life of Okonkwo in pre-colonial Nigeria and the devastating impact of colonialism.'},
    {'title': 'Season of Migration to the North', 'author': 'Tayeb Salih', 'category': 'Literature & Fiction', 'year': 1966, 'pages': 139, 'type': 'book', 'description': 'One of the most important Arabic novels, exploring identity, colonialism, and cultural clash through a Sudanese narrator.'},
    {'title': 'Purple Hibiscus', 'author': 'Chimamanda Ngozi Adichie', 'category': 'Literature & Fiction', 'year': 2003, 'pages': 307, 'type': 'book', 'description': 'A coming-of-age story set in Nigeria, exploring religious fanaticism, family dynamics, and freedom.'},
    {'title': '1984', 'author': 'George Orwell', 'category': 'Literature & Fiction', 'year': 1949, 'pages': 328, 'type': 'book', 'description': 'A dystopian masterpiece about totalitarianism, surveillance, and the destruction of truth.'},
    {'title': 'Half of a Yellow Sun', 'author': 'Chimamanda Ngozi Adichie', 'category': 'Literature & Fiction', 'year': 2006, 'pages': 433, 'type': 'book', 'description': 'A richly drawn story of the Nigerian Civil War (Biafran War) told through the eyes of three characters.'},
    # Science
    {'title': 'A Brief History of Time', 'author': 'Stephen Hawking', 'category': 'Science', 'year': 1988, 'pages': 212, 'type': 'book', 'description': 'Hawking\'s landmark exploration of cosmology, black holes, the Big Bang, and the nature of time. Accessible to non-scientists.'},
    {'title': 'The Selfish Gene', 'author': 'Richard Dawkins', 'category': 'Science', 'year': 1976, 'pages': 360, 'type': 'book', 'description': 'A revolutionary view of evolution from the gene\'s perspective, introducing the concept of the meme.'},
    {'title': 'Sapiens: A Brief History of Humankind', 'author': 'Yuval Noah Harari', 'category': 'Science', 'year': 2011, 'pages': 443, 'type': 'book', 'description': 'A sweeping narrative of human history from the Stone Age through the 21st century.'},
    {'title': 'The Double Helix', 'author': 'James D. Watson', 'category': 'Science', 'year': 1968, 'pages': 226, 'type': 'book', 'description': 'A personal account of the discovery of the structure of DNA.'},
    # History
    {'title': 'The Story of Africa', 'author': 'Basil Davidson', 'category': 'History', 'year': 1984, 'pages': 424, 'type': 'book', 'description': 'A comprehensive history of the African continent from earliest times to the modern era.'},
    {'title': 'Long Walk to Freedom', 'author': 'Nelson Mandela', 'category': 'History', 'year': 1994, 'pages': 656, 'type': 'book', 'description': 'The autobiography of Nelson Mandela, from childhood in rural South Africa to his 27 years in prison and beyond.'},
    {'title': 'Guns, Germs, and Steel', 'author': 'Jared Diamond', 'category': 'History', 'year': 1997, 'pages': 480, 'type': 'book', 'description': 'A Pulitzer Prize winner examining why some civilizations came to dominate others.'},
    {'title': 'The Scramble for Africa', 'author': 'Thomas Pakenham', 'category': 'History', 'year': 1991, 'pages': 738, 'type': 'book', 'description': 'The definitive account of how seven European nations seized 30 territories in just 30 years.'},
    # Business
    {'title': 'The Lean Startup', 'author': 'Eric Ries', 'category': 'Business & Economics', 'year': 2011, 'pages': 336, 'type': 'book', 'description': 'How today\'s entrepreneurs use continuous innovation to create radically successful businesses.'},
    {'title': 'Good to Great', 'author': 'Jim Collins', 'category': 'Business & Economics', 'year': 2001, 'pages': 320, 'type': 'book', 'description': 'Why some companies make the leap to greatness and others don\'t. Based on a five-year research project.'},
    {'title': 'Thinking, Fast and Slow', 'author': 'Daniel Kahneman', 'category': 'Business & Economics', 'year': 2011, 'pages': 499, 'type': 'book', 'description': 'A groundbreaking exploration of the two systems that drive the way we think.'},
    {'title': 'Zero to One', 'author': 'Peter Thiel', 'category': 'Business & Economics', 'year': 2014, 'pages': 224, 'type': 'book', 'description': 'Notes on startups, or how to build the future. Thiel shares unconventional views on innovation.'},
    # Philosophy
    {'title': 'Meditations', 'author': 'Marcus Aurelius', 'category': 'Philosophy', 'year': 180, 'pages': 254, 'type': 'book', 'description': 'The private journals of one of Rome\'s greatest emperors, offering timeless Stoic wisdom.'},
    {'title': 'The Republic', 'author': 'Plato', 'category': 'Philosophy', 'year': -380, 'pages': 416, 'type': 'book', 'description': 'Plato\'s masterwork on justice, beauty, equality, politics, and the ideal state.'},
    {'title': 'Beyond Good and Evil', 'author': 'Friedrich Nietzsche', 'category': 'Philosophy', 'year': 1886, 'pages': 240, 'type': 'book', 'description': 'Nietzsche\'s critique of past philosophers and exploration of ideas that would shape modern thought.'},
    # Health & Medicine
    {'title': 'The Body: A Guide for Occupants', 'author': 'Bill Bryson', 'category': 'Health & Medicine', 'year': 2019, 'pages': 464, 'type': 'book', 'description': 'A fascinating tour of the human body, covering every organ and system with wit and wonder.'},
    {'title': 'Why We Sleep', 'author': 'Matthew Walker', 'category': 'Health & Medicine', 'year': 2017, 'pages': 368, 'type': 'book', 'description': 'Unlocking the power of sleep and dreams. A scientific exploration of sleep\'s vital role in our lives.'},
]


class Command(BaseCommand):
    help = 'Seed the database with mock data for testing. All records are tagged with is_mock_data=True.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('🌱 Seeding SourcePoint with mock data...'))

        # Initialize borrow settings
        settings, _ = BorrowSetting.objects.get_or_create(pk=1)
        settings.default_max_days = 30
        settings.max_concurrent_borrows = 5
        settings.save()
        self.stdout.write('  ✓ Borrow settings initialized')

        # Create super admin (not marked as mock data)
        superadmin, created = User.objects.get_or_create(
            email='superadmin@sourcepoint.lib',
            defaults={
                'first_name': 'Library',
                'last_name': 'Director',
                'role': 'superadmin',
                'is_staff': True,
                'is_superuser': True,
                'is_mock_data': False,
            }
        )
        if created:
            superadmin.set_password('SuperAdmin@2024')
            superadmin.save()
            UserPreference.objects.get_or_create(user=superadmin)
            self.stdout.write(f'  ✓ Super admin: superadmin@sourcepoint.lib / SuperAdmin@2024')

        # Create 5 admin accounts
        admin_data = [
            ('Alice', 'Nakamura', 'alice.admin@sourcepoint.lib'),
            ('Brian', 'Odhiambo', 'brian.admin@sourcepoint.lib'),
            ('Carmen', 'Diallo', 'carmen.admin@sourcepoint.lib'),
            ('David', 'Mensah', 'david.admin@sourcepoint.lib'),
            ('Elena', 'Kamau', 'elena.admin@sourcepoint.lib'),
        ]

        admins = []
        for first, last, email in admin_data:
            admin, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': 'admin',
                    'is_staff': True,
                    'is_mock_data': True,
                }
            )
            if created:
                admin.set_password('Admin@2024')
                admin.save()
                UserPreference.objects.get_or_create(user=admin)
            admins.append(admin)

        self.stdout.write(f'  ✓ 5 admin accounts created (password: Admin@2024)')

        # Create 20 regular users
        user_names = [
            ('James', 'Okonkwo'), ('Amara', 'Nwosu'), ('Samuel', 'Mutua'),
            ('Grace', 'Atieno'), ('Michael', 'Asante'), ('Fatima', 'Bello'),
            ('Daniel', 'Nkrumah'), ('Aisha', 'Mohammed'), ('Peter', 'Waweru'),
            ('Olivia', 'Adeyemi'), ('Kevin', 'Osei'), ('Blessing', 'Eze'),
            ('Patrick', 'Mwangi'), ('Naomi', 'Abubakar'), ('Emmanuel', 'Boateng'),
            ('Sarah', 'Okeke'), ('Joshua', 'Dlamini'), ('Ruth', 'Banda'),
            ('Victor', 'Onyekachi'), ('Mary', 'Kimani'),
        ]

        users = []
        for i, (first, last) in enumerate(user_names):
            email = f"{first.lower()}.{last.lower()}@mail.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': 'user',
                    'is_mock_data': True,
                }
            )
            if created:
                user.set_password('User@2024')
                user.save()
                UserPreference.objects.get_or_create(user=user)
            users.append(user)

        self.stdout.write(f'  ✓ 20 regular users created (password: User@2024)')

        # Create categories
        category_objects = {}
        for cat_data in CATEGORIES_DATA:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'description': cat_data['description'],
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                    'is_mock_data': True,
                    'created_by': superadmin,
                }
            )
            category_objects[cat_data['name']] = cat

        self.stdout.write(f'  ✓ {len(CATEGORIES_DATA)} categories created')

        # Create books
        books = []
        for i, book_data in enumerate(BOOKS_DATA):
            slug = slugify(book_data['title'])
            # Ensure unique slugs
            base_slug = slug
            counter = 1
            while Book.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            book, created = Book.objects.get_or_create(
                title=book_data['title'],
                defaults={
                    'slug': slug,
                    'author': book_data['author'],
                    'publication_year': book_data['year'],
                    'pages': book_data['pages'],
                    'material_type': book_data['type'],
                    'description': book_data['description'],
                    'total_copies': random.randint(3, 10),
                    'available_copies': random.randint(1, 3),
                    'is_available': True,
                    'is_featured': i < 6,  # First 6 books are featured
                    'is_mock_data': True,
                    'added_by': admins[i % len(admins)],
                    'cover_image_url': f"https://picsum.photos/seed/book{i+1}/200/300",
                }
            )

            # Assign category
            category = category_objects.get(book_data['category'])
            if category:
                book.categories.add(category)

            books.append(book)

        self.stdout.write(f'  ✓ {len(BOOKS_DATA)} books added to catalog')

        # Create borrowing records
        borrowing_count = 0
        for user in users[:15]:  # First 15 users have borrowings
            num_borrows = random.randint(1, 4)
            selected_books = random.sample(books, min(num_borrows, len(books)))

            for j, book in enumerate(selected_books):
                # Vary statuses: some active, some returned
                days_ago = random.randint(1, 45)
                borrowed_at = timezone.now() - timedelta(days=days_ago)
                requested_days = random.choice([7, 14, 21, 30])
                due_date = borrowed_at + timedelta(days=requested_days)

                if days_ago > requested_days:
                    borrow_status = 'returned'
                    returned_at = due_date - timedelta(days=random.randint(-2, 3))
                else:
                    borrow_status = 'active'
                    returned_at = None

                borrowing, created = Borrowing.objects.get_or_create(
                    user=user,
                    book=book,
                    status=borrow_status,
                    defaults={
                        'borrowed_at': borrowed_at,
                        'due_date': due_date,
                        'returned_at': returned_at,
                        'requested_days': requested_days,
                        'is_mock_data': True,
                    }
                )
                if created:
                    borrowing_count += 1

        self.stdout.write(f'  ✓ {borrowing_count} borrowing records created')

        # Create ratings
        rating_count = 0
        for user in users:
            num_ratings = random.randint(2, 6)
            rated_books = random.sample(books, min(num_ratings, len(books)))

            for book in rated_books:
                score = random.choices([3, 4, 4, 5, 5, 5], k=1)[0]  # Bias toward higher ratings
                reviews = [
                    "Excellent book, highly recommend!",
                    "Very informative and well-written.",
                    "A good read for anyone interested in this topic.",
                    "Life-changing perspective. Must read.",
                    "Clear explanations and great examples.",
                    "Thoroughly enjoyed this. Will read again.",
                    "",  # Some ratings without reviews
                    "",
                ]
                rating, created = Rating.objects.get_or_create(
                    user=user,
                    book=book,
                    defaults={
                        'score': score,
                        'review': random.choice(reviews),
                        'is_mock_data': True,
                    }
                )
                if created:
                    rating_count += 1

        # Update all book ratings
        for book in books:
            book.update_rating()

        self.stdout.write(f'  ✓ {rating_count} ratings added')

        self.stdout.write(self.style.SUCCESS('\n✅ Mock data seeded successfully!\n'))
        self.stdout.write(self.style.WARNING('Login credentials:'))
        self.stdout.write('  Super Admin: superadmin@sourcepoint.lib / SuperAdmin@2024')
        self.stdout.write('  Any Admin:   alice.admin@sourcepoint.lib / Admin@2024')
        self.stdout.write('  Any User:    james.okonkwo@mail.com / User@2024')
        self.stdout.write(self.style.WARNING('\nTo clear mock data: python manage.py clear_mock_data'))
