import pytest
from unittest.mock import Mock
from blog.permissions import IsAuthorOrReadOnly


class TestIsAuthorOrReadOnly:
    """IsAuthorOrReadOnlyパーミッションクラスのユニットテスト"""
    
    def test_has_permission_safe_methods(self):
        """安全なメソッド（GET, HEAD, OPTIONS）は常に許可"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'GET'
        view = Mock()
        
        assert permission.has_permission(request, view) is True
        
        request.method = 'HEAD'
        assert permission.has_permission(request, view) is True
        
        request.method = 'OPTIONS'
        assert permission.has_permission(request, view) is True
    
    def test_has_permission_authenticated_user(self):
        """認証済みユーザーは書き込み可能"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'POST'
        request.user = Mock()
        request.user.is_authenticated = True
        view = Mock()
        
        assert permission.has_permission(request, view) is True
    
    def test_has_permission_anonymous_write(self):
        """未認証ユーザーは書き込み不可"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'POST'
        request.user = Mock()
        request.user.is_authenticated = False
        view = Mock()
        
        assert permission.has_permission(request, view) is False
    
    def test_has_object_permission_author(self):
        """作者は自分のオブジェクトを編集可能"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'PUT'
        user = Mock()
        request.user = user
        view = Mock()
        obj = Mock()
        obj.author = user
        obj.status = 'published'
        
        assert permission.has_object_permission(request, view, obj) is True
    
    def test_has_object_permission_not_author(self):
        """作者以外は編集不可"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'PUT'
        user1 = Mock()
        user1.id = 1
        user2 = Mock()
        user2.id = 2
        request.user = user1
        view = Mock()
        obj = Mock()
        obj.author = user2  # 異なるユーザー
        obj.status = 'published'
        
        assert permission.has_object_permission(request, view, obj) is False
    
    def test_has_object_permission_safe_method(self):
        """安全なメソッドは誰でもアクセス可能"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'GET'
        user1 = Mock()
        user1.id = 1
        user2 = Mock()
        user2.id = 2
        request.user = user2
        view = Mock()
        obj = Mock()
        obj.author = user1
        obj.status = 'published'  # 公開記事
        
        assert permission.has_object_permission(request, view, obj) is True

    def test_has_object_permission_draft_not_author(self):
        """下書きは作者以外閲覧不可"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'GET'
        user1 = Mock()
        user1.id = 1
        user2 = Mock()
        user2.id = 2
        request.user = user2
        view = Mock()
        obj = Mock()
        obj.author = user1
        obj.status = 'draft'  # 下書き
        
        assert permission.has_object_permission(request, view, obj) is False
    
    def test_has_object_permission_draft_author(self):
        """下書きは作者は閲覧可能"""
        permission = IsAuthorOrReadOnly()
        request = Mock()
        request.method = 'GET'
        user = Mock()
        user.id = 1
        request.user = user
        view = Mock()
        obj = Mock()
        obj.author = user  # 同じユーザー
        obj.status = 'draft'  # 下書き
        
        assert permission.has_object_permission(request, view, obj) is True