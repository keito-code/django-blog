"""
Viewレイヤーのユニットテスト修正版
モック問題を根本的に解決
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth import get_user_model
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
        mock_get_token.return_value = 'test_csrf_token'
        request = factory.get('/api/v1/auth/csrf/')
        
        view = CSRFTokenView.as_view()
        response = view(request)

        response.render()
        data = json.loads(response.content.decode('utf-8'))

        assert response.status_code == 200
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'csrfToken' in data['data']  # camelCaseに変更
        assert data['data']['csrfToken'] == 'test_csrf_token'  # camelCaseに変更
        assert settings.CSRF_COOKIE_NAME in response.cookies

class TestLoginView:
    """LoginViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.PublicUserSerializer')
    @patch('accounts.views.AuthService')
    def test_login_success(self, mock_auth_service_class, mock_serializer_class, factory):
        """ログイン成功時のレスポンスとCookie設定"""
        # AuthServiceのモック
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.username = 'testuser'
        
        mock_service.login.return_value = {
            'ok': True,
            'user': mock_user,
            'tokens': {
                'access': 'test_access_token',
                'refresh': 'test_refresh_token'
            }
        }
        
        # PublicUserSerializerのモック
        mock_serializer = Mock()
        mock_serializer.data = {
            'id': 1,
            'email': 'test@example.com',
            'username': 'testuser'
        }
        mock_serializer_class.return_value = mock_serializer
        
        request = factory.post(
            '/api/v1/auth/login/',
            data={'email': 'test@example.com', 'password': 'testpass'},
            format='json'
        )
        
        view = LoginView.as_view()
        response = view(request)
        
        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'test@example.com'
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in response.cookies
    
    @patch('accounts.views.AuthService')
    def test_login_invalid_credentials(self, mock_auth_service_class, factory):
        """認証失敗時は401エラー"""
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        mock_service.login.return_value = {
            'ok': False,
            'error': 'Authentication failed'
        }
        
        request = factory.post(
            '/api/v1/auth/login/',
            data={'email': 'test@example.com', 'password': 'wrongpass'},
            format='json'
        )
        
        view = LoginView.as_view()
        response = view(request)
        
            
        assert response.status_code == 401
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'error'
        assert 'Authentication failed' in data['message']
    
    def test_login_missing_fields(self, factory):
        """必須フィールド不足時は422エラー"""
        request = factory.post(
            '/api/v1/auth/login/',
            data={'email': 'test@example.com'},
            format='json'
        )
        
        view = LoginView.as_view()
        response = view(request)
        
            
        assert response.status_code == 422
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'fail'


