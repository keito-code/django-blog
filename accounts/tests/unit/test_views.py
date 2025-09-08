"""
Viewレイヤーのユニットテスト (DRF APIView版)
- View自体の責務のみをテスト
- httpステータスコード
- Cookie設定/削除 (基本的な確認のみ)
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from accounts.views import (
    CSRFTokenView, LoginView, LogoutView, RefreshTokenView,
    RegisterView, CurrentUserView, VerifyTokenView
)

User = get_user_model()


class TestCSRFTokenView:
    """CSRFTokenViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.get_token')
    def test_get_csrf_token_success(self, mock_get_token, factory):
        """CSRFトークン取得成功"""
        
        # Arrange
        mock_get_token.return_value = 'test_csrf_token'
        request = factory.get('/api/v1/auth/csrf/')
        
        # Act
        view = CSRFTokenView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['data']['csrfToken'] == 'test_csrf_token'
        
        # Cookie設定を確認
        assert settings.CSRF_COOKIE_NAME in response.cookies


class TestLoginView:
    """LoginViewのユニットテスト (DRF APIView版)"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.AuthService')
    def test_login_success(self, mock_auth_service_class, factory):
        """ログイン成功時のレスポンスとCookie設定"""
        
        # Arrange
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        
        mock_user = User(id=1, email='test@example.com', username='testuser')
        mock_service.login.return_value = {
            'success': True,
            'user': mock_user,
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token'
        }
        
        request = factory.post(
            '/api/v1/auth/login/',
            data={'username': 'testuser', 'password': 'testpass'},
            format='json'
        )
        
        # Act
        view = LoginView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['data']['user']['email'] == 'test@example.com'
        assert data['data']['message'] == 'ログインに成功しました'
        
        # Cookie設定を確認
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in response.cookies
        
        # HttpOnly設定を確認
        access_cookie = response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]
        assert access_cookie['httponly'] is True
        assert access_cookie['samesite'] == 'Lax'
    
    @patch('accounts.views.AuthService')
    def test_login_invalid_credentials(self, mock_auth_service_class, factory):
        """認証失敗時は401エラー"""
        
        # Arrange
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        mock_service.login.return_value = {
            'success': False,
            'error': 'Invalid credentials'
        }
        
        request = factory.post(
            '/api/v1/auth/login/',
            data={'username': 'testuser', 'password': 'wrongpass'},
            format='json'
        )
        
        # Act
        view = LoginView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 401
        data = json.loads(response.content)
        assert data['success'] is False
        assert data['error']['code'] == 'unauthorized'
    
    
    def test_login_missing_fields(self, factory):
        """必須フィールド不足時は400エラー"""
        
        request = factory.post(
            '/api/v1/auth/login/',
            data={'username': 'testuser'},  # passwordなし
            format='json'
        )
        
        view = LoginView.as_view()
        response = view(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['success'] is False


class TestLogoutView:
    """LogoutViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def user(self):
        return User(id=1, email='test@example.com')
    
    @patch('accounts.views.AuthService')
    def test_logout_success(self, mock_auth_service_class, factory):
        """ログアウト成功時のCookie削除"""
        
        # Arrange
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        mock_service.logout.return_value = {'success': True}
        
        request = factory.post(
            '/api/v1/auth/logout/',
            HTTP_COOKIE=f'{settings.AUTH_COOKIE_REFRESH_TOKEN}=test_refresh_token'
        )
        
        # 認証をモック（DBアクセスなし）
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        force_authenticate(request, user=mock_user)

        # Act
        view = LogoutView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['data']['message'] == 'ログアウトしました'

        # サービスが呼ばれたことを確認
        mock_service.logout.assert_called_once_with('test_refresh_token')
        
        # Cookie削除を確認
        access_cookie = response.cookies.get(settings.AUTH_COOKIE_ACCESS_TOKEN)
        refresh_cookie = response.cookies.get(settings.AUTH_COOKIE_REFRESH_TOKEN)
        
        if access_cookie:
            assert access_cookie['max-age'] == 0
        if refresh_cookie:
            assert refresh_cookie['max-age'] == 0
    
    def test_logout_without_auth_returns_401(self, factory):
        """認証なしでのログアウトは401エラー"""
        
        request = factory.post('/api/v1/auth/logout/')
        
        view = LogoutView.as_view()
        response = view(request)
        
        assert response.status_code == 401


