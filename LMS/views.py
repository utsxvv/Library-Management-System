from django.shortcuts import render, redirect, get_object_or_404
from library_db.models import Book, Genre, Language , Request, IssueRecord, WaitingList
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Max
from functools import wraps
from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth import authenticate, login as auth_login
from django.core.paginator import Paginator
from django.core.cache import cache
from django.http import JsonResponse
from django.template.loader import render_to_string
from datetime import date, timedelta
from django.db.models import Count
import pickle
User = get_user_model()


def home(request):
    return redirect('user_login')

@staff_member_required
def admin_dashboard(request):
    total_books = Book.objects.count()
    total_users = User.objects.count()
    pending_list = Request.objects.filter(status='pending').select_related('user', 'book')

    context = {
        'total_books': total_books,
        'total_users': total_users,
        'pending_requests': pending_list,
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def admin_books(request):
    all_books_list = Book.objects.all().order_by('title')
    
    paginator = Paginator(all_books_list, 8) 

    page_number = request.GET.get('page')
    
    books_page_obj = paginator.get_page(page_number)
    
    context = {
        'books_page': books_page_obj,
        'all_genres': Genre.objects.all().order_by('genre_name'),
        'all_languages': Language.objects.all().order_by('language_name'),
        'user_type': 'admin',
    }
    return render(request, 'admin/books.html', context)


class LRUCache:
    def __init__(self, session, key='recently_viewed', capacity=8):
        self.session = session
        self.key = key
        self.capacity = capacity
        # We retrieve the 'queue' from the session (acting as our Linked List)
        # If it doesn't exist, we initialize an empty list.
        self.queue = self.session.get(self.key, [])

    def add(self, book_id):
        # Step 1: Search and Remove (O(N) for lists)
        if book_id in self.queue:
            self.queue.remove(book_id)
        
        # Step 2: Add to Head
        self.queue.insert(0, book_id)
        
        # Step 3: Check Capacity and Truncate Tail
        if len(self.queue) > self.capacity:
            self.queue.pop() # Removes the last element (Tail)
            
        # Save the updated structure back to the session "memory"
        self.save()

    def get_ids(self):
        """Returns the list of IDs in order (Most recent first)"""
        return self.queue

    def save(self):
        """Persists the data structure to the user session"""
        self.session[self.key] = self.queue
        self.session.modified = True
    
def filter_books(request):
    queryset = Book.objects.all().order_by('title')
    
    search_query = request.GET.get('search', '').lower().strip()
    
    # Get comma-separated strings and convert to lists
    genre_in = [x for x in request.GET.get('genre_in', '').split(',') if x]
    genre_ex = [x for x in request.GET.get('genre_ex', '').split(',') if x]
    
    lang_in = [x for x in request.GET.get('lang_in', '').split(',') if x]
    lang_ex = [x for x in request.GET.get('lang_ex', '').split(',') if x]
    
    if search_query:
        pickled_trie = cache.get('book_trie_index')
        if pickled_trie:
            trie = pickle.loads(pickled_trie)
            matching_ids = trie.search_prefix(search_query)
            if matching_ids:
                queryset = queryset.filter(pk__in=matching_ids)
            else:
                queryset = queryset.none() 
        else:
            queryset = queryset.filter(title__icontains=search_query)

    # 1. Include Logic (OR logic within the same category, e.g., Fiction OR Sci-Fi)
    if genre_in:
        queryset = queryset.filter(genre__pk__in=genre_in)
    if lang_in:
        queryset = queryset.filter(language__pk__in=lang_in)

    # 2. Exclude Logic (Exclude books with ANY of these tags)
    if genre_ex:
        queryset = queryset.exclude(genre__pk__in=genre_ex)
    if lang_ex:
        queryset = queryset.exclude(language__pk__in=lang_ex)

    print("query set : -",queryset)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(queryset, 8)
    page_obj = paginator.get_page(page_number)
    books_html = render_to_string('partials/book_grid_content.html', {'books_page': page_obj})
    return JsonResponse({'books_html': books_html})

@staff_member_required
def admin_add_book(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        isbn = request.POST.get('isbn')
        total_copies = request.POST.get('total_copies')
        description = request.POST.get('description')
        
        language_name = request.POST.get('language')
        # This one line finds the language if it exists, or creates it if it doesn't.
        language_obj, _ = Language.objects.get_or_create(language_name=language_name.strip())

        book = Book.objects.create(
            title=title,
            author=author,
            isbn=isbn,
            language=language_obj,
            description=description,
            total_copies=total_copies,
            available_copies=total_copies 
        )
        
        genres_string = request.POST.get('genres')
        genre_names = [name.strip() for name in genres_string.split(',') if name.strip()]
        
        for name in genre_names:
            genre_obj, _ = Genre.objects.get_or_create(genre_name=name)
            book.genre.add(genre_obj)
            
        return redirect('admin_books')
    
    return render(request, 'admin/add_book.html')

@staff_member_required
def admin_edit_book(request, book_id):
    book = get_object_or_404(Book, pk=book_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        isbn = request.POST.get('isbn')
        total_copies = request.POST.get('total_copies')
        description = request.POST.get('description')
        language_name = request.POST.get('language')

        # Find or create language (same logic as add)
        language_obj, _ = Language.objects.get_or_create(language_name=language_name.strip())

        # Update the book fields
        book.title = title
        book.author = author
        book.isbn = isbn
        book.language = language_obj
        book.description = description
        book.total_copies = total_copies
        book.available_copies = total_copies  # same logic as add
        book.save()

        # Update genres
        genres_string = request.POST.get('genres')
        genre_names = [name.strip() for name in genres_string.split(',') if name.strip()]

        # Clear existing genres and re-add (so it works like "replace")
        book.genre.clear()
        for name in genre_names:
            genre_obj, _ = Genre.objects.get_or_create(genre_name=name)
            book.genre.add(genre_obj)

        return redirect('admin_books')

    # Pre-fill existing data for form
    existing_genres = ', '.join([genre.genre_name for genre in book.genre.all()])

    context = {
        'book': book,
        'prefill': {
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn or '',
            'language': book.language.language_name if book.language else '',
            'genres': existing_genres,
            'total_copies': book.total_copies,
            'description': book.description or '',
        }
    }

    return render(request, 'admin/edit_book.html', context)

def admin_delete_book(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    book.delete()
    messages.success(request, f'"{book.title}" has been deleted successfully.')
    return redirect('admin_books')

@staff_member_required
def admin_issue_receive(request):
    active_issues = IssueRecord.objects.filter(status='issued').select_related('book', 'user').order_by('book__title')

    context = {
        # ... your existing context variables ...
        'active_issues': active_issues, 
    }
    return render(request, 'admin/issue_receive.html', context)

@staff_member_required
def return_book_handler(request):
    if request.method == "POST":
        issue_id = request.POST.get('issue_id')
        condition = request.POST.get('condition')
        
        # 1. Get the specific Issue Record directly
        issue_record = get_object_or_404(IssueRecord, pk=issue_id)
        
        # 2. Update Status
        issue_record.status = 'returned'
        issue_record.return_date = date.today()
        # You can save the condition somewhere if your model has a field for it
        # issue_record.return_condition = condition 
        
        # 3. Calculate Fine (Simple Example)
        if issue_record.return_date > issue_record.due_date:
            delta = issue_record.return_date - issue_record.due_date
            fine_amount = delta.days * 1.00
        
        issue_record.save()
        
        # 4. Update Book Availability
        book = issue_record.book
        book.available_copies += 1
        book.save()
        
        messages.success(request, f"Book '{book.title}' returned successfully from {issue_record.user.username}.")
        return redirect('admin_issue_receive')
    
@staff_member_required
def issue_history(request):
    # 1. Base Query
    query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    records = IssueRecord.objects.select_related('user', 'book').all().order_by('-issue_date')

    # 2. Search Logic (Student Name or Book Title)
    if query:
        records = records.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(book__title__icontains=query) |
            Q(book__isbn__icontains=query)
        )

    # 3. Status Filter (Issued, Returned, Overdue, etc.)
    if status_filter:
        records = records.filter(status=status_filter)

    # 4. Pagination (Show 10 rows per page)
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'records': page_obj,
        'search_query': query,
        'status_filter': status_filter
    }
    return render(request, 'admin/issue_history.html', context)

@staff_member_required
def admin_users(request):

    users = User.objects.annotate(
        active_issued_count=Count(
            'issues', 
            filter=Q(issues__status__in=['issued', 'overdue'])
        )
    ).order_by('username')

    context = {
        'users' : users,
        'total_users': users.count()
    }
    return render(request, 'admin/users.html', context)

@staff_member_required
def admin_requests(request):
    pending_requests = Request.objects.filter(status='pending').select_related('user', 'book').order_by('-request_date')
    approved_requests = Request.objects.filter(status='approved').select_related('user', 'book').order_by('-request_date')
    rejected_requests = Request.objects.filter(status='rejected').select_related('user', 'book').order_by('-request_date')

    context = {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
    }
    return render(request, 'admin/requests.html', context)

@staff_member_required
def admin_settings(request):
    return render(request, 'admin/settings.html')

@login_required
def user_dashboard(request):
    lru = LRUCache(request.session)
    
    recent_ids = lru.get_ids()
    
    books_unsorted = Book.objects.filter(pk__in=recent_ids)

    recently_viewed = sorted(books_unsorted, key=lambda book: recent_ids.index(book.pk))
    pending_list = Request.objects.filter(status='pending').select_related('user', 'book')

    context = {
        'pending_list': pending_list,
        'recently_viewed': recently_viewed, 
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def user_browse(request):
    all_books_list = Book.objects.all().order_by('title')
    
    paginator = Paginator(all_books_list, 8) 

    page_number = request.GET.get('page')
    
    books_page_obj = paginator.get_page(page_number)
    
    context = {
        'books_page': books_page_obj,
        'all_genres': Genre.objects.all().order_by('genre_name'),
        'all_languages': Language.objects.all().order_by('language_name'),
        'user_type': 'user',
    }
    return render(request, 'users/browse.html', context)

@login_required
def request_book(request, book_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    
    user = request.user
    print(f"DEBUG: Final User object: {user} (ID: {user.pk})")

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Please log in to request books.'}, status=401)

    book = get_object_or_404(Book, pk=book_id)
    
    # 1. Check if user already has this book issued
    if IssueRecord.objects.filter(book=book, user=user, status__in=['issued', 'overdue']).exists():
        return JsonResponse({
            'status': 'error', 
            'message': 'You already have this book issued.'
        }, status=400)
        
    # 2. Check if user already has a PENDING request
    if Request.objects.filter(book=book, user=user, status='pending').exists():
        return JsonResponse({
            'status': 'error', 
            'message': 'You already have a pending approval request for this book.'
        }, status=400)

    # 2. Check if user is already on the waiting list
    if WaitingList.objects.filter(book=book, user=user).exists():
        return JsonResponse({
            'status': 'error', 
            'message': 'You are already on the waiting list for this book.'
        }, status=400)
        
    if book.available_copies > 0:
        # Book is available. Create a 'pending' request for the admin to approve.
        Request.objects.create(
            user=user,
            book=book,
            status='pending'
        )
        return JsonResponse({
            'status': 'pending', 
            'message': 'Book is available! Your request has been sent for admin approval.'
        })

    # 3. Process the request
    # if book.available_copies > 0:
    #     # --- Book is Available: Create an IssueRecord ---
    #     book.available_copies -= 1
    #     book.save()

    #     newissue = IssueRecord.objects.create(
    #         user=user,
    #         book=book,
    #         issue_date=date.today(),
    #         due_date=date.today() + timedelta(days=14), # 2-week loan period
    #         status='issued'
    #     )
    #     print("new issue created successfully ",newissue)
    #     return JsonResponse({
    #         'status': 'success', 
    #         'message': 'Book issued successfully! It has been added to your profile.',
    #         'new_copies': book.available_copies
    #     })
    else:
        # --- Book is Unavailable: Add to WaitingList (Priority Queue) ---
        
        # Find the next position in the queue for this specific book
        current_count = WaitingList.objects.all().count()
        pos = current_count + 1
        
        newList = WaitingList.objects.create(
            user=user,
            book=book,
            position=pos
        )
        print("new waiting list created successfully ",newList)
        
        return JsonResponse({
            'status': 'waiting', 
            'message': 'This book is unavailable. You have been added to the waiting list.'
        })

@user_passes_test(lambda u: u.is_superuser)
def view_pending_requests(request):
    pending_list = Request.objects.filter(status='pending').select_related('user', 'book')
    approved_list = Request.objects.filter(status='approved').select_related('user', 'book')
    rejected_list = Request.objects.filter(status='rejected').select_related('user', 'book')
    
    context = {
        'pending_requests': pending_list,
        'approved_requests': approved_list,
        'rejected_requests': rejected_list,
    }
    return render(request, 'admin/requests.html', context)

@user_passes_test(lambda u: u.is_superuser)
def approve_request(request, request_id):
    req = get_object_or_404(Request, pk=request_id)
    book = req.book

    if book.available_copies > 0:
        # Issue the book
        book.available_copies -= 1
        book.save()
        
        IssueRecord.objects.create(
            user=req.user,
            book=book,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status='issued'
        )
        
        req.status = 'approved'
        req.save()
        messages.success(request, f"Request for '{book.title}' by {req.user.username} approved.")
    else:
        # No copies, so we must reject it
        req.status = 'rejected'
        req.save()
        messages.error(request, f"Could not approve request for '{book.title}'. No copies available.")

    return redirect('view_pending_requests')

# --- NEW: Admin view to REJECT a request ---
@user_passes_test(lambda u: u.is_superuser)
def reject_request(request, request_id):
    req = get_object_or_404(Request, pk=request_id)
    req.status = 'rejected'
    req.save()
    messages.warning(request, f"Request for '{req.book.title}' by {req.user.username} rejected.")
    return redirect('view_pending_requests')

@login_required
def user_my_books(request):
    issued_books = IssueRecord.objects.filter(user__email =request.user.email).select_related('book')
    user_request = Request.objects.filter(user=request.user).select_related('book')

    context = {
        'issued_books': issued_books,
        'user_request': user_request,
    }
    return render(request, 'users/books.html', context)

@login_required
def user_my_requests(request):
    user = request.user

    # Get requests for the 3 tabs
    pending_requests = Request.objects.filter(user=user, status='pending').select_related('book')
    approved_requests = Request.objects.filter(user=user, status='approved').select_related('book')
    rejected_requests = Request.objects.filter(user=user, status='rejected').select_related('book')
    
    # Get items from the priority queue (WaitingList)
    waiting_list_items = WaitingList.objects.filter(user=user).select_related('book').order_by('position')

    context = {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'waiting_list_items': waiting_list_items,
    }
    return render(request, 'users/requests.html', context)

@staff_member_required
def admin_book_details(request, book_id):
    book = get_object_or_404(Book, book_id=book_id)
    return render(request, 'admin/book_details.html', {'book': book})

@login_required
def user_book_details(request, book_id):
    book = get_object_or_404(Book, book_id=book_id)
    
    lru = LRUCache(request.session)
    
    lru.add(book.pk)

    return render(request, 'users/book_details.html', {'book': book})

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not (email and password):
            messages.error(request, "Please enter email address and password.")
            return render(request, 'auth/user_login.html')
        
        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back!")
            
            # Redirect based on their role
            if user.is_staff:
                return redirect('admin_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'auth/user_login.html')

def user_signup(request):
    if request.method == 'POST':
        # Handle user signup logic here
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password') 

        if not (name and phone and email and password):
            messages.error(request, "Please fill all required fields.")
            return render(request, 'auth/user_signup.html')
        
        if User.objects.filter(Q(email = email) | Q(phone = phone)).exists():
            messages.error(request, "User with this email or phone already exists.")
            return render(request, 'auth/user_signup.html')
        
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name,
                phone=phone
            )
            # Log them in immediately
            auth_login(request, user)
            messages.success(request, "Registration successful. You are now logged in.")
            return redirect('user_dashboard')

        except Exception as e:
            messages.error(request, f"An error occurred during signup: {e}")
            return render(request, 'auth/user_signup.html')

    return render(request, 'auth/user_signup.html')

@login_required
def user_logout(request):
    logout(request)  
    return redirect('user_login')  

@staff_member_required
def admin_logout(request):
    logout(request)
    return redirect('user_login') 