class TestLogoutView:
    """LogoutViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def user(self):
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.is_authenticated = True
        return mock_user
    
    @patch('accounts.views.AuthService')
    def test_logout_success(self, mock_auth_service_class, factory, user):
        """ログアウト成功時のCookie削除"""
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        mock_service.logout.return_value = {'ok': True}  # 辞書形式
        
        request = factory.post('/api/v1/auth/logout/')
        request.COOKIES = {settings.AUTH_COOKIE_REFRESH_TOKEN: 'test_refresh_token'}
        force_authenticate(request, user=user)

        view = LogoutView.as_view()
        response = view(request)
        
            
        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
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
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        mock_service.refresh_tokens.return_value = {
            'ok': True,
            'tokens': {
                'access': 'new_access_token',
                'refresh': 'new_refresh_token'
            }
        }
        
        request = factory.post('/api/v1/auth/refresh/')
        request.COOKIES = {settings.AUTH_COOKIE_REFRESH_TOKEN: 'old_refresh_token'}
        
        view = RefreshTokenView.as_view()
        response = view(request)
        
            
        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in response.cookies
    
    def test_refresh_without_token_returns_401(self, factory):
        """リフレッシュトークンなしは401エラー"""
        request = factory.post('/api/v1/auth/refresh/')
        request.COOKIES = {}
        
        view = RefreshTokenView.as_view()
        response = view(request)
        
            
        assert response.status_code == 401
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'error'


class TestRegisterView:
    """RegisterViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @patch('accounts.views.PublicUserSerializer')
    @patch('accounts.views.AuthService')
    @patch('accounts.views.RegisterSerializer')
    def test_register_success(self, mock_register_serializer_class, 
                             mock_auth_service_class, mock_public_serializer_class, factory):
        """ユーザー登録成功"""
        # RegisterSerializerのモック
        mock_register_serializer = Mock()
        mock_register_serializer.is_valid.return_value = True
        mock_register_serializer.validated_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123'
        }
        mock_register_serializer_class.return_value = mock_register_serializer
        
        # AuthServiceのモック
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'new@example.com'
        mock_user.username = 'newuser'
        
        mock_service.register.return_value = {
            'ok': True,
            'user': mock_user,
            'tokens': {
                'access': 'test_access_token',
                'refresh': 'test_refresh_token'
            }
        }

        # PublicUserSerializerをモック（シリアライズのみ）
        mock_public_serializer_class.return_value.data = {
            'id': 1,
            'email': 'new@example.com',
            'username': 'newuser'
        }      

        request = factory.post(
            '/api/v1/auth/register/',
            data={
                'email': 'new@example.com',
                'username': 'newuser',
                'password': 'newpass123',
                'password_confirm': 'newpass123'
            },
            format='json'
        )
        
        view = RegisterView.as_view()
        response = view(request)
        
            
        assert response.status_code == 201
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'new@example.com'

        # サービス層が呼ばれたことを確認
        mock_service.register.assert_called_once_with(
            username='newuser',
            email='new@example.com',
            password='newpass123'
        )

    def test_returns_422_for_invalid_data(self, factory):
        """無効なデータで422を返す"""
        request = factory.post(
            '/api/v1/auth/register/',
            data={'email': 'invalid'},
            format='json'
        )
        
        view = RegisterView.as_view()
        response = view(request)
        
            
        assert response.status_code == 422
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'fail'


