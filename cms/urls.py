from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Categories CRUD
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/edit/<str:id>/', views.category_edit, name='category_edit'),
    path('categories/delete/<str:id>/', views.category_delete, name='category_delete'),
    
    # Authors CRUD
    path('authors/', views.author_list, name='author_list'),
    path('authors/add/', views.author_add, name='author_add'),
    path('authors/edit/<str:id>/', views.author_edit, name='author_edit'),
    path('authors/delete/<str:id>/', views.author_delete, name='author_delete'),
    
    # Blogs CRUD
    path('blogs/', views.blog_list, name='blog_list'),
    path('blogs/add/', views.blog_add, name='blog_add'),
    path('blogs/edit/<str:id>/', views.blog_edit, name='blog_edit'),
    path('blogs/delete/<str:id>/', views.blog_delete, name='blog_delete'),
    
    # Courses CRUD
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/edit/<str:id>/', views.course_edit, name='course_edit'),
    path('courses/delete/<str:id>/', views.course_delete, name='course_delete'),
    
    # Tutorials CRUD
    path('tutorials/', views.tutorial_list, name='tutorial_list'),
    path('tutorials/add/', views.tutorial_add, name='tutorial_add'),
    path('tutorials/edit/<str:id>/', views.tutorial_edit, name='tutorial_edit'),
    path('tutorials/delete/<str:id>/', views.tutorial_delete, name='tutorial_delete'),
    
    # Users CRUD
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/edit/<str:id>/', views.user_edit, name='user_edit'),
    path('users/delete/<str:id>/', views.user_delete, name='user_delete'),
    
    # Audit Logs & Docs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('docs/', views.docs, name='docs'),
]
