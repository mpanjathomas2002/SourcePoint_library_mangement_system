"""
SourcePoint Library - Serializers
====================================
REST API serializers for library models.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Category, Book, Borrowing, Rating, BorrowSetting


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for book categories."""
    book_count = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'book_count']
        read_only_fields = ['id', 'slug']

    def create(self, validated_data):
        """Auto-generate slug from name."""
        from slugify import slugify
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class BookListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for book lists (search results, catalog).
    Avoids heavy fields for performance.
    """
    categories = CategorySerializer(many=True, read_only=True)
    cover_url = serializers.SerializerMethodField()
    book_file_url = serializers.SerializerMethodField()
    is_borrowed_by_user = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'publisher', 'publication_year',
            'language', 'material_type', 'categories', 'cover_url',
            'average_rating', 'rating_count', 'borrow_count',
            'is_available', 'available_copies', 'is_featured',
            'is_borrowed_by_user', 'user_rating', 'tags', 'book_file_url', 'file_type',
        ]

    def get_cover_url(self, obj):
        return obj.get_cover_url(self.context.get('request'))

    def get_book_file_url(self, obj):
        """Return absolute URL to the book's digital content (PDF etc.) for reading."""
        request = self.context.get('request')
        return obj.get_book_file_url(request) or None

    def get_is_borrowed_by_user(self, obj):
        """Check if the current user has this book borrowed."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.borrowings.filter(
                user=request.user, status='active'
            ).exists()
        return False

    def get_user_rating(self, obj):
        """Return current user's rating for this book, if any."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rating = obj.ratings.get(user=request.user)
                return {'score': rating.score, 'review': rating.review}
            except Rating.DoesNotExist:
                pass
        return None


class BookDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for single book detail view.
    Includes all fields, ratings, and borrowing info.
    """
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(),
        write_only=True, source='categories'
    )
    cover_url = serializers.SerializerMethodField()
    book_file_url = serializers.SerializerMethodField()
    is_borrowed_by_user = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    recent_ratings = serializers.SerializerMethodField()
    effective_max_borrow_days = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'slug', 'author', 'isbn', 'publisher',
            'publication_year', 'language', 'pages', 'material_type',
            'description', 'summary', 'cover_url', 'file_url', 'book_file_url', 'file_type',
            'categories', 'category_ids', 'tags',
            'average_rating', 'rating_count', 'borrow_count', 'view_count',
            'is_available', 'available_copies', 'total_copies',
            'max_borrow_days', 'effective_max_borrow_days',
            'is_featured', 'is_borrowed_by_user', 'user_rating',
            'recent_ratings', 'created_at',
        ]
        read_only_fields = [
            'id', 'slug', 'borrow_count', 'view_count',
            'average_rating', 'rating_count', 'created_at'
        ]

    def get_cover_url(self, obj):
        return obj.get_cover_url(self.context.get('request'))

    def get_book_file_url(self, obj):
        """Return absolute URL to the book's digital content (PDF etc.) for reading."""
        request = self.context.get('request')
        return obj.get_book_file_url(request) or None

    def get_is_borrowed_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.borrowings.filter(user=request.user, status='active').exists()
        return False

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rating = obj.ratings.get(user=request.user)
                return {
                    'id': str(rating.id),
                    'score': rating.score,
                    'review': rating.review,
                    'created_at': rating.created_at,
                }
            except Rating.DoesNotExist:
                pass
        return None

    def get_recent_ratings(self, obj):
        """Return 5 most recent ratings with user info."""
        ratings = obj.ratings.select_related('user').order_by('-created_at')[:5]
        return [
            {
                'user_name': r.user.get_full_name(),
                'score': r.score,
                'review': r.review,
                'date': r.created_at.strftime('%b %d, %Y'),
            }
            for r in ratings
        ]

    def get_effective_max_borrow_days(self, obj):
        return obj.get_effective_max_borrow_days()


class BorrowingSerializer(serializers.ModelSerializer):
    """
    Serializer for borrowing records.
    Used for user's bookshelf/dashboard.
    """
    book = BookListSerializer(read_only=True)
    book_id = serializers.UUIDField(write_only=True)
    days_remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Borrowing
        fields = [
            'id', 'book', 'book_id', 'borrowed_at', 'due_date',
            'returned_at', 'requested_days', 'status',
            'days_remaining', 'is_overdue',
        ]
        read_only_fields = ['id', 'borrowed_at', 'due_date', 'returned_at', 'status']

    def validate(self, attrs):
        """Validate borrowing request."""
        request = self.context['request']
        user = request.user
        book_id = attrs.get('book_id')
        requested_days = attrs.get('requested_days', 14)

        # Get the book
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise serializers.ValidationError({'book_id': 'Book not found.'})

        # Check if book is available
        if not book.is_available or book.available_copies < 1:
            raise serializers.ValidationError({'book_id': 'This book is not currently available.'})

        # Check if user already has this book
        if Borrowing.objects.filter(user=user, book=book, status='active').exists():
            raise serializers.ValidationError({'book_id': 'You already have this book borrowed.'})

        # Check concurrent borrow limit
        settings = BorrowSetting.objects.first()
        max_concurrent = settings.max_concurrent_borrows if settings else 5
        current_count = user.borrowings.filter(status='active').count()
        if current_count >= max_concurrent:
            raise serializers.ValidationError(
                f"You can only borrow {max_concurrent} books at a time. Return a book first."
            )

        # Validate borrow period against book/system max
        max_days = book.get_effective_max_borrow_days()
        if requested_days > max_days:
            raise serializers.ValidationError(
                {'requested_days': f"Maximum borrow period for this book is {max_days} days."}
            )

        attrs['book'] = book
        attrs['max_days'] = max_days
        return attrs

    def create(self, validated_data):
        """Create a new borrowing record."""
        book = validated_data.pop('book')
        validated_data.pop('book_id')
        validated_data.pop('max_days', None)
        requested_days = validated_data.get('requested_days', 14)

        # Calculate due date based on requested days
        due_date = timezone.now() + timedelta(days=requested_days)

        borrowing = Borrowing.objects.create(
            user=self.context['request'].user,
            book=book,
            due_date=due_date,
            **validated_data
        )

        # Decrement available copies
        book.available_copies = max(0, book.available_copies - 1)
        book.borrow_count += 1
        book.save(update_fields=['available_copies', 'borrow_count'])

        return borrowing


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for book ratings."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = ['id', 'book', 'score', 'review', 'user_name', 'created_at']
        read_only_fields = ['id', 'user_name', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def validate_score(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def create(self, validated_data):
        """Create or update a rating (one per user per book)."""
        user = self.context['request'].user
        book = validated_data['book']

        # Upsert: update existing or create new
        rating, created = Rating.objects.update_or_create(
            user=user, book=book,
            defaults={
                'score': validated_data['score'],
                'review': validated_data.get('review', ''),
            }
        )
        return rating


class BorrowSettingSerializer(serializers.ModelSerializer):
    """Serializer for system borrow settings (admin only)."""

    class Meta:
        model = BorrowSetting
        fields = [
            'default_max_days', 'grace_period_days',
            'max_concurrent_borrows', 'updated_at'
        ]
        read_only_fields = ['updated_at']