class TestCurrentUserView:
    """CurrentUserViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def user(self):
        user = Mock(spec=User)
        user.id = 1
        user.email = 'test@example.com'
        user.username = 'testuser'
        user.is_authenticated = True
        user.is_staff = False
        user.is_active = True
        return user
        
    
    @patch('accounts.views.PrivateUserSerializer')
    def test_get_current_user(self, mock_serializer_class, factory, user):
        """現在のユーザー情報取得"""
        # PrivateUserSerializerのモック
        mock_serializer = Mock()
        mock_serializer.data = {
            'id': 1,
            'email': 'test@example.com',
            'username': 'testuser'
        }
        mock_serializer_class.return_value = mock_serializer
        
        request = factory.get('/api/v1/auth/user/')
        force_authenticate(request, user=user)
        
        view = CurrentUserView.as_view()
        response = view(request)
        
            
        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'test@example.com'
    
    @patch('accounts.views.PrivateUserSerializer')
    @patch('accounts.views.UpdateUserSerializer')
    @patch('accounts.views.UserService')
    def test_update_current_user(self, mock_user_service_class, 
                                mock_update_serializer_class,
                                mock_private_serializer_class, factory, user):
        """ユーザー情報更新（PATCHメソッド）"""
        # UpdateUserSerializerのモック
        mock_update_serializer = Mock()
        mock_update_serializer.is_valid.return_value = True
        mock_update_serializer.validated_data = {'username': 'updateduser'}
        mock_update_serializer_class.return_value = mock_update_serializer
        
        # UserServiceのモック
        mock_service = Mock()
        mock_user_service_class.return_value = mock_service
        
        updated_user = Mock(spec=User)
        updated_user.id = 1
        updated_user.email = 'test@example.com'
        updated_user.username = 'updateduser'
        updated_user.is_staff = False
        mock_service.update_user.return_value = updated_user
        
        # PrivateUserSerializerのモック（レスポンス用）
        mock_private_serializer = Mock()
        mock_private_serializer.data = {
            'id': 1,
            'email': 'test@example.com',
            'username': 'updateduser'
        }
        mock_private_serializer_class.return_value = mock_private_serializer
        
        request = factory.patch(
            '/api/v1/auth/user/',
            data={'username': 'updateduser'},
            format='json'
        )
        force_authenticate(request, user=user)
        
        view = CurrentUserView.as_view()
        response = view(request)
        
            
        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['username'] == 'updateduser'
    
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

    @patch('accounts.views.AuthService')
    def test_verify_valid_token(self, mock_auth_service_class, factory):
        """有効なトークンの検証（GETメソッド）"""
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        mock_service.verify_token.return_value = {'ok': True}
  
        request = factory.get('/api/v1/auth/verify/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}

        view = VerifyTokenView.as_view()
        response = view(request)
        

        assert response.status_code == 200
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert data['data']['valid'] is True

        mock_service.verify_token.assert_called_once_with('valid_token')

    @patch('accounts.views.AuthService')
    def test_verify_invalid_token(self, mock_auth_service_class, factory):
        """無効なトークンの検証失敗"""
        mock_service = Mock()
        mock_auth_service_class.return_value = mock_service
        mock_service.verify_token.return_value = {
            'ok': False,
            'error': 'Token is invalid or expired'
        }
        
        request = factory.get('/api/v1/auth/verify/')
        request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'invalid_token'}

        view = VerifyTokenView.as_view()
        response = view(request)

        response.render()

        # 必ずJSONが返されることを確認
        content_type = response.get('Content-Type', '')
        assert 'application/json' in content_type, \
        f"Expected JSON response, got {content_type}"
        
        assert response.status_code == 401
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'error'
        assert data['message'] == 'Token is invalid or expired'

    def test_verify_without_token_returns_401(self, factory):
        """トークンなしは401エラー"""
        request = factory.get('/api/v1/auth/verify/')
        request.COOKIES = {}
        
        view = VerifyTokenView.as_view()
        response = view(request)
        
            
        assert response.status_code == 401
        response.render()
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'error'


class TestAdminUserView:
    """管理者用ユーザー操作のテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def admin_user(self):
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'admin@example.com'
        mock_user.username = 'admin'
        mock_user.is_authenticated = True
        mock_user.is_staff = True
        return mock_user
    
    @patch('accounts.views.AdminUserSerializer')
    @patch('accounts.views.AdminUpdateUserSerializer')
    @patch('accounts.views.UserService')
    def test_admin_update_user_fields(self, mock_user_service_class,
                                     mock_update_serializer_class,
                                     mock_admin_serializer_class,
                                     factory, admin_user):
        """管理者による特権フィールドの更新"""
        # AdminUpdateUserSerializerのモック
        mock_update_serializer = Mock()
        mock_update_serializer.is_valid.return_value = True
        mock_update_serializer.validated_data = {'is_active': False}
        mock_update_serializer_class.return_value = mock_update_serializer
        
        # UserServiceのモック
        mock_service = Mock()
        mock_user_service_class.return_value = mock_service
        
        updated_user = Mock(spec=User)
        updated_user.id = 1
        updated_user.email = 'admin@example.com'
        updated_user.username = 'admin'
        updated_user.is_staff = True
        updated_user.is_active = False
        mock_service.update_user.return_value = updated_user
        
        # AdminUserSerializerのモック（レスポンス用）
        mock_admin_serializer = Mock()
        mock_admin_serializer.data = {
            'id': 1,
            'email': 'admin@example.com',
            'username': 'admin',
            'is_staff': True,
            'is_active': False
        }
        mock_admin_serializer_class.return_value = mock_admin_serializer
        
        request = factory.patch(
            '/api/v1/auth/user/',
            data={'is_active': False},
            format='json'
        )
        force_authenticate(request, user=admin_user)
        
        view = CurrentUserView.as_view()
        response = view(request)

        response.render()
                
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['isActive'] is False
        
        mock_service.update_user.assert_called_once()
        call_args = mock_service.update_user.call_args
        assert 'is_active' in call_args[1]['validated_data']