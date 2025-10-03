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
from accounts.tests.conftest import to_camel_case

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationFlowIntegration:
    """認証フロー全体の統合テスト（CSRF保護含む）"""
    
    def test_complete_auth_flow_with_csrf(self, api_client):
        """新規登録→ログイン→リフレッシュ→ログアウトの完全フロー（CSRF必須）"""
        
        # 0. CSRFトークン取得
        csrf_response = api_client.get(reverse('auth-api:csrf'))
        assert csrf_response.status_code == 200, "CSRF endpoint MUST be implemented"
        data = to_camel_case(csrf_response.data)
        csrf_token = data['data']['csrfToken']
        assert csrf_token, "CSRF token is required"
        
        # 1. 新規登録（CSRFなし→失敗）
        register_data = {
            'email': 'flowuser@example.com',
            'password': 'validpass123',
            'password_confirmation': 'validpass123',
            'username': 'flowuser'
        }
        
        response = api_client.post(
            reverse('auth-api:register'),
            data=register_data,
            format='json'
        )
        assert response.status_code == 403, "Register without CSRF must return 403"
        
        # 2. 新規登録（CSRFあり→成功）
        response = api_client.post(
            reverse('auth-api:register'),
            data=register_data,
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )

        assert response.status_code == 201
        data = to_camel_case(response.data)
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert 'id' in data['data']['user']
        assert 'dateJoined' in data['data']['user']
        assert User.objects.filter(email=register_data['email']).exists()
        
        # 3. ログイン（CSRFあり）
        login_response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': register_data['email'],
                'password': register_data['password']
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        login_data = to_camel_case(login_response.data)
        assert login_data['status'] == 'success'
        assert 'user' in login_data['data']
        assert 'id' in login_data['data']['user']
        assert 'dateJoined' in login_data['data']['user']
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in login_response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in login_response.cookies
        
        # トークンの値を保存
        initial_access = login_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        initial_refresh = login_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        
        time.sleep(1)

        # 4. トークンリフレッシュ（CSRFあり）
        refresh_response = api_client.post(
            reverse('auth-api:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert refresh_response.status_code == 200
        refresh_data = to_camel_case(refresh_response.data)
        assert refresh_data['status'] == 'success'
        
        # 新しいトークンが発行されたか確認
        new_access = refresh_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        new_refresh = refresh_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        assert new_access != initial_access, "Access token should be rotated"
        assert new_refresh != initial_refresh, "Refresh token should be rotated"
        
        # 5. ログアウト（CSRFあり）
        logout_response = api_client.post(
            reverse('auth-api:logout'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert logout_response.status_code == 200
        logout_data = to_camel_case(logout_response.data)
        assert logout_data['status'] == 'success'
        
        # Cookieがクリアされたか確認
        assert logout_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]['max-age'] == 0
        assert logout_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN]['max-age'] == 0
        
        # 6. ログアウト後はリフレッシュ不可（トークンが無効）
        post_logout_refresh = api_client.post(
            reverse('auth-api:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert post_logout_refresh.status_code == 401
        post_logout_data = to_camel_case(post_logout_refresh.data)
        assert post_logout_data['status'] == 'error'
    
    def test_login_with_invalid_csrf_token(self, api_client, test_user, login_data):
        """不正なCSRFトークンでのログイン失敗"""
        # 不正なCSRFトークンでログイン試行
        response = api_client.post(
            reverse('auth-api:login'),
            data=login_data,
            format='json',
            HTTP_X_CSRFTOKEN='invalid_csrf_token_12345'
        )
        assert response.status_code == 403, "Invalid CSRF token must return 403"
    
    def test_invalid_credentials_with_valid_csrf(self, api_client, test_user, csrf_token):
        """CSRFトークンが正しくても認証情報が間違っていれば401"""        
        # 間違ったパスワードでログイン
        response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': test_user.email,
                'password': 'wrongpassword'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 401, "Wrong password must return 401, not 403"
        assert settings.AUTH_COOKIE_ACCESS_TOKEN not in response.cookies
    
    def test_duplicate_user_registration(self, api_client, test_user, csrf_token):
        """既存ユーザーと同じメールでの登録は422エラー"""        
        # 既存ユーザーと同じメールで登録試行
        response = api_client.post(
            reverse('auth-api:register'),
            data={
                'email': test_user.email,
                'password': 'newpass123',
                'password_confirmation': 'newpass123', 
                'username': 'differentuser'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422, "Duplicate email must return 422"
        
        # ユーザー数が増えていないことを確認
        assert User.objects.filter(email=test_user.email).count() == 1

    def test_password_mismatch_registration(self, api_client, csrf_token):
        """パスワード確認が一致しない場合の登録失敗テスト"""        
        # パスワードが一致しない登録試行
        response = api_client.post(
            reverse('auth-api:register'),
            data={
                'email': 'mismatch@example.com',
                'password': 'password123',
                'password_confirmation': 'different456',  # 不一致
                'username': 'mismatchuser'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422, "Password mismatch must return 422"
        data = to_camel_case(response.data)
        assert data['status'] == 'fail'
        # エラーがdata内に存在することだけ確認（詳細は問わない）
        assert len(data['data']) > 0, "Should have validation errors"
        
        # ユーザーが作成されていないことを確認
        assert not User.objects.filter(email='mismatch@example.com').exists()

@pytest.mark.django_db
class TestTokenEdgeCases:
    """トークン関連のエッジケーステスト"""
    
    def test_blacklisted_refresh_token(self, api_client, test_user, csrf_token):
        """ブラックリスト済みトークンのテスト"""        
        # ログイン
        login_response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': test_user.email,
                'password': 'testpass123'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        
        # リフレッシュトークンを取得
        refresh_token = login_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        
        # 一度リフレッシュ（これでブラックリストに入る）
        refresh_response = api_client.post(
            reverse('auth-api:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert refresh_response.status_code == 200
        
        # 古いトークンで再度リフレッシュを試みる（ブラックリスト済み）
        # 古いトークンを明示的にセット
        api_client.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN] = refresh_token
        second_refresh_response = api_client.post(
            reverse('auth-api:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert second_refresh_response.status_code == 401
        data = to_camel_case(second_refresh_response.data)
        assert data['status'] == 'error'

@pytest.mark.django_db
class TestUserUpdateSecurity:
    """ユーザー更新のセキュリティテスト"""
    
    def test_user_update_without_csrf_returns_403(self, api_client, test_user, csrf_token):
        """CSRFトークンなしでユーザー更新 → 403エラー"""
        # ログイン
        login_response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': test_user.email,
                'password': 'testpass123'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        
        # CSRFトークンなしで更新を試みる
        update_response = api_client.patch(
            reverse('users-api:me'),
            data={
                'email': 'newemail@example.com'
            },
            format='json'
            # HTTP_X_CSRFTOKENを意図的に省略
        )
        assert update_response.status_code == 403
    
    def test_user_update_with_valid_csrf_succeeds(self, authenticated_api_client, test_user):
        """CSRFトークン付きでユーザー更新成功"""
        # 認証済みクライアントにはCSRFトークンが含まれている
        csrf_token = authenticated_api_client.csrf_token
                
        # CSRFトークン付きで更新
        update_response = authenticated_api_client.patch(
            reverse('users-api:me'),
            data={
                'email': 'updated@example.com'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert update_response.status_code == 200
        data = to_camel_case(update_response.data)
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'updated@example.com'
        
        # DBでも更新されていることを確認
        test_user.refresh_from_db()
        assert test_user.email == 'updated@example.com'
    
    def test_user_update_without_authentication_returns_401(self, api_client, csrf_token):
        """認証なしでユーザー更新 → 401エラー"""        
        # ログインせずに更新を試みる
        update_response = api_client.patch(
            reverse('users-api:me'),
            data={
                'email': 'unauthorized@example.com'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert update_response.status_code == 401
        data = to_camel_case(update_response.data)
        assert data['status'] == 'error'

@pytest.mark.django_db
class TestCookieSecurityIntegration:
    """Cookie設定の統合テスト"""
    
    def test_cookie_attributes_on_login(self, api_client, test_user, login_data, csrf_token):
        """ログイン時のCookie属性が正しく設定される"""        
        # ログイン
        response = api_client.post(
            reverse('auth-api:login'),
            data=login_data,
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 200
        
        # アクセストークンCookieの属性確認
        access_cookie = response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]
        assert access_cookie['httponly'] == settings.AUTH_COOKIE_HTTPONLY
        assert access_cookie['samesite'] == settings.AUTH_COOKIE_SAMESITE
        assert access_cookie['max-age'] == settings.AUTH_COOKIE_ACCESS_MAX_AGE
        # secure属性: テスト環境ではFalse、空文字列として返る場合がある
        if settings.AUTH_COOKIE_SECURE:
            assert access_cookie['secure'] is True
        else:
            # Falseの場合、空文字列またはFalseとして返る
            assert access_cookie.get('secure', '') in ['', False]

        # リフレッシュトークンCookieの属性確認
        refresh_cookie = response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN]
        assert refresh_cookie['httponly'] == settings.AUTH_COOKIE_HTTPONLY
        assert refresh_cookie['samesite'] == settings.AUTH_COOKIE_SAMESITE
        assert refresh_cookie['max-age'] == settings.AUTH_COOKIE_REFRESH_MAX_AGE
        # secure属性: テスト環境ではFalse
        if settings.AUTH_COOKIE_SECURE:
            assert refresh_cookie['secure'] is True
        else:
            assert refresh_cookie.get('secure', '') in ['', False]

    def test_csrf_cookie_attributes(self, api_client):
        """CSRF Cookieの属性が正しく設定される"""
        response = api_client.get(reverse('auth-api:csrf'))
        
        if settings.CSRF_COOKIE_NAME in response.cookies:
            csrf_cookie = response.cookies[settings.CSRF_COOKIE_NAME]
            
            # CSRFトークンはJavaScriptからアクセス可能である必要
            # CSRF_COOKIE_HTTPONLY = False なので、httponlyは空文字列またはFalse
            assert csrf_cookie.get('httponly', '') in ['', False], \
                "CSRF cookie must be accessible from JavaScript"
            
            # その他の属性
            assert csrf_cookie['samesite'] == settings.CSRF_COOKIE_SAMESITE
            
            # Secure属性は環境依存（テスト環境ではFalse）
            if settings.CSRF_COOKIE_SECURE:
                assert csrf_cookie['secure'] is True
            else:
                assert csrf_cookie.get('secure', '') in ['', False]

@pytest.mark.django_db
class TestErrorHandlingIntegration:
    """エラーハンドリングの統合テスト"""
    
    def test_malformed_json_returns_400(self, api_client, csrf_token):
        """不正なJSONは400エラー"""        
        response = api_client.post(
            reverse('auth-api:login'),
            data='{"invalid": json}', # 不正なJSON
            content_type='application/json',  # 明示的にContent-Type指定
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 400

        # ParseErrorはfailとして処理される
        data = to_camel_case(response.data)
        assert data['status'] == 'fail'
        assert 'detail' in data['data']

    
    def test_missing_required_fields(self, api_client, csrf_token):
        """必須フィールド不足は422エラーバリデーションエラー）"""        
        # passwordなしでログイン試行
        response = api_client.post(
            reverse('auth-api:login'),
            data={'email': 'test@example.com'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422
        data = to_camel_case(response.data)
        assert data['status'] == 'fail'
        assert 'password' in data['data']

        # 不正なメールフォーマット
        response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': 'invalid-email',  # 不正な形式
                'password': 'password123'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422
        data = to_camel_case(response.data)
        assert data['status'] == 'fail'
        assert 'email' in data['data']

    def test_method_not_allowed(self, api_client, csrf_token):
        """許可されていないHTTPメソッドは405エラー(error)"""
        # GETでログインエンドポイントにアクセス
        response = api_client.get(reverse('auth-api:login'))
        assert response.status_code == 405 

        # exceptions.pyによりJSend形式で返される
        data = to_camel_case(response.data)
        assert data['status'] == 'error'
        assert 'message' in data
        assert 'Method' in data['message'] or 'method' in data['message'].lower()
        
        # CSRFトークン付きでDELETEを送ると405が返る
        response = api_client.delete(
            reverse('auth-api:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 405
        data = to_camel_case(response.data)
        assert data['status'] == 'error'
