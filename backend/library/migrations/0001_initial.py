"""
Auto-generated initial migration for SourcePoint Library app.
Run: python manage.py migrate
"""
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BorrowSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default_max_days', models.IntegerField(default=30, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(365)])),
                ('grace_period_days', models.IntegerField(default=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)])),
                ('max_concurrent_borrows', models.IntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'sp_borrow_settings'},
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(blank=True, max_length=50)),
                ('color', models.CharField(default='#4F46E5', max_length=7)),
                ('is_mock_data', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_categories', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'sp_categories', 'verbose_name_plural': 'Categories', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(db_index=True, max_length=300)),
                ('slug', models.SlugField(max_length=300, unique=True)),
                ('author', models.CharField(max_length=200)),
                ('isbn', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('publisher', models.CharField(blank=True, max_length=200)),
                ('publication_year', models.IntegerField(blank=True, null=True)),
                ('language', models.CharField(default='English', max_length=50)),
                ('pages', models.IntegerField(blank=True, null=True)),
                ('material_type', models.CharField(choices=[('book', 'Book'), ('textbook', 'Textbook'), ('journal', 'Academic Journal'), ('magazine', 'Magazine'), ('research_paper', 'Research Paper'), ('ebook', 'E-Book')], default='book', max_length=30)),
                ('description', models.TextField(blank=True)),
                ('summary', models.TextField(blank=True)),
                ('cover_image', models.ImageField(blank=True, help_text='Upload cover image from device', null=True, upload_to='covers/')),
                ('cover_image_url', models.URLField(blank=True)),
                ('book_file', models.FileField(blank=True, help_text='Upload PDF/ebook file directly from device', null=True, upload_to='books/')),
                ('file_url', models.URLField(blank=True)),
                ('file_type', models.CharField(blank=True, max_length=20)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('is_available', models.BooleanField(db_index=True, default=True)),
                ('total_copies', models.IntegerField(default=1)),
                ('available_copies', models.IntegerField(default=1)),
                ('max_borrow_days', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(365)])),
                ('borrow_count', models.IntegerField(default=0)),
                ('view_count', models.IntegerField(default=0)),
                ('average_rating', models.FloatField(default=0.0)),
                ('rating_count', models.IntegerField(default=0)),
                ('is_mock_data', models.BooleanField(default=False)),
                ('is_featured', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('categories', models.ManyToManyField(blank=True, related_name='books', to='library.category')),
                ('added_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_books', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'sp_books', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Borrowing',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('borrowed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('due_date', models.DateTimeField()),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
                ('requested_days', models.IntegerField(default=14, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(365)])),
                ('status', models.CharField(choices=[('active', 'Active'), ('returned', 'Returned'), ('overdue', 'Overdue')], default='active', max_length=20)),
                ('due_reminder_sent', models.BooleanField(default=False)),
                ('is_mock_data', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='borrowings', to='library.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='borrowings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'sp_borrowings', 'ordering': ['-borrowed_at']},
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('score', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('review', models.TextField(blank=True, max_length=1000)),
                ('is_mock_data', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='library.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'sp_ratings', 'ordering': ['-created_at'], 'unique_together': {('user', 'book')}},
        ),
        migrations.AddConstraint(
            model_name='borrowing',
            constraint=models.UniqueConstraint(condition=models.Q(status='active'), fields=['user', 'book'], name='unique_active_borrowing'),
        ),
    ]
