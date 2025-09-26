import pytest
from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets
from blog.api_views import PostViewSet

class TestPostViewSetLogic:
    """PostViewSetのロジックのユニットテスト（DB不使用）"""
    
    def test_get_serializer_class_for_list(self):
        """listアクションで正しいシリアライザーを選択"""
        viewset = PostViewSet()
        viewset.action = 'list'
        
        from blog.serializers import PostListSerializer
        assert viewset.get_serializer_class() == PostListSerializer
    
    def test_get_serializer_class_for_create(self):
        """createアクションで正しいシリアライザーを選択"""
        viewset = PostViewSet()
        viewset.action = 'create'
        
        from blog.serializers import PostCreateSerializer
        assert viewset.get_serializer_class() == PostCreateSerializer
    
    def test_get_serializer_class_for_update(self):
        """updateアクションで正しいシリアライザーを選択"""
        viewset = PostViewSet()
        viewset.action = 'update'
        
        from blog.serializers import PostUpdateSerializer
        assert viewset.get_serializer_class() == PostUpdateSerializer
    
    @patch('blog.api_views.Post.objects')
    def test_get_queryset_authenticated(self, mock_post_objects):
        """認証済みユーザーのクエリセット"""
        viewset = PostViewSet()
        viewset.request = Mock()
        viewset.request.user = Mock()
        viewset.request.user.is_authenticated = True
        viewset.request.user.id = 1
        
        mock_queryset = Mock()
        mock_queryset.select_related.return_value.filter.return_value.distinct.return_value = mock_queryset
        mock_post_objects.select_related.return_value = mock_queryset
        
        result = viewset.get_queryset()
        
        # select_relatedが呼ばれたか確認
        mock_post_objects.select_related.assert_called_once_with('author', 'category')
    
    def test_perform_create(self):
        """作成時に作者を設定"""
        viewset = PostViewSet()
        viewset.request = Mock()
        viewset.request.user = Mock(id=1)
        
        mock_serializer = Mock()
        viewset.perform_create(mock_serializer)
        
        mock_serializer.save.assert_called_once_with(author=viewset.request.user)

    def test_partial_update_changes_status_to_published(self):
        """partial_updateでstatusを'published'に変更することを確認"""
        viewset = PostViewSet()
        viewset.action = 'partial_update'

        # Mockの設定
        mock_post = Mock()
        mock_post.status = 'draft'
        
        viewset.get_object = Mock(return_value=mock_post)
        viewset.request = Mock()
        viewset.request.data = {'status': 'published'}
                
        # シリアライザーをMock
        mock_serializer = Mock()
        mock_serializer.data = {'id': 1, 'status': 'published'}
        viewset.get_serializer = Mock(return_value=mock_serializer)
        viewset.perform_update = Mock()
        
        viewset.partial_update(viewset.request, slug='test-slug')
        
        # シリアライザーが呼ばれたことを確認
        viewset.get_serializer.assert_called_once_with(
            mock_post, data={'status': 'published'}, partial=True
        )
        mock_serializer.is_valid.assert_called_once_with(raise_exception=True)
        viewset.perform_update.assert_called_once_with(mock_serializer)

    def test_partial_update_ignores_same_status_published(self):
        """既に公開済みの投稿を公開にしようとしてもエラーにならない（statusフィールドが削除される）"""
        viewset = PostViewSet()
        viewset.action = 'partial_update'
        
        mock_post = Mock()
        mock_post.status = 'published'
        viewset.get_object = Mock(return_value=mock_post)
        
        viewset.request = Mock()
        viewset.request.data = {'status': 'published', 'title': 'Updated Title'}
        
        # シリアライザーをMock
        mock_serializer = Mock()
        mock_serializer.data = {'id': 1, 'title': 'Updated Title'}
        viewset.get_serializer = Mock(return_value=mock_serializer)
        viewset.perform_update = Mock()
        
        viewset.partial_update(viewset.request, slug='test-slug')
        
        # statusが削除されていることを確認
        expected_data = {'title': 'Updated Title'}
        viewset.get_serializer.assert_called_once_with(
            mock_post, data=expected_data, partial=True
        )
        mock_serializer.is_valid.assert_called_once_with(raise_exception=True)
        viewset.perform_update.assert_called_once_with(mock_serializer)
        
    def test_partial_update_changes_status_to_draft(self):
        """partial_updateでstatusを'draft'に変更することを確認"""
        viewset = PostViewSet()
        viewset.action = 'partial_update'
        
        # Mockの設定
        mock_post = Mock()
        mock_post.status = 'published'
        
        viewset.get_object = Mock(return_value=mock_post)
        viewset.request = Mock()
        viewset.request.data = {'status': 'draft'}
        
        # シリアライザーをMock
        mock_serializer = Mock()
        mock_serializer.data = {'id': 1, 'status': 'draft'}
        viewset.get_serializer = Mock(return_value=mock_serializer)
        viewset.perform_update = Mock()
        
        viewset.partial_update(viewset.request, slug='test-slug')
        
        # シリアライザーが呼ばれたことを確認
        viewset.get_serializer.assert_called_once_with(
            mock_post, data={'status': 'draft'}, partial=True
        )
        mock_serializer.is_valid.assert_called_once_with(raise_exception=True)
        viewset.perform_update.assert_called_once_with(mock_serializer)

    def test_partial_update_ignores_same_status_draft(self):
        """既に下書きの投稿を下書きにしようとしてもエラーにならない（statusフィールドが削除される）"""
        viewset = PostViewSet()
        viewset.action = 'partial_update'
        
        mock_post = Mock()
        mock_post.status = 'draft'
        viewset.get_object = Mock(return_value=mock_post)
        
        viewset.request = Mock()
        viewset.request.data = {'status': 'draft', 'content': 'Updated Content'}
        
        # シリアライザーをMock
        mock_serializer = Mock()
        mock_serializer.data = {'id': 1, 'content': 'Updated Content'}
        viewset.get_serializer = Mock(return_value=mock_serializer)
        viewset.perform_update = Mock()
        
        viewset.partial_update(viewset.request, slug='test-slug')
        
        # statusが削除されていることを確認
        expected_data = {'content': 'Updated Content'}
        viewset.get_serializer.assert_called_once_with(
            mock_post, data=expected_data, partial=True
        )
        mock_serializer.is_valid.assert_called_once_with(raise_exception=True)
        viewset.perform_update.assert_called_once_with(mock_serializer)

    def test_partial_update_invalid_status_raises_error(self):
        """不正なstatus値の場合はValidationErrorを発生させる"""
        viewset = PostViewSet()
        viewset.action = 'partial_update'
        
        mock_post = Mock()
        mock_post.status = 'draft'
        viewset.get_object = Mock(return_value=mock_post)
        
        viewset.request = Mock()
        viewset.request.data = {'status': 'invalid_status'}
        
        with pytest.raises(ValidationError) as exc_info:
            viewset.partial_update(viewset.request, slug='test-slug')
        assert '有効なステータスは "draft" または "published" です' in str(exc_info.value)
        
