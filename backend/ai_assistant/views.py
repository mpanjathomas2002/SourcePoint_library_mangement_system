"""
SourcePoint AI Assistant - Views
===================================
Powered by Groq API — completely FREE, no credit card required.

Why Groq:
  - 100% free tier, no billing setup
  - Sign up at: https://console.groq.com
  - Click "Create API Key" — done in 30 seconds
  - Free limits: 14,400 requests/day, 6,000 tokens/min
  - Uses llama-3.1-8b-instant (extremely fast, very capable)

Models available free on Groq:
  - llama-3.1-8b-instant   (default — fastest)
  - llama-3.3-70b-versatile (smarter, slower)
  - mixtral-8x7b-32768      (large context)
  - gemma2-9b-it            (Google Gemma)

Setup:
  1. Go to https://console.groq.com
  2. Sign up (no credit card)
  3. Create an API key
  4. Add to .env:  GROQ_API_KEY=gsk_your_key_here
  5. Restart server
"""

import logging
import requests
from django.conf import settings
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from library.models import Book, Category, Borrowing, BorrowSetting
from library.serializers import BookListSerializer

logger = logging.getLogger('sourcepoint')

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model fallback order — all free on Groq
GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


def get_groq_key():
    key = getattr(settings, 'GROQ_API_KEY', '') or ''
    return key.strip()


