"""
CookieJWTAuthentication クラスの単体テスト
認証メカニズムのロジックのみをテスト
"""

import pytest
from unittest.mock import Mock, patch
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from accounts.authentication import CookieJWTAuthentication


class TestCookieJWTAuthentication:
    """認証クラスの単体テスト"""
    
    @pytest.fixture
    def auth(self):
        return CookieJWTAuthentication()
    
    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.COOKIES = {}
        request.META = {'HTTP_USER_AGENT': 'pytest/1.0'}
        return request
    
    def test_authenticate_without_cookie(self, auth, mock_request):
        """Cookieがない場合はNone"""
        # Given
        mock_request.COOKIES = {}
        
        # When
        result = auth.authenticate(mock_request)
        
        # Then
        assert result is None
    
    def test_authenticate_with_empty_token(self, auth, mock_request):
        """空のトークンの場合はNone"""
        # Given
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: ''}
        
        # When
        result = auth.authenticate(mock_request)
        
        # Then
        assert result is None
    
    @patch('accounts.authentication.AccessToken')
    @patch('accounts.authentication.User.objects.get')
    def test_authenticate_with_valid_token(self, mock_user_get, mock_access_token, auth, mock_request):
        """有効なトークンで認証成功"""
        # Given
        mock_user = Mock(id=1, username='testuser')
        mock_user_get.return_value = mock_user
        mock_token = Mock(payload={'user_id': 1})
        mock_access_token.return_value = mock_token
        
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}
        
        # When
        result = auth.authenticate(mock_request)
        
        # Then
        assert result is not None
        user, token = result
        assert user == mock_user
    
    @patch('accounts.authentication.AccessToken')
    def test_authenticate_with_expired_token(self, mock_access_token, auth, mock_request):
        """期限切れトークンの処理"""
        # Given
        mock_access_token.side_effect = TokenError("Token is expired")
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'expired_token'}
        
        # When
        result = auth.authenticate(mock_request)
        
        # Then
        assert result is None