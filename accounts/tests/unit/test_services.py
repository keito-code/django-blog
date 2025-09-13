"""
サービス層のユニットテスト（SimpleJWT版）

services.py のビジネスロジックをテスト。
ユニットテストの原則に従い、可能な限りモックを使用。
統合テストはintegrationフォルダで実施。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
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
    
    @patch('accounts.services.authenticate')
    @patch('accounts.services.User')
    @patch('accounts.services.RefreshToken')
    def test_login_with_valid_credentials(self, mock_refresh_token_class, mock_user_class, mock_authenticate, service, mock_user):
        """有効な認証情報でのログイン"""

        # Setup
        mock_authenticate.return_value = mock_user
        
        # RefreshTokenのモック
        mock_refresh = Mock()
        mock_refresh.access_token = 'mock_access_token'
        mock_refresh.__str__ = Mock(return_value='mock_refresh_token')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        # Execute
        result = service.login('test@example.com', 'testpass123', request=None)
        
        # Assert - 新しい辞書形式に変更
        assert result['ok'] is True
        assert result['user'] == mock_user
        assert result['tokens']['access'] == 'mock_access_token'
        assert result['tokens']['refresh'] == 'mock_refresh_token'

        # 呼び出し確認
        mock_authenticate.assert_called_once_with(
            request=None,
            email='test@example.com',
            password='testpass123'
        )
        mock_refresh_token_class.for_user.assert_called_once_with(mock_user)

    @patch('accounts.services.authenticate')
    @patch('accounts.services.RefreshToken')
    def test_login_returns_dict_format(self, mock_refresh_token_class, mock_authenticate, service, mock_user):
        """ログイン時に辞書形式でトークンを返す"""
        # Setup
        mock_authenticate.return_value = mock_user
        
        mock_refresh = Mock()
        mock_refresh.access_token = 'mock_access_token'
        mock_refresh.__str__ = Mock(return_value='mock_refresh_token')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        # Execute
        result = service.login('test@example.com', 'testpass123', request=None)
        
        # Assert - 辞書形式の確認
        assert isinstance(result, dict)
        assert 'ok' in result
        assert 'tokens' in result
        assert result['ok'] is True

    @patch('accounts.services.authenticate')
    def test_login_with_invalid_password(self, mock_authenticate, service):
        """無効なパスワードでのログイン失敗"""
        mock_authenticate.return_value = None
        
        result = service.login('test@example.com', 'wrongpassword', request=None)
        
        assert result['ok'] is False
        assert 'error' in result

    @patch('accounts.services.authenticate')
    def test_login_with_nonexistent_email(self, mock_authenticate, service):
        """存在しないメールでのログイン失敗"""
        mock_authenticate.return_value = None
        
        result = service.login('nonexistent@example.com', 'password',request=None)
        
        assert result['ok'] is False
        assert 'error' in result
    
    @patch('accounts.services.authenticate')
    def test_login_with_inactive_user(self, mock_authenticate, service, mock_user):
        """非アクティブユーザーでのログイン失敗"""
        mock_user.is_active = False
        mock_authenticate.return_value = mock_user
        
        result = service.login('test@example.com', 'testpass123', request=None)
        
        assert result['ok'] is False
        assert result['error'] == 'User account is inactive'

    @patch('accounts.services.authenticate')
    def test_login_with_email_case_insensitive(self, mock_authenticate, service):
        """メールアドレスの大文字小文字を区別しない"""
        mock_authenticate.return_value = None

        service.login('TEST@EXAMPLE.COM', 'testpass123', request=None)
        
        # authenticateが正しく呼ばれることを確認
        mock_authenticate.assert_called_once_with(
            request=None,
            email='TEST@EXAMPLE.COM',
            password='testpass123'
        )

    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_valid_token(self, mock_refresh_token_class, service):
        """有効なリフレッシュトークンでの更新"""
        # Setup
        mock_old_refresh = Mock()
        mock_old_refresh.check_blacklist = Mock()  # ブラックリストチェック成功
        
        mock_new_refresh = Mock()
        mock_new_refresh.access_token = 'new_access_token'
        mock_new_refresh.__str__ = Mock(return_value='new_refresh_token')

        # ユーザーのモック
        mock_user = Mock()
        mock_old_refresh.user = mock_user
        
        mock_refresh_token_class.return_value = mock_old_refresh
        mock_refresh_token_class.for_user.return_value = mock_new_refresh
        
        # Execute
        result = service.refresh_tokens('old_refresh_token')
        
        # Assert - 新しい辞書形式
        assert result['ok'] is True
        assert result['tokens']['access'] == 'new_access_token'
        assert result['tokens']['refresh'] == 'new_refresh_token'

    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_invalid_token(self, mock_refresh_token_class, service):
        """無効なリフレッシュトークンでの更新失敗"""
        mock_refresh_token_class.side_effect = TokenError('Invalid token')
        
        result = service.refresh_tokens('invalid_token')
        
        assert result['ok'] is False
        assert 'error' in result
    
    @patch('accounts.services.RefreshToken')
    def test_refresh_tokens_with_blacklisted_token(self, mock_refresh_token_class, service):
        """ブラックリスト登録済みトークンでの更新失敗"""
        mock_refresh = Mock()
        mock_refresh.blacklist.side_effect = TokenError('Already blacklisted')
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.refresh_tokens('blacklisted_token')
        
        assert result['ok'] is False
        assert 'error' in result
    
    @patch('accounts.services.RefreshToken')
    def test_logout_blacklists_token(self, mock_refresh_token_class, service):
        """ログアウトでトークンをブラックリスト登録"""
        mock_refresh = Mock()
        mock_refresh.blacklist = Mock()
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.logout('refresh_token')
        
        assert result['ok'] is True
        mock_refresh.blacklist.assert_called_once()
    
    @patch('accounts.services.RefreshToken')
    def test_logout_with_invalid_token(self, mock_refresh_token_class, service):
        """無効なトークンでのログアウト"""
        mock_refresh_token_class.side_effect = TokenError('Invalid token')
        
        result = service.logout('invalid_token')
        
        # エラーを隠蔽してTrueを返す
        assert result['ok'] is True
    
    @patch('accounts.services.RefreshToken')
    def test_logout_with_already_blacklisted_token(self, mock_refresh_token_class, service):
        """既にブラックリスト登録済みトークンのログアウト"""
        mock_refresh = Mock()
        mock_refresh.blacklist.side_effect = TokenError('Already blacklisted')
        mock_refresh_token_class.return_value = mock_refresh
        
        result = service.logout('blacklisted_token')
        
        assert result['ok'] is True
    
    @patch('accounts.services.logger')
    @patch('accounts.services.authenticate')
    @patch('accounts.services.User')
    @patch('accounts.services.RefreshToken')
    def test_login_logs_success(self, mock_refresh_token_class, mock_user_class, 
                                mock_authenticate, mock_logger, service, mock_user):
        """ログイン成功時のロギング"""
        mock_authenticate.return_value = mock_user
        
        mock_refresh = Mock()
        mock_refresh.access_token = 'token'
        mock_refresh.__str__ = Mock(return_value='refresh')
        mock_refresh_token_class.for_user.return_value = mock_refresh
        
        service.login('test@example.com', 'testpass123', request=None)
        
        # ログ確認
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert 'ログイン成功' in call_args
    
    @patch('accounts.services.logger')
    @patch('accounts.services.authenticate')
    def test_login_logs_failure(self, mock_authenticate, mock_logger, service, mock_user):
        """ログイン失敗時のロギング"""
        mock_authenticate.return_value = None
        
        service.login('test@example.com', 'wrongpassword', request=None)
        
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        assert 'ログイン失敗' in call_args

    def test_register_creates_user_and_returns_tokens(self, service):
        """新規登録が成功し、ユーザーとトークンが返される"""
        with patch('accounts.services.User.objects.create_user') as mock_create_user:
            with patch('accounts.services.RefreshToken') as mock_refresh_token_class:
                # Setup
                mock_user = Mock()
                mock_user.id = 1
                mock_user.email = 'new@example.com'
                mock_user.username = 'newuser'
                mock_create_user.return_value = mock_user
                
                mock_refresh = Mock()
                mock_refresh.access_token = 'mock_access_token'
                mock_refresh.__str__ = Mock(return_value='mock_refresh_token')
                mock_refresh_token_class.for_user.return_value = mock_refresh
                
                # Execute
                result = service.register('newuser', 'new@example.com', 'password123')
                
                # Assert
                assert result['ok'] is True
                assert result['user'] == mock_user
                assert result['tokens']['access'] == 'mock_access_token'
                assert result['tokens']['refresh'] == 'mock_refresh_token'
                
                mock_create_user.assert_called_once_with(
                    username='newuser',
                    email='new@example.com',
                    password='password123'
                )

    def test_register_returns_dict_format(self, service):
        """新規登録時に辞書形式で結果を返す"""
        with patch('accounts.services.User.objects.create_user') as mock_create_user:
            with patch('accounts.services.RefreshToken') as mock_refresh_token_class:
                mock_user = Mock()
                mock_create_user.return_value = mock_user
                
                mock_refresh = Mock()
                mock_refresh.access_token = 'token'
                mock_refresh.__str__ = Mock(return_value='refresh')
                mock_refresh_token_class.for_user.return_value = mock_refresh
                
                result = service.register('user', 'email@example.com', 'pass')
                
                assert isinstance(result, dict)
                assert 'ok' in result
                assert 'user' in result
                assert 'tokens' in result
                assert isinstance(result['tokens'], dict)
                assert 'access' in result['tokens']
                assert 'refresh' in result['tokens']

    def test_verify_token_with_valid_token(self, service):
        """有効なトークンの検証が成功"""
        with patch('accounts.services.AccessToken') as mock_access_token:
            # AccessTokenのコンストラクタが成功する（例外を投げない）
            mock_access_token.return_value = Mock()
            
            result = service.verify_token('valid_token_string')
            
            assert result['ok'] is True
            assert 'error' not in result
            mock_access_token.assert_called_once_with('valid_token_string')

    def test_verify_token_with_invalid_token(self, service):
        """無効なトークンの検証が失敗"""
        with patch('accounts.services.AccessToken') as mock_access_token:
            mock_access_token.side_effect = TokenError('Token is invalid or expired')
            
            result = service.verify_token('invalid_token_string')
            
            assert result['ok'] is False
            assert 'error' in result
            assert 'invalid or expired' in result['error'].lower()

    def test_verify_token_with_expired_token(self, service):
        """期限切れトークンの検証が失敗"""
        with patch('accounts.services.AccessToken') as mock_access_token:
            mock_access_token.side_effect = TokenError('Token is expired')
            
            result = service.verify_token('expired_token_string')
            
            assert result['ok'] is False
            assert 'error' in result

    @patch('accounts.services.logger')
    def test_verify_token_logs_failure(self, mock_logger, service):
        """トークン検証失敗時のロギング"""
        with patch('accounts.services.AccessToken') as mock_access_token:
            mock_access_token.side_effect = TokenError('Invalid')
            
            service.verify_token('bad_token')
            
            mock_logger.debug.assert_called()

class TestUserService:
    """UserServiceのユニットテスト"""

    @pytest.fixture
    def service(self):
        return UserService()

    def test_update_user_updates_username_only(self, service):
        """ユーザー名のみの更新"""
        mock_user = Mock(spec=User)
        mock_user.save = Mock()
        
        validated_data = {'username': 'updated_name'}
        
        result = service.update_user(mock_user, validated_data)
        
        assert mock_user.username == 'updated_name'
        mock_user.save.assert_called_once()
        assert result == mock_user

    def test_update_user_updates_email_only(self, service):
        """メールアドレスのみの更新"""
        mock_user = Mock(spec=User)
        mock_user.save = Mock()
        
        validated_data = {'email': 'newemail@example.com'}
        
        result = service.update_user(mock_user, validated_data)
        
        assert mock_user.email == 'newemail@example.com'
        mock_user.save.assert_called_once()
        assert result == mock_user

    def test_update_user_updates_username_and_email(self, service):
        """ユーザー名とメールアドレスの同時更新（通常ユーザー）"""
        mock_user = Mock(spec=User)
        mock_user.save = Mock()
        
        # UpdateUserSerializerが扱うフィールドのみ
        validated_data = {
            'username': 'new_username',
            'email': 'newemail@example.com'
        }

        result = service.update_user(mock_user, validated_data)
        
        assert mock_user.username == 'new_username'
        assert mock_user.email == 'newemail@example.com'
        mock_user.save.assert_called_once()
        assert result == mock_user

    def test_update_user_admin_fields(self, service):
        """管理者用フィールドの更新（AdminUpdateUserSerializer用）"""
        mock_user = Mock(spec=User)
        mock_user.save = Mock()
        
        # AdminUpdateUserSerializerが扱うフィールド
        validated_data = {
            'username': 'admin_updated',
            'email': 'admin@example.com',
            'is_active': False,
            'is_staff': True
        }
        
        result = service.update_user(mock_user, validated_data)
        
        assert mock_user.username == 'admin_updated'
        assert mock_user.email == 'admin@example.com'
        assert mock_user.is_active is False
        assert mock_user.is_staff is True
        mock_user.save.assert_called_once()
        assert result == mock_user

    
    def test_update_user_with_empty_data(self, service):
        """空のデータでの更新（何も変更されない）"""
        mock_user = Mock(spec=User)
        mock_user.save = Mock()
        mock_user.username = 'original_name'
        mock_user.email = 'original@example.com'
        
        validated_data = {}
        
        result = service.update_user(mock_user, validated_data)
        
        # 値が変更されていないことを確認
        assert mock_user.username == 'original_name'
        assert mock_user.email == 'original@example.com'
        mock_user.save.assert_called_once()  # saveは呼ばれる
        assert result == mock_user

    @patch('accounts.services.logger')
    def test_update_user_logs_success(self, mock_logger, service):
        """ユーザー更新成功時のロギング"""
        mock_user = Mock(spec=User)
        mock_user.email = 'test@example.com'
        mock_user.save = Mock()
        
        validated_data = {'username': 'updated'}
        
        service.update_user(mock_user, validated_data)
        
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert 'ユーザー更新' in call_args
        assert 'test@example.com' in call_args