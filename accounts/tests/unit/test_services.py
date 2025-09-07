"""
サービス層のユニットテスト

services.py のビジネスロジックをテスト。
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
import uuid
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.services import TokenService, AuthService, UserService

User = get_user_model()


class TestTokenService:
    """TokenServiceのユニットテスト（DBアクセスなし）"""
    
    @pytest.fixture
    def service(self):
        return TokenService()
    
    @pytest.fixture
    def mock_user(self):
        """モックユーザー（DBアクセスなし）"""
        user = Mock()
        user.id = 1
        user.email = 'test@example.com'
        user.username = 'testuser'
        return user
    
    def test_generate_access_token_structure(self, service, mock_user):
        """アクセストークンの基本構造"""
        token = service.generate_access_token(mock_user)
        
        # JWT形式の確認
        assert isinstance(token, str)
        parts = token.split('.')
        assert len(parts) == 3  # header.payload.signature
        
        # ペイロードの検証
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        assert payload['user_id'] == 1
        assert payload['email'] == 'test@example.com'
        assert payload['type'] == 'access'
        assert 'exp' in payload
        assert 'iat' in payload
        assert 'jti' in payload
    
    def test_generate_refresh_token_structure(self, service, mock_user):
        """リフレッシュトークンの基本構造"""
        token = service.generate_refresh_token(mock_user)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        assert payload['user_id'] == 1
        assert payload['type'] == 'refresh'
        assert 'email' not in payload  # リフレッシュには含めない（セキュリティ向上）
        assert 'jti' in payload
    
    @freeze_time("2025-01-01 12:00:00")
    def test_access_token_expiration_matches_settings(self, service, mock_user):
        """アクセストークンの有効期限が設定と一致"""
        token = service.generate_access_token(mock_user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
        
        expected_duration = timedelta(seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE)
        actual_duration = exp_time - iat_time
        
        # 1秒以内の誤差を許容
        assert abs((actual_duration - expected_duration).total_seconds()) <= 1
    
    @freeze_time("2025-01-01 12:00:00")
    def test_refresh_token_expiration_matches_settings(self, service, mock_user):
        """リフレッシュトークンの有効期限が設定と一致"""
        token = service.generate_refresh_token(mock_user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
        
        expected_duration = timedelta(seconds=settings.AUTH_COOKIE_REFRESH_MAX_AGE)
        actual_duration = exp_time - iat_time
        
        assert abs((actual_duration - expected_duration).total_seconds()) <= 1
    
    @freeze_time("2025-01-01 12:00:00")
    def test_access_token_expires_after_max_age(self, service, mock_user):
        """アクセストークンが期限後に無効になる"""
        token = service.generate_access_token(mock_user)
        
        # 期限の1秒前: まだ有効
        before_expiry = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + \
                       timedelta(seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE - 1)
        with freeze_time(before_expiry):
            user_id = service.verify_access_token(token)
            assert user_id == 1
        
        # 期限の1秒後: 無効
        after_expiry = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + \
                      timedelta(seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE + 1)
        with freeze_time(after_expiry):
            user_id = service.verify_access_token(token)
            assert user_id is None
    
    def test_verify_access_token_with_valid_token(self, service, mock_user):
        """有効なアクセストークンの検証"""
        token = service.generate_access_token(mock_user)
        user_id = service.verify_access_token(token)
        assert user_id == 1
    
    def test_verify_access_token_with_invalid_format(self, service):
        """無効な形式のトークン検証"""
        assert service.verify_access_token('invalid') is None
        assert service.verify_access_token('') is None
        assert service.verify_access_token('a.b.c') is None
    
    def test_verify_access_token_with_wrong_type(self, service, mock_user):
        """タイプが異なるトークンの検証"""
        refresh_token = service.generate_refresh_token(mock_user)
        # リフレッシュトークンをアクセストークンとして検証
        user_id = service.verify_access_token(refresh_token)
        assert user_id is None
    
    def test_verify_refresh_token_with_valid_token(self, service, mock_user):
        """有効なリフレッシュトークンの検証"""
        token = service.generate_refresh_token(mock_user)
        user_id = service.verify_refresh_token(token)
        assert user_id == 1
    
    def test_verify_refresh_token_with_wrong_type(self, service, mock_user):
        """タイプが異なるトークンの検証"""
        access_token = service.generate_access_token(mock_user)
        # アクセストークンをリフレッシュトークンとして検証
        user_id = service.verify_refresh_token(access_token)
        assert user_id is None
    
    def test_token_uniqueness_via_jti(self, service, mock_user):
        """JTIによるトークンの一意性"""
        tokens = []
        jtis = set()
        
        for _ in range(10):
            token = service.generate_access_token(mock_user)
            tokens.append(token)
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            jtis.add(payload['jti'])
        
        # すべて異なるトークンとJTI
        assert len(set(tokens)) == 10
        assert len(jtis) == 10


@pytest.mark.django_db
class TestAuthService:
    """AuthServiceのユニットテスト（最小限のDBアクセス）"""
    
    @pytest.fixture
    def service(self):
        return AuthService()
    
    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
    
    def test_login_with_valid_credentials(self, service, test_user):
        """有効な認証情報でのログイン"""
        result = service.login('test@example.com', 'testpass123')
        
        assert result is not None
        user, access_token, refresh_token = result
        assert user.id == test_user.id
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
    
    def test_login_with_invalid_password(self, service, test_user):
        """無効なパスワードでのログイン失敗"""
        result = service.login('test@example.com', 'wrongpassword')
        assert result is None
    
    def test_login_with_nonexistent_email(self, service):
        """存在しないメールでのログイン失敗"""
        result = service.login('nonexistent@example.com', 'password')
        assert result is None
    
    @patch('accounts.services.TokenService')
    def test_refresh_tokens_with_valid_token(self, mock_token_service_class, service, test_user):
        """有効なトークンでのリフレッシュ（TokenServiceモック）"""
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_refresh_token.return_value = test_user.id
        mock_token_service.generate_access_token.return_value = 'new_access'
        mock_token_service.generate_refresh_token.return_value = 'new_refresh'
        
        result = service.refresh_tokens('valid_refresh_token')
        
        assert result == ('new_access', 'new_refresh')
        mock_token_service.verify_refresh_token.assert_called_once_with('valid_refresh_token')
    
    @patch('accounts.services.TokenService')
    def test_refresh_tokens_with_invalid_token(self, mock_token_service_class, service):
        """無効なトークンでのリフレッシュ失敗"""
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_refresh_token.return_value = None
        
        result = service.refresh_tokens('invalid_token')
        
        assert result is None
    
    @patch('accounts.services.TokenService')
    def test_refresh_tokens_with_deleted_user(self, mock_token_service_class, service):
        """削除されたユーザーのトークンでリフレッシュ失敗"""
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_refresh_token.return_value = 99999  # 存在しないID
        
        result = service.refresh_tokens('some_token')
        
        assert result is None
    
    def test_logout_returns_true(self, service):
        """ログアウトは常に成功（現在はスタブ）"""
        result = service.logout('any_refresh_token')
        assert result is True
    
    def test_authenticate_request_without_cookie(self, service):
        """Cookieがない場合の認証失敗"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {}
        mock_request.path = '/test'
        mock_request.META = {}
        
        # When
        result = service.authenticate_request(mock_request)
        
        # Then
        assert result is None
    
    def test_authenticate_request_with_empty_token(self, service):
        """空のトークンでの認証失敗"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: ''}
        mock_request.path = '/test'
        mock_request.META = {}
        
        # When
        result = service.authenticate_request(mock_request)
        
        # Then
        assert result is None
    
    @patch('accounts.services.TokenService')
    def test_authenticate_request_with_valid_token(self, mock_token_service_class, service, test_user):
        """有効なトークンでの認証成功"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}
        mock_request.META = {'HTTP_USER_AGENT': 'test-agent', 'REMOTE_ADDR': '127.0.0.1'}
        mock_request.path = '/test'
        
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_access_token.return_value = test_user.id
        
        # When
        result = service.authenticate_request(mock_request)
        
        # Then
        assert result.id == test_user.id
        mock_token_service.verify_access_token.assert_called_once_with('valid_token')
    
    @patch('accounts.services.TokenService')
    def test_authenticate_request_with_expired_token(self, mock_token_service_class, service):
        """期限切れトークンでの認証失敗"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'expired_token'}
        mock_request.META = {'HTTP_USER_AGENT': 'test-agent'}
        mock_request.path = '/test'
        
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_access_token.return_value = None
        
        # When
        result = service.authenticate_request(mock_request)
        
        # Then
        assert result is None
    
    @patch('accounts.services.logger')
    @patch('accounts.services.TokenService')
    def test_authenticate_request_logs_success(self, mock_token_service_class, mock_logger, 
                                              service, test_user):
        """認証成功時のロギング"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}
        mock_request.META = {'HTTP_USER_AGENT': 'test-agent', 'REMOTE_ADDR': '127.0.0.1'}
        mock_request.path = '/api/test'
        
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_access_token.return_value = test_user.id
        
        # When
        service.authenticate_request(mock_request)
        
        # Then - 成功ログが記録される
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any('認証成功' in call for call in debug_calls)
    
    @patch('accounts.services.logger')
    def test_authenticate_request_logs_no_cookie(self, mock_logger, service):
        """Cookie未検出時のロギング"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {}
        mock_request.path = '/api/test'
        mock_request.META = {}
        
        # When
        service.authenticate_request(mock_request)
        
        # Then - デバッグログが記録される
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any('Cookie未検出' in call for call in debug_calls)
    
    @patch('accounts.services.logger')
    @patch('accounts.services.TokenService')
    def test_authenticate_request_logs_invalid_token(self, mock_token_service_class, mock_logger, service):
        """無効トークン時の警告ログ"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'invalid_token'}
        mock_request.META = {'HTTP_USER_AGENT': 'Mozilla/5.0', 'REMOTE_ADDR': '192.168.1.1'}
        mock_request.path = '/api/secure'
        
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_access_token.return_value = None
        
        # When
        service.authenticate_request(mock_request)
        
        # Then - 警告ログが記録される
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert '無効なアクセストークン' in call_args[0][0]
        # extra情報も確認
        assert 'user_agent' in call_args[1]['extra']
        assert 'ip_address' in call_args[1]['extra']
    
    @patch('accounts.services.logger')
    @patch('accounts.services.TokenService')
    def test_authenticate_request_logs_user_not_found(self, mock_token_service_class, mock_logger, service):
        """存在しないユーザーID時のエラーログ"""
        # Given
        mock_request = Mock()
        mock_request.COOKIES = {settings.AUTH_COOKIE_ACCESS_TOKEN: 'valid_token'}
        mock_request.META = {'HTTP_USER_AGENT': 'test-agent'}
        mock_request.path = '/api/test'
        
        mock_token_service = mock_token_service_class.return_value
        mock_token_service.verify_access_token.return_value = 99999  # 存在しないID
        
        # When
        service.authenticate_request(mock_request)
        
        # Then - エラーログが記録される
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any('存在しないユーザーID' in call for call in error_calls)


@pytest.mark.django_db
class TestUserService:
    """UserServiceのユニットテスト"""
    
    @pytest.fixture
    def service(self):
        return UserService()
    
    def test_create_user_success(self, service):
        """ユーザー作成成功"""
        user = service.create_user(
            email='new@example.com',
            password='newpass123',
            username='newuser'
        )
        
        assert user.email == 'new@example.com'
        assert user.username == 'newuser'
        assert user.check_password('newpass123')
    
    def test_create_user_duplicate_email(self, service):
        """重複メールでの作成失敗"""
        User.objects.create_user(
            email='existing@example.com',
            password='pass123',
            username='user1'
        )
        
        with pytest.raises(ValueError, match="Email already exists"):
            service.create_user(
                email='existing@example.com',
                password='pass456',
                username='user2'
            )
    
    def test_create_user_duplicate_username(self, service):
        """重複ユーザー名での作成失敗"""
        User.objects.create_user(
            email='user1@example.com',
            password='pass123',
            username='existingname'
        )
        
        with pytest.raises(ValueError, match="Username already exists"):
            service.create_user(
                email='user2@example.com',
                password='pass456',
                username='existingname'
            )
    
