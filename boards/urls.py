from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('lists/add/', views.add_list, name='add-list'),
    path('lists/<int:list_id>/add-task/', views.add_task, name='add-task'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete-task'),
    path('tasks/<int:task_id>/edit/', views.edit_task, name='edit-task'),
    path('tasks/<int:task_id>/toggle/', views.toggle_task, name='toggle-task'),
    path('lists/<int:list_id>/reorder-tasks/', views.reorder_tasks, name='reorder-tasks'),
    path('lists/reorder/', views.reorder_lists, name='reorder-lists'),
    path('boards/create/', views.create_board, name='create-board'),
    path('lists/create/', views.create_list, name='create-list'),
    path('lists/<int:list_id>/delete/', views.delete_list, name='delete-list'),

]