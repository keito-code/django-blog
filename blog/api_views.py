from rest_framework import viewsets, filters, generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Post, Category
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    PostUpdateSerializer,
    CategorySerializer
)
from .permissions import IsAuthorOrReadOnly
from .pagination import CustomPageNumberPagination


class PostViewSet(viewsets.ModelViewSet):
    """
    ブログ記事のCRUD操作を提供するAPI ViewSet
    
    エンドポイント:
    - GET /v1/posts/ - 記事一覧
    - POST /v1/posts/ - 記事作成（要認証）
    - GET /v1/posts/{slug}/ - 記事詳細
    - PATCH /v1/posts/{slug}/ - 記事更新（作者のみ、status変更で公開/下書き切り替え）
    - DELETE /v1/posts/{slug}/ - 記事削除（作者のみ）
    """
    
    permission_classes = [IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'author', 'category']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    pagination_class = CustomPageNumberPagination
    lookup_field = 'slug'
    
    def get_queryset(self):
        """認証状態に応じたクエリセット"""
        queryset = Post.objects.select_related('author', 'category')
        
        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(status='published') | Q(author=self.request.user)
            ).distinct()
        else:
            return queryset.filter(status='published')
    
    def get_serializer_class(self):
        """アクションに応じたシリアライザー選択"""
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PostUpdateSerializer
        return PostListSerializer
    
    def perform_create(self, serializer):
        """作成時に作者を自動設定"""
        serializer.save(author=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        """
        記事の部分更新（status変更による公開/下書き切り替えを含む）
        
        PATCH /v1/posts/{slug}/
        {
            "status": "published"  // または "draft"
        }
        """
        instance = self.get_object()
        
        # status変更時のバリデーション
        if 'status' in request.data:
            new_status = request.data['status']
            
            # バリデーション
            if new_status not in ['draft', 'published']:
                raise ValidationError({'status': '有効なステータスは "draft" または "published" です'})
                        
            # 同じステータスへの変更チェック
            if instance.status == new_status:
                status_text = '公開' if new_status == 'published' else '下書き'
                raise ValidationError(f'この投稿は既に{status_text}状態です')
        
        return super().partial_update(request, *args, **kwargs)

class UserPostListView(generics.ListAPIView):
    """
    ユーザーの投稿一覧
    GET /v1/users/me/posts/
    """
    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        """現在のユーザーの投稿を返す"""
        return Post.objects.filter(
            author=self.request.user
        ).select_related('author', 'category')


class CategoryViewSet(viewsets.ModelViewSet):
    """
    カテゴリーのCRUD操作を提供するAPI ViewSet
    
    エンドポイント:
    - GET /v1/categories/ - カテゴリー一覧（誰でも）
    - POST /v1/categories/ - カテゴリー作成（管理者のみ）
    - GET /v1/categories/{slug}/ - カテゴリー詳細（誰でも）
    - PUT/PATCH /v1/categories/{slug}/ - カテゴリー更新（管理者のみ）
    - DELETE /v1/categories/{slug}/ - カテゴリー削除（管理者のみ）
    - GET /v1/categories/{slug}/posts/ - カテゴリーの投稿一覧（誰でも）
    """
    
    queryset = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    )
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    def get_permissions(self):
        """メソッドに応じた権限設定"""
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    @action(detail=True, methods=['get'])
    def posts(self, request, slug=None):
        """カテゴリーに属する公開記事一覧"""
        category = self.get_object()
        posts = Post.objects.filter(
            category=category,
            status='published'
        ).select_related('author')
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)