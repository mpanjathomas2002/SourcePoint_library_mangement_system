"""
SourcePoint Library - Models
==============================
Core library data models.

Models:
    Category       - Book categories (e.g., Fiction, Science, History)
    Book           - Books and educational materials
    BorrowSetting  - Admin-configurable borrow period settings
    Borrowing      - Records of books borrowed by users
    Rating         - User ratings and reviews for books
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta


class Category(models.Model):
    """
    Book categories/genres for organizing the library.
    Admins can create, edit, and delete categories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="CSS icon class or emoji")
    color = models.CharField(max_length=7, default='#4F46E5', help_text="Hex color for UI display")

    # Track which admin created this category
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_categories'
    )

    is_mock_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sp_categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def book_count(self):
        return self.books.filter(is_available=True).count()


class Book(models.Model):
    """
    Represents a book or educational study material in the library.
    Books can be borrowed (virtually) by users.
    """

    MATERIAL_TYPES = [
        ('book', 'Book'),
        ('textbook', 'Textbook'),
        ('journal', 'Academic Journal'),
        ('magazine', 'Magazine'),
        ('research_paper', 'Research Paper'),
        ('ebook', 'E-Book'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Book metadata
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, blank=True, unique=True, null=True)
    publisher = models.CharField(max_length=200, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default='English')
    pages = models.IntegerField(null=True, blank=True)
    material_type = models.CharField(max_length=30, choices=MATERIAL_TYPES, default='book')

    # Content and description
    description = models.TextField(blank=True)
    summary = models.TextField(blank=True, help_text="AI-generated or admin-written summary")
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True, help_text='Upload cover image from device')
    cover_image_url = models.URLField(blank=True, help_text="External URL for cover image")

    # Categorization
    categories = models.ManyToManyField(Category, related_name='books', blank=True)
    tags = models.JSONField(default=list, blank=True, help_text="List of searchable tags")

    # Availability and borrow settings
    is_available = models.BooleanField(default=True, db_index=True)
    total_copies = models.IntegerField(default=1, help_text="Physical or virtual copy count")
    available_copies = models.IntegerField(default=1)

    # Admin-set maximum borrow period for this specific book (in days)
    # If null, uses the system default from BorrowSetting
    max_borrow_days = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Override system default borrow period for this book"
    )

    # File/digital content — admins upload locally, saved to Supabase storage or media/
    file_url = models.URLField(blank=True, help_text="URL to digital content (PDF, ebook, etc.)")
    book_file = models.FileField(
        upload_to='books/', null=True, blank=True,
        help_text="Upload PDF/ebook file directly from device"
    )
    file_type = models.CharField(max_length=20, blank=True, help_text="pdf, epub, etc.")

    # Statistics
    borrow_count = models.IntegerField(default=0, help_text="Total times borrowed")
    view_count = models.IntegerField(default=0)

    # Average rating (denormalized for performance)
    average_rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)

    # Admin tracking
    added_by = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='added_books'
    )
    is_mock_data = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show on homepage")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sp_books'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title', 'author']),
            models.Index(fields=['is_available', 'is_featured']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def get_cover_url(self, request=None):
        """
        Return the URL for displaying the cover image.
        Always returns a Django proxy URL (/api/v1/library/books/<id>/cover/)
        so Supabase bucket permissions never matter.
        Falls back to direct URL only if no proxy is needed.
        """
        has_cover = (
            (self.cover_image_url and self.cover_image_url != '') or
            bool(self.cover_image)
        )
        if has_cover:
            # Always use the proxy endpoint — works regardless of Supabase bucket settings
            base = '/api/v1'
            if request:
                base = request.build_absolute_uri('/api/v1').rstrip('/')
            return f"{base}/library/books/{self.id}/cover/"
        return ''

    def get_book_file_url(self, request=None):
        """Return the URL for reading the book file (PDF etc.)."""
        if self.file_url:
            return self.file_url
        if self.book_file:
            try:
                url = self.book_file.url
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                pass
        return ''


    def update_rating(self):
        """Recalculate and save average rating from all ratings."""
        ratings = self.ratings.all()
        count = ratings.count()
        if count > 0:
            avg = sum(r.score for r in ratings) / count
            self.average_rating = round(avg, 1)
            self.rating_count = count
        else:
            self.average_rating = 0.0
            self.rating_count = 0
        self.save(update_fields=['average_rating', 'rating_count'])

    def get_effective_max_borrow_days(self):
        """Return this book's borrow limit or fall back to system default."""
        if self.max_borrow_days:
            return self.max_borrow_days
        try:
            setting = BorrowSetting.objects.first()
            return setting.default_max_days if setting else 30
        except BorrowSetting.DoesNotExist:
            return 30


class BorrowSetting(models.Model):
    """
    System-wide borrowing configuration set by admins.
    Only one instance exists (singleton pattern).
    Admins can override per-book in the Book model.
    """
    # Default maximum borrow period (users can set less, but not more)
    default_max_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Maximum days a book can be borrowed system-wide"
    )

    # Grace period after due date before marking as overdue
    grace_period_days = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(30)]
    )

    # Maximum number of books a user can borrow at once
    max_concurrent_borrows = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )

    updated_by = models.ForeignKey(
        'users.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='updated_settings'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sp_borrow_settings'

    def __str__(self):
        return f"Borrow Settings (max {self.default_max_days} days)"

    def save(self, *args, **kwargs):
        """Enforce singleton - only one BorrowSetting record."""
        self.pk = 1
        super().save(*args, **kwargs)


class Borrowing(models.Model):
    """
    Tracks which user has borrowed which book and for how long.

    Status flow:
        active -> returned (on return)
        active -> overdue (when past due date)
        overdue -> returned (when returned late)
    """

    STATUS_CHOICES = [
        ('active', 'Active'),       # Currently borrowed
        ('returned', 'Returned'),   # Returned on time
        ('overdue', 'Overdue'),     # Past due date, not returned
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who borrowed what
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='borrowings'
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name='borrowings'
    )

    # Borrow period - set by user but cannot exceed book/system max
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)

    # User-selected borrow period in days
    requested_days = models.IntegerField(
        default=14,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Whether user has been notified about upcoming due date
    due_reminder_sent = models.BooleanField(default=False)

    is_mock_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sp_borrowings'
        ordering = ['-borrowed_at']
        # User can only have one active borrowing per book
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                condition=models.Q(status='active'),
                name='unique_active_borrowing'
            )
        ]

    def __str__(self):
        return f"{self.user.email} borrowed '{self.book.title}' (due: {self.due_date.date()})"

    @property
    def is_overdue(self):
        """Check if borrowing is past due date."""
        return (
            self.status == 'active' and
            timezone.now() > self.due_date
        )

    @property
    def days_remaining(self):
        """Days remaining until due date. Negative means overdue."""
        if self.status != 'active':
            return None
        delta = self.due_date - timezone.now()
        return delta.days

    def return_book(self):
        """Process a book return."""
        self.status = 'returned'
        self.returned_at = timezone.now()
        self.save(update_fields=['status', 'returned_at'])

        # Update book available copies
        self.book.available_copies = min(
            self.book.total_copies,
            self.book.available_copies + 1
        )
        self.book.save(update_fields=['available_copies'])


class Rating(models.Model):
    """
    User ratings and reviews for books.
    One rating per user per book.
    Score is 1-5 stars.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='ratings'
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name='ratings'
    )

    # Star rating 1-5
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 to 5 star rating"
    )

    # Optional text review
    review = models.TextField(blank=True, max_length=1000)

    is_mock_data = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sp_ratings'
        # One rating per user per book
        unique_together = ['user', 'book']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} rated '{self.book.title}': {self.score}/5"

    def save(self, *args, **kwargs):
        """After saving, recalculate the book's average rating."""
        super().save(*args, **kwargs)
        self.book.update_rating()

    def delete(self, *args, **kwargs):
        """After deleting, recalculate the book's average rating."""
        book = self.book
        super().delete(*args, **kwargs)
        book.update_rating()