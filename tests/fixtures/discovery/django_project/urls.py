"""Sample Django URL configuration for testing route discovery."""
from django.urls import path, include

urlpatterns = [
    path("api/users/", views.user_list, name="user-list"),
    path("api/users/<int:pk>/", views.user_detail, name="user-detail"),
    path("api/items/", views.item_list, name="item-list"),
    path("api/items/<slug:slug>/", views.item_detail, name="item-detail"),
    path("health/", views.health_check, name="health"),
]
