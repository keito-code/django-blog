
import pytest
from unittest.mock import Mock, patch
from blog.services import PostService, CategoryService
from blog.exceptions import BlogPermissionError, BlogValidationError, BlogNotFoundError


class TestPostService:
    """PostServiceのユニットテスト（DB不使用）"""
    
    @pytest.fixture
    def service(self):
        return PostService()
    
    @pytest.fixture
    def mock_user(self):
        user = Mock()
        user.id = 1
        user.is_authenticated = True
        return user

    @patch('blog.services.Category.objects.get')
    @patch('blog.services.Post.objects.create')
    def test_create_post_success(self, mock_post_create, mock_category_get, service, mock_user):
        """正常な投稿作成"""
        mock_category = Mock(id=1, name='Tech')
        mock_category_get.return_value = mock_category
        
        mock_post = Mock(id=1, title='Test', slug='auto-slug')
        mock_post_create.return_value = mock_post
        
        data = {
            'title': 'Test Title',
            'content': 'Test Content',
            'category_id': 1,
            'status': 'draft'
        }
        
        result = service.create_post(mock_user, data)
        
        mock_post_create.assert_called_once_with(
            title='Test Title',
            content='Test Content',
            slug=None,  # 自動生成のためNone
            author=mock_user,
            category=mock_category,
            status='draft'
        )
        assert result == mock_post
    
    @patch('blog.services.Post.objects.create')
    def test_create_post_ignores_manual_slug(self, mock_post_create, service, mock_user):
        """手動slugは無視される"""
        mock_post = Mock(slug='auto-generated')
        mock_post_create.return_value = mock_post
        
        data = {
            'title': 'Test',
            'content': 'Content',
            'slug': 'manual-slug'  # 無視されるべき
        }
        
        result = service.create_post(mock_user, data)
        
        # slugはNoneで渡される（手動指定は無視）
        call_args = mock_post_create.call_args[1]
        assert call_args['slug'] is None
        assert result.slug == 'auto-generated'
    
    
    @patch('blog.services.Category.objects.get')
    def test_create_post_invalid_category(self, mock_category_get, service, mock_user):
        """無効なカテゴリーIDでエラー"""
        # Arrange
        from blog.models import Category
        mock_category_get.side_effect = Category.DoesNotExist()
        
        data = {
            'title': 'Test',
            'content': 'Content',
            'category_id': 999
        }
        
        # Act & Assert
        with pytest.raises(BlogValidationError) as exc:
            service.create_post(mock_user, data)
        assert 'Category not found: 999' in str(exc.value)

    @patch('blog.services.Post.objects.get')
    def test_update_post_success(self, mock_post_get, service, mock_user):
        """自分の投稿を正常に更新"""
        mock_post = Mock(author=mock_user, title='Old', content='Old Content')
        mock_post_get.return_value = mock_post
        
        data = {
            'title': 'Updated Title',
            'content': 'Updated Content'
        }
        
        result = service.update_post(1, mock_user, data)
        
        assert mock_post.title == 'Updated Title'
        assert mock_post.content == 'Updated Content'
        mock_post.save.assert_called_once()
        assert result == mock_post
    
    @patch('blog.services.Post.objects.get')
    def test_update_post_partial(self, mock_post_get, service, mock_user):
        """部分更新も可能"""
        mock_post = Mock(author=mock_user, title='Original')
        mock_post_get.return_value = mock_post
        
        result = service.update_post(1, mock_user, {'title': 'New'})
        
        assert mock_post.title == 'New'
        mock_post.save.assert_called_once()

    @patch('blog.services.Post.objects.get')
    def test_update_post_permission_denied(self, mock_post_get, service, mock_user):
        """他人の投稿は更新不可"""
        other_user = Mock(id=2)
        mock_post = Mock(author=other_user)
        mock_post_get.return_value = mock_post
        
        with pytest.raises(BlogPermissionError, match="permission to update"):
            service.update_post(1, mock_user, {'title': 'Hack'})
    
    @patch('blog.services.Post.objects.get')
    def test_update_post_not_found(self, mock_post_get, service, mock_user):
        """存在しない投稿の更新"""
        from blog.models import Post
        mock_post_get.side_effect = Post.DoesNotExist()
        
        with pytest.raises(BlogNotFoundError, match="Post not found: 999"):
            service.update_post(999, mock_user, {})

    @patch('blog.services.Post.objects.get')
    def test_delete_post_success(self, mock_post_get, service, mock_user):
        """自分の投稿を正常に削除"""
        mock_post = Mock(author=mock_user)
        mock_post_get.return_value = mock_post
        
        service.delete_post(1, mock_user)
        
        mock_post.delete.assert_called_once()
    
    @patch('blog.services.Post.objects.get')
    def test_delete_post_permission_denied(self, mock_post_get, service, mock_user):
        """他人の投稿は削除不可"""
        other_user = Mock(id=2)
        mock_post = Mock(author=other_user)
        mock_post_get.return_value = mock_post
        
        with pytest.raises(BlogPermissionError, match="permission to delete"):
            service.delete_post(1, mock_user)
    
    @patch('blog.services.Post.objects.get')
    def test_delete_post_not_found(self, mock_post_get, service, mock_user):
        """存在しない投稿の削除"""
        # Arrange
        from blog.models import Post
        mock_post_get.side_effect = Post.DoesNotExist()
        
        # Act & Assert
        with pytest.raises(BlogNotFoundError):
            service.delete_post(999, mock_user)
    
    def test_get_post_by_id_draft_permission(self, service):
        """下書きの権限チェックロジック"""
        # Arrange
        mock_post = Mock(status='draft')
        mock_post.author = Mock(id=1)
        mock_user = Mock(id=2)
        
        # モデルの取得をモック
        with patch('blog.services.Post.objects.get', return_value=mock_post):
            # Act & Assert
            with pytest.raises(BlogPermissionError) as exc:
                service.get_post_by_id(1, mock_user)
            assert "You don't have permission to view this draft" in str(exc.value)


