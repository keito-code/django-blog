import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client

User = get_user_model()

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
def client():
    """CSRF検証を有効にしたテストクライアント"""
    return Client(enforce_csrf_checks=True)

@pytest.fixture
def authenticated_client(client, test_user):
    """認証済みクライアント（統合テスト用）"""
    client.force_login(test_user)
    return client

@pytest.fixture
def csrf_token(client):
    """CSRFトークン取得（必須）"""
    response = client.get(reverse('accounts:csrf'))
    assert response.status_code == 200, (
        "CSRF endpoint MUST be implemented for multi-user blog system"
    )
    
    token = response.json().get('csrf_token')
    assert token, "CSRF token is required for security"
    
    return token



