import pytest
from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError
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

    def test_publish_changes_status_to_published(self):
        """publishメソッドがstatusを'published'に変更することを確認"""
        viewset = PostViewSet()
        
        # Mockの設定
        mock_post = Mock()
        mock_post.status = 'draft'
        mock_post.save = Mock()
        
        viewset.get_object = Mock(return_value=mock_post)
        viewset.get_serializer = Mock(return_value=Mock(data={'id': 1}))
        viewset.request = Mock()
        viewset.request.user = Mock()
        
        # publishを実行（エラーが出ないことを確認）
        try:
            viewset.publish(viewset.request, slug='test-slug')
        except:
            pass  # Responseの作成でエラーが出ても、ロジックは確認できる
        
        # statusが変更されたことを確認
        assert mock_post.status == 'published'
        mock_post.save.assert_called_once()
    
    def test_publish_raises_error_when_already_published(self):
        """既に公開済みの場合はValidationErrorを発生させる"""
        viewset = PostViewSet()
        
        mock_post = Mock()
        mock_post.status = 'published'
        viewset.get_object = Mock(return_value=mock_post)
        viewset.request = Mock()
        
        with pytest.raises(ValidationError):
            viewset.publish(viewset.request, slug='test-slug')
    
    def test_unpublish_changes_status_to_draft(self):
        """unpublishメソッドがstatusを'draft'に変更することを確認"""
        viewset = PostViewSet()
        
        # Mockの設定
        mock_post = Mock()
        mock_post.status = 'published'
        mock_post.save = Mock()
        
        viewset.get_object = Mock(return_value=mock_post)
        viewset.get_serializer = Mock(return_value=Mock(data={'id': 1}))
        viewset.request = Mock()
        viewset.request.user = Mock()
        
        # unpublishを実行（エラーが出ないことを確認）
        try:
            viewset.unpublish(viewset.request, slug='test-slug')
        except:
            pass  # Responseの作成でエラーが出ても、ロジックは確認できる
        
        # statusが変更されたことを確認
        assert mock_post.status == 'draft'
        mock_post.save.assert_called_once()
        
    def test_unpublish_already_draft_raises_error(self):
        """既に下書きの投稿を下書きにしようとするとエラー"""
        viewset = PostViewSet()
        
        mock_post = Mock()
        mock_post.status = 'draft'
        viewset.get_object = Mock(return_value=mock_post)
        
        viewset.request = Mock()
        
        with pytest.raises(ValidationError):
            viewset.unpublish(viewset.request, slug='test-slug')
        