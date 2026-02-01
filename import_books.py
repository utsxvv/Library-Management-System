import csv
from library_db.models import Book, Genre, Language

with open('books_500.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        isbn = row['isbn'].strip()
        title = row['Title'].strip()
        author = row['Author'].strip()
        description = row.get('Description', '').strip()
        genres_raw = row.get('Genres', '').strip()
        language_name = row.get('Language', '').strip()
        total_copies = int(row.get('Total Copies', 0) or 0)
        available_copies = int(row.get('available_copies', 0) or 0)

        # ✅ Safe handling if 'image_url' column is missing or empty
        image_url = row.get('image_url', '').strip() if 'image_url' in row else None

        # ✅ Get or create the Language
        language_obj, _ = Language.objects.get_or_create(language_name=language_name)

        # ✅ Create or update the Book
        book, created = Book.objects.update_or_create(
            isbn=isbn,
            defaults={
                'title': title,
                'author': author,
                'language': language_obj,
                'description': description,
                'image_url': image_url or None,  # leave empty for now
                'total_copies': total_copies,
                'available_copies': available_copies,
            }
        )

        # ✅ Handle Many-to-Many Genres
        if genres_raw:
            genre_names = [g.strip() for g in genres_raw.replace(';', ',').split(',') if g.strip()]
            for genre_name in genre_names:
                genre_obj, _ = Genre.objects.get_or_create(genre_name=genre_name)
                book.genre.add(genre_obj)

        book.save()
        print(f"{'Created' if created else 'Updated'} book: {book.title}")
