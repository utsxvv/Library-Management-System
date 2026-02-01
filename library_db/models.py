from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    # Django already includes: username, password, first_name, last_name, email, 
    # is_staff (for admin), is_superuser, is_active, date_joined, last_login.
    
    # Add your custom field:
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    
    # Make email unique and required (highly recommended)
    email = models.EmailField(unique=True)

    # Set email as the unique identifier for authentication instead of username
    USERNAME_FIELD = 'email'
    # Fields REQUIRED when creating a superuser (email is automatically required by USERNAME_FIELD)
    REQUIRED_FIELDS = ['username', 'phone'] 

    def __str__(self):
        return self.email

class Genre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    genre_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.genre_name
      
class Language(models.Model):
    language_id = models.AutoField(primary_key=True)
    language_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.language_name

class Book(models.Model):
    book_id = models.AutoField(primary_key=True)
    isbn = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=100)
    genre = models.ManyToManyField(Genre, related_name='books')
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='books', null=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    total_copies = models.IntegerField()
    available_copies = models.IntegerField()

    def __str__(self):
        return self.title
      
    def genre_display(self):
      return ', '.join(genre.genre_name for genre in self.genre.all())

    genre_display.short_description = 'Genres'

class IssueRecord(models.Model):
    STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    ]

    issue_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='issues')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='issues')
    issue_date = models.DateField()
    due_date = models.DateField()
    return_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.book.title} → {self.user.username}"


class Request(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    request_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='requests')
    request_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Request {self.request_id} - {self.book.title} by {self.user.username}"


class WaitingList(models.Model):
    waiting_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='waiting_list')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='waiting_list')
    position = models.IntegerField(default=0)
    request_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} waiting for {self.book.title} (#{self.position})"