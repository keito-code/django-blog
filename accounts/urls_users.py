from django.urls import path
from .views import CurrentUserView
from blog.api_views import UserPostListView

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='me'),
    path('me/posts/', UserPostListView.as_view(), name='my-posts')
]