class TestCategoryService:
    """CategoryServiceのユニットテスト"""
    
    @pytest.fixture
    def service(self):
        return CategoryService()

    @patch('blog.services.Category.objects.get_or_create')
    def test_get_or_create_category_new(self, mock_get_or_create, service):
        """新規カテゴリー作成"""
        mock_category = Mock(name='Tech', slug='tech')
        mock_get_or_create.return_value = (mock_category, True)
        
        result = service.get_or_create_category('Tech')
        
        mock_get_or_create.assert_called_once_with(name='Tech')
        assert result == mock_category
    
    @patch('blog.services.Category.objects.get_or_create')
    def test_get_or_create_category_existing(self, mock_get_or_create, service):
        """既存カテゴリー取得"""
        mock_category = Mock(name='Tech', slug='tech')
        mock_get_or_create.return_value = (mock_category, False)
        
        result = service.get_or_create_category('Tech')
        
        assert result == mock_category
    
    @patch('blog.services.Category.objects.get')
    def test_update_category_success(self, mock_get, service):
        """カテゴリー名を正常に更新"""
        mock_category = Mock(name='Old Name', slug='old-slug')
        mock_get.return_value = mock_category
        
        result = service.update_category(1, 'New Name')
        
        assert mock_category.name == 'New Name'
        mock_category.save.assert_called_once_with(update_fields=['name'])
        assert result == mock_category
    
    @patch('blog.services.Category.objects.get')
    def test_update_category_not_found(self, mock_get, service):
        """存在しないカテゴリーの更新"""
        # Arrange
        from blog.models import Category
        mock_get.side_effect = Category.DoesNotExist()
        
        # Act & Assert
        with pytest.raises(BlogNotFoundError):
            service.update_category(999, 'New Name')

    @patch('blog.services.Category.objects.get')
    def test_delete_category_success(self, mock_get, service):
        """カテゴリーを正常に削除"""
        mock_category = Mock()
        mock_get.return_value = mock_category
        
        service.delete_category(1)
        
        mock_category.delete.assert_called_once()
    
    @patch('blog.services.Category.objects.get')
    def test_delete_category_not_found(self, mock_get, service):
        """存在しないカテゴリーの削除は静かに無視"""
        from blog.models import Category
        mock_get.side_effect = Category.DoesNotExist()
        
        # エラーを出さない（既に削除済みとして扱う）
        service.delete_category(999)