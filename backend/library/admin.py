from django.contrib import admin
from .models import Category, Book, Borrowing, Rating, BorrowSetting

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'average_rating', 'borrow_count', 'is_available']
    list_filter = ['is_available', 'material_type', 'is_featured']
    search_fields = ['title', 'author', 'isbn']

admin.site.register(Category)
admin.site.register(Borrowing)
admin.site.register(Rating)
admin.site.register(BorrowSetting)
