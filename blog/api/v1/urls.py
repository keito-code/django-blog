from django.urls import path, include
from rest_framework.routers import DefaultRouter
from blog.api_views import PostViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    # API エンドポイント（Router）
    path('', include(router.urls)),
]