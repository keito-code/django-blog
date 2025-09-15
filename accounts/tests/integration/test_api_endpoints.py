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
            'password_confirmation': 'validpass123',
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
        assert data['status'] == 'success'
        assert 'id' in data['data']
        assert 'date_joined' in data['data']
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
        assert login_data['status'] == 'success'
        assert 'id' in login_data['data']
        assert 'date_joined' in login_data['data']
        assert settings.AUTH_COOKIE_ACCESS_TOKEN in login_response.cookies
        assert settings.AUTH_COOKIE_REFRESH_TOKEN in login_response.cookies
        
        # トークンの値を保存
        initial_access = login_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        initial_refresh = login_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        
        time.sleep(1)

        # Cookieを明示的に設定（Django Test Clientの問題を回避）
        client.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN] = initial_access
        client.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN] = initial_refresh

        # 4. トークンリフレッシュ（CSRFあり）
        refresh_response = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert refresh_data['status'] == 'success'
        
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
        assert logout_data['status'] == 'success'
        
        # Cookieがクリアされたか確認
        assert logout_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN]['max-age'] == 0
        assert logout_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN]['max-age'] == 0
        
        # 6. ログアウト後はリフレッシュ不可（トークンが無効）
        post_logout_refresh = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert post_logout_refresh.status_code == 401
        post_logout_data = post_logout_refresh.json()
        assert post_logout_data['status'] == 'error'
    
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
        """既存ユーザーと同じメールでの登録は422エラー"""
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
                'password_confirmation': 'newpass123', 
                'username': 'differentuser'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422, "Duplicate email must return 422"
        
        # ユーザー数が増えていないことを確認
        assert User.objects.filter(email=test_user.email).count() == 1

    def test_password_mismatch_registration(self, client):
        """パスワード確認が一致しない場合の登録失敗テスト"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_data = csrf_response.json()
        csrf_token = csrf_data['data']['csrf_token']
        
        # パスワードが一致しない登録試行
        response = client.post(
            reverse('accounts:register'),
            data=json.dumps({
                'email': 'mismatch@example.com',
                'password': 'password123',
                'password_confirmation': 'different456',  # 不一致
                'username': 'mismatchuser'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422, "Password mismatch must return 422"
        data = response.json()
        assert data['status'] == 'fail'
        # エラーがdata内に存在することだけ確認（詳細は問わない）
        assert len(data['data']) > 0, "Should have validation errors"
        
        # ユーザーが作成されていないことを確認
        assert not User.objects.filter(email='mismatch@example.com').exists()

@pytest.mark.django_db
class TestTokenEdgeCases:
    """トークン関連のエッジケーステスト"""
    
    def test_blacklisted_refresh_token(self, client, test_user):
        """ブラックリスト済みトークンのテスト"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_token = csrf_response.json()['data']['csrf_token']
        
        # ログイン
        login_response = client.post(
            reverse('accounts:login'),
            data=json.dumps({
                'email': test_user.email,
                'password': 'testpass123'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        
        # リフレッシュトークンを取得
        refresh_token = login_response.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN].value
        
        # 一度リフレッシュ（これでブラックリストに入る）
        client.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN] = refresh_token
        refresh_response = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert refresh_response.status_code == 200
        
        # 同じトークンで再度リフレッシュを試みる（ブラックリスト済み）
        client.cookies[settings.AUTH_COOKIE_REFRESH_TOKEN] = refresh_token
        second_refresh_response = client.post(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert second_refresh_response.status_code == 401
        data = second_refresh_response.json()
        assert data['status'] == 'error'

@pytest.mark.django_db
class TestUserUpdateSecurity:
    """ユーザー更新のセキュリティテスト"""
    
    def test_user_update_without_csrf_returns_403(self, client, test_user):
        """CSRFトークンなしでユーザー更新 → 403エラー"""
        # ログイン
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_token = csrf_response.json()['data']['csrf_token']
        
        login_response = client.post(
            reverse('accounts:login'),
            data=json.dumps({
                'email': test_user.email,
                'password': 'testpass123'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        
        # CSRFトークンなしで更新を試みる
        update_response = client.patch(
            reverse('accounts:user'),
            data=json.dumps({
                'email': 'newemail@example.com'
            }),
            content_type='application/json'
            # HTTP_X_CSRFTOKENを意図的に省略
        )
        assert update_response.status_code == 403
    
    def test_user_update_with_valid_csrf_succeeds(self, client, test_user):
        """CSRFトークン付きでユーザー更新成功"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_token = csrf_response.json()['data']['csrf_token']
        
        # ログイン
        login_response = client.post(
            reverse('accounts:login'),
            data=json.dumps({
                'email': test_user.email,
                'password': 'testpass123'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert login_response.status_code == 200
        
        # アクセストークンをCookieに設定
        access_token = login_response.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN].value
        client.cookies[settings.AUTH_COOKIE_ACCESS_TOKEN] = access_token
        
        # CSRFトークン付きで更新
        update_response = client.patch(
            reverse('accounts:user'),
            data=json.dumps({
                'email': 'updated@example.com'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data['status'] == 'success'
        assert data['data']['email'] == 'updated@example.com'
        
        # DBでも更新されていることを確認
        test_user.refresh_from_db()
        assert test_user.email == 'updated@example.com'
    
    def test_user_update_without_authentication_returns_401(self, client):
        """認証なしでユーザー更新 → 401エラー"""
        # CSRFトークン取得
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_token = csrf_response.json()['data']['csrf_token']
        
        # ログインせずに更新を試みる
        update_response = client.patch(
            reverse('accounts:user'),
            data=json.dumps({
                'email': 'unauthorized@example.com'
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert update_response.status_code == 401
        data = update_response.json()
        assert data['status'] == 'error'

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

    def test_csrf_cookie_attributes(self, client):
        """CSRF Cookieの属性が正しく設定される"""
        response = client.get(reverse('accounts:csrf'))
        
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

        # カスタムエクセプションハンドラーによりJSend形式で返される
        data = response.json()
        assert data['status'] == 'error'

    def test_method_not_allowed(self, client):
        """許可されていないHTTPメソッドは405エラー"""
        # GETでログインエンドポイントにアクセス（CSRFチェック不要）
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 405 

        # exceptions.pyによりJSend形式で返される
        data = response.json()
        assert data['status'] == 'error'
        assert 'Method' in data['message'] or 'method' in data['message']
        
        # CSRFトークン付きでDELETEを送ると405が返る
        csrf_response = client.get(reverse('accounts:csrf'))
        csrf_token = csrf_response.json()['data']['csrf_token']

        response = client.delete(
            reverse('accounts:refresh'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 405
        data = response.json()
        assert data['status'] == 'error'
    
    def test_missing_required_fields(self, client):
        """必須フィールド不足は422エラーバリデーションエラー）"""
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
        assert response.status_code == 422
        data = response.json()
        assert data['status'] == 'fail'
        assert 'password' in data['data']