class TestRefreshTokenView:
    """RefreshTokenViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.AuthService')
    def test_refresh_success(self, mock_auth_service_class, factory):
        """トークンリフレッシュ成功"""
        from accounts.views import RefreshTokenView
        
        # Arrange
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        mock_service.refresh_token.return_value = {
            'success': True,
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token'
        }
        
        request = factory.post(
            '/api/v1/auth/refresh/',
            HTTP_COOKIE=f'{settings.AUTH_COOKIE_REFRESH_TOKEN}=old_refresh_token'
        )
        # Act
        view = RefreshTokenView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        
        # 新しいトークンがCookieに設定されている
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in response.cookies
    
    def test_refresh_without_token_returns_401(self, factory):
        """リフレッシュトークンなしは401エラー"""
        
        # Cookieなしのリクエスト（HTTP_COOKIEを指定しない）
        request = factory.post('/api/v1/auth/refresh/')
        
        view = RefreshTokenView.as_view()
        response = view(request)
        
        assert response.status_code == 401


class TestRegisterView:
    """RegisterViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.RefreshToken')
    @patch('accounts.views.PublicUserSerializer')
    @patch('accounts.views.RegisterSerializer')
    def test_register_success(self, mock_serializer_class, mock_public_serializer_class, mock_refresh_token_class, factory):
        """ユーザー登録成功"""

        # Arrange
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer
        mock_serializer.is_valid.return_value = True
        

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = 'new@example.com'
        mock_user.username = 'newuser'
        mock_serializer.save.return_value = mock_user
        
        # PublicUserSerializerのモック
        mock_public_serializer_class.return_value.data = {
            'id': 1,
            'email': 'new@example.com',
            'username': 'newuser'
        }
        
        # RefreshTokenのモック  
        mock_refresh = MagicMock()
        mock_refresh_token_class.for_user.return_value = mock_refresh
        mock_refresh.access_token = 'test_access_token'
        mock_refresh.__str__ = MagicMock(return_value='test_refresh_token')
        
        request = factory.post(
            '/api/v1/auth/register/',
            data={
                'email': 'new@example.com',
                'username': 'newuser',
                'password': 'newpass123'
            },
            format='json'
        )
        
        # Act
        view = RegisterView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 201

        # トークンがCookieに設定されている
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in response.cookies

    @patch('accounts.views.RegisterSerializer')
    def test_returns_400_for_invalid_data(self, mock_serializer_class, factory):
        """無効なデータで400を返す"""
        
        # Arrange
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer
        mock_serializer.is_valid.return_value = False
        mock_serializer.errors = {'email': ['Invalid email']}
        
        request = factory.post(
            '/api/v1/auth/register/',
            data={'email': 'invalid'},
            format='json'
        )
        
        # Act
        view = RegisterView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 400

class TestCurrentUserView:
    """CurrentUserViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def user(self):
        return User(id=1, email='test@example.com', username='testuser')
    
    def test_get_current_user(self, factory, user):
        """現在のユーザー情報取得"""
        from accounts.views import CurrentUserView
        
        request = factory.get('/api/v1/auth/user/')
        force_authenticate(request, user=user)
        
        view = CurrentUserView.as_view()
        response = view(request)
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['data']['email'] == 'test@example.com'
    
    @patch('accounts.views.PrivateUserSerializer')
    def test_update_current_user(self, mock_serializer_class, factory, user):
        """ユーザー情報更新"""
        
        # Arrange
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = {'email': 'updated@example.com'}
        
        request = factory.put(
            '/api/v1/auth/user/',
            data={'email': 'updated@example.com'},
            format='json'
        )
        force_authenticate(request, user=user)
        
        # Act
        view = CurrentUserView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['data']['message'] == 'プロフィールを更新しました'
    
    def test_get_user_without_auth_returns_401(self, factory):
        """認証なしでのユーザー情報取得は401エラー"""
        
        request = factory.get('/api/v1/auth/user/')
        
        view = CurrentUserView.as_view()
        response = view(request)
        
        assert response.status_code == 401


class TestVerifyTokenView:
    """VerifyTokenViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    @patch('accounts.views.PublicUserSerializer')
    @patch('accounts.views.AuthService')
    def test_verify_valid_token(self, mock_auth_service_class, mock_public_serializer_class, factory):
        """有効なトークンの検証"""

        # Arrange
        mock_service_instance = MagicMock()
        mock_service_instance.verify_token.return_value = {
            'success': True,
            'user': MagicMock(id=1, email='test@example.com')
        }
        # クラスではなくインスタンスを返すように設定
        mock_auth_service_class.return_value = mock_service_instance
        
         # Serializer のモック
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.data = {
            'id': 1, 'email': 'test@example.com'
        }
        mock_public_serializer_class.return_value = mock_serializer_instance
  
        # Act - HTTP_COOKIEヘッダーを使用
        request = factory.post(
            '/api/v1/auth/verify/',
            HTTP_COOKIE=f"{settings.AUTH_COOKIE_ACCESS_TOKEN}=valid_token"
        )

        # 認証を無効化
        request._force_auth_user = None
        request._force_auth_token = None

        # View を直接呼ぶ
        view = VerifyTokenView()
        response = view.post(request)

        # Assert
        assert response.status_code == 200

        # モックが呼ばれたことを確認
        mock_auth_service_class.assert_called_once()
        mock_service_instance.verify_token.assert_called_once_with("valid_token")

    @patch('accounts.views.AuthService')
    def test_returns_401_when_service_fails(self, mock_auth_service_class, factory):
        """サービスが失敗したら401を返す"""
        
        # Arrange
        mock_service = MagicMock()
        mock_auth_service_class.return_value = mock_service
        mock_service.verify_token.return_value = {
            'success': False,
            'error': 'Invalid token'
        }
        
        request = factory.post(
            '/api/v1/auth/verify/',
            HTTP_COOKIE=f'{settings.AUTH_COOKIE_ACCESS_TOKEN}=invalid'
        )

        # Act
        view = VerifyTokenView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 401

    def test_verify_without_token_returns_401(self, factory):
        """トークンなしは401エラー"""
        
        # Cookieなしのリクエスト（HTTP_COOKIEを指定しない）
        request = factory.post('/api/v1/auth/verify/')
        
        view = VerifyTokenView.as_view()
        response = view(request)
        
        assert response.status_code == 401


