
"""
サービス層の統合テスト
実際のDBを使用してサービス層の動作を確認
"""

import pytest
from django.contrib.auth import get_user_model
from blog.models import Post, Category
from blog.services import PostService, CategoryService
from blog.exceptions import (
    BlogNotFoundError,
    BlogPermissionError,
    BlogValidationError
)

User = get_user_model()


@pytest.mark.django_db
class TestPostService:
    """PostServiceのテスト"""
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def other_user(self):
        return User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
    
    @pytest.fixture
    def category(self):
        return Category.objects.create(name='テストカテゴリー')
    
    @pytest.fixture
    def post(self, user, category):
        return Post.objects.create(
            title='Test Post',
            content='Test content',
            author=user,
            category=category,
            status='published'
        )
    
    @pytest.fixture
    def service(self):
        from blog.services import PostService
        return PostService()
    
    def test_create_post_success(self, service, user, category):
        """投稿作成の正常系テスト"""
        data = {
            'title': '新しい投稿',
            'content': 'コンテンツ内容',
            'category_id': category.id,
            'status': 'draft'
        }
        
        post = service.create_post(user, data)
        
        assert post.title == '新しい投稿'
        assert post.content == 'コンテンツ内容'
        assert post.author == user
        assert post.category == category
        assert post.status == 'draft'
        assert post.slug  # slug自動生成確認
    
    def test_create_post_with_slug(self, service, user, category):
        """slug指定での投稿作成"""
        data = {
            'title': 'Test Title',
            'content': 'Content',
            'slug': 'custom-slug',
            'category_id': category.id
        }
        
        post = service.create_post(user, data)
        
        assert post.slug == 'custom-slug'
    
    def test_create_post_without_category(self, service, user):
        """カテゴリーなしの投稿作成"""
        data = {
            'title': 'No Category Post',
            'content': 'Content'
        }
        
        post = service.create_post(user, data)
        
        assert post.category is None
    
    def test_create_post_invalid_category(self, service, user):
        """無効なカテゴリーIDでエラー"""
        data = {
            'title': 'Test',
            'content': 'Content',
            'category_id': 999
        }
        
        with pytest.raises(BlogValidationError) as exc_info:
            service.create_post(user, data)
        assert 'Category not found' in str(exc_info.value)
    
    def test_update_post_success(self, service, post, user):
        """投稿更新の正常系テスト"""
        data = {
            'title': '更新されたタイトル',
            'content': '更新されたコンテンツ'
        }
        
        updated_post = service.update_post(post.id, user, data)
        
        assert updated_post.title == '更新されたタイトル'
        assert updated_post.content == '更新されたコンテンツ'
        assert updated_post.updated_at > post.updated_at
    
    def test_update_post_category(self, service, post, user):
        """カテゴリーの更新"""
        new_category = Category.objects.create(name='新カテゴリー')
        data = {'category_id': new_category.id}
        
        updated_post = service.update_post(post.id, user, data)
        
        assert updated_post.category == new_category
    
    def test_update_post_not_found(self, service, user):
        """存在しない投稿の更新"""
        with pytest.raises(BlogNotFoundError):
            service.update_post(999, user, {'title': 'Test'})
    
    def test_update_post_permission_denied(self, service, post, other_user):
        """他人の投稿更新で権限エラー"""
        with pytest.raises(BlogPermissionError):
            service.update_post(post.id, other_user, {'title': 'Hack'})
    
    def test_delete_post_success(self, service, post, user):
        """投稿削除の正常系テスト"""
        post_id = post.id
        
        service.delete_post(post_id, user)
        
        assert not Post.objects.filter(id=post_id).exists()
    
    def test_delete_post_not_found(self, service, user):
        """存在しない投稿の削除"""
        with pytest.raises(BlogNotFoundError):
            service.delete_post(999, user)
    
    def test_delete_post_permission_denied(self, service, post, other_user):
        """他人の投稿削除で権限エラー"""
        with pytest.raises(BlogPermissionError):
            service.delete_post(post.id, other_user)
    
    def test_get_user_posts(self, service, user):
        """ユーザーの投稿一覧取得"""
        # 複数投稿作成
        Post.objects.create(title='Post 1', content='C1', author=user)
        Post.objects.create(title='Post 2', content='C2', author=user)
        Post.objects.create(title='Post 3', content='C3', author=user, status='draft')
        
        posts = service.get_user_posts(user)
        
        assert posts.count() == 3
        assert all(p.author == user for p in posts)
    
    def test_get_user_posts_with_status_filter(self, service, user):
        """ステータスでフィルタリング"""
        Post.objects.create(title='Pub 1', content='C1', author=user, status='published')
        Post.objects.create(title='Pub 2', content='C2', author=user, status='published')
        Post.objects.create(title='Draft', content='C3', author=user, status='draft')
        
        posts = service.get_user_posts(user, status='published')
        
        assert posts.count() == 2
        assert all(p.status == 'published' for p in posts)
    
    def test_get_post_by_id(self, service, post, user):
        """ID指定で投稿取得（内部API用）"""
        result = service.get_post_by_id(post.id, user)
        
        assert result == post
    
    def test_get_post_by_id_not_found(self, service, user):
        """存在しない投稿取得"""
        with pytest.raises(BlogNotFoundError):
            service.get_post_by_id(999, user)
    
    def test_get_post_by_id_permission_denied(self, service, user, other_user):
        """他人の下書き投稿へのアクセス拒否"""
        draft = Post.objects.create(
            title='Draft',
            content='Secret',
            author=other_user,
            status='draft'
        )
        
        with pytest.raises(BlogPermissionError):
            service.get_post_by_id(draft.id, user)
    
    def test_get_post_by_id_public_access(self, service, user, other_user):
        """公開投稿は他人でもアクセス可能"""
        public_post = Post.objects.create(
            title='Public',
            content='Content',
            author=other_user,
            status='published'
        )
        
        result = service.get_post_by_id(public_post.id, user)
        assert result == public_post
    
    def test_get_post_by_slug(self, service, user):
        """slug指定で投稿取得（公開URL用）"""
        post = Post.objects.create(
            title='Test Post',
            content='Content',
            slug='test-post',
            author=user,
            status='published'
        )
        
        result = service.get_post_by_slug('test-post', user)
        assert result == post
    
    def test_get_post_by_slug_anonymous(self, service, user):
        """匿名ユーザーでも公開投稿は取得可能"""
        post = Post.objects.create(
            title='Public Post',
            content='Content',
            slug='public-post',
            author=user,
            status='published'
        )
        
        result = service.get_post_by_slug('public-post', None)
        assert result == post
    
    def test_get_post_by_slug_draft_blocked(self, service, user, other_user):
        """他人の下書きはslugでもアクセス不可"""
        draft = Post.objects.create(
            title='Draft',
            content='Secret',
            slug='draft-post',
            author=other_user,
            status='draft'
        )
        
        with pytest.raises(BlogPermissionError):
            service.get_post_by_slug(draft.slug, user)


