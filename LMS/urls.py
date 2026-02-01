"""
URL configuration for LMS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('', views.home, name='home'),

    #Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/books/', views.admin_books, name='admin_books'),
    path('admin/books/<int:book_id>/', views.admin_book_details, name='admin_book_details'),
    path('admin/books/add', views.admin_add_book, name='admin_add_book'),
    path('admin/issue-receive/', views.admin_issue_receive, name='admin_issue_receive'),
    path('return-book-handler/', views.return_book_handler, name='return_book_handler'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin_requests/', views.admin_requests, name='admin_requests'),
    path('issue-history/', views.issue_history, name='issue_history'),
    path('admin/settings/', views.admin_settings, name='admin_settings'),
    path('admin/books/edit/<int:book_id>/', views.admin_edit_book, name='admin_edit_book'),
    path('admin/books/delete/<int:book_id>/', views.admin_delete_book, name='admin_delete_book'),

    #User URLs
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user/my-books', views.user_my_books, name='user_my_books'),
    path('user/my-requests/', views.user_my_requests, name='user_my_requests'),
    path('user/browse/', views.user_browse, name='user_browse'),
    path('user/book/<int:book_id>/', views.user_book_details, name='user_book_details'),

    #Auth
    path('user/login/', views.user_login, name='user_login'),
    path('user/signup/', views.user_signup, name='user_signup'),
    path('user/logout/', views.user_logout, name='user_logout'),

    # path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),

    #APIs
    path('api/filter-books/', views.filter_books, name='filter_books'),
    path('api/request-book/<int:book_id>/', views.request_book, name='request_book'),
    path('admin/requests/', views.view_pending_requests, name='view_pending_requests'),
    path('admin/requests/approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('admin/requests/reject/<int:request_id>/', views.reject_request, name='reject_request'),
]
