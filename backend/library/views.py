"""
SourcePoint Library - Views
==============================
API views for books, categories, borrowings, ratings, and file serving.
"""

import logging
import os
import mimetypes
import requests as http_requests
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import generics, status, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from slugify import slugify

from .models import Category, Book, Borrowing, Rating, BorrowSetting
from users.models import User
from .serializers import (
    CategorySerializer, BookListSerializer, BookDetailSerializer,
    BorrowingSerializer, RatingSerializer, BorrowSettingSerializer
)
from users.permissions import IsAdmin, IsSuperAdmin

logger = logging.getLogger('sourcepoint')


# =============================================================
# SUPABASE STORAGE HELPERS
# =============================================================

def _get_supabase_client():
    """Return (client, bucket_name) or (None, None) if not configured."""
    try:
        from supabase import create_client
        url = getattr(settings, 'SUPABASE_URL', '').strip()
        key = getattr(settings, 'SUPABASE_SERVICE_KEY', '').strip()
        bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'sourcepoint-books')
        if not url or not key:
            return None, bucket
        return create_client(url, key), bucket
    except Exception as e:
        logger.warning(f"Supabase client init failed: {e}")
        return None, 'sourcepoint-books'


def _upload_to_supabase(file_obj, path_in_bucket):
    """
    Upload a file to Supabase Storage.
    Returns the storage path (not URL) on success, None on failure.
    We store the path and reconstruct URLs on demand via _supabase_signed_url().
    """
    sb, bucket = _get_supabase_client()
    if not sb:
        return None
    try:
        # Read file bytes
        file_obj.seek(0)
        file_bytes = file_obj.read()
        mime = mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'

        # Upload — upsert:true means overwrite if exists
        sb.storage.from_(bucket).upload(
            path_in_bucket,
            file_bytes,
            file_options={"content-type": mime, "upsert": "true"},
        )
        logger.info(f"Uploaded to Supabase bucket '{bucket}': {path_in_bucket}")
        return path_in_bucket  # return the path, not the URL

    except Exception as e:
        logger.warning(f"Supabase upload failed ({path_in_bucket}): {e}")
        return None


def _supabase_public_url(path_in_bucket):
    """
    Build a Supabase public URL for a given storage path.
    Format: {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
    Only works if the bucket is set to PUBLIC in Supabase dashboard.
    """
    base = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
    bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'sourcepoint-books')
    if not base:
        return None
    return f"{base}/storage/v1/object/public/{bucket}/{path_in_bucket}"


def _supabase_signed_url(path_in_bucket, expires_in=3600):
    """
    Get a temporary signed URL from Supabase (works even for private buckets).
    Valid for `expires_in` seconds (default 1 hour).
    Returns the signed URL string or None on failure.
    """
    sb, bucket = _get_supabase_client()
    if not sb:
        return None
    try:
        result = sb.storage.from_(bucket).create_signed_url(path_in_bucket, expires_in)
        # SDK returns dict or object depending on version
        if isinstance(result, dict):
            return result.get('signedURL') or result.get('signedUrl')
        return getattr(result, 'signed_url', None) or getattr(result, 'signedURL', None)
    except Exception as e:
        logger.warning(f"Signed URL failed for {path_in_bucket}: {e}")
        return None


def _stream_supabase_file(path_in_bucket):
    """
    Download a file from Supabase Storage and return its bytes.
    Used to proxy private files through Django without exposing Supabase URLs.
    """
    sb, bucket = _get_supabase_client()
    if not sb:
        return None, None
    try:
        data = sb.storage.from_(bucket).download(path_in_bucket)
        mime = mimetypes.guess_type(path_in_bucket)[0] or 'application/octet-stream'
        return data, mime
    except Exception as e:
        logger.warning(f"Supabase download failed ({path_in_bucket}): {e}")
        return None, None


# =============================================================
# CATEGORY VIEWS
# =============================================================

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]


# =============================================================
# BOOK VIEWS
# =============================================================

