from django.contrib import admin
from django.urls import path
from account import views
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.index, name='index'),
    path('delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('check/<int:pk>/', views.toggle_checklist, name='toggle_checklist'),
    path("living/", views.living, name="living"),
]