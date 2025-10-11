from typing import Optional, Dict, Any
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from blog.models import Post, Category
from blog.exceptions import (
    BlogNotFoundError,
    BlogPermissionError,
    BlogValidationError
)

User = get_user_model()


class PostService:
    """投稿に関するビジネスロジック"""
    
    def create_post(self, user: User, data: Dict[str, Any]) -> Post:
        """
        投稿を作成
        
        Args:
            user: 作成ユーザー
            data: 投稿データ（title, content, slug, category_id, status）
        
        Returns:
            作成された投稿
        
        Raises:
            BlogValidationError: カテゴリーが見つからない場合
        """
        # カテゴリー処理
        category = None
        if 'category_id' in data:
            try:
                category = Category.objects.get(id=data['category_id'])
            except Category.DoesNotExist:
                raise BlogValidationError(f"Category not found: {data['category_id']}")
        
        # 投稿作成
        post = Post.objects.create(
            title=data.get('title'),
            content=data.get('content'),
            slug=data.get('slug'),  # Noneの場合はモデルで自動生成
            author=user,
            category=category,
            status=data.get('status', 'published')
        )
        
        return post
    
    def update_post(self, post_id: int, user: User, data: Dict[str, Any]) -> Post:
        """
        投稿を更新
        
        Args:
            post_id: 投稿ID
            user: 更新ユーザー
            data: 更新データ
        
        Returns:
            更新された投稿
        
        Raises:
            BlogNotFoundError: 投稿が見つからない
            BlogPermissionError: 権限がない
            BlogValidationError: カテゴリーが見つからない
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise BlogNotFoundError(f"Post not found: {post_id}")
        
        # 権限チェック
        if post.author != user:
            raise BlogPermissionError("You don't have permission to update this post")
        
        # カテゴリー処理
        if 'category_id' in data:
            try:
                post.category = Category.objects.get(id=data['category_id'])
            except Category.DoesNotExist:
                raise BlogValidationError(f"Category not found: {data['category_id']}")
        
        # フィールド更新
        for field in ['title', 'content', 'slug', 'status']:
            if field in data:
                setattr(post, field, data[field])
        post.save()
        
        return post
    
    def delete_post(self, post_id: int, user: User) -> None:
        """
        投稿を削除
        
        Args:
            post_id: 投稿ID
            user: 削除ユーザー
        
        Raises:
            BlogNotFoundError: 投稿が見つからない
            BlogPermissionError: 権限がない
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise BlogNotFoundError(f"Post not found: {post_id}")
        
        # 権限チェック
        if post.author != user:
            raise BlogPermissionError("You don't have permission to delete this post")
        
        post.delete()
    
    def get_user_posts(self, user: User, status: Optional[str] = None) -> QuerySet:
        """
        ユーザーの投稿一覧を取得
        
        Args:
            user: ユーザー
            status: ステータスフィルター（optional）
        
        Returns:
            投稿のQuerySet
        """
        posts = Post.objects.filter(author=user)
        
        if status:
            posts = posts.filter(status=status)
        
        return posts.order_by('-created')
    
    def get_post_by_id(self, post_id: int, user: User) -> Post:
        """
        ID指定で投稿を取得（内部API、管理画面、編集画面など用）
        
        Args:
            post_id: 投稿ID
            user: リクエストユーザー
        
        Returns:
            投稿
        
        Raises:
            BlogNotFoundError: 投稿が見つからない
            BlogPermissionError: 下書きへのアクセス権限がない
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            raise BlogNotFoundError(f"Post not found: {post_id}")
        
        # 下書きは作者のみアクセス可能
        if post.status == 'draft' and post.author != user:
            raise BlogPermissionError("You don't have permission to view this draft")
        
        return post
    
    def get_post_by_slug(self, slug: str, user: Optional[User] = None) -> Post:
        """
        slug指定で投稿を取得（公開URL用）
        
        Args:
            slug: 投稿のslug
            user: リクエストユーザー（Noneの場合は匿名ユーザー）
        
        Returns:
            投稿
        
        Raises:
            BlogNotFoundError: 投稿が見つからない
            BlogPermissionError: 下書きへのアクセス権限がない
        """
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            raise BlogNotFoundError(f"Post not found: {slug}")
        
        # 下書きは作者のみアクセス可能
        if post.status == 'draft':
            if not user or not user.is_authenticated or post.author != user:
                raise BlogPermissionError("You don't have permission to view this draft")
        
        return post


class CategoryService:
    """カテゴリーに関するビジネスロジック"""
    
    def get_or_create_category(self, name: str) -> Category:
        """
        カテゴリーを取得または作成
        
        Args:
            name: カテゴリー名
        
        Returns:
            カテゴリーインスタンス
        """
        category, created = Category.objects.get_or_create(name=name)
        return category
    
    def get_all_categories(self) -> QuerySet:
        """
        全カテゴリーを取得
        
        Returns:
            カテゴリーのQuerySet
        """
        return Category.objects.all().order_by('name')
    
    def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """
        slugでカテゴリーを取得
        
        Args:
            slug: カテゴリーslug
        
        Returns:
            カテゴリーインスタンス or None
        """
        try:
            return Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            return None
    
    def delete_category(self, category_id: int) -> None:
        """
        カテゴリーを削除
        関連する投稿のカテゴリーはNULLになる
        
        Args:
            category_id: カテゴリーID
        """
        try:
            category = Category.objects.get(id=category_id)
            category.delete()
        except Category.DoesNotExist:
            pass  # 既に削除されている場合は何もしない
    
    def update_category(self, category_id: int, name: str) -> Category:
        """
        カテゴリー名を更新（slugは変更しない）
        
        Args:
            category_id: カテゴリーID
            name: 新しい名前
        
        Returns:
            更新されたカテゴリー
        
        Raises:
            BlogNotFoundError: カテゴリーが見つからない
        """
        try:
            category = Category.objects.get(id=category_id)
            category.name = name
            category.save(update_fields=['name'])
            return category
        except Category.DoesNotExist:
            raise BlogNotFoundError(f"Category not found: {category_id}")