class BookListView(generics.ListAPIView):
    serializer_class = BookListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['language', 'material_type', 'is_available', 'is_featured']
    search_fields = ['title', 'author', 'description', 'isbn', 'publisher']
    ordering_fields = ['title', 'author', 'average_rating', 'borrow_count', 'created_at']
    ordering = ['-is_featured', '-created_at']

    def get_queryset(self):
        queryset = Book.objects.filter(is_available=True).prefetch_related('categories')
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)
        return queryset.distinct()

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}


class BookDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Book.objects.prefetch_related('categories', 'ratings__user')
    serializer_class = BookDetailSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        return Response(self.get_serializer(instance).data)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}


class BookCreateView(APIView):
    """
    POST /api/v1/library/books/create/
    Accepts multipart/form-data with optional cover_image and book_file uploads.
    Files go to Supabase Storage (if configured) or local media/ folder.
    Cover image URL field has been removed — only local upload supported.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data
        title  = data.get('title',  '').strip()
        author = data.get('author', '').strip()
        if not title or not author:
            return Response({'error': 'Title and author are required.'}, status=400)

        # Unique slug
        slug = base_slug = slugify(title)
        counter = 1
        while Book.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"; counter += 1

        # Categories
        raw_cats = data.getlist('category_ids') or []
        if not raw_cats and data.get('category_ids'):
            raw_cats = [c.strip() for c in data.get('category_ids','').split(',') if c.strip()]
        categories = Category.objects.filter(id__in=raw_cats)

        copies = int(data.get('total_copies', 1) or 1)

        book = Book(
            title=title, slug=slug, author=author,
            publisher=data.get('publisher', ''),
            publication_year=data.get('publication_year') or None,
            pages=data.get('pages') or None,
            material_type=data.get('material_type', 'book'),
            language=data.get('language', 'English'),
            description=data.get('description', ''),
            max_borrow_days=data.get('max_borrow_days') or None,
            total_copies=copies, available_copies=copies,
            is_available=True, added_by=request.user,
        )

        # ── Cover image (local upload only) ──────────────────────
        cover_file = request.FILES.get('cover_image')
        if cover_file:
            sb_path = f"covers/{slug}-{cover_file.name}"
            uploaded_path = _upload_to_supabase(cover_file, sb_path)
            if uploaded_path:
                # Store the Supabase storage path so we can build/sign URLs later
                book.cover_image_url = f"supabase://{uploaded_path}"
                logger.info(f"Cover in Supabase: {sb_path}")
            else:
                cover_file.seek(0)
                book.cover_image = cover_file
                logger.info(f"Cover saved locally: {title}")

        # ── Book file (PDF/ebook) ─────────────────────────────────
        book_file = request.FILES.get('book_file')
        if book_file:
            ext = os.path.splitext(book_file.name)[1].lower().lstrip('.')
            book.file_type = ext or 'pdf'
            sb_path = f"books/{slug}-{book_file.name}"
            uploaded_path = _upload_to_supabase(book_file, sb_path)
            if uploaded_path:
                # Store path with supabase:// prefix — served via Django proxy
                book.file_url = f"supabase://{uploaded_path}"
                logger.info(f"Book file in Supabase: {sb_path}")
            else:
                book_file.seek(0)
                book.book_file = book_file
                logger.info(f"Book file saved locally: {title}")

        book.save()
        if categories.exists():
            book.categories.set(categories)

        logger.info(f"Book created: '{title}' by {request.user.email}")
        return Response(BookDetailSerializer(book, context={'request': request}).data, status=201)


class AdminBookListView(generics.ListAPIView):
    serializer_class = BookDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'isbn']
    ordering_fields = ['title', 'created_at', 'borrow_count']

    def get_queryset(self):
        return Book.objects.all().prefetch_related('categories').order_by('-created_at')


# =============================================================
# COVER IMAGE PROXY
# =============================================================

class ServeCoverImageView(APIView):
    """
    GET /api/v1/library/books/<book_id>/cover/
    Proxies the cover image through Django — works for both Supabase and local files.
    Public endpoint (no auth needed for cover images).
    """
    permission_classes = [AllowAny]

    def get(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=404)

        # ── Supabase-stored cover ─────────────────────────────────
        if book.cover_image_url and book.cover_image_url.startswith('supabase://'):
            path_in_bucket = book.cover_image_url[len('supabase://'):]
            img_bytes, mime = _stream_supabase_file(path_in_bucket)
            if img_bytes:
                from django.http import HttpResponse
                response = HttpResponse(img_bytes, content_type=mime or 'image/jpeg')
                response['Cache-Control'] = 'public, max-age=86400'  # cache 24h
                return response
            return Response({'error': 'Cover image unavailable'}, status=404)

        # ── Legacy external URL (http/https) ──────────────────────
        if book.cover_image_url and book.cover_image_url.startswith('http'):
            try:
                r = http_requests.get(book.cover_image_url, timeout=8, stream=True)
                if r.status_code == 200:
                    from django.http import HttpResponse
                    response = HttpResponse(r.content, content_type=r.headers.get('content-type', 'image/jpeg'))
                    response['Cache-Control'] = 'public, max-age=86400'
                    return response
            except Exception:
                pass
            return Response({'error': 'Cover image fetch failed'}, status=404)

        # ── Local uploaded file ───────────────────────────────────
        if book.cover_image:
            try:
                local_path = book.cover_image.path
                if os.path.exists(local_path):
                    mime = mimetypes.guess_type(local_path)[0] or 'image/jpeg'
                    from django.http import FileResponse
                    return FileResponse(open(local_path, 'rb'), content_type=mime)
            except Exception as e:
                logger.warning(f"Cover local serve failed: {e}")

        return Response({'error': 'No cover image'}, status=404)


# =============================================================
# BOOK FILE SERVING (authenticated)
# =============================================================

class ServeBookFileView(APIView):
    """
    GET /api/v1/library/books/<book_id>/read/
    Returns the direct file URL for the client to open.
    For Supabase files: returns the public URL directly (no proxy needed).
    For local files: streams bytes so the client can create a blob URL.
    Access: admins always, users need active borrowing.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found.'}, status=404)

        # Access check
        is_admin = request.user.role in ('admin', 'superadmin')
        if not is_admin:
            if not Borrowing.objects.filter(
                user=request.user, book=book, status='active'
            ).exists():
                return Response({'error': 'Borrow this book first to read it.'}, status=403)

        # ── Supabase file — build public URL and return directly ──────
        if book.file_url and book.file_url.startswith('supabase://'):
            path_in_bucket = book.file_url[len('supabase://'):]
            supabase_base = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
            bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'sourcepoint-books')
            public_url = f"{supabase_base}/storage/v1/object/public/{bucket}/{path_in_bucket}"
            return Response({
                'source': 'supabase',
                'url': public_url,
                'file_type': book.file_type or 'pdf',
                'title': book.title,
            })

        # ── Legacy http/https URL — return directly ───────────────────
        if book.file_url and book.file_url.startswith('http'):
            return Response({
                'source': 'external',
                'url': book.file_url,
                'file_type': book.file_type or 'pdf',
                'title': book.title,
            })

        # ── Local file — stream bytes so frontend makes a blob URL ────
        if book.book_file:
            try:
                local_path = book.book_file.path
                if not os.path.exists(local_path):
                    return Response({'error': 'File not found on disk.'}, status=404)
                mime = mimetypes.guess_type(local_path)[0] or 'application/pdf'
                filename = os.path.basename(local_path)

                def stream(path, chunk=8192):
                    with open(path, 'rb') as f:
                        while True:
                            data = f.read(chunk)
                            if not data:
                                break
                            yield data

                response = StreamingHttpResponse(stream(local_path), content_type=mime)
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                response['Content-Length'] = os.path.getsize(local_path)
                response['X-Frame-Options'] = 'SAMEORIGIN'
                return response
            except Exception as e:
                logger.error(f"Local file serve failed: {e}")
                return Response({'error': str(e)}, status=500)

        return Response({'error': 'No file attached to this book.'}, status=404)
