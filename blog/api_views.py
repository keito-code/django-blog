from rest_framework import viewsets, filters, generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from rest_framework.decorators import action
from core.responses import ResponseFormatter
from drf_spectacular.utils import extend_schema, extend_schema_view
from .mixins import JSendResponseMixin
from .models import Post, Category
from .permissions import IsAuthorOrReadOnly
from .pagination import CustomPageNumberPagination
from .schema import JSendAutoSchema
from core.serializers import (
    SuccessResponseSerializer,
    FailResponseSerializer,
    ErrorResponseSerializer  
)
from .serializers import (
    # Model Serializers
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    PostUpdateSerializer,
    CategorySerializer,
    # Response Serializers
    PostListResponseSerializer,
    PostDetailResponseSerializer,
    PostCreateResponseSerializer,
    PostUpdateResponseSerializer,
    CategoryListResponseSerializer,
    CategoryDetailResponseSerializer,
    CategoryCreateResponseSerializer,
    CategoryUpdateResponseSerializer,
    CategoryPostsResponseSerializer,
    UserPostListResponseSerializer,
)

"""
operation_id を手動指定している理由
list (GET /v1/posts/) と retrieve (GET /v1/posts/{slug}/) は
両方とも GET メソッドのため、自動生成では operation_id が衝突するから
"""

