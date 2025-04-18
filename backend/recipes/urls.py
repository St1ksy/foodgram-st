from django.urls import path

from .views import recipe_detail

app_name = 'recipes'

urlpatterns = [
    path('s/<int:pk>/', recipe_detail, name='shortlink'),
]
