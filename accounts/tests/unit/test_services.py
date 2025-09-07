"""
サービス層のユニットテスト（SimpleJWT版）

services.py のビジネスロジックをテスト。
ユニットテストの原則に従い、可能な限りモックを使用。
統合テストはintegrationフォルダで実施。
"""

import pytest
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.services import AuthService, UserService

User = get_user_model()


class TestAuthService:
    """AuthServiceのユニットテスト（モック中心）"""
    
    @pytest.fixture
    def service(self):
        return AuthService()
    
    @pytest.fixture
    def mock_user(self):
        """モックユーザー"""
        user = Mock(spec=User)
        user.id = 1
        user.email = 'test@example.com'
        user.username = 'testuser'
        user.is_active = True
        user.check_password = Mock(return_value=True)
        return user
    
    @patch('accounts.services.User')
    @patch('accounts.services.RefreshToken')
    def test_login_with_valid_credentials(self, mock_refresh_token_class, mock_user_class, service, mock_user):
        """有効な認証情報でのログイン"""
        # Setup
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        mock_user.check_password.return_value = True
        
        # RefreshTokenのモック
        mock_refresh = Mock()
        mock_refresh.access_token = 'mock_access_token'
        mock_refresh.__str__ = Mock(return_value='mock_refresh_token')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        # Execute
        result = service.login('test@example.com', 'testpass123')
        
        # Assert
        assert result is not None
        user, tokens = result
        assert user == mock_user
        assert tokens['access'] == 'mock_access_token'
        assert tokens['refresh'] == 'mock_refresh_token'
        
        # 呼び出し確認
        mock_user_class.objects.filter.assert_called_once_with(email__iexact='test@example.com')
        mock_user.check_password.assert_called_once_with('testpass123')
        mock_refresh_token_class.for_user.assert_called_once_with(mock_user)
    
    @patch('accounts.services.User')
    @patch('accounts.services.RefreshToken')
    def test_login_returns_dict_format(self, mock_refresh_token_class, mock_user_class, service, mock_user):
        """ログイン時に辞書形式でトークンを返す"""
        # Setup
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        mock_user.check_password.return_value = True
        
        mock_refresh = Mock()
        mock_refresh.access_token = 'mock_access_token'
        mock_refresh.__str__ = Mock(return_value='mock_refresh_token')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        # Execute
        result = service.login('test@example.com', 'testpass123')
        
        # Assert - 辞書形式の確認
        _, tokens = result
        assert isinstance(tokens, dict)
        assert 'access' in tokens
        assert 'refresh' in tokens
    
    @patch('accounts.services.User')
    def test_login_with_invalid_password(self, mock_user_class, service, mock_user):
        """無効なパスワードでのログイン失敗"""
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        mock_user.check_password.return_value = False
        
        result = service.login('test@example.com', 'wrongpassword')
        
        assert result is None
        mock_user.check_password.assert_called_once_with('wrongpassword')
    
    @patch('accounts.services.User')
    def test_login_with_nonexistent_email(self, mock_user_class, service):
        """存在しないメールでのログイン失敗"""
        mock_user_class.objects.filter.return_value.first.return_value = None
        
        result = service.login('nonexistent@example.com', 'password')
        
        assert result is None
        mock_user_class.objects.filter.assert_called_once_with(email__iexact='nonexistent@example.com')
    
    @patch('accounts.services.User')
    def test_login_with_inactive_user(self, mock_user_class, service, mock_user):
        """非アクティブユーザーでのログイン失敗"""
        mock_user.is_active = False
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        
        result = service.login('test@example.com', 'testpass123')
        
        assert result is None

    @patch('accounts.services.User')
    def test_login_with_email_case_insensitive(self, mock_user_class, service):
        """メールアドレスの大文字小文字を区別しない"""
        mock_user_class.objects.filter.return_value.first.return_value = None
        
        service.login('TEST@EXAMPLE.COM', 'testpass123')
        
        # email__iexactが使われることを確認
        mock_user_class.objects.filter.assert_called_once_with(email__iexact='TEST@EXAMPLE.COM')

    
    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_valid_token(self, mock_refresh_token_class, service):
        """有効なリフレッシュトークンでの更新"""
        # Setup
        mock_old_refresh = Mock()
        mock_old_refresh.check_blacklist = Mock()  # ブラックリストチェック成功
        
        mock_new_refresh = Mock()
        mock_new_refresh.access_token = 'new_access_token'
        mock_new_refresh.__str__ = Mock(return_value='new_refresh_token')
        
        mock_refresh_token_class.return_value = mock_old_refresh
        mock_old_refresh.rotate = Mock(return_value=mock_new_refresh)
        
        # Execute
        result = service.refresh_tokens('old_refresh_token')
        
        # Assert
        assert result == {
            'access': 'new_access_token',
            'refresh': 'new_refresh_token'
        }
        mock_refresh_token_class.assert_called_once_with('old_refresh_token')
        mock_old_refresh.check_blacklist.assert_called_once()
        mock_old_refresh.rotate.assert_called_once()
    
    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_invalid_token(self, mock_refresh_token_class, service):
        """無効なリフレッシュトークンでの更新失敗"""
        mock_refresh_token_class.side_effect = TokenError('Invalid token')
        
        result = service.refresh_tokens('invalid_token')
        
        assert result is None
    
    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_blacklisted_token(self, mock_refresh_token_class, service):
        """ブラックリスト登録済みトークンでの更新失敗"""
        mock_refresh = Mock()
        mock_refresh.check_blacklist.side_effect = TokenError('Token is blacklisted')
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.refresh_tokens('blacklisted_token')
        
        assert result is None
    
    @patch('accounts.services.RefreshToken')
    def test_logout_blacklists_token(self, mock_refresh_token_class, service):
        """ログアウトでトークンをブラックリスト登録"""
        mock_refresh = Mock()
        mock_refresh.blacklist = Mock()
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.logout('refresh_token')
        
        assert result is True
        mock_refresh.blacklist.assert_called_once()
    
    @patch('accounts.services.RefreshToken')
    def test_logout_with_invalid_token(self, mock_refresh_token_class, service):
        """無効なトークンでのログアウト"""
        mock_refresh_token_class.side_effect = TokenError('Invalid token')
        
        result = service.logout('invalid_token')
        
        # エラーを隠蔽してTrueを返す
        assert result is True
    
    @patch('accounts.services.RefreshToken')
    def test_logout_with_already_blacklisted_token(self, mock_refresh_token_class, service):
        """既にブラックリスト登録済みトークンのログアウト"""
        mock_refresh = Mock()
        mock_refresh.blacklist.side_effect = TokenError('Already blacklisted')
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.logout('blacklisted_token')
        
        assert result is True
    
    @patch('accounts.services.logger')
    @patch('accounts.services.User')
    @patch('accounts.services.RefreshToken')
    def test_login_logs_success(self, mock_refresh_token_class, mock_user_class, 
                                mock_logger, service, mock_user):
        """ログイン成功時のロギング"""
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        mock_user.check_password.return_value = True
        
        mock_refresh = Mock()
        mock_refresh.access_token = 'token'
        mock_refresh.__str__ = Mock(return_value='refresh')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        service.login('test@example.com', 'testpass123')
        
        # ログ確認
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert 'ログイン成功' in call_args
    
    @patch('accounts.services.logger')
    @patch('accounts.services.User')
    def test_login_logs_failure(self, mock_user_class, mock_logger, service, mock_user):
        """ログイン失敗時のロギング"""
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        mock_user.check_password.return_value = False
        
        service.login('test@example.com', 'wrongpassword')
        
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        assert 'ログイン失敗' in call_args

