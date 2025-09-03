import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.services import TokenService, UserService
from rest_framework_simplejwt.exceptions import TokenError
import jwt

User = get_user_model()


@pytest.mark.django_db
class TestTokenService:
    """トークンサービスのテスト"""
    
    @pytest.fixture
    def user(self):
        """テスト用ユーザー"""
        return User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_generate_token_pair(self, user):
        """トークン生成の基本テスト"""
        # When
        tokens = TokenService.generate_token_pair(user)
        
        # Then: トークンの構造を検証
        assert 'access' in tokens
        assert 'refresh' in tokens
        
        # JWTのデコード
        decoded = jwt.decode(
            tokens['access'],
            settings.SECRET_KEY,
            algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
        )
        
        assert decoded['user_id'] == user.id
        assert decoded['token_type'] == 'access'
    
    @freeze_time("2025-01-01 12:00:00")
    def test_access_token_expiration_matches_cookie_settings(self, user):
        """アクセストークンの有効期限がCookie設定と一致"""
        # Given: トークン生成
        tokens = TokenService.generate_token_pair(user)
        
        # JWT の有効期限を確認
        decoded = jwt.decode(
            tokens['access'],
            settings.SECRET_KEY,
            algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
        )
        
        # トークンの有効期限
        token_exp_seconds = decoded['exp'] - decoded['iat']
        
        # Cookie設定の有効期限と比較
        # AUTH_COOKIE_ACCESS_MAX_AGE は秒単位
        assert abs(token_exp_seconds - settings.AUTH_COOKIE_ACCESS_MAX_AGE) <= 1
    
    @freeze_time("2025-01-01 12:00:00")
    def test_refresh_token_expiration_matches_cookie_settings(self, user):
        """リフレッシュトークンの有効期限がCookie設定と一致"""
        # Given: トークン生成
        tokens = TokenService.generate_token_pair(user)
        
        # JWT の有効期限を確認
        decoded = jwt.decode(
            tokens['refresh'],
            settings.SECRET_KEY,
            algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
        )
        
        # トークンの有効期限
        token_exp_seconds = decoded['exp'] - decoded['iat']
        
        # Cookie設定の有効期限と比較
        # AUTH_COOKIE_REFRESH_MAX_AGE は秒単位
        assert abs(token_exp_seconds - settings.AUTH_COOKIE_REFRESH_MAX_AGE) <= 1
    
    @freeze_time("2025-01-01 12:00:00")
    def test_access_token_expires_after_max_age(self, user):
        """アクセストークンがAUTH_COOKIE_ACCESS_MAX_AGE後に期限切れ"""
        # Given: 固定時刻でトークン生成
        tokens = TokenService.generate_token_pair(user)
        access_token = tokens['access']
        
        # When: MAX_AGEの1秒前
        expire_time = datetime.now() + timedelta(seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE - 1)
        with freeze_time(expire_time):
            # Then: まだ有効
            try:
                jwt.decode(
                    access_token,
                    settings.SECRET_KEY,
                    algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
                )
            except jwt.ExpiredSignatureError:
                pytest.fail("Token should still be valid")
        
        # When: MAX_AGEの1秒後
        expired_time = datetime.now() + timedelta(seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE + 1)
        with freeze_time(expired_time):
            # Then: 期限切れ
            with pytest.raises(jwt.ExpiredSignatureError):
                jwt.decode(
                    access_token,
                    settings.SECRET_KEY,
                    algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
                )
    
    @freeze_time("2025-01-01 12:00:00")
    def test_refresh_token_expires_after_max_age(self, user):
        """リフレッシュトークンがAUTH_COOKIE_REFRESH_MAX_AGE後に期限切れ"""
        # Given
        tokens = TokenService.generate_token_pair(user)
        refresh_token = tokens['refresh']
        
        # When: MAX_AGEの1秒前
        before_expiry = datetime.now() + timedelta(seconds=settings.AUTH_COOKIE_REFRESH_MAX_AGE - 1)
        with freeze_time(before_expiry):
            # Then: ローテーション成功
            new_tokens = TokenService.rotate_refresh_token(refresh_token)
            assert new_tokens is not None
        
        # When: MAX_AGEの1秒後
        after_expiry = datetime.now() + timedelta(seconds=settings.AUTH_COOKIE_REFRESH_MAX_AGE + 1)
        with freeze_time(after_expiry):
            # Then: ローテーション失敗
            with pytest.raises(TokenError):
                TokenService.rotate_refresh_token(refresh_token)
    
    def test_token_rotation_respects_settings(self, user):
        """トークンローテーションが設定に従う"""
        # Given
        original_tokens = TokenService.generate_token_pair(user)
        
        # When: ローテーション
        new_tokens = TokenService.rotate_refresh_token(original_tokens['refresh'])
        
        # Then: 新しいアクセストークンが生成される
        assert new_tokens['access'] != original_tokens['access']
        
        # ROTATE_REFRESH_TOKENS設定を確認
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
            assert new_tokens['refresh'] != original_tokens['refresh']
            
            # BLACKLIST_AFTER_ROTATION設定を確認
            if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                # 古いリフレッシュトークンは使えない
                with pytest.raises(TokenError):
                    TokenService.rotate_refresh_token(original_tokens['refresh'])


@pytest.mark.django_db
class TestUserService:
    """ユーザーサービスのテスト"""
    
    @pytest.fixture
    def user_data(self):
        """テスト用ユーザーデータ"""
        return {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_authenticate_valid_user(self, user_data):
        """有効なユーザーの認証"""
        # Given
        User.objects.create_user(
            email=user_data['email'],
            password=user_data['password']
        )
        
        # When
        service = UserService()
        authenticated_user = service.authenticate(
            user_data['email'],
            user_data['password']
        )
        
        # Then
        assert authenticated_user is not None
        assert authenticated_user.email == user_data['email']