def call_groq(messages, model=None):
    """
    Call the Groq API with OpenAI-compatible chat completions endpoint.
    Tries each model in GROQ_MODELS until one succeeds.
    Returns (reply_text, model_used) or raises an exception.
    """
    key = get_groq_key()
    if not key:
        raise ValueError("NO_KEY")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    models_to_try = [model] + GROQ_MODELS if model else GROQ_MODELS
    # Deduplicate
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    last_error = None
    for m in models_to_try:
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=headers,
                json={
                    "model": m,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return text, m
            elif resp.status_code == 429:
                last_error = "rate_limit"
                continue
            elif resp.status_code == 401:
                raise ValueError("INVALID_KEY")
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue
        except requests.Timeout:
            last_error = "timeout"
            continue
        except ValueError:
            raise
        except Exception as e:
            last_error = str(e)
            continue

    if last_error == "rate_limit":
        raise RuntimeError("RATE_LIMIT")
    raise RuntimeError(f"ALL_FAILED: {last_error}")


def get_library_context():
    """Build context string about the library for the AI."""
    books = Book.objects.filter(is_available=True).prefetch_related('categories')[:60]
    cats = Category.objects.all()
    settings_obj = BorrowSetting.objects.first()
    max_days = settings_obj.default_max_days if settings_obj else 30
    max_concurrent = settings_obj.max_concurrent_borrows if settings_obj else 5

    lines = []
    for b in books:
        cats_str = ', '.join(c.name for c in b.categories.all()) or 'General'
        has_file = 'readable online' if (b.file_url or getattr(b, 'book_file', None)) else 'no digital file'
        lines.append(
            f'- "{b.title}" by {b.author} '
            f'[{cats_str}, {b.material_type}, '
            f'{b.publication_year or "year unknown"}, '
            f'rating {b.average_rating:.1f}/5, {has_file}]'
        )

    return f"""SOURCEPOINT LIBRARY CATALOG
Total books: {books.count()}
Categories: {', '.join(c.name for c in cats)}
Borrow policy: max {max_days} days, up to {max_concurrent} books at once

AVAILABLE BOOKS:
{chr(10).join(lines)}"""


class AIChatView(APIView):
    """
    POST /api/v1/ai/chat/
    Body: { "message": "...", "history": [ {role, content}, ... ] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = (request.data.get('message') or '').strip()
        history = request.data.get('history') or []

        if not message:
            return Response({'error': 'message is required'}, status=400)

        key = get_groq_key()
        if not key:
            return Response({
                'reply': (
                    "The AI assistant is not configured yet.\n\n"
                    "Setup takes 30 seconds and is completely free (no credit card):\n"
                    "1. Go to https://console.groq.com\n"
                    "2. Sign up and click Create API Key\n"
                    "3. Add GROQ_API_KEY=gsk_your_key to your .env file\n"
                    "4. Restart the server\n\n"
                    "Groq gives you 14,400 free requests per day."
                ),
                'books': [],
            })

        # Build user reading history for personalisation
        recent = request.user.borrowings.select_related('book').order_by('-borrowed_at')[:5]
        history_note = ''
        if recent.exists():
            titles = [f'"{b.book.title}"' for b in recent]
            history_note = f"\nThis user recently read: {', '.join(titles)}"

        system_msg = f"""You are Sage, the AI librarian for SourcePoint Digital Library.
You are helpful, warm, and knowledgeable about books.

{get_library_context()}
{history_note}

RULES:
- Only recommend books from the AVAILABLE BOOKS list above.
- For summaries, use your training knowledge about the book.
- Keep answers concise (2-3 paragraphs) unless a detailed summary is requested.
- When listing books, use a numbered list.
- If a book is not in the catalog, say so but still share what you know.
- Current user: {request.user.get_full_name()} ({request.user.email})"""

        # Build messages array (OpenAI format, works with Groq)
        msgs = [{"role": "system", "content": system_msg}]

        # Add conversation history (last 6 turns)
        for turn in history[-6:]:
            role = turn.get('role', '')
            content = turn.get('content', '')
            if role == 'assistant':
                role = 'assistant'
            elif role == 'user':
                role = 'user'
            else:
                continue
            if content:
                msgs.append({"role": role, "content": content})

        msgs.append({"role": "user", "content": message})

        try:
            reply, model_used = call_groq(msgs)
            logger.info(f"AI [{model_used}]: {request.user.email} — {message[:60]}")

            # Find books mentioned in reply for clickable cards
            mentioned = []
            for book in Book.objects.filter(is_available=True).prefetch_related('categories')[:60]:
                if book.title.lower() in reply.lower():
                    mentioned.append(book)
                    if len(mentioned) >= 3:
                        break

            return Response({
                'reply': reply,
                'books': BookListSerializer(mentioned, many=True, context={'request': request}).data,
                'model': model_used,
            })

        except ValueError as e:
            if 'NO_KEY' in str(e) or 'INVALID_KEY' in str(e):
                logger.warning(f"Groq key issue: {e}")
                return Response({
                    'reply': "AI key is invalid. Please check GROQ_API_KEY in your .env file.",
                    'books': [],
                })
            raise

        except RuntimeError as e:
            err = str(e)
            logger.error(f"Groq error: {err}")
            if 'RATE_LIMIT' in err:
                msg = "Rate limit reached. Please wait a moment and try again (free tier: 6,000 tokens/min)."
            else:
                msg = "AI service temporarily unavailable. Please try again."
            return Response({'reply': msg, 'books': []}, status=503)

        except Exception as e:
            logger.error(f"AI unexpected error: {e}")
            return Response({'reply': "Something went wrong. Please try again.", 'books': []}, status=500)


class BookSummaryView(APIView):
    """
    GET /api/v1/ai/books/<book_id>/summary/
    Generates and caches an AI summary. Returns cached if available.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=404)

        if book.summary:
            return Response({'summary': book.summary, 'cached': True, 'title': book.title})

        key = get_groq_key()
        if not key:
            fallback = book.description or 'Configure GROQ_API_KEY to enable AI summaries.'
            return Response({'summary': fallback, 'cached': False, 'title': book.title})

        try:
            cats = ', '.join(c.name for c in book.categories.all())
            msgs = [
                {"role": "system", "content": "You are a knowledgeable librarian who writes engaging book summaries."},
                {"role": "user", "content": f"""Write a 2-3 paragraph summary of this book:

Title: {book.title}
Author: {book.author}
Published: {book.publication_year or 'Unknown'}
Categories: {cats}
Description: {book.description or 'Not provided'}

Cover: (1) what the book is about, (2) key themes, (3) who would enjoy it.
Be engaging. Avoid spoilers for fiction."""},
            ]
            summary, _ = call_groq(msgs)
            book.summary = summary
            book.save(update_fields=['summary'])
            return Response({'summary': summary, 'cached': False, 'title': book.title})

        except Exception as e:
            logger.error(f"Summary error '{book.title}': {e}")
            return Response({
                'summary': book.description or 'Summary unavailable.',
                'cached': False, 'title': book.title
            })


class BookRecommendationView(APIView):
    """
    GET /api/v1/ai/recommendations/
    Returns personalised book picks based on borrowing history.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        borrowed = user.borrowings.select_related('book').prefetch_related('book__categories')[:10]

        borrowed_ids, cat_ids, authors = set(), set(), set()
        for bw in borrowed:
            borrowed_ids.add(bw.book.id)
            authors.add(bw.book.author)
            for c in bw.book.categories.all():
                cat_ids.add(c.id)

        if cat_ids or authors:
            recs = Book.objects.filter(is_available=True)\
                .exclude(id__in=borrowed_ids)\
                .filter(Q(categories__id__in=cat_ids) | Q(author__in=authors))\
                .distinct().order_by('-average_rating', '-borrow_count')[:8]
        else:
            recs = Book.objects.filter(is_available=True)\
                .order_by('-average_rating', '-borrow_count', '-is_featured')[:8]

        return Response({
            'recommendations': BookListSerializer(recs, many=True, context={'request': request}).data,
            'based_on': 'history' if borrowed.exists() else 'popular',
        })