@extend_schema_view(
    list=extend_schema(
        operation_id='posts_list',
        summary="記事一覧取得",
        description="公開された記事の一覧を取得",
        responses={
            200: PostListResponseSerializer,
            422: FailResponseSerializer
        },
        tags=['Posts']
    ),
    create=extend_schema(
        operation_id='posts_create',
        summary="記事作成",
        description="新しい記事を作成（要認証）",
        request=PostCreateSerializer,
        responses={
            201: PostCreateResponseSerializer,
            401: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Posts']
    ),
    retrieve=extend_schema(
        operation_id='posts_retrieve',
        summary="記事詳細取得",
        description="指定されたスラッグの記事詳細を取得。作者は自分の下書きも閲覧可能",
        responses={
            200: PostDetailResponseSerializer,
            404: ErrorResponseSerializer
        },
        tags=['Posts']
    ),
    update=extend_schema(
        operation_id='posts_update',
        summary="記事更新（全体）",
        description="記事を更新（作者のみ）",
        request=PostUpdateSerializer,
        responses={
            200: PostUpdateResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Posts']
    ),
    partial_update=extend_schema(
        operation_id='posts_partial_update',
        summary="記事部分更新",
        description="記事を部分更新（作者のみ）。status変更で公開/下書き切り替え可能",
        request=PostUpdateSerializer,
        responses={
            200: PostUpdateResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Posts']
    ),
    destroy=extend_schema(
        operation_id='posts_destroy',
        summary="記事削除",
        description="記事を削除（作者のみ）",
        responses={
            200: SuccessResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer
        },
        tags=['Posts']
    )
)

class PostViewSet(JSendResponseMixin, viewsets.ModelViewSet):
    """
    ブログ記事のCRUD操作を提供するAPI ViewSet
    
    エンドポイント:
    - GET /v1/posts/ - 記事一覧
    - POST /v1/posts/ - 記事作成（要認証）
    - GET /v1/posts/{slug}/ - 記事詳細
    - PATCH /v1/posts/{slug}/ - 記事更新（作者のみ、status変更で公開/下書き切り替え）
    - DELETE /v1/posts/{slug}/ - 記事削除（作者のみ）
    """

    schema = JSendAutoSchema()
    resource_name = 'posts'
    resource_name_singular = 'post'
    permission_classes = [IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'author', 'category']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    pagination_class = CustomPageNumberPagination
    lookup_field = 'slug'
    
    def get_queryset(self):
        queryset = Post.objects.select_related('author', 'category')

        # 一覧: 公開のみ
        if self.action == 'list':
            return queryset.filter(status='published')

        # 詳細/編集: 公開 + 自分の下書き
        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(status='published') | Q(author=self.request.user)
            )
    
        # 未認証: 公開のみ
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

        data = request.data.copy() 
        
        # status変更時のバリデーション
        if 'status' in request.data:
            new_status = request.data['status']
            
            # バリデーション
            if new_status not in ['draft', 'published']:
                return ResponseFormatter.validation_error({
                    'status': ['有効なステータスは "draft" または "published" です']
                })
                        
            # 同じステータスならフィールドを無視
            if instance.status == new_status:
                data.pop('status')

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # JSend形式で返す
        return ResponseFormatter.success({
            self.resource_name_singular: serializer.data
        })

"""
generics.ListAPIView に @extend_schema をクラスの前に配置する場合、
operation_id を指定すると drf-spectacular が内部の get() メソッドと
二重解釈してエラーが発生する。そのため operation_id は指定せず自動生成に任せる。
"""

@extend_schema(
    summary="ユーザーの投稿一覧",
    description="認証済みユーザー自身の投稿一覧を取得",
    responses={
        200: UserPostListResponseSerializer,
        401: ErrorResponseSerializer
    },
    tags=['Posts']
)

class UserPostListView(generics.ListAPIView):
    """
    ユーザーの投稿一覧
    GET /v1/users/me/posts/
    """
    schema = JSendAutoSchema()
    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    # リソース名を定義（ページネーション用）
    resource_name = 'posts'

    def get_queryset(self):
        """現在のユーザーの投稿を返す"""
        return Post.objects.filter(
            author=self.request.user
        ).select_related('author', 'category')

@extend_schema_view(
    list=extend_schema(
        operation_id='categories_list',
        summary="カテゴリー一覧取得",
        description="すべてのカテゴリー一覧を取得（公開記事数付き）",
        responses={
            200: CategoryListResponseSerializer
        },
        tags=['Categories']
    ),
    create=extend_schema(
        operation_id='categories_create',
        summary="カテゴリー作成",
        description="新しいカテゴリーを作成（管理者のみ）",
        request=CategorySerializer,
        responses={
            201: CategoryCreateResponseSerializer,
            403: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Categories']
    ),
    retrieve=extend_schema(
        operation_id='categories_retrieve',
        summary="カテゴリー詳細取得",
        description="指定されたスラッグのカテゴリー詳細を取得",
        responses={
            200: CategoryDetailResponseSerializer,
            404: ErrorResponseSerializer
        },
        tags=['Categories']
    ),
    update=extend_schema(
        operation_id='categories_update',
        summary="カテゴリー更新（全体）",
        description="カテゴリーを更新（管理者のみ）",
        request=CategorySerializer,
        responses={
            200: CategoryUpdateResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Categories']
    ),
    partial_update=extend_schema(
        operation_id='categories_partial_update',
        summary="カテゴリー部分更新",
        description="カテゴリーを部分更新（管理者のみ）",
        request=CategorySerializer,
        responses={
            200: CategoryUpdateResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            422: FailResponseSerializer,
        },
        tags=['Categories']
    ),
    destroy=extend_schema(
        operation_id='categories_destroy',
        summary="カテゴリー削除",
        description="カテゴリーを削除（管理者のみ）",
        responses={
            200: SuccessResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer
        },
        tags=['Categories']
    ),
    posts=extend_schema(
        operation_id='categories_posts_list',
        summary="カテゴリーの投稿一覧",
        description="指定されたカテゴリーに属する公開記事一覧を取得",
        responses={
            200: CategoryPostsResponseSerializer,
            404: ErrorResponseSerializer
        },
        tags=['Categories']
    )
)

class CategoryViewSet(JSendResponseMixin, viewsets.ModelViewSet):
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

    # リソース名を定義
    resource_name = 'categories'
    resource_name_singular = 'category'
    
    queryset = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    )
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    pagination_class = None # カテゴリーの数が少ないと判断したため
    
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
        ).select_related('author').order_by('-created_at')

        original_resource_name = self.resource_name
        self.resource_name = 'posts'
        try:
            paginator = CustomPageNumberPagination()
            page = paginator.paginate_queryset(posts, request, view=self)

            if page is not None:
                serializer =PostListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = PostListSerializer(posts, many=True)
            return ResponseFormatter.success({'posts': serializer.data})
        finally:
            # 例外が起きても確実に戻す
            self.resource_name = original_resource_name