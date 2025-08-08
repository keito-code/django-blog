from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Post
from .serializers import PostListSerializer, PostDetailSerializer
from .permissions import IsAuthorOrReadOnly



class CustomPageNumberPagination(PageNumberPagination):
    """カスタムページネーション"""
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100


class PostViewSet(viewsets.ModelViewSet):
    """
    ブログ記事のCRUD操作を提供するAPI ViewSet
    
    このAPIでは以下の操作が可能です：
    - **リスト取得** (GET /api/v1/blog/posts/): 記事一覧を取得
    - **詳細取得** (GET /api/v1/blog/posts/{id}/): 特定の記事を取得
    - **作成** (POST /api/v1/blog/posts/): 新規記事を作成（要認証）
    - **更新** (PUT/PATCH /api/v1/blog/posts/{id}/): 記事を更新（要認証、作者のみ）
    - **削除** (DELETE /api/v1/blog/posts/{id}/): 記事を削除（要認証、作者のみ）
    
    ## 認証とアクセス権限
    - 未認証ユーザー: 公開記事（published）の閲覧のみ可能
    - 認証済みユーザー: 自分の記事は全て（draft含む）アクセス可能、作成・編集・削除可能
    
    ## フィルタリング
    - `status`: 記事のステータス（published/draft）でフィルタ
    - `author`: 作者のIDでフィルタ
    
    ## 検索
    - `search`: タイトルと本文を対象にキーワード検索
    
    ## ソート
    - `ordering`: created, updated, publish フィールドでソート可能
    - デフォルトは作成日時の降順（-created）
    
    ## ページネーション
    - デフォルト: 10件/ページ
    - `pageSize`: 最大100件までページサイズ変更可能
    """


    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'author']
    search_fields = ['title', 'content']
    ordering_fields = ['created', 'updated', 'publish']
    ordering = ['-created']
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        """
        クエリセットをユーザーの認証状態に応じて制御
        - 未認証: 公開記事のみ
        - 認証済み: 公開記事 + 自分の全ての記事
        """
        if self.request.user.is_authenticated:
            # 認証済みユーザーは公開記事 + 自分の全ての記事を見ることができる
            return Post.objects.filter(
                Q(status='published') | Q(author=self.request.user)
            ).distinct().order_by('-created')
        else:
            # 未認証ユーザーは公開記事のみ
            return Post.objects.filter(status='published').order_by('-created')
    
    def get_serializer_class(self):
        """
        アクションに応じてシリアライザーを選択
        """
        if self.action == 'retrieve':
            return PostDetailSerializer
        return self.serializer_class
    
    def perform_create(self, serializer):
        """
        記事作成時に作成者を自動設定
        """
        serializer.save(author=self.request.user)