@pytest.mark.django_db
class TestCategoryService:
    """CategoryServiceのテスト"""
    
    @pytest.fixture
    def service(self):
        return CategoryService()
    
    def test_get_or_create_category_new_japanese(self, service):
        """新規カテゴリー作成(日本語)"""
        category = service.get_or_create_category('新カテゴリー')
        
        assert category.name == '新カテゴリー'
        # 日本語はランダム文字列になる
        assert category.slug.startswith('category-')
        assert len(category.slug) == len('category-') + 8  # category- + 8文字
        assert Category.objects.filter(name='新カテゴリー').exists()

    def test_get_or_create_category_new_english(self, service):
        """新規カテゴリー作成（英語）"""
        category = service.get_or_create_category('Programming')
        
        assert category.name == 'Programming'
        assert category.slug == 'programming'  # 英語は正常にslugify
        assert Category.objects.filter(name='Programming').exists()
    
    def test_get_or_create_category_existing(self, service):
        """既存カテゴリー取得"""
        existing = Category.objects.create(name='既存')
        
        category = service.get_or_create_category('既存')
        
        assert category == existing
        assert Category.objects.filter(name='既存').count() == 1
    
    def test_get_all_categories(self, service):
        """全カテゴリー取得"""
        Category.objects.create(name='Cat1')
        Category.objects.create(name='Cat2')
        Category.objects.create(name='Cat3')
        
        categories = service.get_all_categories()
        
        assert categories.count() == 3
    
    def test_get_category_by_slug(self, service):
        """slugでカテゴリー取得"""
        cat = Category.objects.create(name='テスト', slug='test-slug')
        
        result = service.get_category_by_slug('test-slug')
        
        assert result == cat
    
    def test_get_category_by_slug_not_found(self, service):
        """存在しないslugでNone返却"""
        result = service.get_category_by_slug('not-exists')
        
        assert result is None
    
    def test_delete_category(self, service):
        """カテゴリー削除"""
        cat = Category.objects.create(name='削除対象')
        cat_id = cat.id
        
        service.delete_category(cat_id)
        
        assert not Category.objects.filter(id=cat_id).exists()
    
    def test_delete_category_with_posts(self, service):
        """投稿があるカテゴリーの削除（投稿のカテゴリーはNULLになる）"""
        user = User.objects.create_user(username='test', email='t@t.com')
        cat = Category.objects.create(name='カテゴリー')
        post = Post.objects.create(
            title='Test',
            content='Content',
            author=user,
            category=cat
        )
        
        service.delete_category(cat.id)
        
        post.refresh_from_db()
        assert post.category is None
        assert not Category.objects.filter(id=cat.id).exists()
    
    def test_update_category(self, service):
        """カテゴリー更新"""
        cat = Category.objects.create(name='古い名前')
        
        updated = service.update_category(cat.id, name='新しい名前')
        
        assert updated.name == '新しい名前'
        # slugは変更されない
        assert updated.slug == cat.slug