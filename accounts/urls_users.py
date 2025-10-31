from django.urls import path
from .views import CurrentUserView
from blog.views import UserPostListView

urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='me'),
    path('me/posts/', UserPostListView.as_view(), name='my-posts')
]