class TestUserService:
    """UserServiceのユニットテスト（モック中心）"""
    
    @pytest.fixture
    def service(self):
        return UserService()
    
    @patch('accounts.services.User')
    def test_create_user_success(self, mock_user_class, service):
        """ユーザー作成成功"""
        # Setup
        mock_user_class.objects.filter.return_value.exists.side_effect = [False, False]  # 重複なし
        
        mock_user = Mock()
        mock_user.email = 'new@example.com'
        mock_user.username = 'newuser'
        mock_user_class.objects.create_user.return_value = mock_user
        
        # Execute
        user = service.create_user(
            email='new@example.com',
            password='newpass123',
            username='newuser'
        )
        
        # Assert
        assert user == mock_user
        mock_user_class.objects.create_user.assert_called_once_with(
            email='new@example.com',
            password='newpass123',
            username='newuser'
        )
    
    @patch('accounts.services.User')
    def test_create_user_duplicate_email(self, mock_user_class, service):
        """重複メールでの作成失敗"""
        # メール重複あり
        mock_user_class.objects.filter.return_value.exists.side_effect = [True, False]
        
        with pytest.raises(ValueError, match="Email already exists"):
            service.create_user(
                email='existing@example.com',
                password='pass456',
                username='user2'
            )
    
    @patch('accounts.services.User')
    def test_create_user_duplicate_username(self, mock_user_class, service):
        """重複ユーザー名での作成失敗"""
        # ユーザー名重複あり
        mock_user_class.objects.filter.return_value.exists.side_effect = [False, True]
        
        with pytest.raises(ValueError, match="Username already exists"):
            service.create_user(
                email='user2@example.com',
                password='pass456',
                username='existingname'
            )
    
    @patch('accounts.services.User')
    def test_get_user_by_email_exists(self, mock_user_class, service):
        """メールでユーザー取得（存在する場合）"""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = 'findme@example.com'
        mock_user_class.objects.filter.return_value.first.return_value = mock_user
        
        found_user = service.get_user_by_email('findme@example.com')
        
        assert found_user == mock_user
        mock_user_class.objects.filter.assert_called_once_with(email__iexact='findme@example.com')
    
    @patch('accounts.services.User')
    def test_get_user_by_email_not_exists(self, mock_user_class, service):
        """メールでユーザー取得（存在しない場合）"""
        mock_user_class.objects.filter.return_value.first.return_value = None
        
        user = service.get_user_by_email('notfound@example.com')
        
        assert user is None
    
    @patch('accounts.services.logger')
    @patch('accounts.services.User')
    def test_create_user_logs_success(self, mock_user_class, mock_logger, service):
        """ユーザー作成成功時のロギング"""
        mock_user_class.objects.filter.return_value.exists.side_effect = [False, False]
        mock_user = Mock()
        mock_user.email = 'logged@example.com'
        mock_user_class.objects.create_user.return_value = mock_user
        
        service.create_user(
            email='logged@example.com',
            password='pass123',
            username='loggeduser'
        )
        
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert 'ユーザー作成成功' in call_args