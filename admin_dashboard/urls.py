from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('logs/', views.logs, name='logs'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dataset/<path:path>', views.dataset, name='dataset'),
    path('add/', views.add_user, name='add_user'),
    path('edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    path('toggle-blocked/<int:user_id>/', views.toggle_blocked, name='toggle_blocked'),
    path('encoding-status/<int:user_id>/', views.encoding_status_view, name='encoding_status'),
]