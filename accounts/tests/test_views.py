"""
Viewレイヤーのユニットテスト
- サービス層をMockして、View自体の責務のみをテスト
- DBアクセスなし、ミドルウェアなし
- CSRFやCookie設定の詳細は統合テストで確認
"""
import pytest
import json
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.views import LoginView, RegisterView, LogoutView, RefreshView

User = get_user_model()


class TestLoginViewUnit:
    """LoginViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()
    
    @patch('accounts.views.AuthService')
    def test_login_success_returns_200(self, mock_auth_service, factory):
        """ログイン成功時は200を返す"""
        # Arrange
        mock_service = mock_auth_service.return_value
        mock_service.login.return_value = (
            User(id=1, email='test@example.com'),
            'access_token_value',
            'refresh_token_value'
        )
        
        request = factory.post(
            '',
            data=json.dumps({'email': 'test@example.com', 'password': 'pass'}),
            content_type='application/json'
        )

        # ユニットテストではCSRFをスキップ（ビジネスロジックに集中）
        request._dont_enforce_csrf_checks = True
        
        # Act
        view = LoginView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        mock_service.login.assert_called_once_with('test@example.com', 'pass')
    
    @patch('accounts.views.AuthService')
    def test_login_failure_returns_401(self, mock_auth_service, factory):
        """ログイン失敗時は401を返す"""
        # Arrange
        mock_service = mock_auth_service.return_value
        mock_service.login.return_value = None  # 認証失敗
        
        request = factory.post(
            '',
            data=json.dumps({'email': 'test@example.com', 'password': 'wrong'}),
            content_type='application/json'
        )

        request._dont_enforce_csrf_checks = True
        
        # Act
        view = LoginView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 401
    
    def test_login_invalid_json_returns_400(self, factory):
        """不正なJSONは400を返す"""
        request = factory.post(
            '',
            data='invalid json',
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        view = LoginView.as_view()
        response = view(request)
        
        assert response.status_code == 400
    
    def test_login_missing_fields_returns_400(self, factory):
        """必須フィールド不足は400を返す"""
        request = factory.post(
            '',
            data=json.dumps({'email': 'test@example.com'}),  # passwordなし
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        view = LoginView.as_view()
        response = view(request)
        
        assert response.status_code == 400
    
    @patch('accounts.views.AuthService')
    def test_login_calls_service_correctly(self, mock_auth_service, factory):
        """サービス層を正しいパラメータで呼び出す"""
        # Arrange
        mock_service = mock_auth_service.return_value
        user = User(id=1, email='user@test.com')
        mock_service.login.return_value = (user, 'token1', 'token2')
        
        email = 'user@test.com'
        password = 'secret123'
        request = factory.post(
            '',
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        # Act
        view = LoginView.as_view()
        view(request)
        
        # Assert - サービスが正しく呼ばれたか
        mock_service.login.assert_called_once_with(email, password)


class TestRegisterViewUnit:
    """RegisterViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()
    
    @patch('accounts.views.UserService')
    def test_register_success_returns_201(self, mock_user_service, factory):
        """登録成功時は201を返す"""
        # Arrange
        mock_service = mock_user_service.return_value
        mock_service.create_user.return_value = User(
            id=1,
            email='new@example.com',
            username='newuser'
        )
        
        request = factory.post(
            '',
            data=json.dumps({
                'email': 'new@example.com',
                'password': 'pass123',
                'username': 'newuser'
            }),
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        # Act
        view = RegisterView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 201
        mock_service.create_user.assert_called_once_with(
            email='new@example.com',
            password='pass123',
            username='newuser'
        )
    
    @patch('accounts.views.UserService')
    def test_register_duplicate_email_returns_400(self, mock_user_service, factory):
        """重複メールは400を返す"""
        # Arrange
        mock_service = mock_user_service.return_value
        mock_service.create_user.side_effect = ValueError("Email already exists")
        
        request = factory.post(
            '',
            data=json.dumps({
                'email': 'existing@example.com',
                'password': 'pass123',
                'username': 'newuser'
            }),
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        # Act
        view = RegisterView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 400
    
    def test_register_invalid_json_returns_400(self, factory):
        """不正なJSONは400を返す"""
        request = factory.post(
            '',
            data='not json',
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        view = RegisterView.as_view()
        response = view(request)
        
        assert response.status_code == 400
    
    def test_register_missing_fields_returns_400(self, factory):
        """必須フィールド不足は400を返す"""
        request = factory.post(
            '',
            data=json.dumps({'email': 'test@example.com'}),  # password, usernameなし
            content_type='application/json'
        )
        request._dont_enforce_csrf_checks = True
        
        view = RegisterView.as_view()
        response = view(request)
        
        assert response.status_code == 400


class TestLogoutViewUnit:
    """LogoutViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()
    
    @patch('accounts.views.AuthService')
    def test_logout_with_token_calls_service(self, mock_auth_service, factory):
        """トークンがある場合はサービスを呼ぶ"""
        # Arrange
        mock_service = mock_auth_service.return_value
        mock_service.logout.return_value = True
        
        request = factory.post('')
        request._dont_enforce_csrf_checks = True
        request.COOKIES = {settings.AUTH_COOKIE_REFRESH_TOKEN: 'some_token'}
        
        # Act
        view = LogoutView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        mock_service.logout.assert_called_once_with('some_token')
    
    @patch('accounts.views.AuthService')
    def test_logout_without_token_returns_200(self, mock_auth_service, factory):
        """トークンなしでも200を返す（冪等性）"""
        # Arrange
        request = factory.post('')
        request._dont_enforce_csrf_checks = True
        request.COOKIES = {}  # Cookieなし
        
        # Act
        view = LogoutView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        # サービスは呼ばれないか、Noneで呼ばれる


class TestRefreshViewUnit:
    """RefreshViewのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()
    
    @patch('accounts.views.AuthService')
    def test_refresh_success_returns_200(self, mock_auth_service, factory):
        """リフレッシュ成功時は200を返す"""
        # Arrange
        mock_service = mock_auth_service.return_value
        mock_service.refresh_tokens.return_value = (
            'new_access_token',
            'new_refresh_token'
        )
        
        request = factory.post('')
        request._dont_enforce_csrf_checks = True
        request.COOKIES = {settings.AUTH_COOKIE_REFRESH_TOKEN: 'old_token'}
        
        # Act
        view = RefreshView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 200
        mock_service.refresh_tokens.assert_called_once_with('old_token')
    
    @patch('accounts.views.AuthService')
    def test_refresh_invalid_token_returns_401(self, mock_auth_service, factory):
        """無効なトークンは401を返す"""
        # Arrange
        mock_service = mock_auth_service.return_value
        mock_service.refresh_tokens.return_value = None  # トークン無効
        
        request = factory.post('')
        request._dont_enforce_csrf_checks = True
        request.COOKIES = {settings.AUTH_COOKIE_REFRESH_TOKEN: 'invalid_token'}
        
        # Act
        view = RefreshView.as_view()
        response = view(request)
        
        # Assert
        assert response.status_code == 401
    
    def test_refresh_no_token_returns_401(self, factory):
        """トークンなしは401を返す"""
        request = factory.post('')
        request._dont_enforce_csrf_checks = True
        request.COOKIES = {}  # Cookieなし
        
        view = RefreshView.as_view()
        response = view(request)
        
        assert response.status_code == 401