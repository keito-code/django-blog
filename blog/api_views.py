from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Post
from .serializers import PostListSerializer, PostDetailSerializer
from .permissions import IsAuthorOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

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
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            # 詳細取得、作成、更新時はDetailSerializerを使用
            return PostDetailSerializer
        return self.serializer_class
    
    def perform_create(self, serializer):
        """
        記事作成時に作成者を自動設定
        """
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_posts(self, request):
        """
        現在のユーザーの投稿一覧を取得
        
        認証が必要です。
        """
        posts = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def drafts(self, request):
        """
        現在のユーザーの下書き一覧を取得
        
        認証が必要です。
        """
        drafts = self.get_queryset().filter(author=request.user, status='draft')
        page = self.paginate_queryset(drafts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(drafts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """
        下書きを公開状態に変更
        
        投稿の作者のみが実行可能です。
        """
        # 投稿取得
        post = self.get_object()

        # 権限チェック
        if post.author != request.user:
            return Response(
                {'detail': 'この投稿を公開する権限がありません。'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # ステータスチェック
        if post.status == 'published':
            return Response(
                {'detail': 'この投稿は既に公開されています。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 公開処理
        post.status = 'published'
        
        # 保存
        post.save(update_fields=['status', 'updated'])

        # レスポンス
        serializer = self.get_serializer(post)
        return Response(
            {
                'message': '投稿を公開しました。',
                'post': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unpublish(self, request, pk=None):
        """
        公開投稿を下書きに戻す
        
        投稿の作者のみが実行可能です。
        """
        post = self.get_object()
        
        if post.author != request.user:
            return Response(
                {'detail': 'この投稿を非公開にする権限がありません。'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if post.status == 'draft':
            return Response(
                {'detail': 'この投稿は既に下書き状態です。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        post.status = 'draft'
        post.save(update_fields=['status', 'updated'])
        
        serializer = self.get_serializer(post)
        return Response(
            {
                'message': '投稿を下書きに戻しました。',
                'post': serializer.data
            },
            status=status.HTTP_200_OK
        )









