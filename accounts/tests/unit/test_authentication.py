import pytest
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from accounts.authentication import CookieJWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

class TestCookieJWTAuthentication:
    """CookieJWTAuthentication のユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()
    
    @pytest.fixture
    def auth(self):
        """認証クラスのインスタンス"""
        return CookieJWTAuthentication()
    
    def test_get_raw_token_from_cookie_success(self, auth, factory):
        """Cookieからトークンを正常に取得"""
        request = factory.get('/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'test_token_value'}
        
        token = auth.get_raw_token_from_cookie(request)
        assert token == 'test_token_value'
    
    def test_get_raw_token_from_cookie_not_found(self, auth, factory):
        """Cookieが存在しない場合はNone"""
        request = factory.get('/')
        request.COOKIES = {}
        
        token = auth.get_raw_token_from_cookie(request)
        assert token is None
    
    def test_authenticate_no_cookie_returns_none(self, auth, factory):
        """Cookieがない場合、認証はNoneを返す"""
        request = factory.get('/')
        request.COOKIES = {}
        
        result = auth.authenticate(request)
        assert result is None
    
    @patch('accounts.authentication.CookieJWTAuthentication.get_validated_token')
    @patch('accounts.authentication.CookieJWTAuthentication.get_user')
    def test_authenticate_valid_token(self, mock_get_user, mock_get_validated_token, 
                                     auth, factory, test_user):  # conftest.pyのtest_userを使用
        """有効なトークンで認証成功"""
        # モックの設定
        mock_token = Mock()
        mock_token.token_type = "access"
        mock_get_validated_token.return_value = mock_token
        mock_get_user.return_value = test_user  # conftest.pyのフィクスチャを使用
        
        request = factory.get('/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}
        
        result = auth.authenticate(request)
        
        assert result is not None
        authenticated_user, token = result
        assert authenticated_user == test_user
        assert token == mock_token
        
        # メソッドが正しく呼ばれたか確認
        mock_get_validated_token.assert_called_once_with('valid_token')
        mock_get_user.assert_called_once_with(mock_token)
    
    @patch('accounts.authentication.CookieJWTAuthentication.get_validated_token')
    def test_authenticate_invalid_token(self, mock_get_validated_token, auth, factory):
        """無効なトークンで認証失敗"""
        # TokenErrorを発生させる
        mock_get_validated_token.side_effect = TokenError("Invalid token")
        
        request = factory.get('/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'invalid_token'}
        
        # TokenErrorは内部で処理されるべき
        result = auth.authenticate(request)
        assert result is None
    
    @patch('accounts.authentication.CookieJWTAuthentication.get_validated_token')
    def test_authenticate_expired_token(self, mock_get_validated_token, auth, factory):
        """期限切れトークンで認証失敗"""
        mock_get_validated_token.side_effect = TokenError("Token is expired")
        
        request = factory.get('/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'expired_token'}
        
        result = auth.authenticate(request)
        assert result is None
    
    @pytest.mark.django_db
    def test_authenticate_with_real_token(self, auth, factory, test_user):
        """実際のトークンで認証テスト（統合的）"""
        
        # 実際のトークンを生成
        token = AccessToken.for_user(test_user)
        
        request = factory.get('/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: str(token)}
        
        result = auth.authenticate(request)
        
        assert result is not None
        authenticated_user, validated_token = result
        assert authenticated_user.id == test_user.id
        assert authenticated_user.email == test_user.email