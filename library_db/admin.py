
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Genre, Book, IssueRecord, Request, WaitingList, Language

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'phone', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'username', 'phone')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('genre_id', 'genre_name')


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('language_id', 'language_name')


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('book_id', 'isbn', 'title', 'author', 'genre_display', 'language', 'image_url', 'total_copies', 'available_copies')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('genre',)


@admin.register(IssueRecord)
class IssueRecordAdmin(admin.ModelAdmin):
    list_display = ('issue_id', 'user', 'book', 'issue_date', 'due_date', 'return_date', 'status')
    list_filter = ('status', 'issue_date')
    search_fields = ('user__name', 'book__title')


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'user', 'book', 'request_date', 'status')
    list_filter = ('status',)
    search_fields = ('user__name', 'book__title')


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('waiting_id', 'user', 'book', 'position', 'request_date')
    list_filter = ('book',)
    search_fields = ('user__name', 'book__title')
