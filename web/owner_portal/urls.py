from django.urls import path
from .views import owner_home

urlpatterns = [
    path("", owner_home, name="owner-home"),
]