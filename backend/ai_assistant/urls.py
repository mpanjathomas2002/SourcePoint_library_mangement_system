"""SourcePoint AI Assistant URL Configuration"""

from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.AIChatView.as_view(), name='ai_chat'),
    path('books/<uuid:book_id>/summary/', views.BookSummaryView.as_view(), name='book_summary'),
    path('recommendations/', views.BookRecommendationView.as_view(), name='ai_recommendations'),
]
