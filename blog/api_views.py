from rest_framework import viewsets, filters
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
    - PUT/PATCH /v1/posts/{slug}/ - 記事更新（作者のみ）
    - DELETE /v1/posts/{slug}/ - 記事削除（作者のみ）
    - GET /v1/posts/my_posts/ - 自分の投稿一覧（要認証）
    - POST /v1/posts/{slug}/publish/ - 投稿を公開（作者のみ）
    - POST /v1/posts/{slug}/unpublish/ - 投稿を下書きに戻す（作者のみ）
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """現在のユーザーの投稿一覧"""
        posts = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAuthorOrReadOnly])
    def publish(self, request, slug=None):
        """
        下書きを公開
        
        権限チェックはIsAuthorOrReadOnlyが処理
        エラーはDRF標準例外をraiseし、custom_exception_handlerがJSend形式に変換
        成功時はレンダラーが自動的にJSend形式にラップ
        """
        post = self.get_object()
        
        # 既に公開済みの場合はバリデーションエラー
        if post.status == 'published':
            raise ValidationError('この投稿は既に公開されています')
        
        post.status = 'published'
        post.save(update_fields=['status', 'updated_at'])
        
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)  # レンダラーが自動的にJSend形式に
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAuthorOrReadOnly])
    def unpublish(self, request, slug=None):
        """
        公開記事を下書きに戻す
        
        権限チェックはIsAuthorOrReadOnlyが処理
        """
        post = self.get_object()
        
        # 既に下書きの場合はバリデーションエラー
        if post.status == 'draft':
            raise ValidationError('この投稿は既に下書き状態です')
        
        post.status = 'draft'
        post.save(update_fields=['status', 'updated_at'])
        
        serializer = PostDetailSerializer(post)
        return Response(serializer.data)  # レンダラーが自動的にJSend形式に


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