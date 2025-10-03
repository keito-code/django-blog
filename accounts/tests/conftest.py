"""
テスト用フィクスチャ設定

このプロジェクトはDjango REST API + Next.jsの構成のため、
APIレスポンスはCamelCaseで統一している。

重要な注意点：
- APIClientはPythonの辞書（snake_case）を返す
- 実際のHTTPレスポンスはJSendCamelCaseRendererによりCamelCaseに変換される
- settings/base.pyのJSendCamelCaseRendererはAPIClient使用時にはバイパスされる
- テストでは実際のレスポンス形式に合わせるため、camelize()を使用
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from djangorestframework_camel_case.util import camelize


User = get_user_model()

# ===== ヘルパー関数 =====

def to_camel_case(data):
    """APIClientのsnake_caseレスポンスをCamelCaseに変換"""
    if isinstance(data, dict):
        return camelize(data)
    elif hasattr(data, 'items'):
        return camelize(dict(data))
    else:
        return data

# ===== 基本フィクスチャ =====

@pytest.fixture
def test_user(db):
    """基本のテストユーザー"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def login_data():
    """ログイン用のテストデータ"""
    return {
        'email': 'test@example.com',
        'password': 'testpass123'
    }

@pytest.fixture
def another_user(db):
    """重複チェックテスト用の別ユーザー"""
    return User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='anotherpass123'
    )

# ===== APIClient（DRF APIテスト用） =====

@pytest.fixture
def api_client():
    """CSRF検証を有効にしたAPIクライアント（DRF用）"""
    return APIClient(enforce_csrf_checks=True)

@pytest.fixture
def csrf_token(api_client):
    """CSRFトークン取得（必須）"""
    response = api_client.get(reverse('auth-api:csrf'))
    assert response.status_code == 200, (
        "CSRF endpoint MUST be implemented for multi-user blog system"
    )

    data = to_camel_case(response.data)
    token = data['data']['csrfToken']
    assert token, "CSRF token is required for security"
    
    return token

@pytest.fixture
def authenticated_api_client(api_client, test_user, csrf_token):
    """認証済みクライアント（Cookie認証）
    JWTトークンがHttpOnly Cookieとして設定される。
    DRFのAPIClientはCookieを自動的に保持するため、
    以降のリクエストで認証が維持される。
    """
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
    
    assert login_response.status_code == 200, (
        f"Login failed: {to_camel_case(login_response.data)}"
    )
    
    # CSRFトークンも属性として保存（便利のため）
    api_client.csrf_token = csrf_token
    
    return api_client




