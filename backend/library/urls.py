"""SourcePoint Library URL Configuration"""

from django.urls import path
from . import views

urlpatterns = [
    # Public book catalog
    path('books/', views.BookListView.as_view(), name='book_list'),
    path('books/create/', views.BookCreateView.as_view(), name='book_create'),
    path('books/<uuid:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('books/<uuid:book_id>/rate/', views.RateBookView.as_view(), name='rate_book'),
    # Authenticated book reading — proxies file through Django (no Supabase auth issues)
    path('books/<uuid:book_id>/read/', views.ServeBookFileView.as_view(), name='read_book'),
    # Cover image proxy — public, serves from Supabase or local
    path('books/<uuid:book_id>/cover/', views.ServeCoverImageView.as_view(), name='book_cover'),

    # Categories
    path('categories/', views.CategoryListCreateView.as_view(), name='category_list'),
    path('categories/<uuid:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),

    # User borrowings
    path('borrow/', views.BorrowBookView.as_view(), name='borrow_book'),
    path('borrow/<uuid:borrowing_id>/return/', views.ReturnBookView.as_view(), name='return_book'),
    path('my-books/', views.UserBorrowingsView.as_view(), name='user_borrowings'),

    # Settings
    path('settings/', views.BorrowSettingsView.as_view(), name='borrow_settings'),

    # Admin
    path('admin/books/', views.AdminBookListView.as_view(), name='admin_book_list'),
    path('admin/borrowings/', views.AllBorrowingsView.as_view(), name='all_borrowings'),
    path('admin/stats/', views.AdminStatsView.as_view(), name='admin_stats'),

    # Mock data
    path('mock-data/', views.ClearMockDataView.as_view(), name='clear_mock_data'),
]