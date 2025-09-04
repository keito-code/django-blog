"""
統合テスト
- 実際のDB、URL、ミドルウェアを使用
- Mockなし
- ユーザージャーニー全体をテスト
- CSRFトークンは必須
"""
import pytest
import json
import time
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationFlowIntegration:
    """認証フロー全体の統合テスト（CSRF保護含む）"""
    
    def test_complete_auth_flow_with_csrf(self, client):
        """新規登録→ログイン→リフレッシュ→ログアウトの完全フロー（CSRF必須）"""
        
        # 0. CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        assert csrf_response.status_code == 200, "CSRF endpoint MUST be implemented"
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        assert csrf_token, "CSRF token is required"
        
        # 1. 新規登録（CSRFなし→失敗）
        register_data = {
            'email': 'flowuser@example.com',
            'password': 'validpass123',
            'username': 'flowuser'
        }
        
        response = client.post(
            reverse('accounts:register'),
            data=json.dumps(register_data),
            content_type='application/json'
        )
        assert response.status_code == 403, "Register without CSRF must return 403"
        
        # 2. 新規登録（CSRFあり→成功）
        response = client.post(
            reverse('accounts:register'),
            data=json.dumps(register_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True
        assert data['data']['message'] == 'Registration successful'
        assert User.objects.filter(email=register_data['email']).exists()
        
        # 3. ログイン（CSRFあり）
        login_response = client.post(
            reverse('accounts:login'),
            data=json.dumps({
                'email': register_data['email'],
                'password': register_data['password']
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data['success'] == True
        assert login_data['data']['message'] == 'Login successful'
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in login_response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in login_response.cookies
        
        # トークンの値を保存
        initial_access = login_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        initial_refresh = login_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        
        time.sleep(1)

        # 4. トークンリフレッシュ（CSRFあり）
        refresh_response = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert refresh_data['success'] == True
        assert refresh_data['data']['message'] == 'Token refreshed successfully'
        
        # 新しいトークンが発行されたか確認
        new_access = refresh_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        new_refresh = refresh_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        assert new_access != initial_access, "Access token should be rotated"
        assert new_refresh != initial_refresh, "Refresh token should be rotated"
        
        # 5. ログアウト（CSRFあり）
        logout_response = client.post(
            reverse('accounts:logout'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data['success'] == True
        assert logout_data['data']['message'] == 'Logout successful'
        
        # Cookieがクリアされたか確認
        assert int(logout_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]['max-age']) == 0
        assert int(logout_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN]['max-age']) == 0
        
        # 6. ログアウト後はリフレッシュ不可（トークンが無効）
        post_logout_refresh = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert post_logout_refresh.status_code == 401
        post_logout_data = post_logout_refresh.json()
        assert post_logout_data['success'] == False
        assert post_logout_data['error']['code'] == 'unauthorized'
    
    def test_login_with_invalid_csrf_token(self, client, test_user, login_data):
        """不正なCSRFトークンでのログイン失敗"""
        # 不正なCSRFトークンでログイン試行
        response = client.post(
            reverse('accounts:login'),
            data=json.dumps(login_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='invalid_csrf_token_12345'
        )
        assert response.status_code == 403, "Invalid CSRF token must return 403"
    
    def test_invalid_credentials_with_valid_csrf(self, client, test_user):
        """CSRFトークンが正しくても認証情報が間違っていれば401"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        # 間違ったパスワードでログイン
        response = client.post(
            reverse('accounts:login'),
            data=json.dumps({
                'email': test_user.email,
                'password': 'wrongpassword'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 401, "Wrong password must return 401, not 403"
        assert settings.AUTH_COOKIE_ACCESS_TOKEN not in response.cookies
    
    def test_duplicate_user_registration(self, client, test_user):
        """既存ユーザーと同じメールでの登録は400エラー"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        # 既存ユーザーと同じメールで登録試行
        response = client.post(
            reverse('accounts:register'),
            data=json.dumps({
                'email': test_user.email,
                'password': 'newpass123',
                'username': 'differentuser'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 400, "Duplicate email must return 400"
        
        # ユーザー数が増えていないことを確認
        assert User.objects.filter(email=test_user.email).count() == 1


@pytest.mark.django_db
class TestCookieSecurityIntegration:
    """Cookie設定の統合テスト"""
    
    def test_cookie_attributes_on_login(self, client, test_user, login_data):
        """ログイン時のCookie属性が正しく設定される"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        # ログイン
        response = client.post(
            reverse('accounts:login'),
            data=json.dumps(login_data),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        
        assert response.status_code == 200
        
        # アクセストークンCookieの属性確認
        access_cookie = response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]
        assert bool(access_cookie['httponly']) == settings.AUTH_COOKIE_HTTPONLY
        assert access_cookie['samesite'] == settings.AUTH_COOKIE_SAMESITE
        assert bool(access_cookie['secure']) == settings.AUTH_COOKIE_SECURE
        assert int(access_cookie['max-age']) == settings.AUTH_COOKIE_ACCESS_MAX_AGE
        
        # リフレッシュトークンCookieの属性確認
        refresh_cookie = response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN]
        assert bool(refresh_cookie['httponly']) == settings.AUTH_COOKIE_HTTPONLY
        assert refresh_cookie['samesite'] == settings.AUTH_COOKIE_SAMESITE
        assert bool(refresh_cookie['secure']) == settings.AUTH_COOKIE_SECURE
        assert int(refresh_cookie['max-age']) == settings.AUTH_COOKIE_REFRESH_MAX_AGE
    
    def test_csrf_cookie_attributes(self, client):
        """CSRF Cookieの属性が正しく設定される"""
        response = client.get(reverse('accounts:csrf'))
        
        if settings.CSRF_COOKIE_NAME in response.cookies:
            csrf_cookie = response.cookies[settings.CSRF_COOKIE_NAME]
            
            # CSRFトークンはJavaScriptからアクセス可能である必要
            assert bool(csrf_cookie['httponly']) == settings.CSRF_COOKIE_HTTPONLY, \
                "CSRF cookie must be accessible from JavaScript"
            
            # その他の属性
            assert csrf_cookie['samesite'] == settings.CSRF_COOKIE_SAMESITE
            
            # Secure属性は環境依存
            assert bool(csrf_cookie['secure']) == settings.CSRF_COOKIE_SECURE


@pytest.mark.django_db
class TestErrorHandlingIntegration:
    """エラーハンドリングの統合テスト"""
    
    def test_malformed_json_returns_400(self, client):
        """不正なJSONは400エラー"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        response = client.post(
            reverse('accounts:login'),
            data='{"invalid": json}',
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 400
        data = response.json()
        assert data['success'] == False
        assert data['error']['code'] == 'validation_error'
    
    def test_method_not_allowed(self, client):
        """許可されていないHTTPメソッドは405エラー"""
        # GETでログインエンドポイントにアクセス
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 405 # GETは405が返る（CSRFチェック不要）
        
        # DELETEでリフレッシュエンドポイントにアクセス
        # セキュリティ優先：CSRFチェックが先に実行されて403が返る
        response = client.delete(reverse('accounts:refresh'))
        assert response.status_code == 403, \
             "DELETE without CSRF token should return 403 (CSRF protection takes priority)"
    
        # 追加テスト：CSRFトークン付きでDELETEを送ると405が返ることを確認
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']

        response_with_csrf = client.delete(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response_with_csrf.status_code == 405, \
            "DELETE with valid CSRF token should return 405 (Method Not Allowed)"

    def test_missing_required_fields(self, client):
        """必須フィールド不足は400エラー"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        # passwordなしでログイン試行
        response = client.post(
            reverse('accounts:login'),
            data=json.dumps({'email': 'test@example.com'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 400
        data = response.json()
        assert data['success'] == False
        assert data['error']['code'] == 'validation_error'